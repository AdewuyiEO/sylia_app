"""Identity Engine (spec §3.2) — text-first conversational onboarding.

A short chat that extracts a structured identity profile via progressive unlock:
ask only what's still missing, stop when the required fields are filled, persist
to identity_profiles. Uses the real Claude extractor when a key is set, else a
deterministic one — the flow is identical either way.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db import get_db
from ...deps import get_current_user
from ...models import User, IdentityProfile
from ...core.kv import kv
from .schema import Extraction, OPENING, next_question
from .extractor import get_extractor

router = APIRouter(prefix="/v1", tags=["identity"])

# onboarding sessions live in the shared KV store (Redis in prod) so any API
# instance can serve the next turn; they expire if abandoned.
_SESSION_TTL = 2 * 3600


def _load(sid: str) -> dict | None:
    raw = kv.get(f"onboarding:{sid}")
    if raw is None:
        return None
    return {**raw, "extraction": Extraction(**raw["extraction"])}


def _save(sid: str, sess: dict) -> None:
    kv.set(f"onboarding:{sid}", {**sess, "extraction": sess["extraction"].as_dict()}, ttl=_SESSION_TTL)


@router.post("/onboarding/sessions", status_code=201)
def start_session(user: User = Depends(get_current_user)):
    sid = str(uuid.uuid4())
    _save(sid, {"user_id": str(user.id), "extraction": Extraction(), "turns": 0})
    return {"session_id": sid, "question": OPENING, "complete": False}


@router.post("/onboarding/sessions/{sid}/messages")
def turn(sid: str, payload: dict, db: Session = Depends(get_db),
         user: User = Depends(get_current_user)):
    sess = _load(sid)
    if not sess or sess["user_id"] != str(user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(422, "Empty message")

    extractor = get_extractor()
    revealed = extractor.extract(message, sess["extraction"])
    merged: Extraction = sess["extraction"].merge(revealed)
    sess["extraction"] = merged
    sess["turns"] += 1

    _save(sid, sess)
    q = next_question(merged)
    # complete as soon as the REQUIRED fields are in. next_question may still
    # offer optional refinements (insecurities/risk), but those never block
    # completion — a turn cap also forces completion for a vague user.
    required_done = merged.is_complete()
    complete = required_done or sess["turns"] >= 6

    if complete:
        _persist(db, user, merged)
        kv.delete(f"onboarding:{sid}")
        return {"session_id": sid, "complete": True, "question": None,
                "extracted": merged.as_dict(),
                "message": "Got it — your style profile is set. You can refine it anytime."}

    return {"session_id": sid, "complete": False, "question": q,
            "extracted": merged.as_dict(), "turns": sess["turns"]}


@router.get("/identity-profile")
def get_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ip = db.query(IdentityProfile).filter(IdentityProfile.user_id == user.id).first()
    if ip is None:
        return {"exists": False}
    return {"exists": True, "aspirations": ip.style_aspirations,
            "insecurities": ip.insecurities, "lifestyle_patterns": ip.lifestyle_patterns,
            "psychological_traits": ip.psychological_traits,
            "completed": ip.onboarding_completed_at is not None}


@router.patch("/identity-profile")
def patch_profile(payload: dict, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """Direct edits (the user can always correct what the interview inferred)."""
    ip = db.query(IdentityProfile).filter(IdentityProfile.user_id == user.id).first()
    if ip is None:
        ip = IdentityProfile(user_id=user.id)
        db.add(ip)
    for field, kind in (("style_aspirations", list), ("insecurities", list),
                        ("lifestyle_patterns", dict), ("psychological_traits", dict)):
        if field in payload:
            if not isinstance(payload[field], kind):
                raise HTTPException(422, f"{field} must be a {kind.__name__}")
            setattr(ip, field, payload[field])
    coverage = (ip.lifestyle_patterns or {}).get("coverage")
    if coverage not in (None, "standard", "modest"):
        raise HTTPException(422, "coverage must be standard or modest")
    db.commit()
    return {"updated": True}


def _persist(db: Session, user: User, extraction: Extraction) -> None:
    ip = db.query(IdentityProfile).filter(IdentityProfile.user_id == user.id).first()
    if ip is None:
        ip = IdentityProfile(user_id=user.id)
        db.add(ip)
    prof = extraction.to_profile()
    ip.style_aspirations = prof["style_aspirations"]
    ip.insecurities = prof["insecurities"]
    ip.lifestyle_patterns = prof["lifestyle_patterns"]
    ip.psychological_traits = prof["psychological_traits"]
    ip.onboarding_completed_at = datetime.now(timezone.utc)
    db.commit()
