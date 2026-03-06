# Deep Learning-Based COVID-19 Detection from Chest X-ray Images Using Explainable AI

**Module:** 7156CEM Individual Project · **Student:** Channabasavanna Santosh Pawate (16150425)
**Supervisor:** Dr. Mark Elshaw · **Institution:** Coventry University

> **RESEARCH PROTOTYPE ONLY** — Not validated for clinical use. All results require qualified radiologist review.

---

## Overview

This project implements a full-stack research prototype for COVID-19 detection from chest X-ray images. It combines:

- **Vision Transformer (ViT-B/16)** for 3-class classification (Normal / COVID-19 / Viral Pneumonia)
- **Attention Rollout XAI** — mathematically faithful heatmaps showing which image regions the model focused on
- **4-Level Severity Staging** — translating confidence scores into clinically-motivated severity levels
- **Progression Tracker** — comparing serial X-ray uploads over time with trend analysis
- **Full-stack web app** — FastAPI backend + React (Vite + Tailwind) frontend

### Research Gap Addressed

Existing systems (Wang & Wong 2020, Chowdhury et al. 2020, Brunese et al. 2020) are black-box classifiers
with no explainability, severity staging, or temporal tracking. This project integrates all three.

---

## Project Structure

```
covid-xray-explainable/
├── notebooks/
│   ├── 01_data_exploration.ipynb      # EDA, class distribution, sample images
│   ├── 02_preprocessing.ipynb         # Augmentation, normalisation pipeline
│   ├── 03_model_training.ipynb        # ViT fine-tuning with training curves
│   └── 04_evaluation.ipynb            # Accuracy, F1, confusion matrix, ROC
├── model/
│   ├── train.py                       # Training script (CLI)
│   ├── evaluate.py                    # Full metrics report
│   ├── xai.py                         # Attention rollout heatmap generator
│   ├── severity.py                    # 4-level severity staging
│   └── saved/                         # Saved model weights (.pth / HuggingFace format)
├── backend/
│   ├── main.py                        # FastAPI app + all endpoints
│   ├── predict.py                     # Inference pipeline (model singleton)
│   ├── progression.py                 # Session-based progression tracker
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                    # Root component + routing
│   │   ├── components/
│   │   │   ├── UploadZone.jsx         # Drag-drop X-ray upload
│   │   │   ├── ResultCard.jsx         # Prediction + confidence + severity
│   │   │   ├── HeatmapViewer.jsx      # Side-by-side X-ray + attention map
│   │   │   ├── SeverityBadge.jsx      # 4-level severity indicator
│   │   │   ├── ProgressionTracker.jsx # Timeline of multiple uploads
│   │   │   └── InterpretabilityReport.jsx  # Structured AI explanation
│   │   └── main.jsx
│   ├── index.html
│   ├── tailwind.config.js
│   └── vite.config.js
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| ML Model | Vision Transformer (ViT-B/16) via HuggingFace Transformers |
| ML Framework | PyTorch 2.2 + torchvision |
| XAI | ViT attention rollout (Abnar & Zuidema, 2020) |
| Backend | FastAPI 0.110 |
| Frontend | React 18 (Vite) + Tailwind CSS 3 |
| Image processing | OpenCV, PIL |
| Visualisation | Matplotlib, NumPy |

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- CUDA GPU recommended (CPU inference supported but slower)

### 1. Python Environment

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Dataset Download

Download datasets from official sources (no Kaggle):

| Dataset | Source | Classes |
|---|---|---|
| COVIDx CXR-4 | https://github.com/lindawangg/COVID-Net | COVID-19 |
| NIH ChestX-ray14 | https://nihcc.app.box.com/v/ChestXray-NIHCC | Normal + Viral Pneumonia |
| ieee8023 | https://github.com/ieee8023/covid-chestxray-dataset | COVID-19 supplement |

Organise into:
```
data/
  train/
    Normal/
    COVID-19/
    Viral Pneumonia/
  val/
    ...
  test/
    ...
```

Use `notebooks/02_preprocessing.ipynb` → `create_stratified_split()` for automatic 70/15/15 split.

### 3. Train the Model

**Option A — Jupyter Notebook (recommended for dissertation):**
```
jupyter notebook notebooks/03_model_training.ipynb
```

**Option B — CLI:**
```bash
python model/train.py \
  --data data/ \
  --output model/saved/ \
  --stage1-epochs 5 \
  --stage2-epochs 10
```

Target: >95% test accuracy. Model saved to `model/saved/vit_covid_final/`.

### 4. Run Evaluation

```bash
python model/evaluate.py --model model/saved/vit_covid_final --data data/ --output reports/
```

Outputs: confusion matrix, ROC curves, classification report in `reports/`.

### 5. Generate XAI Heatmap (CLI test)

```bash
python model/xai.py --image path/to/sample.jpg --model model/saved/vit_covid_final
```

### 6. Start the Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API documentation: http://localhost:8000/docs

### 7. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/predict` | Upload X-ray → prediction + heatmap + severity |
| `POST` | `/progression/add` | Add result to session progression history |
| `GET` | `/progression/{session_id}` | Retrieve all scans for a session |
| `DELETE` | `/progression/{session_id}` | Clear session history |
| `POST` | `/progression/create` | Create new session |
| `GET` | `/health` | API health check |

### `/predict` Response

```json
{
  "prediction": "COVID-19",
  "confidence": 91.4,
  "probabilities": {
    "Normal": 3.1,
    "COVID-19": 91.4,
    "Viral Pneumonia": 5.5
  },
  "severity_level": 3,
  "severity_label": "High Severity Indicated",
  "severity_guidance": "...",
  "heatmap_base64": "<base64 PNG>",
  "timestamp": "2026-03-02T10:30:00"
}
```

---

## Severity Staging

| Level | Confidence | Label | Colour |
|---|---|---|---|
| 0 | < 30% | No Significant Finding | Green |
| 1 | 30–59% | Mild Abnormality | Yellow |
| 2 | 60–84% | Moderate Concern | Orange |
| 3 | ≥ 85% | High Severity Indicated | Red |

Normal predictions are always Level 0.

---

## XAI: Attention Rollout

Implemented in `model/xai.py`. Method: Abnar & Zuidema (2020).

1. Hook into all 12 ViT attention layers
2. Average attention weights over 12 heads per layer
3. Discard lowest 90% of weights (noise reduction)
4. Multiply matrices across layers: `A_rollout = A_1 @ A_2 @ ... @ A_12`
5. Extract CLS→patch attention: shape (196,) → reshape to (14, 14)
6. Bilinear upsample to (224, 224)
7. Apply jet colourmap + blend with original X-ray

**Advantage over Grad-CAM:** Attention rollout is mathematically faithful to the transformer's
actual information routing. Grad-CAM relies on gradient approximations and is prone to
highlighting non-anatomical regions (Brunese et al. 2020 limitation).

---

## Verification Checklist

1. `notebooks/03_model_training.ipynb` → trains, saves `.pth`, plots training curves
2. `notebooks/04_evaluation.ipynb` → accuracy >95%, confusion matrix + F1 printed
3. `python model/xai.py --image sample.jpg` → heatmap overlay image saved
4. `uvicorn main:app --reload` → API starts on http://localhost:8000
5. `npm run dev` → React app at http://localhost:5173
6. Upload COVID-19 X-ray → "COVID-19", Level 2-3, heatmap highlights lungs
7. Upload Normal X-ray → "Normal", Level 0, green badge
8. Upload 3 scans → Progression Tracker shows timeline + trend arrow

---

## Key References

- Wang & Wong (2020). COVID-Net. *Scientific Reports*.
- Chowdhury et al. (2020). COVID-19 detection using CNNs. *IEEE Access*.
- Brunese et al. (2020). CNN + Grad-CAM. *Computers & Methods in Biomedicine*.
- Zhang et al. (2023). ViT for medical imaging. *IEEE J. Biomedical & Health Informatics*.
- Khan et al. (2020). CoroNet (Xception). *Computers in Biology and Medicine*.
- Abnar & Zuidema (2020). Quantifying attention flow in transformers. *ACL 2020*.
- Dosovitskiy et al. (2020). An image is worth 16×16 words. *ICLR 2021*.

---

## Disclaimer

This prototype was developed for the 7156CEM Individual Project module at Coventry University.
It is a research tool only. It has not been validated in clinical settings and must not be
used for medical diagnosis. All results require review by a qualified radiologist.
