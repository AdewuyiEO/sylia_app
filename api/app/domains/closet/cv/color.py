"""Dominant-colour extraction (spec §1.1: k-means on the background-removed image).

Real and self-contained — no heavy model. Runs k-means over the garment's
opaque pixels (ignoring transparent background from the cut-out so the bed/floor
never pollutes the colour), then maps each dominant cluster to the nearest named
colour. Returns (primary, secondary?).
"""
from __future__ import annotations

import numpy as np
from PIL import Image

try:   # worker image; the API image uses the numpy fallback below
    from sklearn.cluster import KMeans
except Exception:
    KMeans = None

# named palette — muted neutrals + accents the styling engine reasons about.
# name -> RGB. Nearest-neighbour in RGB is good enough for MVP colour naming.
NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (26, 26, 30), "charcoal": (58, 58, 68), "grey": (150, 150, 158),
    "white": (245, 245, 247), "cream": (231, 223, 206), "beige": (214, 199, 170),
    "sand": (201, 168, 124), "brown": (110, 76, 52), "tan": (170, 130, 90),
    "navy": (44, 54, 72), "blue": (70, 110, 165), "denim": (75, 105, 140),
    "olive": (107, 107, 78), "sage": (138, 154, 130), "green": (70, 120, 80),
    "rust": (180, 96, 60), "clay": (169, 105, 78), "red": (168, 52, 52),
    "burgundy": (110, 40, 55), "pink": (210, 150, 165), "purple": (110, 80, 140),
    "yellow": (210, 185, 90), "orange": (205, 130, 60), "stone": (154, 149, 140),
}
_NAMES = list(NAMED_COLORS.keys())
_RGB = np.array([NAMED_COLORS[n] for n in _NAMES], dtype=np.float64)


def _nearest_name(rgb: np.ndarray) -> str:
    d = np.sum((_RGB - rgb) ** 2, axis=1)
    return _NAMES[int(np.argmin(d))]


def _kmeans(pixels: np.ndarray, k: int, iters: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Plain Lloyd's k-means with deterministic k-means++ seeding. (labels, centers)"""
    if KMeans is not None:
        km = KMeans(n_clusters=k, n_init=4, random_state=0).fit(pixels)
        return km.labels_, km.cluster_centers_
    rng = np.random.default_rng(0)
    centers = [pixels[rng.integers(len(pixels))]]
    for _ in range(1, k):
        d = np.min(((pixels[:, None, :] - np.array(centers)[None]) ** 2).sum(-1), axis=1)
        centers.append(pixels[rng.choice(len(pixels), p=d / d.sum())] if d.sum() > 0 else pixels[0])
    centers = np.array(centers)
    for _ in range(iters):
        labels = np.argmin(((pixels[:, None, :] - centers[None]) ** 2).sum(-1), axis=1)
        new = np.array([pixels[labels == j].mean(axis=0) if np.any(labels == j) else centers[j]
                        for j in range(k)])
        if np.allclose(new, centers):
            break
        centers = new
    return labels, centers


def _drop_plain_background(rgb: np.ndarray, h: int, w: int) -> np.ndarray:
    """No cut-out available: treat the photo's border colour as background and
    drop pixels close to it (works for the usual garment-on-plain-surface shot)."""
    img = rgb.reshape(h, w, 3)
    b = max(1, min(h, w) // 20)
    border = np.concatenate([img[:b].reshape(-1, 3), img[-b:].reshape(-1, 3),
                             img[:, :b].reshape(-1, 3), img[:, -b:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    keep = np.sum((rgb - bg) ** 2, axis=1) > 40 ** 2
    return rgb[keep] if keep.mean() >= 0.05 else rgb


def extract_colors(img: Image.Image, k: int = 3, min_secondary_share: float = 0.18
                   ) -> tuple[str, str | None]:
    """Return (primary_color, secondary_color|None) as names.

    If the image has an alpha channel (a cut-out), only opaque pixels are used.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    arr = np.asarray(img)
    rgb = arr[:, :, :3].reshape(-1, 3).astype(np.float64)
    alpha = arr[:, :, 3].reshape(-1)

    mask = alpha > 32
    if mask.all():                     # fully opaque: no cut-out was produced
        pixels = _drop_plain_background(rgb, arr.shape[0], arr.shape[1])
    else:
        pixels = rgb[mask] if mask.any() else rgb
    if len(pixels) == 0:
        return "grey", None

    # downsample for speed on large images
    if len(pixels) > 20000:
        idx = np.random.default_rng(0).choice(len(pixels), 20000, replace=False)
        pixels = pixels[idx]

    k_eff = min(k, len(np.unique(pixels, axis=0)))
    if k_eff < 1:
        return _nearest_name(pixels.mean(axis=0)), None

    labels, centers = _kmeans(pixels, k_eff)
    counts = np.bincount(labels, minlength=k_eff).astype(np.float64)
    shares = counts / counts.sum()
    order = np.argsort(shares)[::-1]

    primary = _nearest_name(centers[order[0]])
    secondary = None
    for j in order[1:]:
        name = _nearest_name(centers[j])
        if name != primary and shares[j] >= min_secondary_share:
            secondary = name
            break
    return primary, secondary
