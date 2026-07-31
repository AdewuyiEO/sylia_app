"""Style coach context assembly (spec §3.6, §4.4).

Builds the RAG preamble the coach reasons over: the user's identity, a compact
wardrobe summary, their palette/fit rules, and recent outfits. This block is
large and mostly static between messages, so it's the thing we prompt-cache —
only the new user turn varies. Kept pure/DB-reading so it's testable.
"""
from __future__ import annotations
from collections import Counter
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import ClothingItem, BodyProfile, IdentityProfile, Outfit


def build_context_preamble(db: Session, user_id) -> str:
    items = list(db.scalars(select(ClothingItem).where(
        ClothingItem.user_id == user_id, ClothingItem.is_active == True)))  # noqa: E712
    body = db.scalar(select(BodyProfile).where(BodyProfile.user_id == user_id))
    ident = db.scalar(select(IdentityProfile).where(IdentityProfile.user_id == user_id))

    lines = [
        "You are Sylia, a warm, concise personal style coach. You help with "
        "outfit feedback, packing, and wardrobe optimisation. Ground every "
        "suggestion in the wardrobe and profile below — recommend things the "
        "user OWNS first; only suggest buying to fill a genuine gap. Keep replies "
        "short and practical. Never comment negatively on the user's body.",
        "",
        "## The user's profile",
    ]

    if ident:
        asp = ", ".join(a.get("label", "") for a in (ident.style_aspirations or [])) or "unspecified"
        ins = ", ".join(i.get("area", "") for i in (ident.insecurities or [])) or "none noted"
        life = ident.lifestyle_patterns or {}
        lines += [f"- Wants to come across as: {asp}",
                  f"- Prefers to steer away from emphasising: {ins}",
                  f"- Lifestyle: {life.get('activity_level', 'desk')} work setting"]
    else:
        lines.append("- (identity onboarding not completed yet)")

    if body:
        pal = body.color_palette or {}
        lines += [f"- Silhouette: {body.silhouette_category or 'unknown'}; "
                  f"undertone: {body.skin_undertone or 'unknown'}",
                  f"- Best colours: {', '.join(pal.get('best_colors', [])) or 'neutral-leaning'}",
                  f"- Fit rules: {', '.join(body.fit_rules or []) or 'none'}"]

    lines += ["", "## Wardrobe summary", _wardrobe_summary(items)]

    recent = list(db.scalars(select(Outfit).where(Outfit.user_id == user_id)
                             .order_by(Outfit.created_at.desc()).limit(5)))
    if recent:
        worn = [o for o in recent if o.user_feedback == "worn"]
        lines += ["", f"## Recently worn: {len(worn)} of last {len(recent)} looks logged as worn"]

    return "\n".join(lines)


def _wardrobe_summary(items: list) -> str:
    if not items:
        return "- (empty closet)"
    by_cat = Counter(i.category for i in items)
    colors = Counter(i.primary_color for i in items if i.primary_color)
    cat_line = ", ".join(f"{n} {c}{'s' if n > 1 else ''}" for c, n in by_cat.items())
    color_line = ", ".join(c for c, _ in colors.most_common(6))
    return f"- {len(items)} items: {cat_line}\n- Main colours: {color_line}"


COACH_FALLBACK = (
    "I can help with that once the style coach is fully online. In the meantime, "
    "a safe move from your closet: pair your most-worn neutral bottom with a top "
    "in one of your best colours, and keep accessories minimal."
)
