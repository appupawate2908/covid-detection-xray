"""
progression.py — Session-Based Progression Tracker
====================================================
Manages in-memory progression history for serial X-ray scan comparisons.

Each session stores an ordered list of scan results.
Trend analysis compares severity levels across uploads to determine
whether the patient's condition is improving, stable, or worsening.

NOTE: This is an in-memory store — data is cleared on server restart.
      For production use, replace with a database backend.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from model.severity import compute_trend


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class ScanRecord:
    """A single scan result stored in a progression session."""
    scan_id: str
    timestamp: str
    prediction: str
    confidence: float
    probabilities: dict
    severity_level: int
    severity_label: str
    heatmap_base64: str          # Base64-encoded PNG overlay
    notes: Optional[str] = None  # Optional clinician notes

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProgressionSession:
    """A collection of sequential scans for one patient/session."""
    session_id: str
    created_at: str
    scans: List[ScanRecord] = field(default_factory=list)

    def add_scan(self, record: ScanRecord):
        self.scans.append(record)

    def get_severity_history(self) -> List[int]:
        return [s.severity_level for s in self.scans]

    def get_trend(self) -> dict:
        """Compute trend across all scans in this session."""
        history = self.get_severity_history()
        return compute_trend(history)

    def to_dict(self) -> dict:
        return {
            'session_id': self.session_id,
            'created_at': self.created_at,
            'scan_count': len(self.scans),
            'scans': [s.to_dict() for s in self.scans],
            'trend': self.get_trend() if len(self.scans) >= 2 else None,
        }


# ─── In-Memory Store ──────────────────────────────────────────────────────────

class ProgressionStore:
    """
    Thread-safe in-memory store for all active progression sessions.

    In a production deployment this would be replaced with:
        - Redis (for distributed deployments)
        - PostgreSQL / SQLite (for persistent storage)
        - A proper patient management system
    """

    def __init__(self):
        self._sessions: Dict[str, ProgressionSession] = {}

    # ── Session Management ──────────────────────────────────────────────────

    def create_session(self) -> str:
        """Create a new progression session and return its ID."""
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = ProgressionSession(
            session_id=session_id,
            created_at=datetime.utcnow().isoformat()
        )
        return session_id

    def get_session(self, session_id: str) -> Optional[ProgressionSession]:
        """Return the session or None if it does not exist."""
        return self._sessions.get(session_id)

    def session_exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if deleted, False if not found."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> List[dict]:
        """Return summary info for all active sessions."""
        return [
            {
                'session_id': sid,
                'created_at': s.created_at,
                'scan_count': len(s.scans),
                'latest_severity': s.scans[-1].severity_level if s.scans else None,
            }
            for sid, s in self._sessions.items()
        ]

    # ── Scan Management ─────────────────────────────────────────────────────

    def add_scan(
        self,
        session_id: str,
        prediction: str,
        confidence: float,
        probabilities: dict,
        severity_level: int,
        severity_label: str,
        heatmap_base64: str,
        notes: Optional[str] = None
    ) -> ScanRecord:
        """
        Add a scan result to an existing session.

        Creates the session if it does not exist.
        Returns the created ScanRecord.
        """
        if not self.session_exists(session_id):
            # Auto-create if not found
            self._sessions[session_id] = ProgressionSession(
                session_id=session_id,
                created_at=datetime.utcnow().isoformat()
            )

        record = ScanRecord(
            scan_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            prediction=prediction,
            confidence=confidence,
            probabilities=probabilities,
            severity_level=severity_level,
            severity_label=severity_label,
            heatmap_base64=heatmap_base64,
            notes=notes,
        )
        self._sessions[session_id].add_scan(record)
        return record

    def get_session_data(self, session_id: str) -> Optional[dict]:
        """Return full session data as a serialisable dict."""
        session = self.get_session(session_id)
        if session is None:
            return None
        return session.to_dict()

    def get_scan_count(self, session_id: str) -> int:
        session = self.get_session(session_id)
        return len(session.scans) if session else 0

    # ── Analytics ───────────────────────────────────────────────────────────

    def get_trend(self, session_id: str) -> Optional[dict]:
        """Return trend analysis for a session."""
        session = self.get_session(session_id)
        if session is None or len(session.scans) < 2:
            return None
        return session.get_trend()

    def get_severity_timeline(self, session_id: str) -> List[dict]:
        """
        Return a simplified timeline of severity levels for charting.

        Returns list of {timestamp, severity_level, prediction, confidence}
        """
        session = self.get_session(session_id)
        if session is None:
            return []
        return [
            {
                'scan_id': s.scan_id,
                'timestamp': s.timestamp,
                'severity_level': s.severity_level,
                'severity_label': s.severity_label,
                'prediction': s.prediction,
                'confidence': s.confidence,
            }
            for s in session.scans
        ]


# ─── Global store instance (used by FastAPI) ──────────────────────────────────

progression_store = ProgressionStore()
