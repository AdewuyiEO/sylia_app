"""Identity engine — structured extraction from a text-first conversation (spec §3.2).

The onboarding is a short chat: Claude asks, the user answers freely, and each
turn Claude EXTRACTS structured fields into the identity schema and decides the
next question. "Progressive unlock" = we only ask what's still missing, and we
stop once the required fields are filled (so a talkative user finishes in 3 turns,
a terse one in 6).

Two implementations behind one interface:
  * `LLMExtractor` — the real Anthropic call (structured JSON extraction +
    next-question selection), prompt-cached identity preamble. Used in prod.
  * `HeuristicExtractor` — deterministic keyword/regex extraction, no network.
    Used when no ANTHROPIC_API_KEY is set and in every test, so the whole
    onboarding flow (state machine, completion, persistence) is verifiable offline.

Both return the same `Extraction` shape, so the router and persistence never know
which ran.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

# ── the identity schema we extract into ──────────────────────────────────────
# required-to-complete fields (progressive unlock stops when these are present)
REQUIRED = ("aspirations", "activity_level", "confidence_baseline")

# vocabularies the scorer understands (must match scorer/ASPIRATION_RULES etc.)
ASPIRATION_VOCAB = {"authoritative", "approachable", "creative", "polished"}
INSECURITY_VOCAB = {"arms", "midsection", "legs"}
ACTIVITY_VOCAB = {"desk", "on_feet"}


@dataclass
class Extraction:
    aspirations: list[str] = field(default_factory=list)      # subset of ASPIRATION_VOCAB
    insecurities: list[str] = field(default_factory=list)     # subset of INSECURITY_VOCAB
    activity_level: str | None = None                         # desk | on_feet
    work_setting: str | None = None
    risk_tolerance: float | None = None                       # 0-1
    confidence_baseline: float | None = None                  # 0-1

    def merge(self, other: "Extraction") -> "Extraction":
        """Later turns fill gaps / extend lists; scalars set once, don't overwrite."""
        return Extraction(
            aspirations=_union(self.aspirations, other.aspirations),
            insecurities=_union(self.insecurities, other.insecurities),
            activity_level=self.activity_level or other.activity_level,
            work_setting=self.work_setting or other.work_setting,
            risk_tolerance=self.risk_tolerance if self.risk_tolerance is not None else other.risk_tolerance,
            confidence_baseline=self.confidence_baseline if self.confidence_baseline is not None else other.confidence_baseline,
        )

    def missing_required(self) -> list[str]:
        out = []
        if not self.aspirations: out.append("aspirations")
        if not self.activity_level: out.append("activity_level")
        if self.confidence_baseline is None: out.append("confidence_baseline")
        return out

    def is_complete(self) -> bool:
        return not self.missing_required()

    def to_profile(self) -> dict:
        """Shape the identity_profiles columns expect."""
        return {
            "style_aspirations": [{"label": a, "priority": i + 1}
                                  for i, a in enumerate(self.aspirations)],
            "insecurities": [{"area": a} for a in self.insecurities],
            "lifestyle_patterns": {
                "activity_level": self.activity_level or "desk",
                "work_setting": self.work_setting,
            },
            "psychological_traits": {
                "confidence_baseline": self.confidence_baseline if self.confidence_baseline is not None else 0.5,
                "risk_tolerance": self.risk_tolerance if self.risk_tolerance is not None else 0.3,
            },
        }

    def as_dict(self) -> dict:
        return asdict(self)


def _union(a: list, b: list) -> list:
    return list(dict.fromkeys([*a, *b]))


# ── question bank (progressive unlock) ───────────────────────────────────────
QUESTIONS: dict[str, str] = {
    "aspirations": "When you walk into a room, how do you want to come across?",
    "activity_level": "What does a typical work day look like — mostly at a desk, or on your feet and moving?",
    "confidence_baseline": "How do you feel about getting dressed most mornings — is it easy, or a bit of a struggle?",
    "insecurities": "Is there anything you'd rather I steer away from suggesting?",
    "risk_tolerance": "Do you like to play it safe with outfits, or enjoy taking a few risks?",
}
OPENING = QUESTIONS["aspirations"]


def next_question(extraction: Extraction) -> str | None:
    """Ask for the most important still-missing thing; required first, then nice-to-have."""
    for key in ("aspirations", "activity_level", "confidence_baseline",
                "insecurities", "risk_tolerance"):
        if key == "aspirations" and not extraction.aspirations:
            return QUESTIONS[key]
        if key == "activity_level" and not extraction.activity_level:
            return QUESTIONS[key]
        if key == "confidence_baseline" and extraction.confidence_baseline is None:
            return QUESTIONS[key]
        if key == "insecurities" and not extraction.insecurities and extraction.is_complete():
            return QUESTIONS[key]
        if key == "risk_tolerance" and extraction.risk_tolerance is None and extraction.is_complete():
            return QUESTIONS[key]
    return None
