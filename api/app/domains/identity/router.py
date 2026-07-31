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
from .schema import Extraction, OPENING, next_question
from .extractor import get_extractor

router = APIRouter(prefix="/v1", tags=["identity"])

# short-lived session store (onboarding lasts a handful of turns).
# swap for Redis in prod; in-memory is fine for a single-process dev/test run.
_SESSIONS: dict[str, dict] = {}


@router.post("/onboarding/sessions", status_code=201)
def start_session(user: User = Depends(get_current_user)):
    sid = str(uuid.uuid4())
    _SESSIONS[sid] = {"user_id": str(user.id), "extraction": Extraction(), "turns": 0}
    return {"session_id": sid, "question": OPENING, "complete": False}


@router.post("/onboarding/sessions/{sid}/messages")
def turn(sid: str, payload: dict, db: Session = Depends(get_db),
         user: User = Depends(get_current_user)):
    sess = _SESSIONS.get(sid)
    if not sess or sess["user_id"] != str(user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Empty message")

    extractor = get_extractor()
    revealed = extractor.extract(message, sess["extraction"])
    merged: Extraction = sess["extraction"].merge(revealed)
    sess["extraction"] = merged
    sess["turns"] += 1

    q = next_question(merged)
    # complete as soon as the REQUIRED fields are in. next_question may still
    # offer optional refinements (insecurities/risk), but those never block
    # completion — a turn cap also forces completion for a vague user.
    required_done = merged.is_complete()
    complete = required_done or sess["turns"] >= 6

    if complete:
        _persist(db, user, merged)
        _SESSIONS.pop(sid, None)
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
    for field in ("style_aspirations", "insecurities", "lifestyle_patterns", "psychological_traits"):
        if field in payload:
            setattr(ip, field, payload[field])
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
