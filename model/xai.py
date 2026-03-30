"""
xai.py — Attention Rollout Heatmap Generator
=============================================
Implements attention rollout for ViT-B/16 to produce faithful saliency maps.

Attention rollout (Abnar & Zuidema, 2020):
    A_rollout = A_1 @ A_2 @ ... @ A_n
    where A_i is the attention matrix at layer i (averaged over heads),
    with residual identity added at each step.

The [CLS] token row of the final rollout matrix represents
the influence of each patch on the classification decision.
Reshape 196 patches → 14×14 grid → bilinear upsample → 224×224 overlay.

CLI usage:
    python model/xai.py --image path/to/xray.jpg --model model/saved/vit_covid_final
"""

import argparse
import os
import sys
import io
import base64
from typing import Tuple, Optional

import numpy as np
import torch
import torch.nn.functional as F
import cv2
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from PIL import Image
from transformers import ViTForImageClassification

# ─── Constants ────────────────────────────────────────────────────────────────

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406])
IMAGENET_STD  = np.array([0.229, 0.224, 0.225])
IMG_SIZE = 224
PATCH_SIZE = 16
N_PATCHES = (IMG_SIZE // PATCH_SIZE) ** 2  # 196
GRID_SIZE = IMG_SIZE // PATCH_SIZE          # 14

CLASSES = ['Normal', 'COVID-19', 'Viral Pneumonia']

# ─── Preprocessing ────────────────────────────────────────────────────────────

def preprocess_image(image: Image.Image) -> torch.Tensor:
    """
    Preprocess a PIL Image for ViT-B/16 inference.

    Steps:
        1. Convert to RGB (handles greyscale DICOM-derived X-rays)
        2. Resize to 224×224
        3. Normalise with ImageNet statistics

    Returns:
        Tensor of shape (1, 3, 224, 224)
    """
    img = image.convert('RGB').resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
    arr = np.array(img, dtype=np.float32) / 255.0
    arr = (arr - IMAGENET_MEAN) / IMAGENET_STD
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).float()
    return tensor


# ─── Attention Rollout ────────────────────────────────────────────────────────

class AttentionRollout:
    """
    Computes attention rollout for a HuggingFace ViTForImageClassification model.

    Uses forward hooks on ViTSelfAttention layers to capture attention probabilities
    (compatible with transformers 4.x and 5.x, where output_attentions API changed).
    """

    def __init__(self, model: ViTForImageClassification, discard_ratio: float = 0.9):
        """
        Args:
            model: Loaded ViTForImageClassification model (in eval mode)
            discard_ratio: Fraction of lowest attention weights to zero out
                           before rollout (reduces noise, default 0.9)
        """
        self.model = model
        self.discard_ratio = discard_ratio
        self.attention_weights: list = []
        self._hooks: list = []
        self._register_hooks()

    def _register_hooks(self):
        """
        Attach forward hooks to ViTSelfAttention layers.
        In transformers 5.x, ViTSelfAttention.forward() returns
        (context_layer, attention_probs) — output[1] is the attention matrix.
        """
        for layer in self.model.vit.encoder.layer:
            # Hook on the self-attention module (layer.attention.attention)
            hook = layer.attention.attention.register_forward_hook(self._hook_fn)
            self._hooks.append(hook)

    def _hook_fn(self, module, input, output):
        """
        Capture attention probabilities from the ViTSelfAttention output.
        output is (context_layer, attention_probs):
            attention_probs shape: (batch, heads, seq_len, seq_len)
        """
        if isinstance(output, tuple) and len(output) >= 2:
            attn_probs = output[1]
            if attn_probs is not None:
                self.attention_weights.append(attn_probs.detach().cpu())

    def remove_hooks(self):
        """Clean up all registered hooks."""
        for h in self._hooks:
            h.remove()
        self._hooks.clear()

    def _compute_rollout(self) -> np.ndarray:
        """
        Compute attention rollout from captured attention weights.
        Returns a (GRID_SIZE, GRID_SIZE) heatmap in [0, 1].
        """
        if not self.attention_weights:
            # Fallback: return uniform heatmap if no attentions captured
            return np.ones((GRID_SIZE, GRID_SIZE)) / (GRID_SIZE * GRID_SIZE)

        # seq_len = 197 (1 CLS + 196 patch tokens for 224×224 / 16×16 patches)
        seq_len = self.attention_weights[0].shape[-1]
        rollout = torch.eye(seq_len)  # identity starting point

        for attn in self.attention_weights:
            # Average over heads: (batch, heads, seq, seq) → (seq, seq)
            attn_mat = attn.squeeze(0).mean(dim=0)

            # Discard low-attention values (noise reduction)
            flat = attn_mat.flatten()
            k = int(self.discard_ratio * flat.numel())
            if k > 0 and k < flat.numel():
                threshold = flat.kthvalue(k).values
                attn_mat = torch.where(attn_mat >= threshold, attn_mat,
                                       torch.zeros_like(attn_mat))

            # Add residual identity and row-normalise
            attn_mat = attn_mat + torch.eye(seq_len)
            row_sums = attn_mat.sum(dim=-1, keepdim=True)
            attn_mat = attn_mat / row_sums.clamp(min=1e-8)

            rollout = attn_mat @ rollout

        # CLS token row (index 0) → patch tokens (indices 1:)
        cls_rollout = rollout[0, 1:].numpy()  # (196,)
        heatmap = cls_rollout.reshape(GRID_SIZE, GRID_SIZE)

        # Normalise to [0, 1]
        mn, mx = heatmap.min(), heatmap.max()
        heatmap = (heatmap - mn) / (mx - mn + 1e-8)
        return heatmap

    def __call__(self, image_tensor: torch.Tensor) -> np.ndarray:
        """
        Run forward pass (triggering hooks) and compute attention rollout.

        Args:
            image_tensor: Preprocessed tensor (1, 3, 224, 224)

        Returns:
            rollout: np.ndarray of shape (GRID_SIZE, GRID_SIZE) in [0, 1]
        """
        self.attention_weights.clear()
        device = next(self.model.parameters()).device

        with torch.no_grad():
            # Hooks capture attention probs during this forward pass
            self.model(pixel_values=image_tensor.to(device))

        heatmap = self._compute_rollout()
        return heatmap


# ─── Overlay Generation ───────────────────────────────────────────────────────

def create_heatmap_overlay(
    original_image: Image.Image,
    attention_map: np.ndarray,
    colormap: str = 'jet',
    alpha: float = 0.45
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Produce a coloured attention heatmap overlaid on the original X-ray.

    Args:
        original_image: PIL Image (will be resized to 224×224 if needed)
        attention_map: 2D array of shape (14, 14) in [0, 1]
        colormap: Matplotlib colormap name ('jet', 'hot', 'inferno')
        alpha: Transparency of the heatmap overlay (0 = invisible, 1 = opaque)

    Returns:
        overlay: uint8 RGB array (224, 224, 3) — X-ray with heatmap overlay
        heatmap_rgb: uint8 RGB array (224, 224, 3) — pure heatmap (no overlay)
    """
    # Resize original to 224×224
    orig_arr = np.array(original_image.convert('RGB').resize((IMG_SIZE, IMG_SIZE)))

    # Upsample attention map 14×14 → 224×224
    attn_upsampled = cv2.resize(
        attention_map.astype(np.float32),
        (IMG_SIZE, IMG_SIZE),
        interpolation=cv2.INTER_LINEAR
    )

    # Apply colourmap
    cmap = plt.get_cmap(colormap)
    heatmap_rgba = cmap(attn_upsampled)                          # (H, W, 4)
    heatmap_rgb = (heatmap_rgba[:, :, :3] * 255).astype(np.uint8)  # (H, W, 3)

    # Blend with original image
    overlay = cv2.addWeighted(orig_arr, 1 - alpha, heatmap_rgb, alpha, 0)

    return overlay, heatmap_rgb


def pil_to_base64(image_array: np.ndarray) -> str:
    """Convert an RGB uint8 numpy array to a base64-encoded PNG string."""
    pil_img = Image.fromarray(image_array)
    buf = io.BytesIO()
    pil_img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('utf-8')


# ─── Full Inference + XAI Pipeline ───────────────────────────────────────────

def predict_with_heatmap(
    model: ViTForImageClassification,
    image: Image.Image,
    discard_ratio: float = 0.9,
    colormap: str = 'jet'
) -> dict:
    """
    Run full inference + XAI in a single call.

    Args:
        model: Loaded ViT model (eval mode, on device)
        image: Input PIL Image
        discard_ratio: Noise reduction threshold for rollout
        colormap: Heatmap colourmap

    Returns:
        dict containing:
            predicted_class: str label
            probabilities: dict {class_name: float percentage}
            confidence: float (max probability %)
            overlay_base64: str — base64 PNG of X-ray + heatmap overlay
            heatmap_base64: str — base64 PNG of pure heatmap
            attention_map: np.ndarray (14, 14) raw attention map
    """
    # Preprocess
    tensor = preprocess_image(image)

    # Attention rollout
    rollout = AttentionRollout(model, discard_ratio=discard_ratio)
    attention_map = rollout(tensor)

    # Classification (separate forward pass; hooks already fired in rollout above)
    device = next(model.parameters()).device
    with torch.no_grad():
        outputs = model(pixel_values=tensor.to(device))
    probs = F.softmax(outputs.logits, dim=-1).cpu().numpy()[0]

    pred_idx = int(probs.argmax())
    confidence = float(probs[pred_idx] * 100)

    # Heatmap overlay
    overlay, heatmap_rgb = create_heatmap_overlay(image, attention_map, colormap=colormap)

    return {
        'predicted_class': CLASSES[pred_idx],
        'probabilities': {cls: round(float(p) * 100, 2) for cls, p in zip(CLASSES, probs)},
        'confidence': round(confidence, 2),
        'overlay_base64': pil_to_base64(overlay),
        'heatmap_base64': pil_to_base64(heatmap_rgb),
        'attention_map': attention_map,
    }


# ─── Visualisation ────────────────────────────────────────────────────────────

def save_heatmap_figure(
    original_image: Image.Image,
    result: dict,
    output_path: str
) -> None:
    """
    Save a 3-panel figure: original | overlay | heatmap.

    Args:
        original_image: Input PIL Image
        result: Output from predict_with_heatmap()
        output_path: Path to save the figure (.png)
    """
    orig_arr = np.array(original_image.convert('RGB').resize((IMG_SIZE, IMG_SIZE)))
    overlay = np.frombuffer(base64.b64decode(result['overlay_base64']), dtype=np.uint8)
    overlay = np.array(Image.open(io.BytesIO(base64.b64decode(result['overlay_base64']))))
    heatmap = np.array(Image.open(io.BytesIO(base64.b64decode(result['heatmap_base64']))))

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    axes[0].imshow(orig_arr, cmap='gray')
    axes[0].set_title('Original X-ray', fontsize=12)
    axes[0].axis('off')

    axes[1].imshow(overlay)
    axes[1].set_title(
        f'Attention Overlay\n({result["predicted_class"]}, {result["confidence"]:.1f}%)',
        fontsize=12
    )
    axes[1].axis('off')

    axes[2].imshow(heatmap)
    axes[2].set_title('Attention Heatmap', fontsize=12)
    axes[2].axis('off')

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap='jet', norm=plt.Normalize(vmin=0, vmax=1))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=axes[2], fraction=0.046, pad=0.04)
    cbar.set_label('Attention Weight', fontsize=10)

    plt.suptitle(
        f'ViT-B/16 Attention Rollout — {result["predicted_class"]}',
        fontsize=14, fontweight='bold'
    )
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=150)
    print(f'Saved heatmap figure: {output_path}')
    plt.close()


# ─── CLI ──────────────────────────────────────────────────────────────────────

def load_model(model_path: str) -> ViTForImageClassification:
    """
    Load a saved ViT model from HuggingFace format directory.

    Forces eager attention implementation so that attention weights are
    returned by the attention modules (SDPA returns None for weights).
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = ViTForImageClassification.from_pretrained(
        model_path,
        attn_implementation='eager',
    )
    model = model.to(device)
    model.eval()
    return model


def main():
    parser = argparse.ArgumentParser(
        description='Generate attention rollout heatmap for a chest X-ray image'
    )
    parser.add_argument('--image',  required=True, help='Path to input X-ray image')
    parser.add_argument('--model',  default='model/saved/vit_covid_final',
                        help='Path to trained ViT model directory')
    parser.add_argument('--output', default='heatmap_output.png',
                        help='Output path for heatmap figure')
    parser.add_argument('--discard-ratio', type=float, default=0.9,
                        help='Attention noise discard ratio (0–1, default 0.9)')
    parser.add_argument('--colormap', default='jet',
                        choices=['jet', 'hot', 'inferno', 'plasma'],
                        help='Heatmap colourmap')
    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.image):
        print(f'Error: Image not found: {args.image}')
        sys.exit(1)
    if not os.path.exists(args.model):
        print(f'Error: Model not found: {args.model}')
        print('Run notebooks/03_model_training.ipynb first.')
        sys.exit(1)

    print(f'Loading model from {args.model} ...')
    model = load_model(args.model)

    print(f'Processing image: {args.image}')
    image = Image.open(args.image)
    result = predict_with_heatmap(model, image,
                                   discard_ratio=args.discard_ratio,
                                   colormap=args.colormap)

    print(f'\n=== Prediction Results ===')
    print(f'  Class:      {result["predicted_class"]}')
    print(f'  Confidence: {result["confidence"]:.2f}%')
    print('  Probabilities:')
    for cls, prob in result['probabilities'].items():
        print(f'    {cls}: {prob:.2f}%')

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    save_heatmap_figure(image, result, args.output)
    print(f'\nDone. Heatmap saved to: {args.output}')


if __name__ == '__main__':
    main()
