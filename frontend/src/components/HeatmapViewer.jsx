import { useState, useCallback, useRef, useEffect } from 'react'

/* ─── Lightbox ─────────────────────────────────────────── */
function Lightbox({ src, label, onClose }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-8"
      style={{ background: 'rgba(15,23,42,0.85)', backdropFilter: 'blur(8px)' }}
      onClick={onClose}
    >
      <div className="relative max-w-4xl w-full" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <p className="font-semibold text-white text-sm">{label}</p>
          <button
            onClick={onClose}
            className="text-white/70 hover:text-white text-sm font-medium transition-colors px-3 py-1.5 rounded-lg"
            style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.15)' }}
          >
            Close ✕
          </button>
        </div>
        <img src={src} alt={label} className="w-full rounded-2xl"
             style={{ border: '1px solid rgba(255,255,255,0.1)', maxHeight: '80vh', objectFit: 'contain', background: '#000' }} />
      </div>
    </div>
  )
}

/* ─── Image panel ──────────────────────────────────────── */
function ImagePanel({ src, label, badge, onExpand }) {
  const [hovering, setHovering] = useState(false)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold" style={{ color: 'var(--text-3)' }}>{label}</p>
        {badge}
      </div>
      <div
        className="relative rounded-xl overflow-hidden cursor-zoom-in"
        style={{ background: '#000', border: '1px solid var(--border)' }}
        onMouseEnter={() => setHovering(true)}
        onMouseLeave={() => setHovering(false)}
        onClick={onExpand}
      >
        <img src={src} alt={label} className="w-full block"
             style={{ maxHeight: 300, objectFit: 'contain' }} />
        {hovering && (
          <div className="absolute inset-0 flex items-center justify-center"
               style={{ background: 'rgba(0,0,0,0.35)' }}>
            <div className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white"
                 style={{ background: 'rgba(0,0,0,0.6)', border: '1px solid rgba(255,255,255,0.15)' }}>
              Click to expand
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/* ─── Compare Slider ───────────────────────────────────── */
function CompareSlider({ originalSrc, heatmapSrc }) {
  const [pos, setPos] = useState(50)
  const containerRef = useRef(null)
  const dragging = useRef(false)

  const move = useCallback((clientX) => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const pct = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100))
    setPos(pct)
  }, [])

  useEffect(() => {
    const onMouseMove = (e) => { if (dragging.current) move(e.clientX) }
    const onMouseUp   = ()  => { dragging.current = false; document.body.style.userSelect = '' }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup',   onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup',   onMouseUp)
    }
  }, [move])

  const startDrag = (e) => {
    e.preventDefault()
    dragging.current = true
    document.body.style.userSelect = 'none'
  }

  const onTouchMove = (e) => move(e.touches[0].clientX)

  return (
    <div className="space-y-3">
      {/* Labels */}
      <div className="flex justify-between text-xs font-semibold" style={{ color: 'var(--text-3)' }}>
        <span>◀ Original X-ray</span>
        <span>Attention Heatmap ▶</span>
      </div>

      {/* Slider container */}
      <div
        ref={containerRef}
        className="relative rounded-xl overflow-hidden select-none"
        style={{ background: '#000', border: '1px solid var(--border)', cursor: 'col-resize', minHeight: 280 }}
        onMouseDown={(e) => { startDrag(e); move(e.clientX) }}
        onTouchStart={(e) => move(e.touches[0].clientX)}
        onTouchMove={onTouchMove}
      >
        {/* Heatmap — full width, underneath */}
        <img
          src={heatmapSrc}
          alt="Heatmap"
          draggable={false}
          className="w-full block"
          style={{ maxHeight: 360, objectFit: 'contain', display: 'block' }}
        />

        {/* Original — clipped on top */}
        <div
          className="absolute inset-0 overflow-hidden"
          style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}
        >
          <img
            src={originalSrc}
            alt="Original"
            draggable={false}
            className="w-full block"
            style={{ maxHeight: 360, objectFit: 'contain', display: 'block' }}
          />
        </div>

        {/* Divider line */}
        <div
          className="absolute top-0 bottom-0"
          style={{ left: `${pos}%`, transform: 'translateX(-50%)', width: 2, background: '#fff', pointerEvents: 'none' }}
        />

        {/* Handle */}
        <div
          onMouseDown={startDrag}
          style={{
            position: 'absolute',
            top: '50%',
            left: `${pos}%`,
            transform: 'translate(-50%, -50%)',
            width: 40,
            height: 40,
            borderRadius: '50%',
            background: '#fff',
            boxShadow: '0 2px 12px rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'col-resize',
            zIndex: 10,
          }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M6 4l-3 5 3 5M12 4l3 5-3 5" stroke="#334155" strokeWidth="1.8"
                  strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>

        {/* Position % badge */}
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full text-xs font-bold"
             style={{ background: 'rgba(0,0,0,0.6)', color: '#fff', pointerEvents: 'none' }}>
          {Math.round(pos)}%
        </div>
      </div>

      <p className="text-xs text-center" style={{ color: 'var(--text-4)' }}>
        Drag the handle to compare original X-ray with attention heatmap
      </p>
    </div>
  )
}

/* ─── Main HeatmapViewer ──────────────────────────────── */
export default function HeatmapViewer({ previewUrl, heatmapBase64, prediction }) {
  const [mode,     setMode]     = useState('compare')
  const [lightbox, setLightbox] = useState(null)

  const heatmapSrc = heatmapBase64 ? `data:image/png;base64,${heatmapBase64}` : null

  const predColor =
    prediction === 'COVID-19' ? 'var(--covid)'  :
    prediction === 'Normal'   ? 'var(--normal)' :
    'var(--pneumo)'

  const predBg =
    prediction === 'COVID-19' ? 'var(--covid-bg)'  :
    prediction === 'Normal'   ? 'var(--normal-bg)' :
    'var(--pneumo-bg)'

  const MODES = [
    { id: 'compare',  label: '⟺ Compare' },
    { id: 'side',     label: 'Side by Side' },
    { id: 'original', label: 'Original Only' },
    { id: 'heatmap',  label: 'Heatmap Only' },
  ]

  return (
    <div className="card p-6 space-y-5 anim-fade-up">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold mb-1" style={{ color: 'var(--text-4)', fontFamily: '"IBM Plex Mono"' }}>
            ATTENTION ROLLOUT · ViT-B/16 · 12 TRANSFORMER LAYERS
          </p>
          <h3 className="font-bold text-lg" style={{ color: 'var(--text-1)' }}>
            XAI Heatmap Viewer
          </h3>
        </div>
        {prediction && (
          <span className="text-xs font-semibold px-3 py-1.5 rounded-full shrink-0"
                style={{ background: predBg, color: predColor, border: `1px solid` }}>
            {prediction}
          </span>
        )}
      </div>

      {/* Mode toggle */}
      <div className="flex gap-1 p-1 rounded-xl flex-wrap" style={{ background: 'var(--bg)', border: '1px solid var(--border)' }}>
        {MODES.map(m => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            className="flex-1 py-2 px-3 text-sm font-semibold rounded-lg transition-all duration-200"
            style={{
              background: mode === m.id ? '#fff' : 'transparent',
              color: mode === m.id ? 'var(--blue)' : 'var(--text-3)',
              boxShadow: mode === m.id ? '0 1px 4px rgba(0,0,0,0.08)' : 'none',
              minWidth: 90,
            }}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Compare mode */}
      {mode === 'compare' && previewUrl && heatmapSrc && (
        <CompareSlider originalSrc={previewUrl} heatmapSrc={heatmapSrc} />
      )}

      {/* Side by side */}
      {mode === 'side' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {previewUrl && (
            <ImagePanel src={previewUrl} label="Original X-ray" onExpand={() => setLightbox('original')} />
          )}
          {heatmapSrc
            ? <ImagePanel src={heatmapSrc} label="Attention Rollout Overlay"
                badge={
                  <span className="text-xs font-medium px-2 py-0.5 rounded-md"
                        style={{ background: '#eff6ff', color: 'var(--blue)', border: '1px solid var(--blue-border)' }}>
                    XAI Output
                  </span>
                }
                onExpand={() => setLightbox('heatmap')} />
            : <div className="rounded-xl flex items-center justify-center"
                   style={{ minHeight: 200, background: 'var(--bg)', border: '1px dashed var(--border)' }}>
                <p className="text-sm" style={{ color: 'var(--text-4)' }}>Heatmap unavailable</p>
              </div>
          }
        </div>
      )}

      {/* Original only */}
      {mode === 'original' && previewUrl && (
        <ImagePanel src={previewUrl} label="Original X-ray" onExpand={() => setLightbox('original')} />
      )}

      {/* Heatmap only */}
      {mode === 'heatmap' && (
        heatmapSrc
          ? <ImagePanel src={heatmapSrc} label="Attention Rollout Overlay"
              badge={
                <span className="text-xs font-medium px-2 py-0.5 rounded-md"
                      style={{ background: '#eff6ff', color: 'var(--blue)', border: '1px solid var(--blue-border)' }}>
                  XAI Output
                </span>
              }
              onExpand={() => setLightbox('heatmap')} />
          : <div className="rounded-xl flex items-center justify-center"
                 style={{ minHeight: 200, background: 'var(--bg)', border: '1px dashed var(--border)' }}>
              <p className="text-sm" style={{ color: 'var(--text-4)' }}>Heatmap unavailable</p>
            </div>
      )}

      {/* Colormap legend */}
      <div className="rounded-xl p-4 space-y-2" style={{ background: 'var(--bg)', border: '1px solid var(--border)' }}>
        <p className="text-xs font-semibold" style={{ color: 'var(--text-3)' }}>
          Attention Intensity — Jet Colormap
        </p>
        <div className="h-3 rounded-full w-full" style={{
          background: 'linear-gradient(90deg, #000080, #0000ff, #00ffff, #00ff00, #ffff00, #ff8000, #ff0000)',
        }} />
        <div className="flex justify-between text-xs" style={{ color: 'var(--text-4)' }}>
          <span>Minimal attention</span>
          <span>Peak model focus</span>
        </div>
      </div>

      {/* Info box */}
      <div className="rounded-xl p-4" style={{ background: 'var(--blue-light)', border: '1px solid var(--blue-border)' }}>
        <p className="text-xs font-semibold mb-1" style={{ color: 'var(--blue)' }}>
          About Attention Rollout
        </p>
        <p className="text-sm leading-relaxed" style={{ color: '#1e40af' }}>
          Attention weights are propagated across all 12 transformer layers via matrix product
          (Abnar & Zuidema, 2020). Red/yellow regions indicate which 16×16 px patches most
          influenced the classification. Unlike Grad-CAM, no gradient back-propagation is required.
        </p>
      </div>

      {/* Lightboxes */}
      {lightbox === 'original' && previewUrl && (
        <Lightbox src={previewUrl} label="Original X-ray" onClose={() => setLightbox(null)} />
      )}
      {lightbox === 'heatmap' && heatmapSrc && (
        <Lightbox src={heatmapSrc} label="Attention Rollout Overlay" onClose={() => setLightbox(null)} />
      )}
    </div>
  )
}
