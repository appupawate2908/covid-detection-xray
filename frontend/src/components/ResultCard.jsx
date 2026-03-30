import { useState } from 'react'
import SeverityBadge from './SeverityBadge.jsx'
import HeatmapViewer from './HeatmapViewer.jsx'
import InterpretabilityReport from './InterpretabilityReport.jsx'

/* ─── Per-class colour config ──────────────────────────── */
const PCFG = {
  'COVID-19':        { color: 'var(--covid)',  bg: 'var(--covid-bg)',  border: 'var(--covid-border)',  left: '#ef4444' },
  'Normal':          { color: 'var(--normal)', bg: 'var(--normal-bg)', border: 'var(--normal-border)', left: '#16a34a' },
  'Viral Pneumonia': { color: 'var(--pneumo)', bg: 'var(--pneumo-bg)', border: 'var(--pneumo-border)', left: '#d97706' },
}

/* ─── Stat card ────────────────────────────────────────── */
function StatCard({ label, value, sub, color, borderColor, children }) {
  return (
    <div className="card p-5 space-y-1" style={{ borderLeft: `4px solid ${borderColor || '#e2e8f0'}` }}>
      <p className="text-xs font-semibold" style={{ color: 'var(--text-4)', fontFamily: '"IBM Plex Mono"' }}>
        {label}
      </p>
      {children || (
        <>
          <p className="font-extrabold text-2xl leading-none tracking-tight" style={{ color: color || 'var(--text-1)' }}>
            {value}
          </p>
          {sub && <p className="text-xs font-medium" style={{ color: 'var(--text-3)' }}>{sub}</p>}
        </>
      )}
    </div>
  )
}

/* ─── Confidence bar ───────────────────────────────────── */
function ConfidenceBar({ value, color }) {
  return (
    <div>
      <div className="flex justify-between text-xs font-medium mb-1.5">
        <span style={{ color: 'var(--text-3)' }}>Confidence</span>
        <span style={{ color }}>{value.toFixed(1)}%</span>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
        <div className="h-full rounded-full confidence-bar" style={{ width: `${value}%`, background: color }} />
      </div>
    </div>
  )
}

/* ─── Probability grid ─────────────────────────────────── */
function ProbGrid({ probabilities, prediction }) {
  return (
    <div className="panel p-4 space-y-3">
      <p className="text-xs font-semibold" style={{ color: 'var(--text-3)' }}>
        All Class Probabilities
      </p>
      <div className="space-y-3">
        {Object.entries(probabilities || {}).sort(([, a], [, b]) => b - a).map(([cls, prob]) => {
          const cfg = PCFG[cls] || PCFG['Normal']
          const isTop = cls === prediction
          return (
            <div key={cls}>
              <div className="flex justify-between text-xs font-medium mb-1">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full" style={{ background: cfg.left }} />
                  <span style={{ color: isTop ? cfg.color : 'var(--text-3)' }}>
                    {cls}
                    {isTop && <span className="ml-1.5 text-[10px] font-semibold px-1 py-0.5 rounded" style={{ background: cfg.bg, color: cfg.color }}>Top</span>}
                  </span>
                </div>
                <span style={{ color: isTop ? cfg.color : 'var(--text-3)' }}>{prob.toFixed(1)}%</span>
              </div>
              <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                <div className="h-full rounded-full confidence-bar"
                     style={{ width: `${prob}%`, background: cfg.left, opacity: isTop ? 1 : 0.35 }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ─── Tabs ─────────────────────────────────────────────── */
const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'heatmap',  label: 'XAI Heatmap' },
  { id: 'report',   label: 'AI Report' },
]

/* ─── Main ResultCard ──────────────────────────────────── */
export default function ResultCard({ result, previewUrl, onReset }) {
  const [tab, setTab] = useState('overview')

  const {
    prediction, confidence, probabilities,
    severity_level, severity_label, severity_guidance,
    heatmap_base64, timestamp,
  } = result

  const cfg = PCFG[prediction] || PCFG['Normal']
  const sevColor = ['#16a34a', '#ca8a04', '#ea580c', '#dc2626'][severity_level] || '#64748b'

  return (
    <div className="max-w-5xl mx-auto space-y-6">

      {/* Top bar */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-extrabold text-2xl tracking-tight" style={{ color: 'var(--text-1)' }}>
            Analysis Results
          </h2>
          {timestamp && (
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-4)' }}>
              {new Date(timestamp).toLocaleString()}
            </p>
          )}
        </div>
        <button className="btn-ghost text-sm" onClick={onReset}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M12 7A5 5 0 1 1 7 2V1M7 1L5 3M7 1l2 2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          New Analysis
        </button>
      </div>

      {/* Stat cards row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 anim-fade-up">
        {/* Prediction */}
        <StatCard label="PREDICTION" borderColor={cfg.left}>
          <div className="flex items-center gap-2 mt-1">
            <div className="w-3 h-3 rounded-full" style={{ background: cfg.left }} />
            <p className="font-extrabold text-xl leading-tight" style={{ color: cfg.color }}>
              {prediction}
            </p>
          </div>
          <p className="text-xs font-medium mt-0.5" style={{ color: 'var(--text-4)' }}>
            Primary classification
          </p>
        </StatCard>

        {/* Confidence */}
        <StatCard label="CONFIDENCE" borderColor={cfg.left}>
          <p className="font-extrabold text-3xl leading-none tracking-tight mt-1" style={{ color: cfg.color }}>
            {confidence.toFixed(1)}<span className="text-lg font-semibold">%</span>
          </p>
          <div className="mt-2">
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
              <div className="h-full rounded-full confidence-bar"
                   style={{ width: `${confidence}%`, background: cfg.left }} />
            </div>
          </div>
        </StatCard>

        {/* Severity */}
        <StatCard label="SEVERITY" borderColor={sevColor}>
          <div className="flex items-center gap-2 mt-1">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-extrabold text-sm"
                 style={{ background: `${sevColor}18`, color: sevColor, border: `1px solid ${sevColor}30` }}>
              L{severity_level}
            </div>
            <div>
              <p className="font-bold text-sm leading-none" style={{ color: sevColor }}>
                {severity_label}
              </p>
              <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-4)' }}>
                Level {severity_level} of 3
              </p>
            </div>
          </div>
        </StatCard>
      </div>

      {/* Tab bar */}
      <div className="flex gap-0 border-b" style={{ borderColor: 'var(--border)' }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="px-5 py-3 text-sm font-semibold transition-all duration-200 relative"
            style={{ color: tab === t.id ? 'var(--blue)' : 'var(--text-3)' }}
          >
            {t.label}
            {tab === t.id && (
              <span className="absolute bottom-0 inset-x-0 h-0.5 rounded-t-full"
                    style={{ background: 'var(--blue)' }} />
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'overview' && (
        <div className="space-y-5 anim-fade-up">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <SeverityBadge
              level={severity_level}
              label={severity_label}
              guidance={severity_guidance}
              size="lg"
            />
            <ProbGrid probabilities={probabilities} prediction={prediction} />
          </div>

          {/* Heatmap preview */}
          {heatmap_base64 && (
            <div className="card p-5 space-y-3 delay-2 anim-fade-up">
              <div className="flex items-center justify-between">
                <p className="font-semibold text-sm" style={{ color: 'var(--text-2)' }}>
                  Attention Heatmap Preview
                </p>
                <button
                  className="text-sm font-semibold transition-colors"
                  style={{ color: 'var(--blue)' }}
                  onClick={() => setTab('heatmap')}
                >
                  Full viewer →
                </button>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {previewUrl && (
                  <div className="rounded-xl overflow-hidden" style={{ background: '#000', border: '1px solid var(--border)' }}>
                    <img src={previewUrl} alt="X-ray" className="w-full"
                         style={{ maxHeight: 200, objectFit: 'contain', filter: 'grayscale(1) contrast(1.05)' }} />
                  </div>
                )}
                <div className="rounded-xl overflow-hidden" style={{ background: '#000', border: '1px solid var(--border)' }}>
                  <img src={`data:image/png;base64,${heatmap_base64}`} alt="Heatmap"
                       className="w-full heatmap-reveal"
                       style={{ maxHeight: 200, objectFit: 'contain' }} />
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'heatmap' && (
        <div className="anim-fade-up">
          <HeatmapViewer previewUrl={previewUrl} heatmapBase64={heatmap_base64} prediction={prediction} />
        </div>
      )}

      {tab === 'report' && (
        <div className="anim-fade-up">
          <InterpretabilityReport result={result} />
        </div>
      )}
    </div>
  )
}
