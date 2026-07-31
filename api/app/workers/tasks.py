"""Background tasks. Stubs encode the pipeline shape (spec §1.1 CV pipeline).

Each task updates the JobStore so the API's poll endpoints reflect progress.
Real implementations:
  * process_garment: rembg (U^2-Net) bg-removal → CLIP zero-shot category/pattern
    → k-means dominant colour → write clothing_items row.
  * analyze_body: MediaPipe Pose (shoulder/waist/hip, torso/leg ratios → silhouette)
    + FaceMesh (cheek/forehead sample → undertone) → palette + fit_rules.
The `.delay()` calls are no-ops until a Redis broker is running; the API still
returns a job_id so the client contract holds in every environment.
"""
from ..core.jobs import jobs

try:
    from .celery_app import celery_app
    _HAS_CELERY = True
except Exception:  # celery/redis not installed in this env — degrade to inline stub
    _HAS_CELERY = False


def _register(fn):
    """Expose a `.delay(...)` that enqueues on Celery if present, else marks queued."""
    if _HAS_CELERY:
        return celery_app.task(name=fn.__name__)(fn)

    class _Local:
        __name__ = fn.__name__
        def __call__(self, *a, **k): return fn(*a, **k)
        def delay(self, *a, **k):
            # No broker in this environment → run eagerly, inline (like Celery's
            # task_always_eager). Keeps the full pipeline live in dev and tests.
            job_id = a[0] if a else None
            if job_id:
                jobs.update(job_id, status="queued")
            return fn(*a, **k)
    return _Local()


def process_garment(job_id: str, item_id: str, s3_key: str | None):
    """Background-remove → classify → colour-extract → persist to the item row.

    The row already exists (the upload endpoint created it), so this UPDATES it
    in place and flips classification_confidence from NULL ('processing') to a
    real value. CV models are stubbed; the persistence path is real, so wiring
    rembg/CLIP/k-means later means replacing `_classify()` only.
    """
    from ..db import SessionLocal
    from ..models import ClothingItem
    import uuid as _uuid

    jobs.update(job_id, status="processing")
    try:
        result = _classify(s3_key)               # ← swap for rembg + CLIP + k-means
        db = SessionLocal()
        try:
            item = db.get(ClothingItem, _uuid.UUID(item_id))
            if item is None:
                jobs.update(job_id, status="failed", error="item row missing")
                return
            item.s3_key_processed = result["s3_key_processed"]
            item.category = result["category"]
            item.subcategory = result["subcategory"]
            item.primary_color = result["primary_color"]
            item.secondary_color = result.get("secondary_color")
            item.pattern = result["pattern"]
            item.fit = result["fit"]
            item.formality_score = result["formality_score"]
            item.warmth_score = result["warmth_score"]
            item.classification_confidence = result["confidence"]
            item.tags = result.get("tags", [])
            db.commit()
        finally:
            db.close()
        jobs.update(job_id, status="done", result={"item_id": item_id})
    except Exception as e:  # keep the worker alive; surface the failure on the job
        jobs.update(job_id, status="failed", error=str(e))


def _classify(s3_key: str | None) -> dict:
    """Fetch the raw image from storage, run the CV pipeline (rembg → CLIP →
    k-means), persist-ready dict out. Colour extraction is always real; CLIP and
    rembg degrade to low-confidence/passthrough if not installed, so the worker
    never hard-fails. Falls back to a provisional result if bytes are unreadable
    (e.g. a key registered in a test without an actual upload)."""
    from ..core.storage import storage
    from ..domains.closet.cv.pipeline import classify_garment

    if not s3_key:
        return _provisional()
    try:
        raw = storage.get_bytes(s3_key)
    except Exception:
        return _provisional()
    processed_key = s3_key.replace("uploads/", "cutouts/")
    result = classify_garment(raw, processed_key=processed_key)
    # persist the background-removed cut-out so s3_key_processed resolves to real bytes
    try:
        if result.cutout_png is not None:
            storage.put_bytes(processed_key, result.cutout_png)
    except Exception:
        pass
    return result.as_dict()


def _provisional() -> dict:
    """No readable image → provisional low-confidence row for the confirm step."""
    return {
        "s3_key_processed": None, "category": "top", "subcategory": None,
        "primary_color": None, "secondary_color": None, "pattern": "solid",
        "fit": "regular", "formality_score": 3, "warmth_score": 2,
        "confidence": 0.3, "tags": ["needs-review"],
    }


def analyze_body(job_id: str, user_id: str, s3_keys: list[str]):
    """MediaPipe Pose + FaceMesh → silhouette + undertone → palette + fit_rules,
    persisted to body_profiles. Every signal carries confidence; low confidence
    routes the user to the quiz cross-check. Degrades to a neutral, low-confidence
    profile (never a confident guess) if the images or models aren't usable."""
    from ..db import SessionLocal
    from ..models import BodyProfile
    from ..core.storage import storage
    from ..domains.vision.analysis.pipeline import analyze_body_images
    from datetime import datetime, timezone
    import uuid as _uuid

    jobs.update(job_id, status="processing")
    try:
        front = storage.get_bytes(s3_keys[0]) if s3_keys else None
        face = storage.get_bytes(s3_keys[1]) if len(s3_keys) > 1 else None
        if front is None:
            jobs.update(job_id, status="failed", error="no front image")
            return
        analysis = analyze_body_images(front, face)

        db = SessionLocal()
        try:
            bp = db.query(BodyProfile).filter(BodyProfile.user_id == _uuid.UUID(user_id)).first()
            if bp is None:
                bp = BodyProfile(user_id=_uuid.UUID(user_id))
                db.add(bp)
            bp.silhouette_category = analysis.silhouette_category
            bp.skin_undertone = analysis.skin_undertone
            bp.color_palette = analysis.color_palette
            bp.fit_rules = analysis.fit_rules
            bp.analysis_method = analysis.analysis_method
            bp.analyzed_at = datetime.now(timezone.utc)
            # privacy: the raw intake image is not retained by default (spec)
            bp.intake_image_s3_key = None
            db.commit()
        finally:
            db.close()

        jobs.update(job_id, status="done", result={
            "silhouette_category": analysis.silhouette_category,
            "silhouette_confidence": analysis.silhouette_confidence,
            "skin_undertone": analysis.skin_undertone,
            "undertone_confidence": analysis.undertone_confidence,
            "needs_confirmation": analysis.needs_confirmation,
        })
    except Exception as e:
        jobs.update(job_id, status="failed", error=str(e))


process_garment = _register(process_garment)
analyze_body = _register(analyze_body)
