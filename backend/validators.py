"""
validators.py — X-ray Image Heuristic Validation
==================================================
Rejects clearly non-X-ray images before running inference.
Three checks: aspect ratio, near-grayscale, intensity distribution.
Size is intentionally NOT checked — X-rays can come in any resolution.
"""

import io
import numpy as np
from PIL import Image


def validate_xray_image(image_bytes: bytes) -> tuple[bool, str]:
    """
    Returns (True, "") if the image plausibly looks like a chest X-ray.
    Returns (False, reason) if any heuristic check fails.

    Checks:
        1. Aspect ratio must be between 0.5 and 2.0
        2. Image must be near-grayscale (low colour channel variance)
        3. Intensity distribution must span dark and bright regions
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return False, "Cannot decode image"

    w, h = img.size

    # Check 1 — aspect ratio (chest X-rays are roughly square)
    ratio = w / h
    if ratio < 0.5 or ratio > 2.0:
        return False, "Aspect ratio is too extreme for a chest X-ray"

    arr = np.array(img, dtype=np.float32)

    # Check 2 — near-grayscale (X-rays have very low colour saturation)
    # Compute mean pixel value per channel; a colour photo will have very
    # different R/G/B means, an X-ray will have almost identical means.
    channel_means = arr.mean(axis=(0, 1))   # shape (3,) — [R, G, B]
    if channel_means.std() > 15:
        return False, "Image appears to be a colour photo, not an X-ray"

    # Check 3 — intensity distribution (X-rays have wide dynamic range:
    # dark lung fields and bright bone/soft-tissue regions)
    grey = arr.mean(axis=2)                  # shape (H, W)
    dark_fraction   = (grey < 100).mean()    # fraction of darker pixels
    bright_fraction = (grey > 180).mean()    # fraction of brighter pixels
    # Loose check — just ensure image isn't a completely flat/uniform colour
    if dark_fraction < 0.10 or bright_fraction < 0.01:
        return False, "Intensity distribution does not match a chest X-ray"

    return True, ""
