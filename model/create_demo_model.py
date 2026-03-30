"""
create_demo_model.py — Demo Model Initialiser
==============================================
Downloads google/vit-base-patch16-224-in21k from HuggingFace and
configures it for 3-class COVID-19 chest X-ray classification.

The classifier head weights are randomly initialised (not trained on data).
This allows the full application stack to run and demonstrate the UI,
XAI heatmaps, and severity staging WITHOUT requiring the COVID-19 dataset.

NOTE: Predictions from this demo model are NOT clinically meaningful.
      Run notebooks/03_model_training.ipynb with real data for accurate results.

Usage:
    python model/create_demo_model.py
"""

import os
import sys

print("=" * 60)
print("COVID-19 X-ray Demo Model Initialiser")
print("=" * 60)
print("\nDownloading base ViT-B/16 pretrained weights from HuggingFace...")
print("(This may take a moment — ~330 MB)")

from transformers import ViTForImageClassification, ViTConfig

CLASSES = ['Normal', 'COVID-19', 'Viral Pneumonia']
ID2LABEL = {i: c for i, c in enumerate(CLASSES)}
LABEL2ID = {c: i for i, c in enumerate(CLASSES)}
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'saved', 'vit_covid_final')

model = ViTForImageClassification.from_pretrained(
    'google/vit-base-patch16-224-in21k',
    num_labels=3,
    id2label=ID2LABEL,
    label2id=LABEL2ID,
    ignore_mismatched_sizes=True,
)
model.eval()

os.makedirs(OUTPUT_DIR, exist_ok=True)
model.save_pretrained(OUTPUT_DIR)

print(f"\nDemo model saved to: {OUTPUT_DIR}")
print("\nParameters:")
total = sum(p.numel() for p in model.parameters())
print(f"  Total parameters: {total:,} (~86M for ViT-B/16)")
print(f"  Classes: {CLASSES}")
print(f"\nNOTE: The classifier head is randomly initialised.")
print("      Predictions are NOT accurate without fine-tuning on COVID-19 data.")
print("      To train properly: run notebooks/03_model_training.ipynb")
print("\nDemo model ready. You can now start the API.")
