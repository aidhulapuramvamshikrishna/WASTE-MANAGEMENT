"""Constants for WasteML: 12 material classes, 4 SWM-2026 streams, ImageNet normalization."""

import os
from pathlib import Path

# Alphabetical order as produced by torchvision.datasets.ImageFolder.
# Must match ARCHITECTURE.md §3 exactly.
CLASS_NAMES: list[str] = [
    "battery",
    "cardboard",
    "e_waste",
    "glass",
    "mask_glove",
    "medicine_syringe",
    "metal",
    "misc_trash",
    "organic",
    "paper",
    "plastic",
    "textile",
]

NUM_CLASSES: int = len(CLASS_NAMES)

CLASS_TO_IDX: dict[str, int] = {name: i for i, name in enumerate(CLASS_NAMES)}
IDX_TO_CLASS: dict[int, str] = {i: name for i, name in enumerate(CLASS_NAMES)}

# Four-stream segregation under India's Solid Waste Management (SWM) Rules 2026:
# dry, wet, sanitary, special_care.
CLASS_TO_STREAM: dict[str, str] = {
    "battery": "special_care",
    "cardboard": "dry",
    "e_waste": "special_care",
    "glass": "dry",
    "mask_glove": "sanitary",
    "medicine_syringe": "special_care",
    "metal": "dry",
    "misc_trash": "dry",
    "organic": "wet",
    "paper": "dry",
    "plastic": "dry",
    "textile": "dry",
}

STREAMS: list[str] = ["wet", "dry", "sanitary", "special_care"]

# Image parameters
IMG_SIZE: int = 224
EVAL_RESIZE_SIZE: int = 256

# Standard ImageNet statistics for transfer learning and torchvision models
IMAGENET_MEAN: list[float] = [0.485, 0.456, 0.406]
IMAGENET_STD: list[float] = [0.229, 0.224, 0.225]


def get_default_data_dir() -> Path:
    """Return default dataset directory, checking WASTE_DATA_DIR env or relative paths."""
    env_dir = os.environ.get("WASTE_DATA_DIR")
    if env_dir:
        return Path(env_dir).resolve()

    # Fallbacks from common execution directories
    cwd = Path.cwd()
    candidates = [
        cwd / "data" / "processed" / "waste12",
        cwd.parent / "data" / "processed" / "waste12",
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed" / "waste12",
    ]
    for c in candidates:
        if c.is_dir() and (c / "train").is_dir():
            return c

    return candidates[0]
