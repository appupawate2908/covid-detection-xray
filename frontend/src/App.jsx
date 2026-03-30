import { useState, useCallback, useReducer } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import UploadZone from './components/UploadZone.jsx'
import ResultCard from './components/ResultCard.jsx'
import ProgressionTracker from './components/ProgressionTracker.jsx'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

/* ─── Navigation ──────────────────────────────────────── */
function NavBar() {
  const { pathname } = useLocation()

  return (
    <header style={{ background: '#fff', borderBottom: '1px solid #e2e8f0' }}>
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between gap-6">

        {/* Logo */}
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
               style={{ background: 'var(--blue)' }}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 3v12M3 9h12" stroke="#fff" strokeWidth="2" strokeLinecap="round"/>
              <circle cx="9" cy="9" r="3.5" stroke="#fff" strokeWidth="1.5" opacity="0.5"/>
            </svg>
          </div>
          <div>
            <p className="font-bold text-sm leading-none" style={{ color: 'var(--text-1)' }}>
              COVID-19 XAI
            </p>
            <p className="text-[10px] mt-0.5 leading-none" style={{ color: 'var(--text-4)', fontFamily: 'var(--font-mono)' }}>
              Diagnostic Research Tool
            </p>
          </div>
        </div>

        {/* Nav links */}
        <nav className="flex items-center gap-1">
          {[
            { to: '/',           label: 'Analyse' },
            { to: '/progression', label: 'Progression' },
          ].map(({ to, label }) => {
            const active = pathname === to
            return (
              <Link
                key={to}
                to={to}
                className="relative px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-150"
                style={{
                  color: active ? 'var(--blue)' : 'var(--text-3)',
                  background: active ? 'var(--blue-light)' : 'transparent',
                }}
              >
                {label}
              </Link>
            )
          })}
        </nav>

        {/* Status */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-50" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
          </span>
          <span className="text-xs font-medium" style={{ color: 'var(--text-3)' }}>API Online</span>
        </div>
      </div>
    </header>
  )
}

/* ─── Disclaimer ──────────────────────────────────────── */
function Disclaimer() {
  return (
    <div className="flex items-center justify-center gap-2 py-2 px-6"
         style={{ background: '#fffbeb', borderBottom: '1px solid #fde68a' }}>
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
        <path d="M6 1.5L11 10.5H1L6 1.5Z" stroke="#d97706" strokeWidth="1.2"/>
        <path d="M6 5v2.5" stroke="#d97706" strokeWidth="1.2" strokeLinecap="round"/>
        <circle cx="6" cy="9" r="0.5" fill="#d97706"/>
      </svg>
      <span className="text-xs font-medium" style={{ color: '#92400e' }}>
        Research prototype only — not a clinical diagnostic tool — results require radiologist review
      </span>
    </div>
  )
}

/* ─── State Machine ───────────────────────────────────── */
// States: XRAY → UI_UPDATE → ANALYSIS → FOUND → REPORT | ERROR
const initialXrayState = { phase: 'XRAY', result: null, previewUrl: null, errorMsg: '' }

function xrayReducer(state, action) {
  switch (action.type) {
    case 'FILE_SELECTED': return { ...state, phase: 'UI_UPDATE', previewUrl: action.previewUrl }
    case 'SUBMIT':        return { ...state, phase: 'ANALYSIS' }
    case 'FOUND':         return { ...state, phase: 'FOUND', result: action.result }
    case 'SHOW_REPORT':   return { ...state, phase: 'REPORT' }
    case 'STOP':          return { ...initialXrayState, phase: 'STOP' }
    case 'ERROR':         return { ...state, phase: 'ERROR', errorMsg: action.message }
    case 'RESET':         return { ...initialXrayState }
    default:              return state
  }
}

/* ─── Upload / Results Page ───────────────────────────── */
function AnalysePage({ sessionId, onNewResult, xrayState, dispatch }) {
  const handleFileSelected = useCallback((_, url) => {
    dispatch({ type: 'FILE_SELECTED', previewUrl: url })
  }, [dispatch])

  const handleUpload = useCallback(async (file) => {
    dispatch({ type: 'SUBMIT' })
    const fd = new FormData()
    fd.append('file', file)

    try {
      const { data } = await axios.post(`${API_BASE}/predict`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 90000,
      })
      dispatch({ type: 'FOUND', result: data })
      dispatch({ type: 'SHOW_REPORT' })

      try {
        await axios.post(`${API_BASE}/progression/add`, {
          session_id:     sessionId,
          prediction:     data.prediction,
          confidence:     data.confidence,
          probabilities:  data.probabilities,
          severity_level: data.severity_level,
          severity_label: data.severity_label,
          heatmap_base64: data.heatmap_base64,
        })
        onNewResult?.()
      } catch {}
    } catch (err) {
      const detail = err.response?.data?.detail
      const message = typeof detail === 'object' ? (detail?.message || 'Invalid image') : (detail || err.message || 'Analysis failed')
      dispatch({ type: 'ERROR', message })
    }
  }, [sessionId, onNewResult, dispatch])

  const handleReset = () => dispatch({ type: 'RESET' })

  const { phase, result, previewUrl, errorMsg } = xrayState

  const hasResult = (phase === 'FOUND' || phase === 'REPORT') && result

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">

      {/* "New Analysis" strip — shown when a result is already loaded */}
      {hasResult && (
        <div className="flex items-center justify-between mb-6 px-5 py-3 rounded-2xl anim-fade-up"
             style={{ background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
            <span className="text-sm font-semibold" style={{ color: '#15803d' }}>
              Analysis complete — results saved to Progression
            </span>
          </div>
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all duration-150"
            style={{ background: '#fff', border: '1px solid #bbf7d0', color: '#15803d',
                     boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}
            onMouseEnter={e => e.currentTarget.style.background = '#dcfce7'}
            onMouseLeave={e => e.currentTarget.style.background = '#fff'}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M12 7A5 5 0 1 1 7 2V1M7 1L5 3M7 1l2 2"
                    stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Analyse New X-ray
          </button>
        </div>
      )}

      {(phase === 'XRAY' || phase === 'UI_UPDATE' || phase === 'ANALYSIS') && (
        <div className="anim-fade-up">
          <UploadZone
            onUpload={handleUpload}
            onFileSelected={handleFileSelected}
            loading={phase === 'ANALYSIS'}
            previewUrl={previewUrl}
          />
        </div>
      )}

      {phase === 'ERROR' && (
        <div className="anim-zoom-in max-w-md mx-auto">
          <div className="card p-8 text-center space-y-4">
            <div className="w-12 h-12 mx-auto rounded-full flex items-center justify-center"
                 style={{ background: '#fef2f2', border: '1px solid #fecaca' }}>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="10" r="8" stroke="#ef4444" strokeWidth="1.5"/>
                <path d="M10 6v5" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round"/>
                <circle cx="10" cy="14" r="1" fill="#ef4444"/>
              </svg>
            </div>
            <div>
              <p className="font-bold text-base" style={{ color: 'var(--text-1)' }}>Analysis Failed</p>
              <p className="text-sm mt-1" style={{ color: 'var(--text-3)' }}>{errorMsg}</p>
            </div>
            <button className="btn-ghost" onClick={handleReset}>← Try Again</button>
          </div>
        </div>
      )}

      {hasResult && (
        <div className="anim-slide-up">
          <ResultCard result={result} previewUrl={previewUrl} onReset={handleReset} />
        </div>
      )}
    </div>
  )
}

/* ─── Root App ────────────────────────────────────────── */
export default function App() {
  const [sessionId] = useState(() => {
    const stored = sessionStorage.getItem('xai_session_id')
    if (stored) return stored
    const id = crypto.randomUUID()
    sessionStorage.setItem('xai_session_id', id)
    return id
  })
  const [progKey, setProgKey] = useState(0)

  // Lifted up so results survive navigation between Analyse ↔ Progression
  const [xrayState, dispatch] = useReducer(xrayReducer, initialXrayState)

  return (
    <BrowserRouter>
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
        <Disclaimer />
        <NavBar />
        <main style={{ flex: 1 }}>
          <Routes>
            <Route path="/" element={
              <AnalysePage
                sessionId={sessionId}
                onNewResult={() => setProgKey(k => k + 1)}
                xrayState={xrayState}
                dispatch={dispatch}
              />
            } />
            <Route path="/progression" element={
              <ProgressionTracker sessionId={sessionId} refreshKey={progKey} />
            } />
          </Routes>
        </main>
        <footer style={{ borderTop: '1px solid var(--border)', background: '#fff' }}
                className="py-4 px-6 text-center">
          <p className="text-xs" style={{ color: 'var(--text-4)' }}>
            7156CEM Individual Project · Channabasavanna Santosh Pawate (16150425) · Supervisor: Dr. Mark Elshaw · Coventry University
          </p>
        </footer>
      </div>
    </BrowserRouter>
  )
}
