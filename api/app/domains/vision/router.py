"""Vision & Body (spec §3.3). Camera path is async (job handle); quiz fallback is
sync and persists directly. Both write to body_profiles; the quiz is treated as a
confident source, not a degraded one."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...db import get_db
from ...deps import get_current_user
from ...models import User, BodyProfile
from ...core.jobs import jobs
from ...workers import tasks
from .analysis.pipeline import analyze_from_quiz

router = APIRouter(prefix="/v1", tags=["vision"])


@router.post("/body-scan", status_code=202)
def body_scan(payload: dict, user: User = Depends(get_current_user)):
    """Register uploaded front/side/face photo keys; enqueue geometry + undertone."""
    job = jobs.create("body_scan", user_id=str(user.id))
    tasks.analyze_body.delay(job.id, str(user.id), payload.get("s3_keys", []))
    return {"job_id": job.id, "status": job.status}


@router.get("/body-scan/jobs/{job_id}")
def body_scan_status(job_id: str, user: User = Depends(get_current_user)):
    job = jobs.get(job_id)
    return {"job_id": job_id, "status": job.status if job else "unknown",
            "result": job.result if job else None}


@router.post("/body-profile/quiz-fallback")
def quiz_fallback(payload: dict, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """Non-camera path: swatch-picker undertone + self-reported shape. Self-report
    is often MORE reliable than a photo heuristic, so this is a confident result."""
    analysis = analyze_from_quiz(payload.get("undertone"), payload.get("silhouette"))

    bp = db.query(BodyProfile).filter(BodyProfile.user_id == user.id).first()
    if bp is None:
        bp = BodyProfile(user_id=user.id)
        db.add(bp)
    bp.silhouette_category = analysis.silhouette_category
    bp.skin_undertone = analysis.skin_undertone
    bp.color_palette = analysis.color_palette
    bp.fit_rules = analysis.fit_rules
    bp.analysis_method = "quiz_fallback"
    bp.analyzed_at = datetime.now(timezone.utc)
    db.commit()

    return {"analysis_method": "quiz_fallback",
            "skin_undertone": analysis.skin_undertone,
            "silhouette_category": analysis.silhouette_category,
            "color_palette": analysis.color_palette,
            "fit_rules": analysis.fit_rules,
            "status": "saved"}


@router.get("/body-profile")
def get_body_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    bp = db.query(BodyProfile).filter(BodyProfile.user_id == user.id).first()
    if bp is None:
        return {"exists": False}
    return {"exists": True, "silhouette_category": bp.silhouette_category,
            "skin_undertone": bp.skin_undertone, "color_palette": bp.color_palette,
            "fit_rules": bp.fit_rules, "analysis_method": bp.analysis_method}
