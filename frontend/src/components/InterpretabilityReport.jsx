import { useState } from 'react'

/* ─── Collapsible section ──────────────────────────────── */
function Section({ title, badge, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="card overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-5 py-4 text-left transition-colors duration-150"
        style={{ background: open ? '#fff' : 'var(--bg)' }}
        onClick={() => setOpen(v => !v)}
      >
        <div className="flex items-center gap-2.5">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
               style={{ transform: open ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
            <path d="M5 3l4 4-4 4" stroke="var(--text-4)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="font-semibold text-sm" style={{ color: 'var(--text-1)' }}>{title}</span>
        </div>
        {badge && (
          <span className="text-xs font-medium px-2 py-0.5 rounded-full"
                style={{ background: 'var(--blue-light)', color: 'var(--blue)', border: '1px solid var(--blue-border)' }}>
            {badge}
          </span>
        )}
      </button>
      {open && (
        <div className="px-5 pb-5 pt-1 space-y-3" style={{ borderTop: '1px solid var(--border)' }}>
          {children}
        </div>
      )}
    </div>
  )
}

/* ─── Key/value row ────────────────────────────────────── */
function KV({ label, value, accent }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2"
         style={{ borderBottom: '1px solid var(--border)' }}>
      <span className="text-xs font-medium" style={{ color: 'var(--text-3)' }}>{label}</span>
      <span className="text-xs font-semibold text-right" style={{ color: accent || 'var(--text-1)' }}>{value}</span>
    </div>
  )
}

/* ─── Probability bar ──────────────────────────────────── */
function ProbBar({ cls, prob, isTop }) {
  const color = cls === 'COVID-19' ? '#ef4444' : cls === 'Normal' ? '#16a34a' : '#d97706'
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs font-medium">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: color }} />
          <span style={{ color: isTop ? color : 'var(--text-3)' }}>
            {cls}
            {isTop && <span className="ml-1 text-[10px] font-bold">▲</span>}
          </span>
        </div>
        <span style={{ color: isTop ? color : 'var(--text-3)' }}>{prob.toFixed(2)}%</span>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
        <div className="h-full rounded-full confidence-bar"
             style={{ width: `${prob}%`, background: color, opacity: isTop ? 1 : 0.3 }} />
      </div>
    </div>
  )
}

/* ─── Explanations per class ───────────────────────────── */
const EXPLAIN = {
  'Normal': {
    summary:   'The model found no significant pathological features consistent with COVID-19 or viral pneumonia. Lung fields appear clear.',
    attention: 'Attention maps should show diffuse, low-intensity distribution across lung fields with no concentrated high-attention clusters.',
    clinical:  'High-confidence Normal classification suggests clear lung parenchyma. Early-stage or subtle disease may still be missed — clinical correlation is essential.',
  },
  'COVID-19': {
    summary:   'The model detected imaging features consistent with COVID-19 pneumonia — typically bilateral, peripheral ground-glass opacities or consolidation.',
    attention: 'Attention maps should highlight bilateral peripheral lung regions. Unilateral or central focus warrants additional radiologist scrutiny.',
    clinical:  'COVID-19 pneumonia on CXR typically presents as bilateral peripheral, lower-lobe-predominant opacities. CT is more sensitive for early disease. PCR confirmation required.',
  },
  'Viral Pneumonia': {
    summary:   'The model detected features consistent with viral pneumonia (non-COVID). Distribution patterns differ from typical COVID-19 bilateral peripheral presentation.',
    attention: 'Attention may highlight perihilar or unilateral regions — characteristic of non-COVID viral pneumonia.',
    clinical:  'Viral pneumonia may present as unilateral or bilateral opacities, often with perihilar distribution. Clinical correlation with PCR is essential.',
  },
}

/* ─── Clinical report card ─────────────────────────────── */
function ClinicalReport({ report }) {
  if (!report) return null
  const uncColor =
    report.uncertainty_level === 'Low'      ? '#16a34a' :
    report.uncertainty_level === 'Moderate' ? '#ca8a04' : '#dc2626'
  const confColor =
    report.confidence_label === 'High'     ? '#16a34a' :
    report.confidence_label === 'Moderate' ? '#ca8a04' :
    report.confidence_label === 'Low'      ? '#ea580c' : '#dc2626'

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4" style={{ background: 'linear-gradient(135deg,#0d1f35,#1a3c5f)' }}>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <p className="text-xs font-bold tracking-widest uppercase mb-1" style={{ color: 'rgba(255,255,255,0.5)' }}>
              AI-Generated · 7156CEM Coventry University
            </p>
            <p className="font-extrabold text-lg text-white leading-tight">{report.title}</p>
          </div>
          <p className="text-xs font-mono" style={{ color: 'rgba(255,255,255,0.45)' }}>{report.generated_at}</p>
        </div>
      </div>

      <div className="p-5 space-y-4">
        {/* Warning banner */}
        {report.warning && (
          <div className="flex items-start gap-3 px-4 py-3 rounded-xl text-sm font-semibold"
               style={{ background: '#fff7ed', border: '1px solid #fed7aa', color: '#c2410c' }}>
            <span className="mt-0.5 shrink-0">⚠</span>
            <span>{report.warning}</span>
          </div>
        )}

        {/* Key metrics row */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'PREDICTION',   value: report.prediction,                  color: report.prediction === 'COVID-19' ? '#ef4444' : report.prediction === 'Normal' ? '#16a34a' : '#d97706' },
            { label: 'CONFIDENCE',   value: `${report.confidence}% (${report.confidence_label})`, color: confColor },
            { label: 'UNCERTAINTY',  value: `±${report.uncertainty}% (${report.uncertainty_level})`, color: uncColor },
          ].map(({ label, value, color }) => (
            <div key={label} className="rounded-xl px-3 py-3 text-center"
                 style={{ background: 'var(--bg)', border: '1px solid var(--border)' }}>
              <p className="text-[10px] font-bold tracking-widest mb-1" style={{ color: 'var(--text-4)' }}>{label}</p>
              <p className="text-xs font-bold leading-tight" style={{ color }}>{value}</p>
            </div>
          ))}
        </div>

        {/* Findings */}
        <div>
          <p className="text-xs font-bold tracking-widest uppercase mb-2" style={{ color: 'var(--text-4)' }}>Findings</p>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text-2)' }}>{report.finding}</p>
        </div>

        {/* Impression */}
        <div className="rounded-xl p-4" style={{ background: 'var(--blue-light)', border: '1px solid var(--blue-border)' }}>
          <p className="text-xs font-bold tracking-widest uppercase mb-1.5" style={{ color: 'var(--blue)' }}>Impression</p>
          <p className="text-sm font-semibold leading-relaxed" style={{ color: '#1e40af' }}>{report.impression}</p>
        </div>

        {/* Uncertainty statement */}
        <div>
          <p className="text-xs font-bold tracking-widest uppercase mb-2" style={{ color: 'var(--text-4)' }}>
            Uncertainty Analysis · Monte Carlo Dropout
          </p>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text-2)' }}>{report.uncertainty_statement}</p>
        </div>

        {/* Severity + Recommendation */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="rounded-xl p-4" style={{ background: 'var(--bg)', border: '1px solid var(--border)' }}>
            <p className="text-xs font-bold tracking-widest uppercase mb-1.5" style={{ color: 'var(--text-4)' }}>Severity</p>
            <p className="text-sm font-semibold" style={{ color: 'var(--text-1)' }}>
              Level {report.severity_level}/3 — {report.severity_label}
            </p>
            <p className="text-xs mt-1 leading-relaxed" style={{ color: 'var(--text-3)' }}>{report.severity_guidance}</p>
          </div>
          <div className="rounded-xl p-4" style={{ background: 'var(--bg)', border: '1px solid var(--border)' }}>
            <p className="text-xs font-bold tracking-widest uppercase mb-1.5" style={{ color: 'var(--text-4)' }}>Recommendation</p>
            <p className="text-sm leading-relaxed" style={{ color: 'var(--text-2)' }}>{report.recommendation}</p>
          </div>
        </div>

        {/* Method */}
        <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-4)' }}>
          <span className="font-semibold">Method:</span>
          <span>{report.method}</span>
        </div>

        {/* Disclaimer */}
        <div className="rounded-xl p-3 text-xs leading-relaxed"
             style={{ background: '#fffbeb', border: '1px solid #fde68a', color: '#92400e' }}>
          {report.disclaimer}
        </div>
      </div>
    </div>
  )
}

/* ─── Main report ──────────────────────────────────────── */
export default function InterpretabilityReport({ result }) {
  if (!result) return null
  const { prediction, confidence, probabilities, severity_level, severity_label, severity_guidance, report } = result
  const exp = EXPLAIN[prediction] || EXPLAIN['Normal']

  const predColor =
    prediction === 'COVID-19'        ? '#ef4444' :
    prediction === 'Normal'           ? '#16a34a' :
    '#d97706'

  const sevColor = ['#16a34a', '#ca8a04', '#ea580c', '#dc2626'][severity_level] || '#64748b'
  const sortedProbs = Object.entries(probabilities || {}).sort(([, a], [, b]) => b - a)

  return (
    <div className="space-y-3 anim-fade-up">

      {/* Auto-generated clinical report (Feature B) */}
      <ClinicalReport report={report} />

      {/* Summary box */}
      <div className="card p-5" style={{ borderLeft: `4px solid var(--blue)` }}>
        <p className="text-xs font-semibold mb-2" style={{ color: 'var(--blue)', fontFamily: '"IBM Plex Mono"' }}>
          INTERPRETABILITY REPORT · 7156CEM
        </p>
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text-2)' }}>
          {exp.summary}
        </p>
      </div>

      {/* Model decision */}
      <Section title="Model Decision Summary" badge="Inference" defaultOpen>
        <KV label="Predicted Class"    value={prediction}                          accent={predColor} />
        <KV label="Confidence Score"   value={`${confidence.toFixed(2)}%`}         accent={predColor} />
        <KV label="Uncertainty (MC)"   value={`±${result.uncertainty?.toFixed(2)}% — ${result.uncertainty_level}`}
                                       accent={result.uncertainty_level === 'Low' ? '#16a34a' : result.uncertainty_level === 'Moderate' ? '#ca8a04' : '#dc2626'} />
        <KV label="MC Dropout Passes"  value={`${result.mc_passes || 30} stochastic forward passes`} />
        <KV label="Severity Level"     value={`L${severity_level} — ${severity_label}`} accent={sevColor} />
        <KV label="XAI Method"         value="Attention Rollout (Abnar & Zuidema, 2020)" />
        <KV label="Uncertainty Method" value="Monte Carlo Dropout (Gal & Ghahramani, 2016)" />
        <KV label="Model Architecture" value="ViT-B/16 (google/vit-base-patch16-224-in21k)" />
        <KV label="Patch Resolution"   value="16×16 px · 196 patches · 12 layers" />
      </Section>

      {/* Probabilities */}
      <Section title="Class Probability Distribution" badge="Softmax output" defaultOpen>
        <div className="space-y-4">
          {sortedProbs.map(([cls, prob], i) => (
            <ProbBar key={cls} cls={cls} prob={prob} isTop={i === 0} />
          ))}
        </div>
      </Section>

      {/* Heatmap explanation */}
      <Section title="Attention Heatmap Interpretation" badge="XAI" defaultOpen>
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text-2)' }}>
          {exp.attention}
        </p>
        <div className="rounded-xl p-4" style={{ background: 'var(--blue-light)', border: '1px solid var(--blue-border)' }}>
          <p className="text-xs font-semibold mb-1" style={{ color: 'var(--blue)' }}>
            Rollout Algorithm
          </p>
          <p className="text-xs leading-relaxed font-mono" style={{ color: '#1e40af' }}>
            A_rollout = A₁ ⊗ A₂ ⊗ … ⊗ A₁₂. Attention matrices multiplied across all 12 layers.
            Final map: 196 patch tokens → 14×14 grid → bilinearly upsampled to 224×224.
          </p>
        </div>
      </Section>

      {/* Severity */}
      <Section title={`Severity Assessment — Level ${severity_level}`} badge={`L${severity_level}/3`} defaultOpen>
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text-2)' }}>
          {severity_guidance || exp.clinical}
        </p>
        <div className="grid grid-cols-2 gap-2 mt-1">
          {[
            { l: 0, range: '< 30%',  label: 'No Significant Finding', c: '#16a34a' },
            { l: 1, range: '30–59%', label: 'Mild Abnormality',       c: '#ca8a04' },
            { l: 2, range: '60–84%', label: 'Moderate Concern',       c: '#ea580c' },
            { l: 3, range: '≥ 85%',  label: 'High Severity',          c: '#dc2626' },
          ].map(({ l, range, label, c }) => (
            <div key={l}
                 className="px-3 py-2.5 rounded-xl text-xs"
                 style={{
                   background: l === severity_level ? `${c}12` : 'var(--bg)',
                   border: `1px solid ${l === severity_level ? `${c}40` : 'var(--border)'}`,
                 }}>
              <p className="font-bold" style={{ color: l === severity_level ? c : 'var(--text-3)' }}>
                L{l} · {range}
              </p>
              <p style={{ color: 'var(--text-4)' }}>{label}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Limitations */}
      <Section title="Known Limitations & Caveats" defaultOpen={false}>
        <div className="space-y-3">
          {[
            { head: 'Not clinically validated', body: 'Trained on COVIDx & NIH ChestX-ray14 research datasets. No clinical trial validation conducted.' },
            { head: 'Attention ≠ causation', body: 'High attention in a region indicates model focus — not confirmed pathology. Spurious correlations may occasionally occur.' },
            { head: 'Dataset bias risk', body: 'Training distribution may not represent all demographics, imaging equipment, or acquisition protocols.' },
            { head: 'Inter-disease overlap', body: 'COVID-19 pneumonia can appear radiographically similar to other bilateral airspace diseases.' },
          ].map(({ head, body }) => (
            <div key={head} className="flex gap-3">
              <span className="text-amber-500 font-bold text-sm mt-0.5">!</span>
              <div>
                <p className="text-sm font-semibold" style={{ color: 'var(--text-2)' }}>{head}</p>
                <p className="text-xs mt-0.5 leading-relaxed" style={{ color: 'var(--text-3)' }}>{body}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="rounded-xl p-3 text-xs" style={{ background: '#fffbeb', border: '1px solid #fde68a', color: '#92400e' }}>
          Research prototype — 7156CEM · Coventry University · Supervisor: Dr. Mark Elshaw.
          All results require qualified radiologist review before any clinical action.
        </div>
      </Section>

      {/* References */}
      <Section title="Key References" defaultOpen={false}>
        <div className="space-y-2 text-xs" style={{ color: 'var(--text-3)' }}>
          {[
            'Abnar & Zuidema (2020). Quantifying attention flow in transformers. ACL 2020.',
            'Dosovitskiy et al. (2020). An image is worth 16×16 words. ICLR 2021.',
            'Gal & Ghahramani (2016). Dropout as a Bayesian approximation. ICML 2016.',
            'Zhang et al. (2023). ViT for medical image classification. IEEE J. BHI.',
            'Chowdhury et al. (2020). COVID-19 detection via CNN. IEEE Access.',
            'Wang & Wong (2020). COVID-Net. Scientific Reports.',
          ].map((ref, i) => (
            <div key={i} className="flex gap-2">
              <span className="shrink-0 font-semibold" style={{ color: 'var(--text-4)' }}>[{i + 1}]</span>
              <span className="leading-relaxed">{ref}</span>
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}
