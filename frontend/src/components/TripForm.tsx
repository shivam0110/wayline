import { useEffect, useRef, useState } from 'react'
import { ArrowDownUp, ArrowRight, CalendarDays, Check, ChevronDown, Circle, LoaderCircle, MapPin, Package, Search } from 'lucide-react'
import { api } from '../api'
import type { Place, PlanInput } from '../types'

const initialOrigin: Place = { label: 'Chicago, Illinois, United States', coordinate: [-87.6298, 41.8781] }
const initialDestination: Place = { label: 'Detroit, Michigan, United States', coordinate: [-83.0458, 42.3314] }
const localDate = (date: Date) => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)

function PlaceInput({ label, place, onChange, destination }: { label: string; place: Place | null; onChange: (value: Place | null) => void; destination?: boolean }) {
  const [query, setQuery] = useState(place?.label || '')
  const [results, setResults] = useState<Place[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [active, setActive] = useState(0)
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => { if (place) setQuery(place.label) }, [place])
  useEffect(() => {
    if (!open || place || query.trim().length < 2) return
    const controller = new AbortController()
    const timer = setTimeout(async () => {
      setLoading(true); setError(''); setResults([])
      try {
        const data = await api<{ candidates: Place[] }>(`geocode?q=${encodeURIComponent(query)}`, undefined, controller.signal)
        setResults(data.candidates)
        if (!data.candidates.length) setError('No places found. Try a nearby city.')
      } catch (err) {
        if (!controller.signal.aborted) setError((err as Error).message)
      } finally { if (!controller.signal.aborted) setLoading(false) }
    }, 350)
    return () => { clearTimeout(timer); controller.abort() }
  }, [query, open, place])
  return <div className="place-wrap">
    <label htmlFor={`place-${label}`} className="field-label">{label}</label>
    <div className="place-field">
      {destination ? <MapPin size={17} className="accent" /> : <Circle size={15} />}
      <input id={`place-${label}`} ref={input} autoComplete="off" placeholder="Search city or place" value={query}
        onFocus={() => { if (!place) setOpen(true) }} onBlur={() => setOpen(false)}
        onChange={e => { setQuery(e.target.value); onChange(null); setResults([]); setActive(0); setOpen(true); setError('') }}
        onKeyDown={e => {
          if (e.key === 'Escape') setOpen(false)
          if (!open || !results.length) return
          if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); setActive((active + (e.key === 'ArrowDown' ? 1 : -1) + results.length) % results.length) }
          if (e.key === 'Enter') { e.preventDefault(); onChange(results[active]); setQuery(results[active].label); setOpen(false) }
        }}
        role="combobox" aria-expanded={open && !place} aria-controls={`results-${label}`} aria-activedescendant={open && results.length ? `result-${label}-${active}` : undefined} />
      {place ? <Check size={14} className="place-check" /> : loading ? <LoaderCircle size={15} className="spin" /> : <Search size={14} />}
    </div>
    {open && !place && query.length >= 2 && <div className="search-results" id={`results-${label}`} role="listbox">
      {results.map((p, i) => <button key={`${p.label}-${p.coordinate}`} id={`result-${label}-${i}`} type="button" role="option" aria-selected={i === active} onMouseDown={e => e.preventDefault()} onClick={() => { onChange(p); setQuery(p.label); setOpen(false) }}><MapPin size={15} /><span>{p.label}</span></button>)}
      {!results.length && <p>{loading ? 'Finding places…' : error || 'Keep typing to search…'}</p>}
    </div>}
  </div>
}

export default function TripForm({ onPlan, busy }: { onPlan: (data: PlanInput, label: string) => void; busy: boolean }) {
  const [origin, setOrigin] = useState<Place | null>(initialOrigin)
  const [destination, setDestination] = useState<Place | null>(initialDestination)
  const [departure, setDeparture] = useState(() => localDate(new Date(Date.now() + 3600000)))
  const [load, setLoad] = useState(35000)
  const [interval, setInterval] = useState(25)
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
  return <form className="trip-form" onSubmit={e => {
    e.preventDefault()
    if (origin && destination) onPlan({ origin: origin.coordinate, destination: destination.coordinate, departure: new Date(departure).toISOString(), load_lb: load, interval_miles: interval }, `${origin.label.split(',')[0]} → ${destination.label.split(',')[0]}`)
  }}>
    <div className="section-heading"><span className="eyebrow">YOUR NEXT JOURNEY</span><span className="tiny-pill">01 / Plan</span></div>
    <h1>A clearer road<br />ahead<span className="accent">.</span></h1>
    <p className="intro">Find the best way through the weather.</p>
    <div className="places">
      <PlaceInput label="Origin" place={origin} onChange={setOrigin} />
      <button type="button" className="swap-button" aria-label="Swap origin and destination" onClick={() => { setOrigin(destination); setDestination(origin) }}><ArrowDownUp size={14} /></button>
      <PlaceInput label="Destination" place={destination} onChange={setDestination} destination />
    </div>
    <label className="field-label" htmlFor="departure">Departure <span className="field-hint">{timezone}</span></label>
    <div className="input-field"><CalendarDays size={16} /><input id="departure" type="datetime-local" required value={departure} min={localDate(new Date())} max={localDate(new Date(Date.now() + 6 * 86400000))} onChange={e => setDeparture(e.target.value)} /></div>
    <label className="field-label" htmlFor="weight">Cargo weight <span className="field-hint">not gross vehicle weight</span></label>
    <div className="input-field"><Package size={16} /><input id="weight" type="number" min="0" max="200000" required value={load} onChange={e => setLoad(Number(e.target.value))} /><span className="input-unit">lb</span></div>
    <div className="spacing-heading"><label className="field-label" id="spacing-label">Weather checkpoints</label><span className="field-hint">Every</span></div>
    <div className="spacing-control" role="group" aria-labelledby="spacing-label">{[10, 25, 50].map(value => <button type="button" key={value} aria-pressed={interval === value} className={interval === value ? 'active' : ''} onClick={() => setInterval(value)}>{value} <span>mi</span>{interval === value && <Check size={13} />}</button>)}</div>
    <button className="plan-button" type="submit" disabled={busy || !origin || !destination}>{busy ? <><LoaderCircle size={18} className="spin" /> Checking the road ahead…</> : <>Find my routes <ArrowRight size={18} /></>}</button>
    <div className="form-note"><span className="status-dot" />Live forecasts · Depart within 6 days</div>
    <details className="rules"><summary>How your route is assessed <ChevronDown size={14} /></summary><p>Wind, rain and snow are checked at your estimated arrival time. Your cargo weight applies the assignment’s wind rules.</p><p>Routes rank by Severe miles, High miles, distance-weighted average risk, then travel time. Any No Travel or missing forecast excludes a route.</p><p>Estimates exclude rest stops. Forecasts are guidance; road conditions can change.</p></details>
  </form>
}
