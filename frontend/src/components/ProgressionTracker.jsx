import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { SeverityBadgeCompact } from './SeverityBadge.jsx'

const API_BASE = 'http://localhost:8000'

const SEV_COLOR  = ['#16a34a', '#ca8a04', '#ea580c', '#dc2626']
const PRED_COLOR = { 'Normal': '#16a34a', 'COVID-19': '#ef4444', 'Viral Pneumonia': '#d97706' }

/* ─── Trend banner ─────────────────────────────────────── */
function TrendBanner({ trend }) {
  if (!trend) return null
  const cfg = {
    improving: { label: 'Improving',    icon: '↓', color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' },
    stable:    { label: 'Stable',       icon: '→', color: '#ca8a04', bg: '#fefce8', border: '#fde047' },
    worsening: { label: 'Worsening',    icon: '↑', color: '#dc2626', bg: '#fef2f2', border: '#fecaca' },
  }[trend.direction] || { label: 'Stable', icon: '→', color: '#ca8a04', bg: '#fefce8', border: '#fde047' }

  return (
    <div className="card p-5 flex items-center gap-5 anim-zoom-in"
         style={{ borderLeft: `4px solid ${cfg.color}`, background: cfg.bg, borderTop: `1px solid ${cfg.border}`, borderRight: `1px solid ${cfg.border}`, borderBottom: `1px solid ${cfg.border}` }}>
      <div className="text-4xl font-extrabold leading-none" style={{ color: cfg.color }}>
        {cfg.icon}
      </div>
      <div>
        <p className="text-xs font-semibold mb-0.5" style={{ color: 'var(--text-4)', fontFamily: '"IBM Plex Mono"' }}>
          OVERALL TREND
        </p>
        <p className="font-bold text-lg" style={{ color: cfg.color }}>{cfg.label}</p>
        <p className="text-sm" style={{ color: 'var(--text-3)' }}>{trend.description}</p>
      </div>
    </div>
  )
}

/* ─── Severity chart ───────────────────────────────────── */
function SeverityChart({ timeline }) {
  if (!timeline || timeline.length < 2) return null

  const W = 500, H = 90
  const PAD = { l: 32, r: 16, t: 12, b: 28 }
  const iW = W - PAD.l - PAD.r
  const iH = H - PAD.t - PAD.b

  const pts = timeline.map((t, i) => ({
    x: PAD.l + (i / (timeline.length - 1)) * iW,
    y: PAD.t + iH - (t.severity_level / 3) * iH,
    level: t.severity_level,
  }))

  const linePath = `M ${pts.map(p => `${p.x},${p.y}`).join(' L ')}`
  const areaPath = `${linePath} L ${pts[pts.length-1].x},${PAD.t+iH} L ${pts[0].x},${PAD.t+iH} Z`

  return (
    <div className="card p-5 anim-fade-up">
      <div className="flex items-center justify-between mb-3">
        <p className="font-semibold text-sm" style={{ color: 'var(--text-2)' }}>
          Severity Timeline
        </p>
        <p className="text-xs" style={{ color: 'var(--text-4)' }}>{timeline.length} scans</p>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 100 }}>
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2563eb" stopOpacity="0.12" />
            <stop offset="100%" stopColor="#2563eb" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Grid */}
        {[0, 1, 2, 3].map(l => {
          const y = PAD.t + iH - (l / 3) * iH
          return (
            <g key={l}>
              <line x1={PAD.l} y1={y} x2={W-PAD.r} y2={y}
                    stroke="#e2e8f0" strokeWidth="1" strokeDasharray="3 5" />
              <text x={PAD.l - 6} y={y + 4} textAnchor="end" fontSize="8"
                    fill="#94a3b8" fontFamily="'IBM Plex Mono', monospace">
                L{l}
              </text>
            </g>
          )
        })}

        {/* Area */}
        <path d={areaPath} fill="url(#areaGrad)" />

        {/* Line */}
        <path d={linePath} fill="none" stroke="#2563eb" strokeWidth="2"
              strokeLinejoin="round" strokeLinecap="round" />

        {/* Points */}
        {pts.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r="5"
                    fill={SEV_COLOR[p.level]} stroke="#fff" strokeWidth="2" />
            <text x={p.x} y={H-4} textAnchor="middle" fontSize="8"
                  fill="#94a3b8" fontFamily="'IBM Plex Mono', monospace">
              #{i + 1}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}

/* ─── Scan card ────────────────────────────────────────── */
function ScanCard({ scan, index, isLatest }) {
  const [showHm, setShowHm] = useState(false)
  const sColor = SEV_COLOR[scan.severity_level] ?? SEV_COLOR[0]
  const pColor = PRED_COLOR[scan.prediction] || 'var(--text-2)'

  return (
    <div className="card card-hover p-4 space-y-3"
         style={{ borderLeft: `4px solid ${sColor}` }}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold shrink-0"
               style={{ background: `${sColor}12`, color: sColor, border: `1px solid ${sColor}25` }}>
            {String(index + 1).padStart(2, '0')}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="font-bold text-sm" style={{ color: pColor }}>{scan.prediction}</p>
              {isLatest && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                      style={{ background: 'var(--blue-light)', color: 'var(--blue)', border: '1px solid var(--blue-border)' }}>
                  Latest
                </span>
              )}
            </div>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-4)' }}>
              {new Date(scan.timestamp).toLocaleString([], { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <p className="text-sm font-bold" style={{ color: pColor }}>
            {scan.confidence?.toFixed(1)}%
          </p>
          <SeverityBadgeCompact level={scan.severity_level} />
        </div>
      </div>

      {/* Mini progress bar */}
      <div className="h-1 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
        <div className="h-full rounded-full" style={{ width: `${scan.confidence}%`, background: pColor, opacity: 0.5 }} />
      </div>

      {/* Heatmap toggle */}
      {scan.heatmap_base64 && (
        <div>
          <button
            className="text-xs font-semibold flex items-center gap-1 transition-colors"
            style={{ color: 'var(--blue)' }}
            onClick={() => setShowHm(v => !v)}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none"
                 style={{ transform: showHm ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
              <path d="M3 2l4 3-4 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            {showHm ? 'Hide' : 'Show'} attention heatmap
          </button>
          {showHm && (
            <div className="mt-2 rounded-xl overflow-hidden" style={{ background: '#000', border: '1px solid var(--border)' }}>
              <img
                src={`data:image/png;base64,${scan.heatmap_base64}`}
                alt="Attention heatmap"
                className="w-full heatmap-reveal"
                style={{ maxHeight: 220, objectFit: 'contain' }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ─── Empty state ──────────────────────────────────────── */
function EmptyState() {
  return (
    <div className="card py-20 flex flex-col items-center gap-5 text-center anim-zoom-in">
      <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
           style={{ background: 'var(--bg)', border: '1px solid var(--border)' }}>
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <rect x="3" y="5" width="22" height="18" rx="3" stroke="#cbd5e1" strokeWidth="1.5"/>
          <path d="M9 14h10M14 9v10" stroke="#cbd5e1" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      </div>
      <div>
        <p className="font-bold text-base" style={{ color: 'var(--text-2)' }}>No scans recorded yet</p>
        <p className="text-sm mt-1" style={{ color: 'var(--text-4)' }}>
          Upload X-ray images from the Analyse tab to start tracking.
        </p>
      </div>
    </div>
  )
}

/* ─── Main ─────────────────────────────────────────────── */
export default function ProgressionTracker({ sessionId, refreshKey }) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  const fetchData = useCallback(async () => {
    if (!sessionId) return
    setLoading(true); setError(null)
    try {
      const { data: resp } = await axios.get(`${API_BASE}/progression/${sessionId}`, { timeout: 10000 })
      setData(resp)
    } catch (err) {
      if (err.response?.status === 404) {
        setData({ scans: [], scan_count: 0, trend: null, severity_timeline: [] })
      } else {
        setError(err.message || 'Failed to load')
      }
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => { fetchData() }, [fetchData, refreshKey])

  const handleClear = async () => {
    if (!confirm('Clear all scan history?')) return
    await axios.delete(`${API_BASE}/progression/${sessionId}`)
    setData({ scans: [], scan_count: 0, trend: null, severity_timeline: [] })
  }

  const handleDownload = () => {
    if (!data?.scans?.length) return
    const lines = [
      'COVID-19 XAI — Progression Report', '='.repeat(46),
      `Session: ${sessionId}`, `Generated: ${new Date().toLocaleString()}`, '',
    ]
    if (data.trend) lines.push(`Trend: ${data.trend.direction} — ${data.trend.description}`, '')
    data.scans.forEach((s, i) => {
      lines.push(`Scan ${i + 1} · ${new Date(s.timestamp).toLocaleString()}`,
        `  Prediction: ${s.prediction}`, `  Confidence: ${s.confidence?.toFixed(1)}%`,
        `  Severity: L${s.severity_level} — ${s.severity_label}`, '')
    })
    lines.push('DISCLAIMER: Research prototype — not a clinical diagnostic tool.')
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `progression-${sessionId.slice(0, 8)}.txt`
    a.click()
  }

  if (loading) return (
    <div className="max-w-3xl mx-auto px-6 py-24 flex flex-col items-center gap-4">
      <div className="w-9 h-9 rounded-full border-4 border-blue-100 border-t-blue-500"
           style={{ animation: 'spin 1s linear infinite' }} />
      <p className="text-sm font-medium" style={{ color: 'var(--text-4)' }}>Loading progression data…</p>
    </div>
  )

  if (error) return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <div className="card p-8 text-center space-y-3">
        <p className="text-sm" style={{ color: '#ef4444' }}>{error}</p>
        <button className="btn-ghost" onClick={fetchData}>Retry</button>
      </div>
    </div>
  )

  const scans    = data?.scans            || []
  const trend    = data?.trend
  const timeline = data?.severity_timeline || []

  return (
    <div className="max-w-3xl mx-auto px-6 py-10 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 anim-fade-up">
        <div>
          <h1 className="font-extrabold text-2xl tracking-tight" style={{ color: 'var(--text-1)' }}>
            Progression Tracker
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-4)' }}>
            Session{' '}
            <code className="font-mono text-xs px-1.5 py-0.5 rounded"
                  style={{ background: 'var(--blue-light)', color: 'var(--blue)' }}>
              {sessionId.slice(0, 8)}…
            </code>
            {' '}· {scans.length} scan{scans.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-ghost text-xs" onClick={fetchData}>↺ Refresh</button>
          {scans.length > 0 && (
            <>
              <button className="btn-ghost text-xs" onClick={handleDownload}>↓ Report</button>
              <button
                className="text-xs font-semibold px-3 py-2 rounded-xl transition-all duration-200"
                style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626' }}
                onClick={handleClear}
              >
                Clear
              </button>
            </>
          )}
        </div>
      </div>

      {scans.length === 0 ? <EmptyState /> : (
        <>
          {trend && <TrendBanner trend={trend} />}
          <SeverityChart timeline={timeline} />
          <div className="space-y-3">
            <p className="text-xs font-semibold" style={{ color: 'var(--text-4)', fontFamily: '"IBM Plex Mono"' }}>
              SCAN TIMELINE — MOST RECENT FIRST
            </p>
            {[...scans].reverse().map((scan, revIdx) => (
              <ScanCard
                key={scan.scan_id}
                scan={scan}
                index={scans.length - 1 - revIdx}
                isLatest={revIdx === 0}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
