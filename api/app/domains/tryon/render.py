"""Try-on renderer: draws a garment onto the user's own fitting-room photo at the
size they picked. numpy + Pillow only, so it runs on the API box with no GPU and
no outside service.

How it works
  1. Scale: the user's head-to-feet span in pixels / their height → px per cm.
  2. Garment cut-out: the photo's alpha, or the plain background dropped.
  3. Warp: each garment row is resampled so its width matches what that size
     measures at that height on this body (bust → waist → hips), centred on the
     body's midline, from the shoulder (or waist) down to the size's length.
     A bigger size is wider and longer here because the chart says so.
  4. Light: the photo's own shading under the garment is borrowed, plus a soft
     contact shadow, so the piece sits in the scene.
This is a fitted 2D preview, not a cloth simulation: it shows proportion, length
and roominess per size; fabric folds come from the garment photo itself.
"""
from __future__ import annotations
import io
import numpy as np
from PIL import Image, ImageFilter, ImageOps

from .fit import Body

MAX_SIDE = 1400
FRONT = 2.9            # circumference → visible front width (cm/cm), torso is an ellipse
NECK_LIFT_CM = 2.5     # shoulder seam sits a little above the shoulder joint


class RenderError(ValueError):
    pass


def _load_rgb(data: bytes, max_side: int = MAX_SIDE) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
    img = img.convert("RGB")
    s = max_side / max(img.size)
    if s < 1:
        img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    return img


def garment_cutout(data: bytes) -> np.ndarray:
    """RGBA float array (0..1) cropped to the garment."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
    img = img.convert("RGBA")
    s = 900 / max(img.size)
    if s < 1:
        img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    arr = np.asarray(img).astype(np.float32) / 255.0
    alpha = arr[..., 3]
    if (alpha < 0.98).mean() < 0.05:            # no real transparency → drop the plain background
        rgb = arr[..., :3]
        h, w = alpha.shape
        b = max(1, min(h, w) // 25)
        border = np.concatenate([rgb[:b].reshape(-1, 3), rgb[-b:].reshape(-1, 3),
                                 rgb[:, :b].reshape(-1, 3), rgb[:, -b:].reshape(-1, 3)])
        bg = np.median(border, axis=0)
        mask = (np.sqrt(((rgb - bg) ** 2).sum(-1)) > 0.15).astype(np.uint8) * 255
        m = Image.fromarray(mask).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
        m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1))
        alpha = np.asarray(m).astype(np.float32) / 255.0
        if alpha.mean() < 0.03:
            raise RenderError("Couldn't find the garment in its photo")
        arr = np.dstack([rgb, alpha])
    ys, xs = np.where(arr[..., 3] > 0.5)
    if len(ys) < 50:
        raise RenderError("Couldn't find the garment in its photo")
    return arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _run_width(alpha_row: np.ndarray, center: int) -> float:
    """Width of the opaque run through (or nearest to) the centre column — the body
    of the garment, not a sleeve laid out beside it."""
    on = alpha_row > 0.5
    if not on.any():
        return 0.0
    idx = np.where(on)[0]
    c = idx[np.argmin(np.abs(idx - center))]
    left = c
    while left > 0 and on[left - 1]:
        left -= 1
    right = c
    while right < len(on) - 1 and on[right + 1]:
        right += 1
    return float(right - left + 1)


# source rows (fraction of garment height) where each zone sits, by category
_SRC_ROWS = {
    "top": {"bust": 0.36, "waist": 0.85},
    "outerwear": {"bust": 0.30, "waist": 0.70},
    "dress": {"bust": 0.18, "waist": 0.36, "hips": 0.55},
    "bottom": {"waist": 0.02, "hips": 0.22},
}


def render(person_bytes: bytes, landmarks: dict, body: Body, garment_bytes: bytes,
           category: str, garment_cm: dict) -> bytes:
    if category not in _SRC_ROWS:
        raise RenderError(f"Try-on doesn't support {category} yet")
    person = _load_rgb(person_bytes)
    W, H = person.size
    P = {k: (float(v[0]) * W, float(v[1]) * H) for k, v in landmarks.items()}
    for k in ("head", "l_shoulder", "r_shoulder", "l_hip", "r_hip", "feet"):
        if k not in P:
            raise RenderError(f"missing landmark {k}")
    ppc = (P["feet"][1] - P["head"][1]) / body.height_cm
    if ppc <= 0:
        raise RenderError("landmarks are upside down")

    sh_y = (P["l_shoulder"][1] + P["r_shoulder"][1]) / 2
    sh_x = (P["l_shoulder"][0] + P["r_shoulder"][0]) / 2
    hip_y = (P["l_hip"][1] + P["r_hip"][1]) / 2
    hip_x = (P["l_hip"][0] + P["r_hip"][0]) / 2
    waist_y = sh_y + (hip_y - sh_y) * 0.62
    feet_x, feet_y = P["feet"]

    g = garment_cutout(garment_bytes)
    gh, gw = g.shape[:2]
    rows = _SRC_ROWS[category]

    length_px = float(garment_cm.get("length") or 70) * ppc
    if category == "bottom":
        top_y = waist_y
    else:
        top_y = sh_y - NECK_LIFT_CM * ppc
    hem_y = min(top_y + length_px, feet_y + 2 * ppc)
    if hem_y - top_y < 20:
        raise RenderError("garment too short to draw")

    # target front width at each zone: what this size measures, never narrower than the body
    def tw(zone: str) -> float:
        gcm = float(garment_cm.get(zone) or body.zone(zone) + 6)
        return max(gcm, body.zone(zone) + 0.5) / FRONT * ppc

    gc = gw / 2
    key_src, key_scale = [], []
    for zone, frac in rows.items():
        r = min(gh - 1, int(frac * gh))
        sw = _run_width(g[r, :, 3], int(gc))
        if sw < 4:
            continue
        key_src.append(frac)
        key_scale.append(tw(zone) / sw)
    if not key_scale:
        raise RenderError("couldn't measure the garment")

    # inverse-map every target pixel in the garment's box back into the cut-out
    ty = np.arange(int(np.floor(top_y)), int(np.ceil(hem_y)))
    ty = ty[(ty >= 0) & (ty < H)]
    frac = (ty - top_y) / (hem_y - top_y)                      # 0..1 down the garment
    scale = np.interp(frac, key_src, key_scale)                # px out per px in, per row
    # midline: shoulders → hips → feet
    cx = np.interp(ty, [sh_y, hip_y, feet_y], [sh_x, hip_x, feet_x])
    half = (gw / 2) * scale.max() + 4
    x0, x1 = int(max(0, np.floor(cx.min() - half))), int(min(W, np.ceil(cx.max() + half)))
    tx = np.arange(x0, x1)
    sx = gc + (tx[None, :] - cx[:, None]) / scale[:, None]      # source x per target pixel
    sy = np.broadcast_to((frac * (gh - 1))[:, None], sx.shape)

    patch = _bilinear(g, sx, sy)                               # (rows, cols, 4)
    a = patch[..., 3]
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1)),
                   dtype=np.float32) / 255.0

    base = np.asarray(person, dtype=np.float32) / 255.0
    region = base[ty[0]:ty[-1] + 1, x0:x1]

    # borrow the photo's local light (body folds, side light) but not its colours:
    # fine luminance over broad luminance, so dark clothes underneath don't darken the garment
    grey = person.convert("L")
    fine = np.asarray(grey.filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)[ty[0]:ty[-1] + 1, x0:x1] + 8
    broad = np.asarray(grey.filter(ImageFilter.GaussianBlur(28)), dtype=np.float32)[ty[0]:ty[-1] + 1, x0:x1] + 8
    shade = np.clip((fine / broad) ** 0.6, 0.82, 1.12)
    rgb = np.clip(patch[..., :3] * shade[..., None], 0, 1)

    # soft contact shadow under the edges
    sh_img = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7))
    shadow = np.roll(np.asarray(sh_img, dtype=np.float32) / 255.0, (int(3 * ppc / 4) or 2, 2), axis=(0, 1))
    region = region * (1 - 0.28 * shadow[..., None])

    out_region = region * (1 - a[..., None]) + rgb * a[..., None]
    out = base.copy()
    out[ty[0]:ty[-1] + 1, x0:x1] = out_region
    buf = io.BytesIO()
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


def _bilinear(img: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Sample an (h, w, c) image at float coords; outside → transparent."""
    h, w = img.shape[:2]
    inside = (x >= 0) & (x <= w - 1) & (y >= 0) & (y <= h - 1)
    xc, yc = np.clip(x, 0, w - 1), np.clip(y, 0, h - 1)
    x0, y0 = np.floor(xc).astype(int), np.floor(yc).astype(int)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    fx, fy = (xc - x0)[..., None], (yc - y0)[..., None]
    out = (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy)
           + img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)
    out[~inside] = 0
    return out
