"""
report.py — Auto-Generated Radiologist-Style Report
=====================================================
Produces a structured clinical report from prediction outputs.
Template-based (no LLM required) — language is tailored per
predicted class, confidence band, and uncertainty level.

No application currently combines ViT-based COVID detection
with uncertainty-aware, auto-generated clinical reports.
This is the novel contribution of this dissertation project.
"""

from datetime import datetime


# ─── Per-class clinical language ─────────────────────────────────────────────

_FINDINGS = {
    "COVID-19": {
        "finding": (
            "The model has identified imaging features consistent with COVID-19 pneumonia. "
            "Typical radiographic features include bilateral, peripheral, lower-lobe-predominant "
            "ground-glass opacities and/or consolidation. The attention map highlights regions "
            "of highest model focus, which may correspond to areas of parenchymal involvement."
        ),
        "impression": (
            "Imaging features are consistent with COVID-19 pneumonia. "
            "Bilateral peripheral opacities with lower-zone predominance are characteristic."
        ),
        "attention_note": (
            "Attention Rollout maps should demonstrate bilateral peripheral focus, "
            "particularly in the lower lung zones. Concentrated unilateral attention "
            "may warrant additional clinical scrutiny."
        ),
    },
    "Viral Pneumonia": {
        "finding": (
            "The model has identified imaging features consistent with viral pneumonia "
            "(non-COVID aetiology). Distribution patterns differ from the typical bilateral "
            "peripheral presentation of COVID-19. Features may include perihilar opacities, "
            "unilateral consolidation, or interstitial infiltrates."
        ),
        "impression": (
            "Imaging features are consistent with viral pneumonia of non-COVID aetiology. "
            "Clinical and microbiological correlation is essential for definitive diagnosis."
        ),
        "attention_note": (
            "Attention maps may highlight perihilar or unilateral lung regions, "
            "consistent with non-COVID viral pneumonia distribution patterns."
        ),
    },
    "Normal": {
        "finding": (
            "The model found no significant pathological features consistent with COVID-19 "
            "or viral pneumonia. Lung fields appear clear with no appreciable consolidation, "
            "ground-glass opacities, or interstitial infiltrates identified."
        ),
        "impression": (
            "No significant radiological abnormality detected. "
            "Lung parenchyma appears clear within the limitations of this AI analysis."
        ),
        "attention_note": (
            "Attention maps should show low-intensity, diffuse distribution across lung fields "
            "with no concentrated high-attention clusters corresponding to pathological regions."
        ),
    },
}

_SEVERITY_GUIDANCE = {
    0: "No urgent action indicated based on AI analysis alone. Routine clinical follow-up as appropriate.",
    1: "Mild abnormality detected. Clinical correlation with symptoms and history is recommended.",
    2: "Moderate concern. Further investigation including CT imaging and laboratory tests is advised.",
    3: "High severity indicated. Urgent clinical review and immediate management consideration required.",
}

_RECOMMENDATION = {
    "COVID-19": {
        0: "Routine monitoring. Correlate with RT-PCR result and clinical presentation.",
        1: "Correlate with RT-PCR and clinical symptoms. Self-isolation and supportive care as per guidelines.",
        2: "Recommend CT chest for further characterisation. Correlate with RT-PCR. Consider hospital assessment.",
        3: "Urgent clinical review required. Hospital admission should be considered. RT-PCR confirmation essential.",
    },
    "Viral Pneumonia": {
        0: "Correlate with clinical history. Microbiological workup recommended if symptomatic.",
        1: "Clinical and microbiological correlation advised. Monitor for symptom progression.",
        2: "Further investigation recommended. Consider sputum culture, blood tests, and CT chest.",
        3: "Urgent clinical review. Inpatient assessment and broad-spectrum antimicrobial therapy may be warranted.",
    },
    "Normal": {
        0: "No immediate action required. If symptomatic, correlate clinically — early disease may not be radiologically apparent.",
        1: "No significant finding. If clinical suspicion remains, repeat imaging or CT may be considered.",
        2: "No significant finding. High clinical suspicion warrants CT chest for higher sensitivity.",
        3: "No significant finding. Clinical symptoms should guide further management.",
    },
}


# ─── Report generator ────────────────────────────────────────────────────────

def generate_report(
    prediction: str,
    confidence: float,
    probabilities: dict,
    uncertainty: float,
    uncertainty_level: str,
    requires_review: bool,
    severity_level: int,
    severity_label: str,
    severity_guidance: str,
) -> dict:
    """
    Generate a structured radiologist-style report from prediction outputs.

    Args:
        prediction:        Predicted class label
        confidence:        Top-class confidence (%)
        probabilities:     Mean class probabilities from MC Dropout (%)
        uncertainty:       MC Dropout std of top class (%)
        uncertainty_level: "Low" | "Moderate" | "High"
        requires_review:   True if uncertainty is Moderate or High
        severity_level:    0–3 severity stage
        severity_label:    Human-readable severity label
        severity_guidance: Severity-specific guidance text

    Returns:
        Structured report dict for JSON serialisation and frontend rendering.
    """
    lang = _FINDINGS.get(prediction, _FINDINGS["Normal"])
    rec  = _RECOMMENDATION.get(prediction, _RECOMMENDATION["Normal"])
    recommendation = rec.get(severity_level, rec[0])

    # Confidence band label
    if confidence >= 85:
        conf_label = "High"
    elif confidence >= 60:
        conf_label = "Moderate"
    elif confidence >= 30:
        conf_label = "Low"
    else:
        conf_label = "Very Low"

    # Uncertainty statement
    if uncertainty_level == "Low":
        uncertainty_statement = (
            f"Model uncertainty is low (±{uncertainty:.1f}%), indicating consistent predictions "
            f"across {30} Monte Carlo Dropout inference passes. Result is considered reliable."
        )
    elif uncertainty_level == "Moderate":
        uncertainty_statement = (
            f"Model uncertainty is moderate (±{uncertainty:.1f}%) across {30} stochastic inference passes. "
            f"The model shows some variability in this prediction. Radiologist review is advised."
        )
    else:
        uncertainty_statement = (
            f"Model uncertainty is high (±{uncertainty:.1f}%) across {30} stochastic inference passes. "
            f"The model is not confident in this prediction. Radiologist review is strongly recommended "
            f"before any clinical action is taken."
        )

    # Warning flag
    warning = None
    if requires_review:
        warning = (
            f"⚠ {uncertainty_level.upper()} UNCERTAINTY — Radiologist review recommended before clinical action."
        )

    # Probability summary lines
    prob_lines = [
        f"{cls}: {prob:.1f}% (±{0:.1f}%)"
        for cls, prob in sorted(probabilities.items(), key=lambda x: -x[1])
    ]

    return {
        "title":                "Chest X-Ray AI Analysis Report",
        "generated_at":         datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "prediction":           prediction,
        "confidence":           round(confidence, 1),
        "confidence_label":     conf_label,
        "finding":              lang["finding"],
        "impression":           lang["impression"],
        "attention_note":       lang["attention_note"],
        "uncertainty":          round(uncertainty, 1),
        "uncertainty_level":    uncertainty_level,
        "uncertainty_statement": uncertainty_statement,
        "requires_review":      requires_review,
        "warning":              warning,
        "severity_level":       severity_level,
        "severity_label":       severity_label,
        "severity_guidance":    severity_guidance or _SEVERITY_GUIDANCE.get(severity_level, ""),
        "recommendation":       recommendation,
        "probability_lines":    prob_lines,
        "method":               "ViT-B/16 + Attention Rollout + Monte Carlo Dropout (N=30)",
        "disclaimer": (
            "RESEARCH PROTOTYPE ONLY — NOT FOR CLINICAL USE. "
            "This report is AI-generated and has not been validated for clinical diagnosis. "
            "All results must be reviewed by a qualified radiologist or clinician before any action. "
            "7156CEM Individual Project — Coventry University."
        ),
    }
