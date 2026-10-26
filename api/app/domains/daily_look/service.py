"""Daily Look service: assemble context → score (deterministic) → explain.

Translates DB rows into the pure scorer's dataclasses, runs the scorer, and
(in prod) hands ONLY the winning score_breakdown to Claude for a one-sentence
explanation. Claude never chooses; it narrates a decision the scorer made.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .scorer import (
    Garment, BodyProfile, ColorPalette, IdentityProfile, Context, WornRecord,
    generate_daily_looks, Candidate,
)


def _garment_from_row(item: Any) -> Garment:
    return Garment(
        id=str(item.id),
        category=item.category,
        subcategory=item.subcategory or "",
        primary_color=item.primary_color or "",
        secondary_color=item.secondary_color,
        pattern=item.pattern or "solid",
        fit=item.fit or "regular",
        formality_score=int(item.formality_score or 3),
        warmth_score=int(item.warmth_score or 3),
        tags=list(item.tags or []),
    )


def _body_from_row(bp: Any | None) -> BodyProfile:
    if bp is None:
        return BodyProfile()
    pal = bp.color_palette or {}
    return BodyProfile(
        silhouette_category=bp.silhouette_category or "rectangle",
        skin_undertone=bp.skin_undertone or "neutral",
        palette=ColorPalette(
            best_colors=pal.get("best_colors", []),
            avoid_colors=pal.get("avoid_colors", []),
            neutrals=pal.get("neutrals", []),
        ),
        fit_rules=list(bp.fit_rules or []),
    )


def _identity_from_row(ip: Any | None) -> IdentityProfile:
    if ip is None:
        return IdentityProfile()
    traits = ip.psychological_traits or {}
    life = ip.lifestyle_patterns or {}
    return IdentityProfile(
        aspirations=[a["label"] for a in (ip.style_aspirations or []) if "label" in a],
        insecurities=[i["area"] for i in (ip.insecurities or []) if "area" in i],
        activity_level=life.get("activity_level", "desk"),
        risk_tolerance=float(traits.get("risk_tolerance", 0.3)),
        confidence_baseline=float(traits.get("confidence_baseline", 0.5)),
        coverage=life.get("coverage") or "standard",
    )


def build_looks(items: list[Any], body_row: Any | None, identity_row: Any | None,
                context: dict, *, recent: list[WornRecord] | None = None, top_n: int = 3,
                seed: int = 0, exclude_ids: set[str] | None = None,
                exclude_signatures: set | None = None) -> list[Candidate]:
    """context: {"weather": {...}, "calendar": {"formality_category": n}, "context_kind": ...}"""
    wardrobe = [_garment_from_row(i) for i in items if i.is_active]
    body = _body_from_row(body_row)
    identity = _identity_from_row(identity_row)
    weather = context.get("weather") or {}
    ctx = Context(
        temp_f=float(weather.get("temp_f", 68)),
        formality_signal=int((context.get("calendar") or {}).get("formality_category", 3)),
        precipitation=bool(weather.get("precipitation", False)),
        context_kind=context.get("context_kind", "work"),
    )
    return generate_daily_looks(wardrobe, body, identity, ctx, recent=recent, top_n=top_n,
                                seed=seed, exclude_ids=exclude_ids,
                                exclude_signatures=exclude_signatures)


def local_today(user: Any) -> date:
    """The user's calendar day in their own timezone (worldwide users)."""
    tz_name = getattr(user, "timezone", None)
    if tz_name:
        try:
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo(tz_name)).date()
        except Exception:
            pass
    return datetime.now(timezone.utc).date()


def context_kind(day: date, formality: int, driver: str | None) -> str:
    """Weekend unless the calendar says there's something to dress up for."""
    if day.weekday() >= 5 and (driver is None or formality <= 3):
        return "weekend"
    return "work"


def wear_stats(db, user, today: date) -> dict:
    """North-star + closet health numbers for the You tab.

    WWO = distinct days in the last 7 with a look logged as worn.
    """
    from sqlalchemy import select
    from ...models import Outfit, OutfitItem, ClothingItem

    worn = list(db.execute(
        select(Outfit.outfit_date, OutfitItem.clothing_item_id)
        .join(OutfitItem, OutfitItem.outfit_id == Outfit.id)
        .where(Outfit.user_id == user.id, Outfit.user_feedback == "worn",
               Outfit.outfit_date > today - timedelta(days=90))))
    days = {d for d, _ in worn}
    wwo = len({d for d in days if d > today - timedelta(days=7)})

    streak, d = 0, today
    if d not in days:
        d -= timedelta(days=1)          # today not logged yet doesn't break a streak
    while d in days:
        streak += 1
        d -= timedelta(days=1)

    active = list(db.scalars(select(ClothingItem).where(
        ClothingItem.user_id == user.id, ClothingItem.is_active == True)))  # noqa: E712
    worn_30 = {iid for dd, iid in worn if dd > today - timedelta(days=30)}
    counts: dict = {}
    for _, iid in worn:
        counts[iid] = counts.get(iid, 0) + 1
    by_id = {i.id: i for i in active}
    top = sorted(((n, iid) for iid, n in counts.items() if iid in by_id), reverse=True)[:5]
    return {
        "weekly_worn_outfits": wwo,
        "streak_days": streak,
        "closet_size": len(active),
        "closet_utilization_30d": round(len(worn_30 & set(by_id)) / len(active), 2) if active else 0.0,
        "never_worn": sum(1 for i in active if i.id not in counts),
        "most_worn": [{"item_id": str(iid), "subcategory": by_id[iid].subcategory,
                       "primary_color": by_id[iid].primary_color, "times_worn": n} for n, iid in top],
    }


def explain(breakdown: dict, *, context: dict | None = None, pieces: list | None = None,
            locale: str | None = None) -> str:
    """Turn the winning score_breakdown into a 1–2 sentence rationale.

    Prod: a single cached Claude call (spec §4.4) — the static styling-voice
    preamble is prompt-cached; only the per-look breakdown varies. Offline (no
    key): a deterministic template. Both describe the SAME real subscores, so the
    'Claude explains, never chooses' invariant holds either way.
    """
    template = _template_explain(breakdown, locale)

    from ...core import llm
    if not llm.available():
        return template

    system = (
        "You write one short, warm sentence explaining why an outfit suits "
        "someone, for a personal styling app. You are given the outfit's score "
        "breakdown (context/color/body/identity, 0-100) and the day's context. "
        "Explain the pick in plain language grounded in those numbers. Never "
        "invent facts not implied by the scores. No more than 25 words. No emoji. "
        "Write in the language of the given locale."
    )
    facts = {"breakdown": breakdown, "context": _explain_context(context),
             "pieces": [getattr(p, "subcategory", str(p)) for p in (pieces or [])],
             "locale": locale or "en"}
    import json
    user = "Write the explanation for this look.\n" + json.dumps(facts)
    return llm.complete(
        system, [{"role": "user", "content": user}],
        model=llm.model_for('explanation'), max_tokens=80, fallback=template,
    )


# phrasebook for the no-LLM template, per language (falls back to English)
_PHRASES = {
    "en": {"context": "suits today's weather and plans", "identity": "leans into how you want to come across",
           "color": "sits in your palette", "body": "works with your fit rules",
           "lead": "This look {parts}.", "and": "and", "default": "A balanced pick from your closet for today."},
    "fr": {"context": "convient à la météo et au programme du jour", "identity": "reflète l'image que vous voulez donner",
           "color": "reste dans votre palette", "body": "respecte vos règles de coupe",
           "lead": "Cette tenue {parts}.", "and": "et", "default": "Un choix équilibré dans votre dressing pour aujourd'hui."},
    "es": {"context": "encaja con el tiempo y los planes de hoy", "identity": "refleja cómo quieres que te vean",
           "color": "está dentro de tu paleta", "body": "respeta tus reglas de corte",
           "lead": "Este look {parts}.", "and": "y", "default": "Una elección equilibrada de tu armario para hoy."},
}


def phrases(locale: str | None) -> dict:
    return _PHRASES.get((locale or "en").split("-")[0].lower(), _PHRASES["en"])


def join_list(items: list[str], conj: str) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} {conj} {items[-1]}"


def _template_explain(breakdown: dict, locale: str | None = None) -> str:
    ph = phrases(locale)
    parts = [ph[k] for k in ("context", "identity", "color", "body") if breakdown.get(k, 0) >= 70]
    if not parts:
        return ph["default"]
    return ph["lead"].format(parts=join_list(parts, ph["and"]))


def _explain_context(context: dict | None) -> dict:
    """Only the facts the explanation may mention (no tokens, ids or raw payloads)."""
    if not context:
        return {}
    w = context.get("weather") or {}
    cal = context.get("calendar") or {}
    return {"temp_c": w.get("temp_c"), "temp_f": w.get("temp_f"),
            "precipitation": w.get("precipitation"), "occasion": cal.get("driver"),
            "formality": cal.get("formality_category"), "day": context.get("context_kind")}
