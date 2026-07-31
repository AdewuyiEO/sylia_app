"""Background removal (spec §1.1: rembg / U^2-Net, SAM only as low-confidence fallback).

Optional heavy dep. If rembg isn't installed (e.g. the API image, or this
sandbox), we degrade to a passthrough that returns the original image — the
pipeline still runs, colour extraction just can't exclude the background as
cleanly. The worker image installs rembg; the API image doesn't need it.
"""
from __future__ import annotations
from PIL import Image

try:
    from rembg import remove as _rembg_remove, new_session as _new_session
    _SESSION = None
    _HAS_REMBG = True
except Exception:
    _HAS_REMBG = False


def has_rembg() -> bool:
    return _HAS_REMBG


def remove_background(img: Image.Image) -> Image.Image:
    """Return an RGBA cut-out (transparent background). Passthrough if rembg absent."""
    if not _HAS_REMBG:
        return img.convert("RGBA")
    global _SESSION
    if _SESSION is None:
        _SESSION = _new_session("u2net")   # downloads the model once, then cached
    out = _rembg_remove(img, session=_SESSION)
    return out.convert("RGBA")
