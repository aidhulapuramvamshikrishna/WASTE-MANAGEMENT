"""Inference and image processing service for EcoSort."""

import io
import time
import warnings
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageOps
from wasteml.gradcam import overlay_cam_on_image
from wasteml.transforms import eval_tfms

from app.config import settings
from app.services.registry import LoadedModel, registry

# Treat Pillow decompression bombs as errors (SECURITY.md T2)
Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS
warnings.simplefilter("error", Image.DecompressionBombWarning)


def validate_and_process_upload(raw_bytes: bytes) -> tuple[Image.Image, bytes]:
    """Validate image format, protect against bombs, downscale, and strip EXIF."""
    # Check max file size (8 MB)
    if len(raw_bytes) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"Payload too large. Maximum size is {settings.MAX_UPLOAD_MB} MB.")

    # Pillow decoding & verification
    try:
        test_img = Image.open(io.BytesIO(raw_bytes))
        test_img.verify()
        fmt = (test_img.format or "").upper()
        if fmt not in {"JPEG", "JPG", "PNG", "WEBP"}:
            raise ValueError(f"Unsupported format '{fmt}'. Allowed: JPEG, PNG, WebP.")

        # Reopen after verify
        img = Image.open(io.BytesIO(raw_bytes))
        if img.width * img.height > settings.MAX_IMAGE_PIXELS:
            raise ValueError(
                f"Image resolution {img.width}x{img.height} ({img.width * img.height} pixels) "
                f"exceeds maximum allowed limit of {settings.MAX_IMAGE_PIXELS} pixels."
            )
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Invalid image file: {e}") from e

    # Transpose according to EXIF orientation if present
    img = ImageOps.exif_transpose(img)

    # Convert to standard RGB
    img = img.convert("RGB")

    # Downscale if larger than 1024x1024 while preserving aspect ratio
    if img.width > 1024 or img.height > 1024:
        img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

    # Re-encode as clean JPEG q90 (strips all EXIF metadata per SECURITY.md T3)
    out_io = io.BytesIO()
    img.save(out_io, format="JPEG", quality=90, optimize=True)
    clean_bytes = out_io.getvalue()

    return img, clean_bytes


def run_prediction(
    loaded_model: LoadedModel,
    img: Image.Image,
    explain: bool = True,
) -> dict[str, Any]:
    """Run model inference, calibration scaling, stream mapping, and Grad-CAM explanation."""
    t0 = time.perf_counter()

    # Preprocessing using eval_tfms imported directly from wasteml (no duplicate code)
    tfm = eval_tfms()
    input_tensor = tfm(img).unsqueeze(0).to(loaded_model.device)

    # Forward pass
    with torch.no_grad():
        logits = loaded_model.model(input_tensor)

    # Apply calibration temperature scaling
    T = loaded_model.temperature
    scaled_logits = logits / T
    probs = torch.softmax(scaled_logits, dim=-1).squeeze(0)

    # Top-3 predictions
    top_probs, top_indices = torch.topk(probs, k=min(3, len(loaded_model.class_names)))
    top3 = []
    for p, idx in zip(top_probs, top_indices, strict=False):
        top3.append({
            "label": loaded_model.class_names[idx.item()],
            "confidence": round(float(p.item()), 4),
        })

    top1_label = top3[0]["label"]
    top1_conf = top3[0]["confidence"]
    top1_idx = top_indices[0].item()

    # Uncertainty check
    uncertain = bool(top1_conf < loaded_model.uncertain_threshold)

    # Stream & disposal lookup from classes info
    classes_info = {c["name"]: c for c in registry.get_classes()}
    c_meta = classes_info.get(top1_label, {"stream": "dry", "disposal": "Check local municipal sorting guidelines."})
    stream = c_meta["stream"]
    disposal = c_meta["disposal"]

    # Grad-CAM explanation (under per-model lock)
    gradcam_png_bytes: bytes | None = None
    if explain:
        with loaded_model.lock:
            cam = loaded_model.gradcam_engine.generate(input_tensor, target_class=top1_idx)

        # Overlay on downscaled original image
        img_np = np.array(img)
        overlay = overlay_cam_on_image(img_np, cam, colormap="jet", alpha=0.45)

        overlay_img = Image.fromarray(overlay)
        cam_io = io.BytesIO()
        overlay_img.save(cam_io, format="PNG", optimize=True)
        gradcam_png_bytes = cam_io.getvalue()

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "label": top1_label,
        "stream": stream,
        "confidence": top1_conf,
        "uncertain": uncertain,
        "uncertain_threshold": loaded_model.uncertain_threshold,
        "top3": top3,
        "disposal": disposal,
        "gradcam_png_bytes": gradcam_png_bytes,
        "latency_ms": elapsed_ms,
    }
