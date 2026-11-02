import { ArrowUpRight, Check, Clock3, MapPinned, ShieldCheck, TriangleAlert } from 'lucide-react'
import { duration, time } from '../types'
import type { Plan, Route } from '../types'

export default function RouteSummary({ plan, selected, onSelect }: { plan: Plan; selected: string; onSelect: (id: string) => void }) {
  return <section className="route-results">
    <div className="section-heading"><span className="eyebrow">THE ROAD OPTIONS</span><span className="result-count">{plan.routes.length} found</span></div>
    <p className="routes-explainer">Ranked by weather risk, then travel time.</p>
    {!plan.recommendation_id && <div className="notice danger"><TriangleAlert size={17} /><span>No route recommended under these rules. Review the exclusions below.</span></div>}
    {plan.routes.map((route: Route) => {
      const recommended = route.id === plan.recommendation_id
      return <button key={route.id} type="button" className={`route-card ${selected === route.id ? 'selected' : ''}`} onClick={() => onSelect(route.id)} aria-pressed={selected === route.id}>
        <div className="route-card-top"><span className="route-name"><span className="route-radio">{selected === route.id && <span />}</span>{route.name}</span>{recommended ? <span className="recommended"><ShieldCheck size={12} />Recommended</span> : !route.eligible ? <span className="excluded">Excluded</span> : <ArrowUpRight size={15} />}</div>
        <div className="route-main-stats"><strong>{duration(route.duration_seconds)}</strong><span className="stat-separator" /><span>{Math.round(route.distance_miles).toLocaleString()} <small>miles</small></span></div>
        <div className="arrival"><Clock3 size={12} /> Arrive {time(route.arrival)}</div>
        <div className="risk-stats"><span><i className="severe-dot" /><b>{route.risk_miles.Severe.toFixed(1)}</b> severe mi</span><span><i className="high-dot" /><b>{route.risk_miles.High.toFixed(1)}</b> high mi</span><span><b>{route.average_risk?.toFixed(2) ?? '—'}</b> avg / 4</span></div>
        {recommended && <div className="recommendation-reason"><Check size={12} />Best eligible risk ranking{route.risk_miles.Severe === 0 && route.risk_miles.High === 0 ? ' · no High or Severe miles' : ''}</div>}
        {!route.eligible && <div className="exclusion-reason">{route.exclusion_reasons.join(' · ')}</div>}
      </button>
    })}
    <div className="provider-note"><MapPinned size={13} /><span>{plan.provider} · Open-Meteo forecasts</span></div>
    <details className="route-notes"><summary>Route assumptions & limitations</summary>{plan.warnings.map(warning => <p key={warning}>{warning}</p>)}</details>
  </section>
}
