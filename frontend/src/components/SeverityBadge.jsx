/* ─── Severity config ─────────────────────────────────── */
const SEV = {
  0: { color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0', label: 'No Significant Finding', short: 'NONE' },
  1: { color: '#ca8a04', bg: '#fefce8', border: '#fde047', label: 'Mild Abnormality',       short: 'MILD' },
  2: { color: '#ea580c', bg: '#fff7ed', border: '#fed7aa', label: 'Moderate Concern',       short: 'MOD.'  },
  3: { color: '#dc2626', bg: '#fef2f2', border: '#fecaca', label: 'High Severity Indicated', short: 'HIGH' },
}

/* ─── Arc gauge (270°, SVG) ───────────────────────────── */
function ArcGauge({ level, size = 96 }) {
  const cfg   = SEV[level] ?? SEV[0]
  const r     = 38
  const circ  = 2 * Math.PI * r
  const track = circ * 0.75
  const fill  = track * (level / 3)

  return (
    <div className="relative flex items-center justify-center shrink-0"
         style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" className="absolute inset-0 w-full h-full"
           style={{ transform: 'rotate(135deg)' }}>
        {/* Track */}
        <circle cx="50" cy="50" r={r}
          fill="none" stroke="#e2e8f0" strokeWidth="7"
          strokeDasharray={`${track} ${circ - track}`}
          strokeLinecap="round"
        />
        {/* Fill */}
        <circle cx="50" cy="50" r={r}
          fill="none" stroke={cfg.color} strokeWidth="7"
          strokeDasharray={`${fill} ${circ}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.9s cubic-bezier(.4,0,.2,1)' }}
        />
      </svg>
      <div className="relative flex flex-col items-center leading-none">
        <span className="font-extrabold" style={{ fontSize: size * 0.30, color: cfg.color, lineHeight: 1 }}>
          {level}
        </span>
        <span className="font-mono text-center" style={{ fontSize: size * 0.10, color: 'var(--text-4)' }}>
          /3
        </span>
      </div>
    </div>
  )
}

/* ─── Compact inline badge ────────────────────────────── */
export function SeverityBadgeCompact({ level }) {
  const cfg = SEV[level] ?? SEV[0]
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold"
      style={{ background: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.color }}
    >
      L{level} · {cfg.short}
    </span>
  )
}

/* ─── Full severity card ──────────────────────────────── */
export default function SeverityBadge({ level, label, guidance, size = 'md' }) {
  const cfg      = SEV[level] ?? SEV[0]
  const gaugeSize = size === 'lg' ? 110 : 88

  return (
    <div className="card p-5 flex items-start gap-5"
         style={{ borderLeft: `4px solid ${cfg.color}` }}>
      <ArcGauge level={level} size={gaugeSize} />

      <div className="flex-1 min-w-0 pt-1 space-y-2.5">
        <div>
          <p className="text-xs font-medium mb-1" style={{ color: 'var(--text-4)', fontFamily: '"IBM Plex Mono"' }}>
            SEVERITY ASSESSMENT
          </p>
          <p className="font-bold text-base leading-tight" style={{ color: cfg.color }}>
            {label || cfg.label}
          </p>
        </div>

        {/* Dot indicator */}
        <div className="flex items-center gap-1.5">
          {[0, 1, 2, 3].map(i => (
            <div key={i} className="w-2.5 h-2.5 rounded-full transition-all duration-500"
                 style={{
                   background: i <= level ? cfg.color : '#e2e8f0',
                   transform: i === level ? 'scale(1.25)' : 'scale(1)',
                 }} />
          ))}
          <span className="text-xs ml-1 font-medium" style={{ color: 'var(--text-4)' }}>
            Level {level} of 3
          </span>
        </div>

        {guidance && (
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text-3)' }}>
            {guidance}
          </p>
        )}
      </div>
    </div>
  )
}
