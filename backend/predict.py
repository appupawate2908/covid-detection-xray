"""
predict.py — Inference Pipeline
=================================
Wraps the ViT model + XAI + severity staging into a single
callable that the FastAPI endpoint uses.

The model is loaded once at startup and reused across all requests.
"""

import os
import sys
import io
import base64
import contextlib
from datetime import datetime
from typing import Optional

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import ViTForImageClassification

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from model.xai import predict_with_heatmap, preprocess_image, CLASSES
from model.severity import assess_severity, SeverityResult


# ─── Model Singleton ──────────────────────────────────────────────────────────

_model: Optional[ViTForImageClassification] = None
_device: Optional[torch.device] = None


def get_model(model_path: str = 'model/saved/vit_covid_final') -> ViTForImageClassification:
    """
    Load the ViT model once and return the cached instance.

    This function is idempotent — calling it multiple times returns the
    same model object without reloading from disk.
    """
    global _model, _device

    if _model is not None:
        return _model

    _device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f'Model not found at: {model_path}\n'
            f'Please train the model first by running:\n'
            f'  python model/train.py --data data/ --output model/saved/'
        )

    print(f'[predict.py] Loading model from {model_path} on {_device} ...')
    # Force eager attention so hooks can capture attention weights for XAI
    _model = ViTForImageClassification.from_pretrained(
        model_path,
        attn_implementation='eager',
    )
    _model = _model.to(_device)
    _model.eval()
    print(f'[predict.py] Model ready.')

    return _model


# ─── Monte Carlo Dropout ─────────────────────────────────────────────────────

@contextlib.contextmanager
def _mc_dropout_mode(model: ViTForImageClassification, p: float = 0.1):
    """
    Context manager that temporarily enables dropout at inference time.

    ViT-B/16 pre-trained weights have dropout probability 0.0 by default.
    We temporarily set p=0.1 on all Dropout layers and switch them to
    train mode so they stochastically drop activations during forward passes.
    This lets us sample multiple predictions and measure spread (uncertainty).
    """
    dropout_layers = [m for m in model.modules() if isinstance(m, torch.nn.Dropout)]
    original = [(layer.p, layer.training) for layer in dropout_layers]
    for layer in dropout_layers:
        layer.p = p
        layer.train()
    try:
        yield
    finally:
        for layer, (orig_p, orig_training) in zip(dropout_layers, original):
            layer.p = orig_p
            layer.training = orig_training


def run_mc_uncertainty(
    model: ViTForImageClassification,
    image: "Image.Image",
    n_passes: int = 30,
    dropout_p: float = 0.1,
) -> dict:
    """
    Monte Carlo Dropout uncertainty estimation.

    Runs N stochastic forward passes with dropout enabled and measures
    the spread of the softmax outputs across passes.

    Args:
        model:      Loaded ViT model (will be temporarily set to train-dropout mode)
        image:      Input PIL Image (will be preprocessed internally)
        n_passes:   Number of MC forward passes (default 30)
        dropout_p:  Dropout probability to use during MC passes (default 0.1)

    Returns:
        dict:
            mean_probs:        {class: mean probability %}
            std_probs:         {class: std deviation %}
            uncertainty:       float — std % of the top predicted class
            uncertainty_level: "Low" | "Moderate" | "High"
            requires_review:   bool — True if uncertainty is Moderate or High
            mc_passes:         int — number of passes used
    """
    device = next(model.parameters()).device
    tensor = preprocess_image(image).to(device)

    all_probs = []
    with _mc_dropout_mode(model, p=dropout_p):
        for _ in range(n_passes):
            with torch.no_grad():
                outputs = model(pixel_values=tensor)
            probs = F.softmax(outputs.logits, dim=-1).cpu().numpy()[0]
            all_probs.append(probs)

    all_probs = np.array(all_probs)           # (n_passes, n_classes)
    mean_probs = all_probs.mean(axis=0)       # (n_classes,)
    std_probs  = all_probs.std(axis=0)        # (n_classes,)

    top_idx     = int(mean_probs.argmax())
    uncertainty = float(std_probs[top_idx] * 100)

    if uncertainty < 5.0:
        level = "Low"
    elif uncertainty < 15.0:
        level = "Moderate"
    else:
        level = "High"

    return {
        "mean_probs":        {cls: round(float(p) * 100, 2) for cls, p in zip(CLASSES, mean_probs)},
        "std_probs":         {cls: round(float(s) * 100, 2) for cls, s in zip(CLASSES, std_probs)},
        "uncertainty":       round(uncertainty, 2),
        "uncertainty_level": level,
        "requires_review":   level != "Low",
        "mc_passes":         n_passes,
    }


# ─── Inference Pipeline ───────────────────────────────────────────────────────

def run_prediction(image_bytes: bytes, model_path: str = 'model/saved/vit_covid_final') -> dict:
    """
    End-to-end prediction pipeline for a single X-ray image.

    Args:
        image_bytes: Raw image file bytes (JPEG or PNG)
        model_path: Path to the trained ViT model directory

    Returns:
        dict matching the /predict API response schema:
        {
            prediction: str,
            confidence: float,
            probabilities: {class: float, ...},
            severity_level: int,
            severity_label: str,
            severity_colour: str,
            severity_guidance: str,
            heatmap_base64: str,
            timestamp: str
        }

    Raises:
        ValueError: If the image cannot be decoded
        FileNotFoundError: If the model is not found
    """
    # Decode image
    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise ValueError(f'Cannot decode image: {e}')

    # Load (cached) model
    model = get_model(model_path)

    # Run XAI inference: prediction + attention heatmap
    xai_result = predict_with_heatmap(model, image, discard_ratio=0.9, colormap='jet')

    # Monte Carlo Dropout — uncertainty estimation (10 stochastic passes)
    mc = run_mc_uncertainty(model, image, n_passes=10, dropout_p=0.1)

    # Assess severity (use MC mean probabilities for more stable severity)
    severity: SeverityResult = assess_severity(
        predicted_class=xai_result['predicted_class'],
        probabilities=mc['mean_probs']
    )

    # Auto-generate clinical report
    from backend.report import generate_report
    report = generate_report(
        prediction=xai_result['predicted_class'],
        confidence=xai_result['confidence'],
        probabilities=mc['mean_probs'],
        uncertainty=mc['uncertainty'],
        uncertainty_level=mc['uncertainty_level'],
        requires_review=mc['requires_review'],
        severity_level=severity.level,
        severity_label=severity.label,
        severity_guidance=severity.guidance,
    )

    return {
        'prediction':         xai_result['predicted_class'],
        'confidence':         xai_result['confidence'],
        'probabilities':      mc['mean_probs'],
        'severity_level':     severity.level,
        'severity_label':     severity.label,
        'severity_colour':    severity.colour,
        'severity_hex':       severity.hex_colour,
        'severity_guidance':  severity.guidance,
        'severity_icon':      severity.icon,
        'heatmap_base64':     xai_result['overlay_base64'],
        'raw_heatmap_base64': xai_result['heatmap_base64'],
        # Uncertainty (Feature A)
        'uncertainty':        mc['uncertainty'],
        'uncertainty_level':  mc['uncertainty_level'],
        'uncertainty_probs':  mc['std_probs'],
        'requires_review':    mc['requires_review'],
        'mc_passes':          mc['mc_passes'],
        # Clinical report (Feature B)
        'report':             report,
        'timestamp':          datetime.utcnow().isoformat(),
    }


def is_model_loaded() -> bool:
    """Check whether the model singleton has been initialised."""
    return _model is not None


def get_device_info() -> dict:
    """Return runtime device information for the health endpoint."""
    cuda_available = torch.cuda.is_available()
    return {
        'device': str(_device) if _device else ('cuda' if cuda_available else 'cpu'),
        'cuda_available': cuda_available,
        'gpu_name': torch.cuda.get_device_name(0) if cuda_available else None,
        'model_loaded': is_model_loaded(),
    }
