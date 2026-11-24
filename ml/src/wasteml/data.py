"""Data loading, dataset inspection, and class weighting for WasteML."""

from pathlib import Path

import torch
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision.datasets import ImageFolder

from wasteml.constants import CLASS_NAMES, NUM_CLASSES, get_default_data_dir
from wasteml.transforms import eval_tfms, train_tfms


def compute_class_weights(
    dataset_or_targets: ImageFolder | list[int] | torch.Tensor
) -> torch.Tensor:
    """Compute balanced class weights: w_c = N / (K * n_c).

    Ensures smaller classes receive proportionally higher loss weight.
    """
    if isinstance(dataset_or_targets, ImageFolder):
        targets = dataset_or_targets.targets
    elif isinstance(dataset_or_targets, torch.Tensor):
        targets = dataset_or_targets.tolist()
    else:
        targets = dataset_or_targets

    counts = torch.zeros(NUM_CLASSES, dtype=torch.float32)
    for t in targets:
        counts[t] += 1.0

    total_samples = len(targets)
    weights = total_samples / (NUM_CLASSES * counts)

    # Normalize weights so mean is 1.0 (sums to NUM_CLASSES)
    weights = weights / weights.mean()
    return weights


def build_dataloaders(
    data_dir: str | Path | None = None,
    batch_size: int = 32,
    num_workers: int = 4,
    use_sampler: bool = False,
    pin_memory: bool | None = None,
) -> tuple[DataLoader, DataLoader, DataLoader, torch.Tensor | None]:
    """Build PyTorch DataLoaders for train, val, and test splits.

    Args:
        data_dir: Path to directory containing train, val, test subdirectories.
        batch_size: Batch size for loading.
        num_workers: Number of background worker processes.
        use_sampler: If True, uses WeightedRandomSampler instead of class weights.
        pin_memory: If True, copies tensors into pinned CUDA memory (auto-detected if None).

    Returns:
        (train_loader, val_loader, test_loader, class_weights)
    """
    base_dir = Path(data_dir) if data_dir else get_default_data_dir()
    train_dir = base_dir / "train"
    val_dir = base_dir / "val"
    test_dir = base_dir / "test"

    for p in [train_dir, val_dir, test_dir]:
        if not p.is_dir():
            raise FileNotFoundError(f"Dataset split directory not found: {p}")

    train_dataset = ImageFolder(str(train_dir), transform=train_tfms())
    val_dataset = ImageFolder(str(val_dir), transform=eval_tfms())
    test_dataset = ImageFolder(str(test_dir), transform=eval_tfms())

    # Verify ImageFolder class order matches constants.CLASS_NAMES
    if train_dataset.classes != CLASS_NAMES:
        raise ValueError(
            f"ImageFolder classes {train_dataset.classes} do not match CLASS_NAMES {CLASS_NAMES}"
        )

    if pin_memory is None:
        pin_memory = torch.cuda.is_available()

    persistent = num_workers > 0

    if use_sampler:
        # WeightedRandomSampler for class balance
        class_weights = compute_class_weights(train_dataset)
        sample_weights = [class_weights[target].item() for target in train_dataset.targets]
        sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True,
        )
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            sampler=sampler,
            num_workers=num_workers,
            pin_memory=pin_memory,
            persistent_workers=persistent,
        )
        # When sampler is used, loss weights are not applied to avoid double-weighting
        loss_weights = None
    else:
        loss_weights = compute_class_weights(train_dataset)
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
            pin_memory=pin_memory,
            persistent_workers=persistent,
        )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
        persistent_workers=persistent,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
        persistent_workers=persistent,
    )

    return train_loader, val_loader, test_loader, loss_weights
