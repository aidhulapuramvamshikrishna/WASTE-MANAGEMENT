"""Hand-written Grad-CAM implementation using PyTorch forward and backward hooks.

No external libraries (such as pytorch-grad-cam) are used, adhering strictly
to ARCHITECTURE.md §4.7.
"""

from pathlib import Path
from typing import Any, Self

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torch import nn


class GradCAM:
    """Manual Grad-CAM implementation via forward and backward module hooks.

    Computes activation heatmaps by weighting feature activation maps with
    gradients pooled across spatial dimensions.

    Args:
        model: PyTorch model in eval mode.
        target_layer: The convolutional layer whose activations/gradients to track.
    """

    def __init__(self, model: nn.Module, target_layer: nn.Module) -> None:
        self.model = model
        self.target_layer = target_layer
        self.activations: torch.Tensor | None = None
        self.gradients: torch.Tensor | None = None
        self._hooks: list[Any] = []
        self._register_hooks()

    def _register_hooks(self) -> None:
        def forward_hook(module: nn.Module, inp: Any, out: torch.Tensor) -> None:
            self.activations = out

        def backward_hook(module: nn.Module, grad_inp: Any, grad_out: tuple[torch.Tensor, ...]) -> None:
            self.gradients = grad_out[0]

        h1 = self.target_layer.register_forward_hook(forward_hook)
        h2 = self.target_layer.register_full_backward_hook(backward_hook)
        self._hooks.extend([h1, h2])

    def remove_hooks(self) -> None:
        """Remove forward and backward hooks from the model."""
        for hook in self._hooks:
            hook.remove()
        self._hooks.clear()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.remove_hooks()

    def generate(
        self,
        input_tensor: torch.Tensor,
        target_class: int | None = None,
    ) -> np.ndarray:
        """Generate normalized 2D Grad-CAM heatmap for an input image tensor.

        Args:
            input_tensor: Image tensor of shape (1, C, H, W) or (C, H, W).
            target_class: Target class index. If None, uses top-1 predicted class.

        Returns:
            np.ndarray: 2D float32 heatmap of shape (H, W) with values in [0, 1].
        """
        if input_tensor.dim() == 3:
            input_tensor = input_tensor.unsqueeze(0)

        device = next(self.model.parameters()).device
        input_tensor = input_tensor.to(device)
        _b, _c, h, w = input_tensor.shape

        self.model.eval()
        self.model.zero_grad(set_to_none=True)

        with torch.enable_grad():
            inp_var = input_tensor.clone().detach().requires_grad_(False)
            logits = self.model(inp_var)

            if target_class is None:
                target_class = int(logits.argmax(dim=-1).item())

            score = logits[0, target_class]
            score.backward(retain_graph=False)

        if self.activations is None or self.gradients is None:
            raise RuntimeError("Grad-CAM hooks failed to capture activations or gradients.")

        # Spatial average pooling of gradients: weights alpha_k = (1 / Z) * sum(gradients)
        # activations: (1, C, H', W'), gradients: (1, C, H', W')
        weights = torch.mean(self.gradients, dim=(2, 3), keepdim=True)

        # Weighted combination of activation maps followed by ReLU
        cam = torch.sum(weights * self.activations, dim=1, keepdim=True)
        cam = F.relu(cam)

        # Upsample heatmap to match input tensor spatial dimensions (H, W)
        cam = F.interpolate(cam, size=(h, w), mode="bilinear", align_corners=False)
        cam_np = cam.squeeze().detach().cpu().numpy()

        # Min-max normalization to [0, 1]
        c_min = float(cam_np.min())
        c_max = float(cam_np.max())
        if c_max > c_min:
            cam_np = (cam_np - c_min) / (c_max - c_min)
        else:
            cam_np = np.zeros_like(cam_np)

        return cam_np.astype(np.float32)


def overlay_cam_on_image(
    image: Image.Image | np.ndarray,
    heatmap: np.ndarray,
    colormap: str = "jet",
    alpha: float = 0.45,
) -> np.ndarray:
    """Overlay 2D float heatmap on RGB image with colormap blending.

    Args:
        image: PIL Image or (H, W, 3) uint8 numpy array.
        heatmap: 2D float numpy array in range [0, 1].
        colormap: Matplotlib colormap name (default 'jet' as per ARCHITECTURE §5).
        alpha: Blending weight for heatmap overlay (0.0 = original, 1.0 = heatmap).

    Returns:
        np.ndarray: (H, W, 3) uint8 blended RGB image.
    """
    if isinstance(image, Image.Image):
        img_np = np.array(image.convert("RGB"))
    else:
        img_np = image.copy()

    h, w = img_np.shape[:2]

    # Resize heatmap if shape differs from image
    if heatmap.shape != (h, w):
        hm_pil = Image.fromarray((heatmap * 255).astype(np.uint8))
        hm_resized = np.array(hm_pil.resize((w, h), Image.Resampling.BILINEAR)) / 255.0
    else:
        hm_resized = heatmap

    # Apply colormap to heatmap
    cmap = plt.get_cmap(colormap)
    heatmap_colored = (cmap(hm_resized)[:, :, :3] * 255).astype(np.uint8)

    # Linear alpha blend
    blended = (1.0 - alpha) * img_np.astype(np.float32) + alpha * heatmap_colored.astype(np.float32)
    blended = np.clip(blended, 0, 255).astype(np.uint8)
    return blended


def save_overlay(overlay: np.ndarray, output_path: str | Path) -> None:
    """Save RGB overlay image as PNG."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    pil_img = Image.fromarray(overlay)
    pil_img.save(p, format="PNG")
