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
from datetime import datetime
from typing import Optional

import torch
from PIL import Image
from transformers import ViTForImageClassification

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from model.xai import predict_with_heatmap
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

    # Assess severity
    severity: SeverityResult = assess_severity(
        predicted_class=xai_result['predicted_class'],
        probabilities=xai_result['probabilities']
    )

    return {
        'prediction': xai_result['predicted_class'],
        'confidence': xai_result['confidence'],
        'probabilities': xai_result['probabilities'],
        'severity_level': severity.level,
        'severity_label': severity.label,
        'severity_colour': severity.colour,
        'severity_hex': severity.hex_colour,
        'severity_guidance': severity.guidance,
        'severity_icon': severity.icon,
        'heatmap_base64': xai_result['overlay_base64'],   # X-ray + heatmap overlay
        'raw_heatmap_base64': xai_result['heatmap_base64'],  # Pure heatmap
        'timestamp': datetime.utcnow().isoformat(),
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
