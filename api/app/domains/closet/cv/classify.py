"""Zero-shot garment attribute classification (spec §1.1: CLIP, no training data yet).

Optional heavy dep (open-clip-torch + torch). When present, we embed the image
once and score it against the subcategory / pattern / fit prompt sets. When
absent, `classify_attributes` returns None and the pipeline flags the item
low-confidence so the human-in-the-loop confirm step catches it — exactly the
behaviour we want before the model is wired, and the safe degrade in prod too.
"""
from __future__ import annotations
from dataclasses import dataclass
from PIL import Image

from .taxonomy import (
    SUBCATEGORIES, PATTERNS, FITS, FIT_MAP,
    SUBCATEGORY_PROMPTS, PATTERN_PROMPTS, FIT_PROMPTS,
)

try:
    import torch
    import open_clip
    _HAS_CLIP = True
except Exception:
    _HAS_CLIP = False

_MODEL = None
_PREPROCESS = None
_TOKENIZER = None
_TEXT_CACHE: dict[str, "torch.Tensor"] = {}


@dataclass
class Attributes:
    subcategory: str
    pattern: str
    fit: str
    confidence: float


def has_clip() -> bool:
    return _HAS_CLIP


def _load():
    global _MODEL, _PREPROCESS, _TOKENIZER
    if _MODEL is None:
        _MODEL, _, _PREPROCESS = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k")
        _MODEL.eval()
        _TOKENIZER = open_clip.get_tokenizer("ViT-B-32")
    return _MODEL, _PREPROCESS, _TOKENIZER


def _score(image_features, labels: list[str], templates: list[str], model, tokenizer):
    # build averaged text embeddings per label (cached across calls)
    key = "|".join(templates) + "::" + "|".join(labels)
    if key not in _TEXT_CACHE:
        embs = []
        for label in labels:
            toks = tokenizer([t.format(label=label) for t in templates])
            with torch.no_grad():
                te = model.encode_text(toks)
                te = te / te.norm(dim=-1, keepdim=True)
                embs.append(te.mean(dim=0))
        mat = torch.stack(embs)
        _TEXT_CACHE[key] = mat / mat.norm(dim=-1, keepdim=True)
    text = _TEXT_CACHE[key]
    sims = (image_features @ text.T).softmax(dim=-1)[0]
    best = int(sims.argmax())
    return labels[best], float(sims[best])


def classify_attributes(img: Image.Image) -> Attributes | None:
    if not _HAS_CLIP:
        return None
    model, preprocess, tokenizer = _load()
    tensor = preprocess(img.convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        feats = model.encode_image(tensor)
        feats = feats / feats.norm(dim=-1, keepdim=True)

    subcats = list(SUBCATEGORIES.keys())
    sub, sub_conf = _score(feats, subcats, SUBCATEGORY_PROMPTS, model, tokenizer)
    pat, _ = _score(feats, PATTERNS, PATTERN_PROMPTS, model, tokenizer)
    fit_label, _ = _score(feats, FITS, FIT_PROMPTS, model, tokenizer)
    return Attributes(subcategory=sub, pattern=pat,
                      fit=FIT_MAP.get(fit_label, "regular"), confidence=round(sub_conf, 3))
