import { useEffect, useRef, useState } from 'react'
import { ArrowUpRight, CloudSun, LoaderCircle, Route as RouteIcon, ShieldCheck, TriangleAlert, X } from 'lucide-react'
import { api } from './api'
import type { Corridor, Metric, Plan, PlanInput } from './types'
import TripForm from './components/TripForm'
import RouteSummary from './components/RouteSummary'
import RouteMap from './components/RouteMap'
import ForecastSlider from './components/ForecastSlider'

export default function App() {
  const [plan, setPlan] = useState<Plan | null>(null)
  const [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [label, setLabel] = useState('Your next journey starts here')
  const [corridor, setCorridor] = useState<Corridor | null>(null)
  const [overlayLoading, setOverlayLoading] = useState(false)
  const [overlayError, setOverlayError] = useState('')
  const [hour, setHour] = useState(0)
  const [metric, setMetric] = useState<Metric>('wind')
  const [overlay, setOverlay] = useState(true)
  const planRequest = useRef<AbortController | null>(null)
  const overlayRequest = useRef<AbortController | null>(null)
  useEffect(() => () => { planRequest.current?.abort(); overlayRequest.current?.abort() }, [])
  async function loadCorridor(result: Plan) {
    overlayRequest.current?.abort()
    const controller = new AbortController(); overlayRequest.current = controller
    setOverlayLoading(true); setOverlayError('')
    try {
      const data = await api<Corridor>('corridor-weather', { routes: result.routes.map(r => r.geometry) }, controller.signal)
      if (controller.signal.aborted) return
      setCorridor(data)
      if (data.unavailable_cells === data.cells.length) setOverlayError('Weather provider unavailable. Cells are shown in gray.')
    } catch (err) { if (!controller.signal.aborted) setOverlayError((err as Error).message) }
    finally { if (!controller.signal.aborted) setOverlayLoading(false) }
  }
  async function planTrip(input: PlanInput, title: string) {
    planRequest.current?.abort(); overlayRequest.current?.abort()
    const controller = new AbortController(); planRequest.current = controller
    setBusy(true); setError(''); setPlan(null); setSelected(''); setCorridor(null); setOverlayError(''); setOverlayLoading(false)
    try {
      const result = await api<Plan>('plan', input, controller.signal)
      if (controller.signal.aborted) return
      setPlan(result); setSelected(result.recommendation_id || result.routes[0].id); setLabel(title); setHour(0)
      void loadCorridor(result)
    } catch (err) { if (!controller.signal.aborted) setError((err as Error).message) }
    finally { if (!controller.signal.aborted) setBusy(false) }
  }
  return <div className="app-shell">
    <header className="header"><a href="/" className="brand" aria-label="Wayline home"><span className="brand-mark"><svg viewBox="0 0 30 30" fill="none"><path d="m4 8 5 15 6-11 6 11 5-15" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" /></svg></span>wayline<span className="brand-period">.</span></a><span className="header-divider" /><span className="header-subtitle">A little weather-wise.</span><div className="header-right"><span className="live-status"><span className="status-dot" />Live weather data</span><a className="about-link" href="https://open-meteo.com/" target="_blank" rel="noreferrer">Powered by Open-Meteo <ArrowUpRight size={13} /></a></div></header>
    <main className="workspace">
      <aside className="sidebar"><TripForm onPlan={planTrip} busy={busy} />
        {error && <div className="notice danger request-error" role="alert"><TriangleAlert size={18} /><span>{error}</span><button type="button" aria-label="Dismiss error" onClick={() => setError('')}><X size={14} /></button></div>}
        {plan ? <RouteSummary plan={plan} selected={selected} onSelect={setSelected} /> : <div className="sidebar-empty"><div className="sidebar-illustration"><RouteIcon size={22} /><span /><CloudSun size={25} /></div><h3>Less guesswork. More open road.</h3><p>Compare your options with forecasts that follow your trip, mile by mile.</p><div className="sidebar-mini"><ShieldCheck size={13} />Cargo-aware weather rules</div></div>}
        <div className="sidebar-footer">MADE FOR THE MILES AHEAD<span>Weather-aware route planning</span></div>
      </aside>
      <section className="map-workspace">
        <div className="journey-bar"><div><span className="journey-dot" /><strong>{label}</strong></div><span>{plan ? `${plan.routes.reduce((sum, route) => sum + route.checkpoints.length, 0)} arrival-time checkpoints` : 'PLAN SMARTER. DRIVE INFORMED.'}</span></div>
        <div className={`map-area ${plan ? 'has-plan' : ''}`}><RouteMap plan={plan} selected={selected} onSelect={setSelected} corridor={corridor} hour={hour} metric={metric} overlay={overlay} />
          {busy && <div className="planning-overlay" role="status"><LoaderCircle size={22} className="spin" /><strong>Looking a few miles ahead…</strong><span>Finding routes and checking arrival-time weather</span></div>}
          {plan && <ForecastSlider corridor={corridor} hour={hour} setHour={setHour} metric={metric} setMetric={setMetric} visible={overlay} setVisible={setOverlay} loading={overlayLoading} error={overlayError} retry={() => void loadCorridor(plan)} />}
        </div>
        <footer className="map-footer"><span><ShieldCheck size={13} />Forecasts inform the journey. You make the call.</span><span>{plan?.provider || 'Real routes. Real forecasts.'}</span></footer>
      </section>
    </main>
  </div>
}
