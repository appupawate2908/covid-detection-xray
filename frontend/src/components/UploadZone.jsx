import { useState, useRef, useCallback } from 'react'

const ACCEPTED = ['image/jpeg', 'image/png', 'image/jpg']
const MAX_MB   = 10

/* ─── Cloud upload icon ───────────────────────────────── */
function UploadIcon({ color = '#94a3b8' }) {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
      <path d="M13.3 26.7A6.67 6.67 0 0 1 10 14.2a10 10 0 0 1 19.6-1.9A6.67 6.67 0 0 1 30 26.7"
            stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M20 20v13.3M15 25l5-5 5 5" stroke={color} strokeWidth="1.8"
            strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

/* ─── Spinner ─────────────────────────────────────────── */
function Spinner() {
  return (
    <div className="w-10 h-10 rounded-full border-4 border-blue-100 border-t-blue-500"
         style={{ animation: 'spin 1s linear infinite' }} />
  )
}

/* ─── Loading state ───────────────────────────────────── */
function LoadingState({ previewUrl }) {
  return (
    <div className="max-w-xl mx-auto">
      <div className="card p-10 flex flex-col items-center gap-6 text-center">
        {previewUrl ? (
          <img src={previewUrl} alt="Uploaded X-ray" className="w-32 h-32 rounded-xl object-cover"
               style={{ border: '2px solid var(--border)', filter: 'grayscale(1)' }} />
        ) : (
          <Spinner />
        )}
        {previewUrl && <Spinner />}
        <div>
          <p className="font-bold text-lg" style={{ color: 'var(--text-1)' }}>
            Analysing X-ray
          </p>
          <p className="text-sm mt-1" style={{ color: 'var(--text-3)' }}>
            Running ViT-B/16 inference + attention rollout…
          </p>
        </div>
      </div>
    </div>
  )
}

/* ─── Feature badges ──────────────────────────────────── */
function FeatureBadges() {
  const items = [
    'Attention Rollout XAI',
    '4-Level Severity',
    'ViT-B/16 Model',
    'Progression Tracking',
  ]
  return (
    <div className="flex flex-wrap items-center justify-center gap-2 mt-5">
      {items.map(label => (
        <span key={label}
              className="text-xs font-medium px-3 py-1.5 rounded-full"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-3)',
                       boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
          {label}
        </span>
      ))}
    </div>
  )
}

/* ─── Main Upload Zone ────────────────────────────────── */
export default function UploadZone({ onUpload, onFileSelected, loading, previewUrl: externalPreview }) {
  const [dragging, setDragging] = useState(false)
  const [preview,  setPreview]  = useState(null)
  const [file,     setFile]     = useState(null)
  const [fileErr,  setFileErr]  = useState('')
  const inputRef = useRef(null)

  const validate = (f) => {
    if (!ACCEPTED.includes(f.type)) return `Unsupported format: ${f.type || 'unknown'}`
    if (f.size > MAX_MB * 1024 * 1024) return `File too large (${(f.size/1024/1024).toFixed(1)} MB). Max ${MAX_MB} MB.`
    return null
  }

  const process = useCallback((f) => {
    const err = validate(f)
    if (err) { setFileErr(err); return }
    setFileErr('')
    setFile(f)
    const url = URL.createObjectURL(f)
    setPreview(url)
    onFileSelected?.(f, url)
  }, [onFileSelected])

  const handleDrop = useCallback((e) => {
    e.preventDefault(); setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) process(f)
  }, [process])

  const handleReset = (e) => {
    e.stopPropagation()
    setFile(null); setPreview(null); setFileErr('')
    if (inputRef.current) inputRef.current.value = ''
  }

  if (loading) return <LoadingState previewUrl={externalPreview} />

  return (
    <div className="max-w-2xl mx-auto">
      {/* Page heading */}
      <div className="text-center mb-8 space-y-2 anim-fade-up">
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full"
              style={{ background: 'var(--blue-light)', color: 'var(--blue)', border: '1px solid var(--blue-border)' }}>
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 inline-block" />
          7156CEM · Channabasavanna Santosh Pawate
        </span>
        <h1 className="font-extrabold text-4xl tracking-tight" style={{ color: 'var(--text-1)' }}>
          Chest X-ray AI Analysis
        </h1>
        <p className="text-base max-w-md mx-auto" style={{ color: 'var(--text-3)' }}>
          Upload a chest X-ray to receive an AI classification, attention heatmap, and severity assessment.
        </p>
      </div>

      {/* Drop zone */}
      <div
        className="anim-zoom-in"
        style={{
          border: `2px dashed ${dragging ? 'var(--blue)' : file ? 'var(--normal-border)' : 'var(--border)'}`,
          borderRadius: 20,
          background: dragging ? 'var(--blue-light)' : file ? 'var(--normal-bg)' : 'var(--surface)',
          transition: 'all 0.2s ease',
          cursor: file ? 'default' : 'pointer',
          boxShadow: dragging ? '0 0 0 4px rgba(37,99,235,0.08)' : 'var(--shadow-card)',
        }}
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onClick={() => !file && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".jpg,.jpeg,.png"
          className="hidden"
          onChange={e => { const f = e.target.files[0]; if (f) process(f) }}
        />

        <div className="p-10 flex flex-col items-center gap-4 text-center">
          {preview ? (
            <>
              <div className="relative">
                <img
                  src={preview}
                  alt="X-ray preview"
                  className="w-40 h-40 rounded-xl object-cover"
                  style={{ border: '2px solid #bbf7d0', filter: 'grayscale(1) contrast(1.1)' }}
                />
                <div className="absolute -top-2 -right-2 w-7 h-7 rounded-full flex items-center justify-center"
                     style={{ background: 'var(--normal)', boxShadow: '0 2px 8px rgba(22,163,74,0.3)' }}>
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M2.5 7l3 3 6-6" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>
              <div>
                <p className="font-semibold text-sm" style={{ color: 'var(--normal)' }}>
                  Image ready
                </p>
                <p className="text-sm mt-0.5" style={{ color: 'var(--text-3)' }}>
                  {file?.name} · {(file?.size / 1024).toFixed(0)} KB
                </p>
              </div>
              <button
                onClick={handleReset}
                className="text-sm font-medium transition-colors"
                style={{ color: 'var(--text-4)' }}
                onMouseEnter={e => e.target.style.color = 'var(--text-2)'}
                onMouseLeave={e => e.target.style.color = 'var(--text-4)'}
              >
                × Remove image
              </button>
            </>
          ) : (
            <>
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-200"
                   style={{ background: dragging ? 'rgba(37,99,235,0.1)' : 'var(--bg)', border: '1px solid var(--border)' }}>
                <UploadIcon color={dragging ? 'var(--blue)' : '#94a3b8'} />
              </div>
              <div>
                <p className="font-bold text-lg" style={{ color: 'var(--text-1)' }}>
                  {dragging ? 'Drop it here' : 'Drop your chest X-ray here'}
                </p>
                <p className="text-sm mt-1" style={{ color: 'var(--text-3)' }}>
                  or click to browse files
                </p>
              </div>
              <div className="flex items-center gap-2">
                {['JPEG', 'PNG', 'Max 10 MB'].map(t => (
                  <span key={t} className="text-xs font-medium px-2.5 py-1 rounded-lg"
                        style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-4)' }}>
                    {t}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Error */}
      {fileErr && (
        <div className="mt-3 px-4 py-3 rounded-xl text-sm font-medium anim-fade-up"
             style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626' }}>
          {fileErr}
        </div>
      )}

      {/* CTA */}
      <div className="mt-5 flex flex-col items-center gap-3 anim-fade-up delay-2">
        {file && !fileErr ? (
          <button className="btn-primary" onClick={() => onUpload(file)}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 2v9M5 8l3 3 3-3" stroke="currentColor" strokeWidth="1.8"
                    strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M2 13h12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
            Run Analysis
          </button>
        ) : (
          <button className="btn-ghost" onClick={() => inputRef.current?.click()}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <rect x="1" y="2" width="12" height="11" rx="2" stroke="currentColor" strokeWidth="1.3"/>
              <path d="M5 2V1a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v1" stroke="currentColor" strokeWidth="1.3"/>
            </svg>
            Browse files
          </button>
        )}
      </div>

      <FeatureBadges />
    </div>
  )
}
