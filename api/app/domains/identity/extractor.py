"""Extractors: the real Claude call + a deterministic offline fallback.

Both take (user_message, prior_extraction) and return a fresh Extraction of what
THIS message revealed. The router merges it into session state.
"""
from __future__ import annotations
import re

from ...config import get_settings
from .schema import (
    Extraction, ASPIRATION_VOCAB, INSECURITY_VOCAB,
)

settings = get_settings()



def get_extractor():
    """Real LLM extractor when a provider is configured; deterministic otherwise."""
    from ...core import llm
    if llm.available():
        return LLMExtractor()
    return HeuristicExtractor()


# ── deterministic fallback (keyword/phrase extraction) ───────────────────────
_ASPIRATION_CUES = {
    "authoritative": ["authorit", "taken seriously", "in charge", "command", "respect", "powerful", "boss", "lead"],
    "approachable":  ["approachable", "friendly", "warm", "easy to talk", "relatable", "down to earth"],
    "creative":      ["creative", "artistic", "expressive", "stand out", "original", "unique"],
    "polished":      ["polished", "put together", "sharp", "professional", "clean", "sophisticat", "elegant"],
}
_INSECURITY_CUES = {
    "arms": ["arms", "upper arm"],
    "midsection": ["stomach", "midsection", "belly", "tummy", "waist area", "middle"],
    "legs": ["legs", "thighs", "calves"],
}


class HeuristicExtractor:
    name = "heuristic"

    def extract(self, message: str, prior: Extraction) -> Extraction:
        m = message.lower()
        e = Extraction()

        for asp, cues in _ASPIRATION_CUES.items():
            if any(c in m for c in cues):
                e.aspirations.append(asp)
        for area, cues in _INSECURITY_CUES.items():
            if any(c in m for c in cues):
                e.insecurities.append(area)

        if any(w in m for w in ["on my feet", "moving", "standing", "walk", "active", "nurse", "retail", "warehouse"]):
            e.activity_level = "on_feet"
        elif any(w in m for w in ["desk", "sitting", "office", "computer", "zoom", "remote"]):
            e.activity_level = "desk"

        if any(w in m for w in ["struggle", "hard", "stressful", "overwhelm", "hate", "difficult", "anxious", "never know"]):
            e.confidence_baseline = 0.3
        elif any(w in m for w in ["easy", "love", "enjoy", "confident", "fun", "no problem"]):
            e.confidence_baseline = 0.75

        if any(w in m for w in ["risk", "bold", "experiment", "adventurous", "try new"]):
            e.risk_tolerance = 0.7
        elif any(w in m for w in ["safe", "simple", "classic", "conservative", "stick to"]):
            e.risk_tolerance = 0.2

        return e


# ── real Claude extractor (prod) ─────────────────────────────────────────────
_SYSTEM = """You are the onboarding interviewer for a personal styling app.
Extract ONLY what the user's latest message reveals into this JSON schema; use
null / [] for anything not stated. Never infer beyond the text.

{
  "aspirations": [subset of: authoritative, approachable, creative, polished],
  "insecurities": [subset of: arms, midsection, legs],
  "activity_level": "desk" | "on_feet" | null,
  "work_setting": string | null,
  "risk_tolerance": 0.0-1.0 | null,
  "confidence_baseline": 0.0-1.0 | null
}
Return ONLY the JSON object, no prose."""


class LLMExtractor:
    name = "llm"

    def extract(self, message: str, prior: Extraction) -> Extraction:
        import json
        from ...core import llm
        text = llm.complete(
            _SYSTEM, [{"role": "user", "content": message}],
            model=llm.model_for("coach"), max_tokens=400, fallback="",
        )
        if not text:
            return HeuristicExtractor().extract(message, prior)
        try:
            return _coerce(json.loads(_strip_fences(text)))
        except Exception:
            return HeuristicExtractor().extract(message, prior)


def _strip_fences(t: str) -> str:
    t = re.sub(r"^```(json)?", "", t.strip())
    return re.sub(r"```$", "", t.strip()).strip()


def _coerce(data: dict) -> Extraction:
    return Extraction(
        aspirations=[a for a in data.get("aspirations", []) if a in ASPIRATION_VOCAB],
        insecurities=[i for i in data.get("insecurities", []) if i in INSECURITY_VOCAB],
        activity_level=data.get("activity_level") if data.get("activity_level") in ("desk", "on_feet") else None,
        work_setting=data.get("work_setting"),
        risk_tolerance=_clamp(data.get("risk_tolerance")),
        confidence_baseline=_clamp(data.get("confidence_baseline")),
    )


def _clamp(v):
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return None
