"""
train.py — ViT-B/16 Training Script (CLI)
==========================================
Trains a Vision Transformer for 3-class chest X-ray classification.

Usage:
    python model/train.py --data data/ --output model/saved/ --epochs 15

Strategy:
    Stage 1 (5 epochs, lr=1e-4): Freeze encoder, train classifier head only
    Stage 2 (10 epochs, lr=2e-5): Unfreeze all, full fine-tuning with cosine LR
"""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from transformers import ViTForImageClassification
from PIL import Image


# ─── Constants ────────────────────────────────────────────────────────────────

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]
IMG_SIZE = 224
CLASSES = ['Normal', 'COVID-19', 'Viral Pneumonia']
CLASS2IDX = {c: i for i, c in enumerate(CLASSES)}
ID2LABEL = {i: c for i, c in enumerate(CLASSES)}
LABEL2ID = {c: i for i, c in enumerate(CLASSES)}


# ─── Dataset ──────────────────────────────────────────────────────────────────

class ChestXrayDataset(Dataset):
    """Chest X-ray dataset loading from class-organised directories."""

    def __init__(self, root_dir: str, transform=None):
        self.transform = transform
        self.samples: list = []
        for cls in CLASSES:
            cls_dir = os.path.join(root_dir, cls)
            if not os.path.isdir(cls_dir):
                continue
            for fname in sorted(os.listdir(cls_dir)):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                    self.samples.append((os.path.join(cls_dir, fname), CLASS2IDX[cls]))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        path, label = self.samples[idx]
        image = Image.open(path).convert('RGB')
        if self.transform:
            image = self.transform(image)
        return image, label

    def get_class_weights(self) -> torch.Tensor:
        """Inverse-frequency class weights for imbalanced datasets."""
        from collections import Counter
        counts = Counter(lbl for _, lbl in self.samples)
        total = len(self.samples)
        n_classes = len(CLASSES)
        weights = [total / (n_classes * counts.get(i, 1)) for i in range(n_classes)]
        return torch.FloatTensor(weights)


# ─── Transforms ───────────────────────────────────────────────────────────────

def build_transforms():
    train_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE + 20, IMG_SIZE + 20)),
        transforms.RandomCrop(IMG_SIZE),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
        transforms.Grayscale(num_output_channels=3),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.Grayscale(num_output_channels=3),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])
    return train_tf, val_tf


# ─── Training Utilities ───────────────────────────────────────────────────────

def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = correct = total = 0
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        loss = criterion(model(pixel_values=images).logits, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * images.size(0)
        preds = model(pixel_values=images).logits.argmax(dim=1)
        correct += preds.eq(labels).sum().item()
        total += labels.size(0)
    return total_loss / total, correct / total


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = correct = total = 0
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        logits = model(pixel_values=images).logits
        total_loss += criterion(logits, labels).item() * images.size(0)
        correct += logits.argmax(dim=1).eq(labels).sum().item()
        total += labels.size(0)
    return total_loss / total, correct / total


# ─── Main Training Loop ───────────────────────────────────────────────────────

def train(args):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'Device: {device}')

    # Data
    train_tf, val_tf = build_transforms()
    train_ds = ChestXrayDataset(os.path.join(args.data, 'train'), train_tf)
    val_ds   = ChestXrayDataset(os.path.join(args.data, 'val'),   val_tf)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                               num_workers=args.workers, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False,
                               num_workers=args.workers, pin_memory=True)

    class_weights = train_ds.get_class_weights().to(device)
    print(f'Train: {len(train_ds)} | Val: {len(val_ds)}')
    print(f'Class weights: {class_weights.tolist()}')

    # Model
    print(f'\nLoading {args.pretrained} ...')
    model = ViTForImageClassification.from_pretrained(
        args.pretrained,
        num_labels=len(CLASSES),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True
    ).to(device)

    criterion = nn.CrossEntropyLoss(weight=class_weights)
    history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}
    best_val_acc = 0.0
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Stage 1: Head-only ─────────────────────────────────────────────────────
    print(f'\n=== Stage 1: Head-only ({args.stage1_epochs} epochs, lr={args.stage1_lr}) ===')
    for p in model.parameters(): p.requires_grad = False
    for p in model.classifier.parameters(): p.requires_grad = True

    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=args.stage1_lr, weight_decay=0.01
    )

    for epoch in range(1, args.stage1_epochs + 1):
        t0 = time.time()
        tl, ta = train_one_epoch(model, train_loader, criterion, optimizer, device)
        vl, va = evaluate(model, val_loader, criterion, device)
        elapsed = time.time() - t0
        _update_history(history, tl, ta, vl, va)
        if va > best_val_acc:
            best_val_acc = va
            torch.save(model.state_dict(), output_dir / 'vit_covid_stage1_best.pth')
        print(f'  Epoch {epoch:02d}/{args.stage1_epochs} | '
              f'Loss {tl:.4f}/{vl:.4f} | Acc {ta:.4f}/{va:.4f} | {elapsed:.0f}s')

    # ── Stage 2: Full fine-tuning ──────────────────────────────────────────────
    print(f'\n=== Stage 2: Full fine-tune ({args.stage2_epochs} epochs, lr={args.stage2_lr}) ===')
    for p in model.parameters(): p.requires_grad = True

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.stage2_lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.stage2_epochs)

    for epoch in range(1, args.stage2_epochs + 1):
        t0 = time.time()
        tl, ta = train_one_epoch(model, train_loader, criterion, optimizer, device)
        vl, va = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0
        _update_history(history, tl, ta, vl, va)
        if va > best_val_acc:
            best_val_acc = va
            model.save_pretrained(output_dir / 'vit_covid_best')
        print(f'  Epoch {epoch:02d}/{args.stage2_epochs} | '
              f'Loss {tl:.4f}/{vl:.4f} | Acc {ta:.4f}/{va:.4f} | '
              f'LR {scheduler.get_last_lr()[0]:.2e} | {elapsed:.0f}s')

    # ── Save final model ───────────────────────────────────────────────────────
    model.save_pretrained(output_dir / 'vit_covid_final')
    with open(output_dir / 'training_history.json', 'w') as f:
        json.dump(history, f, indent=2)

    print(f'\nBest Val Acc: {best_val_acc:.4f}')
    print(f'Model saved: {output_dir / "vit_covid_final"}')
    print(f'History saved: {output_dir / "training_history.json"}')


def _update_history(history, tl, ta, vl, va):
    history['train_loss'].append(round(tl, 6))
    history['train_acc'].append(round(ta, 6))
    history['val_loss'].append(round(vl, 6))
    history['val_acc'].append(round(va, 6))


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description='Train ViT-B/16 for COVID-19 X-ray detection')
    p.add_argument('--data',         default='data/',
                   help='Root data dir with train/ val/ test/ subdirectories')
    p.add_argument('--output',       default='model/saved/',
                   help='Directory to save model weights and history')
    p.add_argument('--pretrained',   default='google/vit-base-patch16-224-in21k',
                   help='HuggingFace model ID for pretrained weights')
    p.add_argument('--batch-size',   type=int, default=32)
    p.add_argument('--workers',      type=int, default=4)
    p.add_argument('--stage1-epochs', type=int, default=5)
    p.add_argument('--stage1-lr',    type=float, default=1e-4)
    p.add_argument('--stage2-epochs', type=int, default=10)
    p.add_argument('--stage2-lr',    type=float, default=2e-5)
    p.add_argument('--seed',         type=int, default=42)
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    train(args)
