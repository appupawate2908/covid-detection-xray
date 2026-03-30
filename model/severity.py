"""
severity.py — 4-Level COVID-19 Severity Staging Module
=======================================================
Maps model confidence scores to a clinically-motivated 4-level severity system.

Severity Levels:
    0 — No Significant Finding (green)   < 30% COVID-19 confidence
    1 — Mild Abnormality       (yellow)  30–59%
    2 — Moderate Concern       (orange)  60–84%
    3 — High Severity Indicated (red)    ≥ 85%

For Normal predictions: always Level 0 regardless of confidence.
For Viral Pneumonia: uses pneumonia confidence with same thresholds.

IMPORTANT: This system is a research prototype only.
           It is NOT a validated clinical diagnostic tool.
"""

from dataclasses import dataclass
from typing import Dict


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class SeverityResult:
    """Encapsulates a severity staging result."""
    level: int           # 0, 1, 2, or 3
    label: str           # Human-readable label
    colour: str          # CSS/Tailwind colour name
    hex_colour: str      # Hex colour code
    guidance: str        # Clinical guidance text (research context only)
    icon: str            # Emoji icon for UI display

    def to_dict(self) -> dict:
        return {
            'level': self.level,
            'label': self.label,
            'colour': self.colour,
            'hex_colour': self.hex_colour,
            'guidance': self.guidance,
            'icon': self.icon,
        }


# ─── Severity Definitions ─────────────────────────────────────────────────────

SEVERITY_DEFINITIONS = {
    0: SeverityResult(
        level=0,
        label='No Significant Finding',
        colour='green',
        hex_colour='#2ecc71',
        guidance=(
            'The model did not detect significant abnormality. '
            'This result should be confirmed by a qualified radiologist. '
            'Routine follow-up as clinically indicated.'
        ),
        icon='✓'
    ),
    1: SeverityResult(
        level=1,
        label='Mild Abnormality',
        colour='yellow',
        hex_colour='#f1c40f',
        guidance=(
            'Mild abnormality detected. The model shows low-to-moderate confidence '
            'in an abnormal finding. Clinical correlation and radiologist review '
            'are recommended. Monitor for symptom progression.'
        ),
        icon='⚠'
    ),
    2: SeverityResult(
        level=2,
        label='Moderate Concern',
        colour='orange',
        hex_colour='#e67e22',
        guidance=(
            'Moderate concern detected. The model shows significant confidence '
            'in a pathological finding. Prompt radiologist review is strongly '
            'recommended. Consider PCR testing and clinical assessment.'
        ),
        icon='⚠⚠'
    ),
    3: SeverityResult(
        level=3,
        label='High Severity Indicated',
        colour='red',
        hex_colour='#e74c3c',
        guidance=(
            'High severity indicated. The model shows very high confidence in '
            'a significant pathological finding consistent with COVID-19 pneumonia. '
            'Urgent radiologist and clinical review is strongly recommended. '
            'This is a research prototype — not a clinical diagnosis.'
        ),
        icon='🔴'
    ),
}

# Confidence thresholds for each level
THRESHOLDS = {
    'level_0_max': 30.0,   # < 30% → Level 0
    'level_1_max': 60.0,   # 30–59% → Level 1
    'level_2_max': 85.0,   # 60–84% → Level 2
    # ≥ 85% → Level 3
}


# ─── Core Staging Logic ───────────────────────────────────────────────────────

def assess_severity(
    predicted_class: str,
    probabilities: Dict[str, float],
) -> SeverityResult:
    """
    Determine the severity level based on prediction and confidence scores.

    Args:
        predicted_class: One of 'Normal', 'COVID-19', 'Viral Pneumonia'
        probabilities: dict mapping class names to percentage probabilities
                       e.g. {'Normal': 5.1, 'COVID-19': 89.4, 'Viral Pneumonia': 5.5}

    Returns:
        SeverityResult dataclass

    Logic:
        - Normal prediction → always Level 0
        - COVID-19 prediction → level based on COVID-19 confidence
        - Viral Pneumonia → level based on Viral Pneumonia confidence
    """
    # Validate
    if predicted_class not in ('Normal', 'COVID-19', 'Viral Pneumonia'):
        raise ValueError(f'Unknown class: {predicted_class}')

    # Normal predictions are always Level 0
    if predicted_class == 'Normal':
        return SEVERITY_DEFINITIONS[0]

    # For pathological predictions, use the predicted class confidence
    confidence = probabilities.get(predicted_class, 0.0)

    return _confidence_to_severity(confidence)


def _confidence_to_severity(confidence: float) -> SeverityResult:
    """
    Map a confidence percentage to a severity level.

    Args:
        confidence: Float in range [0, 100]

    Returns:
        SeverityResult for the appropriate level
    """
    if confidence < THRESHOLDS['level_0_max']:
        return SEVERITY_DEFINITIONS[0]
    elif confidence < THRESHOLDS['level_1_max']:
        return SEVERITY_DEFINITIONS[1]
    elif confidence < THRESHOLDS['level_2_max']:
        return SEVERITY_DEFINITIONS[2]
    else:
        return SEVERITY_DEFINITIONS[3]


# ─── Trend Analysis (for Progression Tracker) ─────────────────────────────────

def compute_trend(severity_history: list) -> dict:
    """
    Compute trend direction between consecutive severity levels.

    Args:
        severity_history: List of severity level ints (oldest to newest)
                          e.g. [2, 3, 2, 1]

    Returns:
        dict with keys:
            direction: 'improving' | 'stable' | 'worsening'
            arrow: ↓ | → | ↑
            colour: CSS colour for arrow
            delta: int (last - first)
            description: str explanation
    """
    if len(severity_history) < 2:
        return {
            'direction': 'stable',
            'arrow': '→',
            'colour': '#95a5a6',
            'delta': 0,
            'description': 'Insufficient data for trend analysis (need ≥ 2 scans)'
        }

    first = severity_history[0]
    last = severity_history[-1]
    delta = last - first

    # Recent trend (last 2 scans)
    recent_delta = severity_history[-1] - severity_history[-2]

    if recent_delta < 0:
        direction = 'improving'
        arrow = '↓'
        colour = '#2ecc71'
        description = f'Severity decreasing — improving trend (Level {severity_history[-2]} → {last})'
    elif recent_delta > 0:
        direction = 'worsening'
        arrow = '↑'
        colour = '#e74c3c'
        description = f'Severity increasing — worsening trend (Level {severity_history[-2]} → {last})'
    else:
        direction = 'stable'
        arrow = '→'
        colour = '#f39c12'
        description = f'Severity unchanged — stable (Level {last})'

    return {
        'direction': direction,
        'arrow': arrow,
        'colour': colour,
        'delta': delta,
        'description': description
    }


# ─── Utility ──────────────────────────────────────────────────────────────────

def get_severity_badge_config(level: int) -> dict:
    """Return UI badge configuration for a given severity level."""
    if level not in SEVERITY_DEFINITIONS:
        level = 0
    srv = SEVERITY_DEFINITIONS[level]
    return {
        'level': srv.level,
        'label': srv.label,
        'colour': srv.colour,
        'hex_colour': srv.hex_colour,
        'icon': srv.icon,
    }


def severity_summary() -> str:
    """Return a human-readable summary of all severity levels."""
    lines = ['4-Level Severity Staging System', '=' * 35]
    for level, srv in SEVERITY_DEFINITIONS.items():
        threshold = {
            0: '< 30%',
            1: '30–59%',
            2: '60–84%',
            3: '≥ 85%'
        }[level]
        lines.append(f'Level {level}: {srv.label} ({threshold} confidence)')
        lines.append(f'  {srv.guidance[:80]}...')
    return '\n'.join(lines)


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print(severity_summary())
    print()

    test_cases = [
        ('Normal',          {'Normal': 96.0, 'COVID-19': 2.0, 'Viral Pneumonia': 2.0}),
        ('COVID-19',        {'Normal': 5.0,  'COVID-19': 25.0, 'Viral Pneumonia': 70.0}),
        ('COVID-19',        {'Normal': 5.0,  'COVID-19': 45.0, 'Viral Pneumonia': 50.0}),
        ('COVID-19',        {'Normal': 3.0,  'COVID-19': 72.0, 'Viral Pneumonia': 25.0}),
        ('COVID-19',        {'Normal': 2.0,  'COVID-19': 91.4, 'Viral Pneumonia': 6.6}),
        ('Viral Pneumonia', {'Normal': 5.0,  'COVID-19': 10.0, 'Viral Pneumonia': 85.0}),
    ]

    print('Severity Assessment Test Cases:')
    print('-' * 60)
    for cls, probs in test_cases:
        result = assess_severity(cls, probs)
        conf = probs[cls]
        print(f'  [{cls}] conf={conf:.0f}% → Level {result.level}: {result.label}')

    print()
    print('Trend Analysis Test:')
    histories = [[0, 0, 1], [3, 2, 1, 0], [1, 1, 1], [0, 1, 2, 3]]
    for hist in histories:
        trend = compute_trend(hist)
        print(f'  {hist} → {trend["arrow"]} {trend["direction"]}: {trend["description"]}')
