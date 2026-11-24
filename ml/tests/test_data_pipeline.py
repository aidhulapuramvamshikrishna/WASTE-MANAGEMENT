"""Unit tests for ML data pipeline, class ordering, transforms, and weights."""

import os

import torch
from PIL import Image

from wasteml.constants import (
    CLASS_NAMES,
    CLASS_TO_STREAM,
    NUM_CLASSES,
    STREAMS,
    get_default_data_dir,
)
from wasteml.data import build_dataloaders, compute_class_weights
from wasteml.transforms import eval_tfms
from wasteml.utils import get_device


def test_class_order_alphabetical_and_matches_folders():
    """Verify class order is strictly alphabetical and matches ImageFolder on disk."""
    data_dir = get_default_data_dir()
    train_dir = data_dir / "train"
    val_dir = data_dir / "val"
    test_dir = data_dir / "test"

    assert train_dir.is_dir(), f"Train dir missing: {train_dir}"
    assert val_dir.is_dir(), f"Val dir missing: {val_dir}"
    assert test_dir.is_dir(), f"Test dir missing: {test_dir}"

    train_classes = sorted([d for d in os.listdir(train_dir) if (train_dir / d).is_dir()])
    val_classes = sorted([d for d in os.listdir(val_dir) if (val_dir / d).is_dir()])
    test_classes = sorted([d for d in os.listdir(test_dir) if (test_dir / d).is_dir()])

    # Must equal CLASS_NAMES exactly
    assert train_classes == CLASS_NAMES, f"Expected {CLASS_NAMES}, got {train_classes}"
    assert val_classes == CLASS_NAMES, f"Val classes mismatch: {val_classes}"
    assert test_classes == CLASS_NAMES, f"Test classes mismatch: {test_classes}"

    # Assert exactly 12 classes
    assert len(CLASS_NAMES) == 12
    assert NUM_CLASSES == 12


def test_batch_shape_and_labels():
    """Verify one DataLoader batch has shape [B, 3, 224, 224] and labels in [0, 11]."""
    # Fast test: num_workers=0, batch_size=4
    train_loader, _, _, _ = build_dataloaders(
        batch_size=4,
        num_workers=0,
        use_sampler=False,
    )

    images, labels = next(iter(train_loader))

    assert images.shape == (4, 3, 224, 224)
    assert images.dtype == torch.float32
    assert labels.shape == (4,)
    assert labels.dtype == torch.int64

    for label in labels:
        assert 0 <= label.item() < NUM_CLASSES


def test_class_weights_positive_and_sum():
    """Verify class weights are positive and sum to NUM_CLASSES."""
    # Synthetic realistic counts
    mock_targets = [0] * 1400 + [7] * 442 + [8] * 1280
    for c in range(NUM_CLASSES):
        if c not in [0, 7, 8]:
            mock_targets.extend([c] * 1000)

    weights = compute_class_weights(mock_targets)

    assert isinstance(weights, torch.Tensor)
    assert weights.shape == (NUM_CLASSES,)
    assert (weights > 0).all()
    # Normalized weights sum to NUM_CLASSES
    assert torch.isclose(weights.sum(), torch.tensor(float(NUM_CLASSES)), atol=1e-4)

    # Smaller classes must have higher weight
    assert weights[7] > weights[0]


def test_eval_transform_deterministic():
    """Verify eval_tfms produces identical deterministic tensors on repeated calls."""
    tfm = eval_tfms()
    dummy_img = Image.new("RGB", (300, 400), color=(128, 64, 32))

    tensor1 = tfm(dummy_img)
    tensor2 = tfm(dummy_img)

    assert tensor1.shape == (3, 224, 224)
    assert torch.equal(tensor1, tensor2)
    assert torch.allclose(tensor1, tensor2, atol=0.0)


def test_stream_mapping_coverage():
    """Verify all 12 classes map to legitimate SWM-2026 streams."""
    assert len(CLASS_TO_STREAM) == NUM_CLASSES
    for cls_name, stream in CLASS_TO_STREAM.items():
        assert cls_name in CLASS_NAMES
        assert stream in STREAMS


def test_device_selection():
    """Verify get_device returns a valid torch.device and prints device."""
    dev = get_device("auto")
    assert isinstance(dev, torch.device)
    assert dev.type in ["cuda", "mps", "cpu"]
