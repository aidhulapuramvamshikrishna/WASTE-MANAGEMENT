"""Unit tests for Milestone 3: Transfer learning models and two-phase fine-tuning."""

import pytest
import torch
from torch import nn

from wasteml.models.factory import (
    build_model,
    get_backbone_and_head,
    gradcam_target_layer,
)
from wasteml.train import (
    freeze_backbone,
    set_backbone_bn_eval,
    setup_phase_optimizer_and_scheduler,
)


@pytest.mark.parametrize("model_name", ["mobilenet_v3", "efficientnet_b0"])
def test_transfer_model_output_shape(model_name: str) -> None:
    """Verify that transfer models output logits of shape [B, 12] with pretrained=False."""
    model = build_model(name=model_name, num_classes=12, pretrained=False)
    model.eval()

    batch = torch.randn(4, 3, 224, 224)
    with torch.no_grad():
        outputs = model(batch)

    assert outputs.shape == (4, 12), f"Expected shape (4, 12), got {outputs.shape}"


@pytest.mark.parametrize("model_name", ["mobilenet_v3", "efficientnet_b0"])
def test_phase1_freezing_and_bn_eval(model_name: str) -> None:
    """Verify Phase 1: backbone is frozen, classifier head requires grad, backbone BN in eval mode."""
    model = build_model(name=model_name, num_classes=12, pretrained=False)
    backbone, head = get_backbone_and_head(model, model_name)

    # Apply Phase 1 freeze
    freeze_backbone(model, model_name)
    set_backbone_bn_eval(model, model_name)

    # 1. Check requires_grad flags
    for name, param in backbone.named_parameters():
        assert not param.requires_grad, f"Backbone parameter {name} should be frozen (requires_grad=False)"

    for name, param in head.named_parameters():
        assert param.requires_grad, f"Head parameter {name} should be trainable (requires_grad=True)"

    # 2. Check BatchNorm eval mode
    bn_count = 0
    for module in backbone.modules():
        if isinstance(module, (nn.BatchNorm2d, nn.modules.batchnorm._BatchNorm)):
            bn_count += 1
            assert not module.training, "Backbone BatchNorm layer must be in eval mode during Phase 1"

    assert bn_count > 0, f"Expected BatchNorm modules in {model_name} backbone, found {bn_count}"


@pytest.mark.parametrize("model_name", ["mobilenet_v3", "efficientnet_b0"])
def test_phase2_unfreezing_and_param_groups(model_name: str) -> None:
    """Verify Phase 2: all parameters trainable, optimizer has 2 param groups with differential LRs."""
    model = build_model(name=model_name, num_classes=12, pretrained=False)

    cfg = {
        "model_name": model_name,
        "epochs": 25,
        "freeze_epochs": 3,
        "learning_rate": 1e-3,
        "unfreeze_lr": 3e-4,
        "backbone_lr_ratio": 0.1,
        "weight_decay": 1e-4,
        "warmup_epochs": 1,
    }

    # Setup Phase 2 optimizer & scheduler
    optimizer, _scheduler = setup_phase_optimizer_and_scheduler(
        model=model,
        model_name=model_name,
        phase=2,
        cfg=cfg,
        steps_per_epoch=10,
    )

    # 1. Check that all parameters require grad
    for name, param in model.named_parameters():
        assert param.requires_grad, f"Parameter {name} should be trainable in Phase 2"

    # 2. Check optimizer parameter groups
    assert len(optimizer.param_groups) == 2, f"Expected 2 parameter groups, got {len(optimizer.param_groups)}"

    backbone_group = optimizer.param_groups[0]
    head_group = optimizer.param_groups[1]

    expected_head_lr = 3e-4
    expected_backbone_lr = 3e-4 * 0.1  # 3e-5

    # Note: initial factor in LinearLR is 0.01
    assert backbone_group["initial_lr"] == pytest.approx(expected_backbone_lr)
    assert head_group["initial_lr"] == pytest.approx(expected_head_lr)


@pytest.mark.parametrize("model_name", ["mobilenet_v3", "efficientnet_b0"])
def test_gradcam_target_layer_features_last(model_name: str) -> None:
    """Verify Grad-CAM target layer is features[-1] for transfer learning models."""
    model = build_model(name=model_name, num_classes=12, pretrained=False)
    target = gradcam_target_layer(model, model_name)

    assert target is model.features[-1], f"Expected target layer to be model.features[-1] for {model_name}"
