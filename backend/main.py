"""
main.py — FastAPI Application
==============================
COVID-19 Chest X-ray Detection API with Explainable AI

Endpoints:
    POST   /predict                    — X-ray upload → prediction + heatmap + severity
    POST   /progression/add            — Add scan to session progression history
    GET    /progression/{session_id}   — Retrieve all scans for a session
    DELETE /progression/{session_id}   — Clear a session
    POST   /progression/create         — Create a new session (returns session_id)
    GET    /progression/list           — List all active sessions
    GET    /health                     — API health check

CORS is configured for the Vite dev server at http://localhost:5173.

Usage:
    cd backend
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.predict import run_prediction, get_model, get_device_info, is_model_loaded
from backend.progression import progression_store
from backend.validators import validate_xray_image

# ─── Model Path ───────────────────────────────────────────────────────────────

MODEL_PATH = os.environ.get('MODEL_PATH', 'model/saved/vit_covid_final')

# ─── Lifespan: Startup / Shutdown ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model at startup to avoid cold-start latency on first request."""
    print('=' * 60)
    print('COVID-19 X-ray Detection API — Starting up')
    print('=' * 60)
    try:
        get_model(MODEL_PATH)
        print('Model loaded successfully at startup.')
    except FileNotFoundError as e:
        print(f'WARNING: {e}')
        print('API will start but /predict will fail until model is trained.')
    yield
    print('API shutting down.')


# ─── App Initialisation ───────────────────────────────────────────────────────

app = FastAPI(
    title='COVID-19 X-ray Detection API',
    description=(
        'Deep Learning-Based COVID-19 Detection from Chest X-ray Images '
        'with Explainable AI (Attention Rollout) and Severity Staging. '
        '\n\n**RESEARCH PROTOTYPE ONLY — NOT A CLINICAL DIAGNOSTIC TOOL.**'
    ),
    version='1.0.0',
    lifespan=lifespan,
)

# CORS — allow Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:3000',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class AddScanRequest(BaseModel):
    session_id: str
    prediction: str
    confidence: float
    probabilities: dict
    severity_level: int
    severity_label: str
    heatmap_base64: str
    notes: Optional[str] = None


class CreateSessionResponse(BaseModel):
    session_id: str
    message: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get('/health', tags=['Utility'])
async def health_check():
    """API health check — returns model and runtime status."""
    device_info = get_device_info()
    return {
        'status': 'ok',
        'model_loaded': is_model_loaded(),
        'model_path': MODEL_PATH,
        **device_info,
        'active_sessions': len(progression_store.list_sessions()),
    }


@app.post('/predict', tags=['Prediction'])
async def predict(file: UploadFile = File(...)):
    """
    Upload a chest X-ray image and receive:
    - Classification (Normal / COVID-19 / Viral Pneumonia)
    - Confidence scores
    - 4-level severity staging
    - Attention rollout heatmap (base64 PNG overlay)

    **Accepted formats:** JPEG, PNG

    **DISCLAIMER:** This is a research prototype only.
    Results must NOT be used for clinical diagnosis.
    """
    # Validate file type
    if file.content_type not in ('image/jpeg', 'image/png', 'image/jpg'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported file type: {file.content_type}. Use JPEG or PNG.'
        )

    # Read image bytes
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Empty file uploaded.'
        )

    # Validate that the image looks like a chest X-ray
    is_xray, reason = validate_xray_image(image_bytes)
    if not is_xray:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={'error': 'not_xray', 'message': reason}
        )

    # Run prediction
    try:
        result = run_prediction(image_bytes, model_path=MODEL_PATH)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Prediction failed: {str(e)}'
        )

    return JSONResponse(content=result)


# ─── Progression Tracker Endpoints ────────────────────────────────────────────

@app.post('/progression/create', tags=['Progression'])
async def create_session():
    """Create a new progression tracking session. Returns a session_id."""
    session_id = progression_store.create_session()
    return CreateSessionResponse(
        session_id=session_id,
        message='Session created. Use session_id with /progression/add to add scans.'
    )


@app.post('/progression/add', tags=['Progression'])
async def add_to_progression(body: AddScanRequest):
    """
    Add a scan result to a session's progression history.

    The session is auto-created if it does not exist.
    Typically called client-side after a successful /predict call.
    """
    try:
        record = progression_store.add_scan(
            session_id=body.session_id,
            prediction=body.prediction,
            confidence=body.confidence,
            probabilities=body.probabilities,
            severity_level=body.severity_level,
            severity_label=body.severity_label,
            heatmap_base64=body.heatmap_base64,
            notes=body.notes,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    scan_count = progression_store.get_scan_count(body.session_id)
    trend = progression_store.get_trend(body.session_id)

    return {
        'success': True,
        'scan_id': record.scan_id,
        'scan_count': scan_count,
        'trend': trend,
        'message': f'Scan added. Session now has {scan_count} scan(s).'
    }


@app.get('/progression/{session_id}', tags=['Progression'])
async def get_progression(session_id: str):
    """
    Retrieve all scans and trend analysis for a session.

    Returns:
        - All scan records (prediction, confidence, severity, heatmap, timestamp)
        - Trend direction (improving / stable / worsening)
        - Severity timeline for charting
    """
    data = progression_store.get_session_data(session_id)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Session not found: {session_id}'
        )

    timeline = progression_store.get_severity_timeline(session_id)
    data['severity_timeline'] = timeline
    return data


@app.delete('/progression/{session_id}', tags=['Progression'])
async def delete_progression(session_id: str):
    """Delete a progression session and all its scan history."""
    deleted = progression_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Session not found: {session_id}'
        )
    return {'success': True, 'message': f'Session {session_id} deleted.'}


@app.get('/progression', tags=['Progression'])
async def list_sessions():
    """List all active progression sessions (summary only)."""
    return {
        'sessions': progression_store.list_sessions(),
        'total': len(progression_store.list_sessions()),
    }


# ─── Error Handlers ───────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={'detail': f'Internal server error: {str(exc)}'}
    )


# ─── Dev entry point ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
