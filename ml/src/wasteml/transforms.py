"""Image transformation pipelines for training and evaluation.

eval_tfms() is deterministic and shared with the backend inference engine.
"""

from torchvision import transforms

from wasteml.constants import EVAL_RESIZE_SIZE, IMAGENET_MEAN, IMAGENET_STD, IMG_SIZE


def train_tfms() -> transforms.Compose:
    """Data augmentation pipeline for training."""
    return transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.6, 1.0)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.02),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        transforms.RandomErasing(p=0.25, scale=(0.02, 0.2), value="random"),
    ])


def eval_tfms() -> transforms.Compose:
    """Deterministic evaluation and serving transformation pipeline."""
    return transforms.Compose([
        transforms.Resize(EVAL_RESIZE_SIZE),
        transforms.CenterCrop(IMG_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])
