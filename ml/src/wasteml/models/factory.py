"""Model factory and Grad-CAM target layer registry for WasteML."""

from torch import nn
from torchvision.models import (
    EfficientNet_B0_Weights,
    MobileNet_V3_Large_Weights,
    efficientnet_b0,
    mobilenet_v3_large,
)

from wasteml.models.wastenet import WasteNet

SUPPORTED_MODELS: list[str] = ["wastenet", "mobilenet_v3", "efficientnet_b0"]


def build_model(name: str, num_classes: int = 12, pretrained: bool = False) -> nn.Module:
    """Build and initialize model by name.

    Args:
        name: One of 'wastenet', 'mobilenet_v3', 'efficientnet_b0'.
        num_classes: Number of output material classes (default 12).
        pretrained: If True, loads ImageNet pretrained weights for transfer models.
    """
    model_key = name.lower().strip()

    if model_key == "wastenet":
        model = WasteNet(num_classes=num_classes)

    elif model_key == "mobilenet_v3":
        weights = MobileNet_V3_Large_Weights.IMAGENET1K_V2 if pretrained else None
        model = mobilenet_v3_large(weights=weights)
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = nn.Linear(in_features, num_classes)

    elif model_key == "efficientnet_b0":
        weights = EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
        model = efficientnet_b0(weights=weights)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, num_classes)

    else:
        raise ValueError(
            f"Unsupported model name '{name}'. Choose from: {SUPPORTED_MODELS}"
        )

    return model


def get_backbone_and_head(model: nn.Module, name: str) -> tuple[nn.Module, nn.Module]:
    """Return (backbone, head) modules for transfer learning and layer freezing.

    Args:
        model: Instantiated PyTorch model.
        name: Architecture name.
    """
    model_key = name.lower().strip()
    if model_key in ["mobilenet_v3", "efficientnet_b0"]:
        return model.features, model.classifier
    elif model_key == "wastenet":
        return model, model.classifier
    else:
        raise ValueError(f"Unknown model name '{name}' for backbone/head split")


def gradcam_target_layer(model: nn.Module, name: str) -> nn.Module:
    """Return target layer for Grad-CAM activation mapping.

    Args:
        model: Loaded model instance.
        name: Model architecture name.
    """
    model_key = name.lower().strip()

    if model_key == "wastenet":
        if hasattr(model, "target_conv_layer"):
            return model.target_conv_layer
        return model.block5.conv2

    elif model_key in ["mobilenet_v3", "efficientnet_b0"]:
        return model.features[-1]

    else:
        raise ValueError(f"Unknown model name '{name}' for Grad-CAM target layer")
