"""
evaluate.py — Full Model Evaluation Report
===========================================
Generates a comprehensive evaluation report for the trained ViT-B/16 model.

Outputs:
    - Classification report (precision, recall, F1 per class + macro)
    - Confusion matrix (counts + normalised)
    - ROC-AUC curves (one-vs-rest per class)
    - Per-class metrics bar chart
    - Summary JSON

Usage:
    python model/evaluate.py --model model/saved/vit_covid_final --data data/ --output reports/
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import torch
import torch.nn.functional as F
from PIL import Image
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_curve, auc, ConfusionMatrixDisplay,
    precision_score, recall_score, f1_score
)
from sklearn.preprocessing import label_binarize
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from transformers import ViTForImageClassification


CLASSES = ['Normal', 'COVID-19', 'Viral Pneumonia']
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]
IMG_SIZE = 224
CLASS_COLORS = ['#2ecc71', '#e74c3c', '#f39c12']


# ─── Dataset ──────────────────────────────────────────────────────────────────

class ChestXrayDataset(Dataset):
    CLASS2IDX = {c: i for i, c in enumerate(CLASSES)}

    def __init__(self, root_dir, transform=None):
        self.transform = transform
        self.samples = []
        for cls in CLASSES:
            d = os.path.join(root_dir, cls)
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    self.samples.append((os.path.join(d, f), self.CLASS2IDX[cls]))

    def __len__(self): return len(self.samples)

    def __getitem__(self, idx):
        p, l = self.samples[idx]
        img = Image.open(p).convert('RGB')
        if self.transform: img = self.transform(img)
        return img, l


# ─── Inference ────────────────────────────────────────────────────────────────

@torch.no_grad()
def run_inference(model, loader, device):
    model.eval()
    labels_list, preds_list, probs_list = [], [], []
    for images, labels in loader:
        images = images.to(device)
        logits = model(pixel_values=images).logits
        probs = F.softmax(logits, dim=1).cpu().numpy()
        preds = probs.argmax(axis=1)
        labels_list.extend(labels.numpy())
        preds_list.extend(preds)
        probs_list.extend(probs)
    return (np.array(labels_list),
            np.array(preds_list),
            np.array(probs_list))


# ─── Plotting ─────────────────────────────────────────────────────────────────

def plot_confusion_matrix(y_true, y_pred, output_dir):
    cm = confusion_matrix(y_true, y_pred)
    cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    disp = ConfusionMatrixDisplay(cm, display_labels=CLASSES)
    disp.plot(ax=axes[0], colorbar=False, cmap='Blues')
    axes[0].set_title('Confusion Matrix (Counts)', fontweight='bold')
    axes[0].tick_params(axis='x', labelrotation=15)

    im = axes[1].imshow(cm_norm, cmap='Blues', vmin=0, vmax=1)
    plt.colorbar(im, ax=axes[1])
    axes[1].set_xticks(range(len(CLASSES)))
    axes[1].set_yticks(range(len(CLASSES)))
    axes[1].set_xticklabels(CLASSES, rotation=15)
    axes[1].set_yticklabels(CLASSES)
    axes[1].set_xlabel('Predicted')
    axes[1].set_ylabel('True')
    axes[1].set_title('Confusion Matrix (Normalised)', fontweight='bold')
    for i in range(len(CLASSES)):
        for j in range(len(CLASSES)):
            axes[1].text(j, i, f'{cm_norm[i,j]:.2f}', ha='center', va='center',
                         color='white' if cm_norm[i, j] > 0.5 else 'black')

    plt.suptitle('ViT-B/16 Confusion Matrix', fontsize=13, fontweight='bold')
    plt.tight_layout()
    out = Path(output_dir) / 'figures' / 'confusion_matrix.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, bbox_inches='tight', dpi=150)
    plt.close()
    print(f'Saved: {out}')


def plot_roc_curves(y_true, y_prob, output_dir):
    y_bin = label_binarize(y_true, classes=[0, 1, 2])
    fig, ax = plt.subplots(figsize=(8, 6))

    aucs = {}
    for i, (cls, color) in enumerate(zip(CLASSES, CLASS_COLORS)):
        fpr, tpr, _ = roc_curve(y_bin[:, i], y_prob[:, i])
        roc_auc = auc(fpr, tpr)
        aucs[cls] = round(roc_auc, 4)
        ax.plot(fpr, tpr, color=color, lw=2, label=f'{cls} (AUC={roc_auc:.4f})')

    ax.plot([0, 1], [0, 1], 'k--', lw=1, alpha=0.5)
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1.05])
    ax.set_xlabel('False Positive Rate', fontsize=11)
    ax.set_ylabel('True Positive Rate', fontsize=11)
    ax.set_title('ROC Curves — One-vs-Rest', fontsize=12, fontweight='bold')
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out = Path(output_dir) / 'figures' / 'roc_curves.png'
    plt.savefig(out, bbox_inches='tight', dpi=150)
    plt.close()
    print(f'Saved: {out}')
    return aucs


def plot_per_class_metrics(y_true, y_pred, y_prob, output_dir):
    metric_names = ['Precision', 'Recall', 'F1']
    metric_colors = ['#3498db', '#2ecc71', '#e74c3c']
    x = np.arange(len(CLASSES))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5))
    for j, (metric, color) in enumerate(zip(metric_names, metric_colors)):
        vals = [
            precision_score(y_true == i, y_pred == i) if metric == 'Precision'
            else recall_score(y_true == i, y_pred == i) if metric == 'Recall'
            else f1_score(y_true == i, y_pred == i)
            for i in range(len(CLASSES))
        ]
        ax.bar(x + j * width - width, vals, width, label=metric, color=color, alpha=0.85)

    ax.set_xlabel('Class')
    ax.set_ylabel('Score')
    ax.set_title('Per-Class Metrics', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(CLASSES)
    ax.set_ylim([0, 1.1])
    ax.legend()
    ax.axhline(y=0.95, color='black', linestyle=':', alpha=0.4)
    ax.grid(True, alpha=0.2, axis='y')
    plt.tight_layout()
    out = Path(output_dir) / 'figures' / 'per_class_metrics.png'
    plt.savefig(out, bbox_inches='tight', dpi=150)
    plt.close()
    print(f'Saved: {out}')


# ─── Main ─────────────────────────────────────────────────────────────────────

def evaluate(args):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'figures').mkdir(exist_ok=True)

    # Load model
    print(f'Loading model: {args.model}')
    model = ViTForImageClassification.from_pretrained(args.model).to(device)
    model.eval()

    # Load test data
    val_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.Grayscale(num_output_channels=3),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])
    test_ds = ChestXrayDataset(os.path.join(args.data, 'test'), val_tf)
    test_loader = DataLoader(test_ds, batch_size=64, shuffle=False, num_workers=4)
    print(f'Test set: {len(test_ds)} images')

    # Inference
    print('Running inference ...')
    y_true, y_pred, y_prob = run_inference(model, test_loader, device)

    # Metrics
    acc = (y_true == y_pred).mean()
    macro_f1 = f1_score(y_true, y_pred, average='macro')
    report = classification_report(y_true, y_pred, target_names=CLASSES, digits=4)

    print(f'\n=== Classification Report ===')
    print(report)
    print(f'Test Accuracy: {acc*100:.2f}%')
    print(f'Macro F1:      {macro_f1:.4f}')

    # Plots
    plot_confusion_matrix(y_true, y_pred, output_dir)
    aucs = plot_roc_curves(y_true, y_prob, output_dir)
    plot_per_class_metrics(y_true, y_pred, y_prob, output_dir)

    # Save text report
    report_path = output_dir / 'classification_report.txt'
    with open(report_path, 'w') as f:
        f.write('ViT-B/16 COVID-19 Chest X-ray Classification\n')
        f.write('=' * 50 + '\n\n')
        f.write(f'Test Accuracy: {acc*100:.2f}%\n')
        f.write(f'Macro F1:      {macro_f1:.4f}\n\n')
        f.write(report)
        f.write('\nROC-AUC per class:\n')
        for cls, roc_auc in aucs.items():
            f.write(f'  {cls}: {roc_auc}\n')
    print(f'\nReport saved: {report_path}')

    # Save summary JSON
    summary = {
        'test_accuracy': round(float(acc), 4),
        'macro_f1': round(float(macro_f1), 4),
        'roc_auc': aucs,
        'n_test_samples': len(y_true),
    }
    with open(output_dir / 'eval_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f'Summary JSON: {output_dir / "eval_summary.json"}')


def parse_args():
    p = argparse.ArgumentParser(description='Evaluate trained ViT model')
    p.add_argument('--model',  default='model/saved/vit_covid_final')
    p.add_argument('--data',   default='data/')
    p.add_argument('--output', default='reports/')
    return p.parse_args()


if __name__ == '__main__':
    evaluate(parse_args())
