"""Garment taxonomy for zero-shot classification.

CLIP scores the image against these *subcategory* prompts; the DB `category`
(the enum the scorer slots by) and the formality/warmth priors are then derived
from the winning subcategory. Priors are exactly that — starting points the
user corrects, and those corrections become training data for a future
supervised classifier (spec §1.1).
"""
from __future__ import annotations

# subcategory -> (category, formality 1-5, warmth 1-5)
SUBCATEGORIES: dict[str, tuple[str, int, int]] = {
    # tops
    "t-shirt": ("top", 1, 1), "shirt": ("top", 3, 2), "blouse": ("top", 3, 2),
    "sweater": ("top", 3, 3), "knit top": ("top", 3, 3), "tank top": ("top", 1, 1),
    "polo shirt": ("top", 2, 2), "hoodie": ("top", 1, 3),
    # bottoms
    "jeans": ("bottom", 2, 2), "trousers": ("bottom", 3, 2), "chinos": ("bottom", 3, 2),
    "shorts": ("bottom", 1, 1), "skirt": ("bottom", 3, 1), "leggings": ("bottom", 1, 2),
    # dresses
    "dress": ("dress", 3, 1), "gown": ("dress", 5, 1), "sundress": ("dress", 2, 1),
    # outerwear
    "blazer": ("outerwear", 4, 3), "coat": ("outerwear", 4, 5), "jacket": ("outerwear", 3, 3),
    "parka": ("outerwear", 2, 5), "cardigan": ("outerwear", 2, 3), "trench coat": ("outerwear", 4, 4),
    # shoes
    "sneakers": ("shoes", 2, 2), "loafers": ("shoes", 3, 2), "boots": ("shoes", 3, 3),
    "heels": ("shoes", 4, 2), "sandals": ("shoes", 1, 1), "oxfords": ("shoes", 4, 2),
    "flats": ("shoes", 3, 2),
    # accessories
    "belt": ("accessory", 2, 0), "scarf": ("accessory", 2, 3), "hat": ("accessory", 2, 2),
    "handbag": ("accessory", 2, 0),
}

PATTERNS: list[str] = ["solid", "striped", "checked", "plaid", "floral", "printed", "polka dot"]

FITS: list[str] = ["slim fit", "regular fit", "oversized"]
FIT_MAP = {"slim fit": "slim", "regular fit": "regular", "oversized": "oversized"}

# CLIP prompt templates — averaged per label for a more stable embedding
SUBCATEGORY_PROMPTS = [
    "a photo of {label}", "a product photo of {label}", "a piece of clothing: {label}",
]
PATTERN_PROMPTS = ["a {label} pattern garment", "clothing with a {label} pattern"]
FIT_PROMPTS = ["a {label} garment", "clothing with a {label} silhouette"]


def category_for(subcategory: str) -> str:
    entry = SUBCATEGORIES.get(subcategory)
    return entry[0] if entry else "top"


def priors_for(subcategory: str) -> tuple[int, int]:
    """(formality_score, warmth_score) prior for a subcategory."""
    entry = SUBCATEGORIES.get(subcategory)
    return (entry[1], entry[2]) if entry else (3, 2)
