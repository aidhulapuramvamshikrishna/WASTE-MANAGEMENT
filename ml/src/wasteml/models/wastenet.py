"""WasteNet: Custom Convolutional Neural Network from scratch for waste classification.

Architecture (ARCHITECTURE.md §4.2):
5 blocks of [Conv3x3 - BatchNorm - ReLU x2 -> MaxPool]
Channels: 32 -> 64 -> 128 -> 256 -> 384
Block 1 starts with stride=2 conv to reduce activation memory by 4x.
Followed by Global Average Pooling (GAP) -> Dropout(0.4) -> Linear(384 -> 12).
Trained from scratch with Kaiming He normal weight initialization for Conv/BN
and small Normal(0, 0.01) initialization for Linear classifier head.
"""

import torch
from torch import nn


class ConvBlock(nn.Module):
    """Two Conv3x3-BN-ReLU sequences followed by 2x2 MaxPool.

    stride1: stride for the first convolution (default 1; set to 2 for stem downsampling).
    """

    def __init__(self, in_channels: int, out_channels: int, stride1: int = 1):
        super().__init__()
        self.conv1 = nn.Conv2d(
            in_channels, out_channels, kernel_size=3, stride=stride1, padding=1, bias=False
        )
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.relu1 = nn.ReLU(inplace=True)

        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.relu2 = nn.ReLU(inplace=True)

        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.relu1(self.bn1(self.conv1(x)))
        x = self.relu2(self.bn2(self.conv2(x)))
        x = self.pool(x)
        return x


class WasteNet(nn.Module):
    """Custom 10-layer CNN with 5 two-conv blocks, GAP, and classifier head.

    Block 1 stem starts with stride-2 conv to reduce activation memory by 4x.
    """

    def __init__(self, num_classes: int = 12, dropout_rate: float = 0.4):
        super().__init__()
        self.num_classes = num_classes

        # 5 Convolutional Blocks: 3 -> 32 -> 64 -> 128 -> 256 -> 384
        # Block 1 starts with stride=2 for 4x activation memory reduction
        self.block1 = ConvBlock(3, 32, stride1=2)  # 224x224 -> 112x112 -> pool 56x56
        self.block2 = ConvBlock(32, 64)            # 56x56 -> pool 28x28
        self.block3 = ConvBlock(64, 128)           # 28x28 -> pool 14x14
        self.block4 = ConvBlock(128, 256)          # 14x14 -> pool 7x7
        self.block5 = ConvBlock(256, 384)          # 7x7   -> pool 3x3

        # Global Average Pooling & Head
        self.gap = nn.AdaptiveAvgPool2d((1, 1))
        self.flatten = nn.Flatten()
        self.dropout = nn.Dropout(p=dropout_rate)
        self.classifier = nn.Linear(384, num_classes)

        # Initialize weights
        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0.0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1.0)
                nn.init.constant_(m.bias, 0.0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0.0, 0.01)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0.0)

    @property
    def target_conv_layer(self) -> nn.Module:
        """Target layer for Grad-CAM explainability: last conv layer in block5."""
        return self.block5.conv2

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.block4(x)
        x = self.block5(x)
        x = self.gap(x)
        x = self.flatten(x)
        x = self.dropout(x)
        x = self.classifier(x)
        return x

    def count_parameters(self) -> int:
        """Count total trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
