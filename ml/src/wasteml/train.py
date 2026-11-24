"""Training pipeline for WasteML classification models.

Config-driven training with:
- Custom from-scratch CNN (wastenet) and two-phase transfer learning (mobilenet_v3, efficientnet_b0)
- Phase 1: Frozen backbone (BN in eval mode) + trained classifier head with per-step warmup
- Phase 2: Full network fine-tuning with differential learning rates (backbone 0.1x head)
- Gradient clipping (clip_grad_norm_ <= 1.0) for numerical stability
- Mixed precision (AMP) on CUDA
- Class-weighted CrossEntropyLoss with label smoothing
- Early stopping monitored on validation macro-F1 (counts in phase 2)
- History logging to history.csv per epoch (with phase and LR per group)
- Resumable training via last.pt checkpoint
- Optional --artifacts-dir CLI parameter for cloud/Drive persistence
"""

import argparse
import csv
import os
import random
import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any

import certifi
import numpy as np
import torch
import yaml
from sklearn.metrics import f1_score
from torch import nn

# Ensure PyTorch hub/download can verify SSL certificates on macOS
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR
from torch.utils.data import DataLoader, Subset
from torchvision.datasets import ImageFolder

from wasteml.constants import CLASS_NAMES, get_default_data_dir
from wasteml.data import build_dataloaders
from wasteml.models.factory import build_model, get_backbone_and_head
from wasteml.transforms import eval_tfms
from wasteml.utils import AverageMeter, Timer, get_device, seed_everything


def freeze_backbone(model: nn.Module, model_name: str) -> None:
    """Freeze backbone parameters and ensure classifier head requires grad."""
    backbone, head = get_backbone_and_head(model, model_name)
    for p in backbone.parameters():
        p.requires_grad = False
    for p in head.parameters():
        p.requires_grad = True


def set_backbone_bn_eval(model: nn.Module, model_name: str) -> None:
    """Set all BatchNorm modules in backbone to eval mode to preserve running stats."""
    backbone, _ = get_backbone_and_head(model, model_name)
    for m in backbone.modules():
        if isinstance(m, (nn.BatchNorm2d, nn.modules.batchnorm._BatchNorm)):
            m.eval()


def unfreeze_all(model: nn.Module) -> None:
    """Unfreeze all model parameters for full network fine-tuning."""
    for p in model.parameters():
        p.requires_grad = True


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    scheduler: Any = None,
    scaler: torch.amp.GradScaler | None = None,
    max_grad_norm: float = 1.0,
    model_name: str = "wastenet",
    phase: int = 1,
) -> tuple[float, float]:
    """Train for one epoch with per-step scheduler and gradient clipping."""
    model.train()
    # In transfer Phase 1, force backbone BatchNorm layers to stay in eval mode
    if model_name in ["mobilenet_v3", "efficientnet_b0"] and phase == 1:
        set_backbone_bn_eval(model, model_name)

    loss_meter = AverageMeter("Loss")
    correct = 0
    total = 0

    use_amp = device.type == "cuda" and scaler is not None

    for images, targets in loader:
        images = images.to(device)
        targets = targets.to(device)

        optimizer.zero_grad()
        if use_amp:
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                outputs = model(images)
                loss = criterion(outputs, targets)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=max_grad_norm)
            scaler.step(optimizer)
            scaler.update()
        else:
            outputs = model(images)
            loss = criterion(outputs, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=max_grad_norm)
            optimizer.step()

        if scheduler is not None:
            scheduler.step()

        preds = outputs.argmax(dim=1)
        correct += (preds == targets).sum().item()
        total += targets.size(0)
        loss_meter.update(loss.item(), targets.size(0))

    accuracy = correct / total if total > 0 else 0.0
    return loss_meter.avg, accuracy


@torch.no_grad()
def evaluate_val(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, float, float]:
    """Evaluate on validation set and compute loss, accuracy, and macro-F1."""
    model.eval()
    loss_meter = AverageMeter("Val Loss")
    all_preds: list[int] = []
    all_targets: list[int] = []

    for images, targets in loader:
        images = images.to(device)
        targets = targets.to(device)

        outputs = model(images)
        loss = criterion(outputs, targets)

        preds = outputs.argmax(dim=1)
        all_preds.extend(preds.cpu().tolist())
        all_targets.extend(targets.cpu().tolist())
        loss_meter.update(loss.item(), targets.size(0))

    all_preds_arr = np.array(all_preds)
    all_targets_arr = np.array(all_targets)

    val_acc = (all_preds_arr == all_targets_arr).mean() if len(all_targets_arr) > 0 else 0.0
    val_macro_f1 = f1_score(all_targets_arr, all_preds_arr, average="macro", zero_division=0)

    return loss_meter.avg, float(val_acc), float(val_macro_f1)


def run_sanity_check(cfg: dict[str, Any], device: torch.device) -> bool:
    """Overfit 64 stratified images across all 12 classes to >= 95% accuracy."""
    print("=" * 60)
    print("RUNNING SANITY CHECK: Overfit 64 stratified images (12 classes)")
    print("=" * 60)

    data_dir = get_default_data_dir()
    train_dir = data_dir / "train"
    if not train_dir.is_dir():
        raise FileNotFoundError(f"Train directory not found: {train_dir}")

    full_ds = ImageFolder(str(train_dir), transform=eval_tfms())

    random.seed(cfg.get("seed", 42))
    targets_array = np.array(full_ds.targets)
    stratified_indices: list[int] = []

    for c in range(12):
        cls_indices = np.where(targets_array == c)[0].tolist()
        num_samples = 6 if c < 4 else 5
        stratified_indices.extend(random.sample(cls_indices, num_samples))

    selected_indices = stratified_indices[:64]
    selected_labels = [full_ds.targets[i] for i in selected_indices]
    assert len(selected_indices) == 64
    assert len(set(selected_labels)) == 12, f"Expected 12 unique classes, got {len(set(selected_labels))}"

    label_counts = Counter(selected_labels)
    hist_str = ", ".join(f"{CLASS_NAMES[c]}: {label_counts[c]}" for c in range(12))
    print(f"Stratified 64 samples label distribution (12 classes):\n  {hist_str}")

    subset = Subset(full_ds, selected_indices)
    sanity_loader = DataLoader(subset, batch_size=16, shuffle=True, num_workers=0)

    model_name = cfg["model_name"]
    is_transfer = model_name in ["mobilenet_v3", "efficientnet_b0"]
    pretrained = cfg.get("pretrained", True) if is_transfer else False

    model = build_model(
        name=model_name,
        num_classes=cfg.get("num_classes", 12),
        pretrained=pretrained,
    ).to(device)

    criterion = nn.CrossEntropyLoss()

    if is_transfer:
        freeze_backbone(model, model_name)
        set_backbone_bn_eval(model, model_name)
        _, head = get_backbone_and_head(model, model_name)
        optimizer = torch.optim.AdamW(head.parameters(), lr=1e-3, weight_decay=1e-4)
    else:
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    start_time = time.perf_counter()
    step = 0
    passed = False

    while step < 60:
        for images, targets in sanity_loader:
            step += 1
            images = images.to(device)
            targets = targets.to(device)

            model.train()
            if is_transfer:
                set_backbone_bn_eval(model, model_name)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            preds = outputs.argmax(dim=1)
            acc = (preds == targets).float().mean().item()
            loss_val = loss.item()
            elapsed = time.perf_counter() - start_time

            if elapsed > 180.0:
                print(f"Sanity check timeout after {elapsed:.1f}s!")
                return False

            if step <= 20 or step % 5 == 0 or acc >= 0.95:
                print(f"Sanity Step {step:03d} | Loss: {loss_val:.4f} | Train Acc: {acc:.1%} | Elapsed: {elapsed:.1f}s")

            if acc >= 0.95:
                print(f"SUCCESS: Sanity check passed at step {step} with {acc:.1%} accuracy in {elapsed:.1f}s!")
                passed = True
                break

        if passed:
            break

    if not passed:
        print("FAILURE: Sanity check did not reach 95% accuracy within 60 steps.")
        return False
    return True


def run_real_data_smoke(cfg: dict[str, Any], device: torch.device) -> bool:
    """Run 30 optimizer steps of real training setup with train augmentation and warmup."""
    print("=" * 60)
    print("RUNNING REAL-DATA SMOKE TEST: 30 steps with actual train setup")
    print("=" * 60)

    seed_everything(cfg.get("seed", 42))

    train_loader, _, _, class_weights = build_dataloaders(
        batch_size=16,
        num_workers=0,
        use_sampler=False,
    )

    model_name = cfg["model_name"]
    is_transfer = model_name in ["mobilenet_v3", "efficientnet_b0"]
    pretrained = cfg.get("pretrained", True) if is_transfer else False

    model = build_model(
        name=model_name,
        num_classes=cfg.get("num_classes", 12),
        pretrained=pretrained,
    ).to(device)

    criterion_weights = class_weights.to(device) if class_weights is not None else None
    criterion = nn.CrossEntropyLoss(
        weight=criterion_weights,
        label_smoothing=float(cfg.get("label_smoothing", 0.1)),
    )

    base_lr = float(cfg.get("learning_rate", 1e-3))
    if is_transfer:
        freeze_backbone(model, model_name)
        set_backbone_bn_eval(model, model_name)
        _, head = get_backbone_and_head(model, model_name)
        optimizer = torch.optim.AdamW(head.parameters(), lr=base_lr, weight_decay=1e-4)
    else:
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=1e-4)

    scheduler = build_scheduler(
        optimizer=optimizer,
        base_lr=base_lr,
        warmup_epochs=int(cfg.get("warmup_epochs", 1)),
        epochs=int(cfg.get("epochs", 25)),
        steps_per_epoch=len(train_loader),
    )

    initial_lr = optimizer.param_groups[0]["lr"]
    print(f"Setup: batch_size=16, num_workers=0, base_lr={base_lr}, initial_lr={initial_lr:.7f}")

    start_time = time.perf_counter()
    data_iter = iter(train_loader)
    first_loss = None
    current_lr = initial_lr

    for step in range(1, 31):
        try:
            images, targets = next(data_iter)
        except StopIteration:
            data_iter = iter(train_loader)
            images, targets = next(data_iter)

        images = images.to(device)
        targets = targets.to(device)

        model.train()
        if is_transfer:
            set_backbone_bn_eval(model, model_name)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, targets)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()

        current_lr = optimizer.param_groups[0]["lr"]
        loss_val = loss.item()
        if step == 1:
            first_loss = loss_val

        preds = outputs.argmax(dim=1)
        acc = (preds == targets).float().mean().item()
        print(f"Smoke Step {step:02d}/30 | Loss: {loss_val:.4f} | Train Acc: {acc:.1%} | LR: {current_lr:.7f}")

    elapsed = time.perf_counter() - start_time
    print("-" * 60)
    print(f"Smoke run finished in {elapsed:.1f}s. Initial step-1 loss: {first_loss:.4f}, final LR: {current_lr:.7f}")
    assert first_loss is not None
    assert 0.5 <= first_loss <= 3.5, f"Expected realistic initial loss, got {first_loss:.4f}"
    assert current_lr > initial_lr, f"LR must increase during warmup (initial={initial_lr:.7f}, current={current_lr:.7f})"
    print("SUCCESS: Real-data smoke test passed with stable loss and functioning warm-up.")
    return True


def build_scheduler(
    optimizer: torch.optim.Optimizer,
    base_lr: float,
    warmup_epochs: int,
    epochs: int,
    steps_per_epoch: int,
) -> SequentialLR:
    """Build per-step linear warmup into cosine annealing schedule."""
    warmup_steps = max(1, warmup_epochs * steps_per_epoch)
    total_steps = max(warmup_steps + 1, epochs * steps_per_epoch)
    cosine_steps = max(1, total_steps - warmup_steps)

    sched_warmup = LinearLR(
        optimizer,
        start_factor=0.01,
        end_factor=1.0,
        total_iters=warmup_steps,
    )
    sched_cosine = CosineAnnealingLR(
        optimizer,
        T_max=cosine_steps,
        eta_min=base_lr * 0.01,
    )
    return SequentialLR(
        optimizer,
        schedulers=[sched_warmup, sched_cosine],
        milestones=[warmup_steps],
    )


def setup_phase_optimizer_and_scheduler(
    model: nn.Module,
    model_name: str,
    phase: int,
    cfg: dict[str, Any],
    steps_per_epoch: int,
) -> tuple[torch.optim.Optimizer, Any]:
    """Setup optimizer and scheduler for Phase 1 (frozen backbone) or Phase 2 (differential fine-tuning)."""
    weight_decay = float(cfg.get("weight_decay", 1e-4))
    warmup_epochs = int(cfg.get("warmup_epochs", 1))
    freeze_epochs = int(cfg.get("freeze_epochs", 3))
    total_epochs = int(cfg.get("epochs", 25))

    is_transfer = model_name in ["mobilenet_v3", "efficientnet_b0"]

    if not is_transfer:
        # Standard single-phase training (wastenet)
        lr = float(cfg.get("learning_rate", 1e-3))
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = build_scheduler(
            optimizer=optimizer,
            base_lr=lr,
            warmup_epochs=warmup_epochs,
            epochs=total_epochs,
            steps_per_epoch=steps_per_epoch,
        )
        return optimizer, scheduler

    if phase == 1:
        # Phase 1: Train classifier head only with frozen backbone
        lr = float(cfg.get("learning_rate", 1e-3))
        freeze_backbone(model, model_name)
        set_backbone_bn_eval(model, model_name)
        _, head = get_backbone_and_head(model, model_name)
        optimizer = torch.optim.AdamW(head.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = build_scheduler(
            optimizer=optimizer,
            base_lr=lr,
            warmup_epochs=min(warmup_epochs, freeze_epochs),
            epochs=freeze_epochs,
            steps_per_epoch=steps_per_epoch,
        )
        return optimizer, scheduler

    else:
        # Phase 2: Unfreeze full network with differential learning rates
        unfreeze_all(model)
        unfreeze_lr = float(cfg.get("unfreeze_lr", 3e-4))
        backbone_ratio = float(cfg.get("backbone_lr_ratio", 0.1))
        backbone_lr = unfreeze_lr * backbone_ratio

        backbone, head = get_backbone_and_head(model, model_name)
        optimizer = torch.optim.AdamW(
            [
                {"params": backbone.parameters(), "lr": backbone_lr},
                {"params": head.parameters(), "lr": unfreeze_lr},
            ],
            weight_decay=weight_decay,
        )
        phase2_epochs = max(1, total_epochs - freeze_epochs)
        scheduler = build_scheduler(
            optimizer=optimizer,
            base_lr=unfreeze_lr,
            warmup_epochs=min(warmup_epochs, phase2_epochs),
            epochs=phase2_epochs,
            steps_per_epoch=steps_per_epoch,
        )
        return optimizer, scheduler


def main() -> None:
    parser = argparse.ArgumentParser(description="Train WasteML classification models.")
    parser.add_argument("--config", type=str, default="configs/wastenet.yaml", help="Path to config yaml")
    parser.add_argument("--sanity", action="store_true", help="Run 64-image stratified sanity check and exit")
    parser.add_argument("--smoke", action="store_true", help="Run 30-step real-data training smoke test and exit")
    parser.add_argument("--device", type=str, default="auto", help="Compute device (auto, cuda, mps, cpu)")
    parser.add_argument("--resume", action="store_true", help="Resume from last.pt checkpoint")
    parser.add_argument(
        "--artifacts-dir",
        type=str,
        default=None,
        help="Directory for saving artifacts/checkpoints (default: artifacts/<model>)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_file():
        alt_path = Path(__file__).resolve().parent.parent.parent / args.config
        if alt_path.is_file():
            config_path = alt_path
        else:
            raise FileNotFoundError(f"Config file not found: {args.config}")

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    device = get_device(args.device)

    if args.sanity:
        success = run_sanity_check(cfg, device)
        if not success:
            raise SystemExit(1)
        return

    if args.smoke:
        success = run_real_data_smoke(cfg, device)
        if not success:
            raise SystemExit(1)
        return

    # Full training pipeline
    seed = cfg.get("seed", 42)
    seed_everything(seed)

    model_name = cfg["model_name"]
    is_transfer = model_name in ["mobilenet_v3", "efficientnet_b0"]
    batch_size = cfg.get("batch_size", 64)
    epochs = cfg.get("epochs", 45 if not is_transfer else 25)
    freeze_epochs = int(cfg.get("freeze_epochs", 3)) if is_transfer else 0
    patience = int(cfg.get("early_stop_patience", 8))
    label_smoothing = float(cfg.get("label_smoothing", 0.1))
    use_sampler = cfg.get("use_sampler", False)
    num_workers = cfg.get("num_workers", 4)
    num_classes = cfg.get("num_classes", 12)
    pretrained = cfg.get("pretrained", True) if is_transfer else False

    # Artifact output directory
    if args.artifacts_dir is not None:
        artifacts_dir = Path(args.artifacts_dir)
    else:
        artifacts_dir = Path("artifacts") / model_name
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Save copy of configuration
    shutil.copy(config_path, artifacts_dir / "config.yaml")

    print(f"Building data loaders (batch_size={batch_size}, num_workers={num_workers}, use_sampler={use_sampler})...")
    train_loader, val_loader, _, class_weights = build_dataloaders(
        batch_size=batch_size,
        num_workers=num_workers,
        use_sampler=use_sampler,
    )

    print(f"Instantiating model '{model_name}' (pretrained={pretrained})...")
    model = build_model(
        name=model_name,
        num_classes=num_classes,
        pretrained=pretrained,
    ).to(device)

    # Loss criterion
    if class_weights is not None:
        criterion_weights = class_weights.to(device)
    else:
        criterion_weights = None

    criterion = nn.CrossEntropyLoss(
        weight=criterion_weights,
        label_smoothing=label_smoothing,
    )

    # Initial Phase Setup
    initial_phase = 1 if is_transfer and freeze_epochs > 0 else 2 if is_transfer else 1
    optimizer, scheduler = setup_phase_optimizer_and_scheduler(
        model=model,
        model_name=model_name,
        phase=initial_phase,
        cfg=cfg,
        steps_per_epoch=len(train_loader),
    )

    # Scaler for AMP on CUDA
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    # History file
    history_file = artifacts_dir / "history.csv"
    history_fields = [
        "epoch",
        "phase",
        "train_loss",
        "train_acc",
        "val_loss",
        "val_acc",
        "val_macro_f1",
        "lr_backbone",
        "lr_head",
        "seconds",
    ]

    start_epoch = 1
    current_phase = initial_phase
    best_val_f1 = -1.0
    best_epoch = 0
    patience_counter = 0

    # Resume checkpoint handling
    last_pt = artifacts_dir / "last.pt"
    if args.resume and last_pt.is_file():
        print(f"Resuming training from {last_pt}...")
        ckpt = torch.load(last_pt, weights_only=True)
        if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
            model.load_state_dict(ckpt["model_state_dict"])
            start_epoch = ckpt.get("epoch", 0) + 1
            current_phase = ckpt.get("phase", 2 if start_epoch > freeze_epochs else 1)
            best_val_f1 = ckpt.get("best_val_f1", -1.0)
            best_epoch = ckpt.get("best_epoch", 0)
            patience_counter = ckpt.get("patience_counter", 0)

            # Rebuild phase optimizer and scheduler for the resumed phase
            optimizer, scheduler = setup_phase_optimizer_and_scheduler(
                model=model,
                model_name=model_name,
                phase=current_phase,
                cfg=cfg,
                steps_per_epoch=len(train_loader),
            )
            if "optimizer_state_dict" in ckpt:
                try:
                    optimizer.load_state_dict(ckpt["optimizer_state_dict"])
                except (KeyError, ValueError, RuntimeError) as err:
                    print(f"Note: optimizer state dict structure changed across phase ({err}); initialized fresh.")
            if "scheduler_state_dict" in ckpt:
                try:
                    scheduler.load_state_dict(ckpt["scheduler_state_dict"])
                except (KeyError, ValueError, RuntimeError) as err:
                    print(f"Note: scheduler state dict structure changed across phase ({err}); initialized fresh.")
        print(f"Resumed at epoch {start_epoch} in Phase {current_phase} (best_val_f1: {best_val_f1:.4f})")
    elif not args.resume or not history_file.is_file():
        with open(history_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(history_fields)

    print("=" * 70)
    print(f"Starting Training: {model_name} | Max Epochs: {epochs} | Early Stop Patience: {patience}")
    if is_transfer:
        print(f"Transfer Mode: Phase 1 (frozen backbone) = {freeze_epochs} epochs | Phase 2 (fine-tune) = {epochs - freeze_epochs} epochs")
    print(f"Artifacts output directory: {artifacts_dir}")
    print("=" * 70)

    for epoch in range(start_epoch, epochs + 1):
        # Determine if we should transition to Phase 2
        if is_transfer and current_phase == 1 and epoch > freeze_epochs:
            print("\n" + "=" * 70)
            print(f"TRANSITIONING TO PHASE 2 (Epoch {epoch}): Unfreezing backbone for full fine-tuning...")
            print("=" * 70)
            current_phase = 2
            optimizer, scheduler = setup_phase_optimizer_and_scheduler(
                model=model,
                model_name=model_name,
                phase=2,
                cfg=cfg,
                steps_per_epoch=len(train_loader),
            )

        epoch_timer = Timer()
        with epoch_timer:
            train_loss, train_acc = train_one_epoch(
                model=model,
                loader=train_loader,
                criterion=criterion,
                optimizer=optimizer,
                device=device,
                scheduler=scheduler,
                scaler=scaler,
                max_grad_norm=1.0,
                model_name=model_name,
                phase=current_phase,
            )

            val_loss, val_acc, val_f1 = evaluate_val(
                model=model,
                loader=val_loader,
                criterion=criterion,
                device=device,
            )

        elapsed = epoch_timer.seconds

        # Record group learning rates
        if is_transfer:
            if current_phase == 1:
                lr_backbone = 0.0
                lr_head = optimizer.param_groups[0]["lr"]
            else:
                lr_backbone = optimizer.param_groups[0]["lr"]
                lr_head = optimizer.param_groups[1]["lr"]
        else:
            lr_backbone = optimizer.param_groups[0]["lr"]
            lr_head = optimizer.param_groups[0]["lr"]

        # Log epoch history
        with open(history_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                epoch,
                current_phase,
                f"{train_loss:.5f}",
                f"{train_acc:.5f}",
                f"{val_loss:.5f}",
                f"{val_acc:.5f}",
                f"{val_f1:.5f}",
                f"{lr_backbone:.7f}",
                f"{lr_head:.7f}",
                f"{elapsed:.2f}",
            ])

        # Best model tracking & early stopping
        improved = val_f1 > best_val_f1
        if improved:
            best_val_f1 = val_f1
            best_epoch = epoch
            patience_counter = 0
            torch.save(model.state_dict(), artifacts_dir / "best.pt")
            flag = "★ BEST"
        else:
            if is_transfer and current_phase == 1:
                flag = "Phase 1 (frozen)"
            else:
                patience_counter += 1
                flag = f"Patience: {patience_counter}/{patience}"

        # Save last checkpoint
        torch.save(
            {
                "epoch": epoch,
                "phase": current_phase,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
                "best_val_f1": best_val_f1,
                "best_epoch": best_epoch,
                "patience_counter": patience_counter,
            },
            artifacts_dir / "last.pt",
        )

        lr_info = f"LR_head: {lr_head:.6f}" if current_phase == 1 else f"LR_bb: {lr_backbone:.6f} LR_head: {lr_head:.6f}"
        print(
            f"Epoch {epoch:02d}/{epochs:02d} (P{current_phase}) [{elapsed:.1f}s] | "
            f"Train Loss: {train_loss:.4f} Acc: {train_acc:.1%} | "
            f"Val Loss: {val_loss:.4f} Acc: {val_acc:.1%} F1: {val_f1:.4f} | "
            f"{lr_info} | {flag}"
        )

        # Runtime estimation after epoch 1
        if epoch == 1:
            est_total_seconds = elapsed * epochs
            est_minutes = est_total_seconds / 60.0
            print("-" * 70)
            print(f"REPORT: Epoch 1 took {elapsed:.1f}s. Estimated full run: {est_minutes:.1f} minutes ({est_total_seconds:.0f}s).")
            print("-" * 70)

        # Early stopping check (counts only in Phase 2 for transfer models)
        if (not is_transfer or current_phase == 2) and patience_counter >= patience:
            print(f"Early stopping triggered at epoch {epoch}. No validation F1 improvement for {patience} epochs.")
            break

    print("=" * 70)
    print(f"Training Complete. Best Epoch: {best_epoch:02d} with Val Macro-F1: {best_val_f1:.4f}")
    print(f"Artifacts saved to {artifacts_dir}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
