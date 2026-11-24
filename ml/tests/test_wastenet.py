"""Unit tests for WasteNet architecture, factory, and optimization step."""

import torch
from torch import nn

from wasteml.models.factory import build_model, gradcam_target_layer
from wasteml.models.wastenet import WasteNet


def test_wastenet_forward_shape():
    """Verify WasteNet forward pass produces output of shape [B, 12]."""
    model = WasteNet(num_classes=12)
    model.eval()

    dummy_input = torch.randn(2, 3, 224, 224)
    with torch.no_grad():
        output = model(dummy_input)

    assert output.shape == (2, 12)
    assert not torch.isnan(output).any()


def test_optimizer_step_lowers_loss():
    """Verify that a single training step lowers the cross-entropy loss on a fixed batch."""
    torch.manual_seed(42)
    model = WasteNet(num_classes=12)
    model.train()

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)

    images = torch.randn(8, 3, 224, 224)
    targets = torch.tensor([0, 1, 2, 3, 4, 5, 6, 7], dtype=torch.int64)

    # Initial loss
    out1 = model(images)
    loss1 = criterion(out1, targets)

    # Optimization step
    optimizer.zero_grad()
    loss1.backward()
    optimizer.step()

    # Subsequent loss
    out2 = model(images)
    loss2 = criterion(out2, targets)

    assert loss2.item() < loss1.item(), f"Loss did not decrease: {loss1.item()} -> {loss2.item()}"


def test_gradcam_target_layer_wastenet():
    """Verify gradcam_target_layer returns a Conv2d module for WasteNet."""
    model = build_model("wastenet", num_classes=12)
    target_layer = gradcam_target_layer(model, "wastenet")

    assert isinstance(target_layer, nn.Conv2d)
    assert target_layer.out_channels == 384


def test_factory_build_models():
    """Verify factory builds all supported architectures."""
    m1 = build_model("wastenet", num_classes=12)
    assert isinstance(m1, WasteNet)
    assert m1.count_parameters() > 3_000_000

    m2 = build_model("mobilenet_v3", num_classes=12, pretrained=False)
    assert hasattr(m2, "classifier")

    m3 = build_model("efficientnet_b0", num_classes=12, pretrained=False)
    assert hasattr(m3, "classifier")


def test_warmup_scheduler_lr_progression():
    """Verify that learning rate at step 0 is strictly lower than LR at the end of warm-up."""
    from wasteml.train import build_scheduler

    param = [torch.nn.Parameter(torch.randn(2, 2))]
    base_lr = 0.001
    optimizer = torch.optim.AdamW(param, lr=base_lr)

    warmup_epochs = 1
    epochs = 45
    steps_per_epoch = 100
    warmup_steps = warmup_epochs * steps_per_epoch

    scheduler = build_scheduler(
        optimizer=optimizer,
        base_lr=base_lr,
        warmup_epochs=warmup_epochs,
        epochs=epochs,
        steps_per_epoch=steps_per_epoch,
    )

    initial_lr = optimizer.param_groups[0]["lr"]
    assert initial_lr <= base_lr * 0.02, f"Expected initial LR near 1e-5, got {initial_lr}"

    for _ in range(warmup_steps):
        optimizer.step()
        scheduler.step()

    end_warmup_lr = optimizer.param_groups[0]["lr"]
    assert end_warmup_lr >= base_lr * 0.99, f"Expected end of warmup LR near {base_lr}, got {end_warmup_lr}"
    assert initial_lr < end_warmup_lr, f"Step 0 LR ({initial_lr}) must be < warmup end LR ({end_warmup_lr})"

