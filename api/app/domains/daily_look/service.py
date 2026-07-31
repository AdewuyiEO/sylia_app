"""Daily Look service: assemble context → score (deterministic) → explain.

Translates DB rows into the pure scorer's dataclasses, runs the scorer, and
(in prod) hands ONLY the winning score_breakdown to Claude for a one-sentence
explanation. Claude never chooses; it narrates a decision the scorer made.
"""
from __future__ import annotations
from typing import Any

from ...config import get_settings
from .scorer import (
    Garment, BodyProfile, ColorPalette, IdentityProfile, Context,
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
    )


def build_looks(items: list[Any], body_row: Any | None, identity_row: Any | None,
                weather: dict, calendar_signal: int, *, top_n: int = 3,
                seed: int = 0) -> list[Candidate]:
    wardrobe = [_garment_from_row(i) for i in items if i.is_active]
    body = _body_from_row(body_row)
    identity = _identity_from_row(identity_row)
    ctx = Context(
        temp_f=float(weather.get("temp_f", 68)),
        formality_signal=int(calendar_signal),
        precipitation=bool(weather.get("precipitation", False)),
        context_kind=weather.get("context_kind", "work"),
    )
    return generate_daily_looks(wardrobe, body, identity, ctx, top_n=top_n, seed=seed)


def explain(breakdown: dict, *, context: dict | None = None, pieces: list | None = None) -> str:
    """Turn the winning score_breakdown into a 1–2 sentence rationale.

    Prod: a single cached Claude call (spec §4.4) — the static styling-voice
    preamble is prompt-cached; only the per-look breakdown varies. Offline (no
    key): a deterministic template. Both describe the SAME real subscores, so the
    'Claude explains, never chooses' invariant holds either way.
    """
    template = _template_explain(breakdown)

    from ...core import llm
    if not llm.available():
        return template

    system = (
        "You write one short, warm sentence explaining why an outfit suits "
        "someone, for a personal styling app. You are given the outfit's score "
        "breakdown (context/color/body/identity, 0-100) and the day's context. "
        "Explain the pick in plain language grounded in those numbers. Never "
        "invent facts not implied by the scores. No more than 25 words. No emoji."
    )
    facts = {"breakdown": breakdown, "context": context or {},
             "pieces": [getattr(p, "subcategory", str(p)) for p in (pieces or [])]}
    import json
    user = ("Write the explanation for this look.\n" + json.dumps(facts))
    return llm.complete(
        system, [{"role": "user", "content": user}],
        model=llm.model_for('explanation'), max_tokens=80, fallback=template,
    )


def _template_explain(breakdown: dict) -> str:
    parts = []
    if breakdown.get("context", 0) >= 70:
        parts.append("matches today's weather and your schedule")
    if breakdown.get("identity", 0) >= 70:
        parts.append("leans into how you want to show up")
    if breakdown.get("color", 0) >= 70:
        parts.append("sits in your palette")
    body_part = "and works with your fit rules" if breakdown.get("body", 0) >= 70 else ""
    lead = ", ".join(parts) if parts else "a balanced pick from your closet"
    return f"This look {lead} {body_part}".strip().rstrip(",") + "."
