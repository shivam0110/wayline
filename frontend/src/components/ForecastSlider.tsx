import { CloudRain, Layers2, LoaderCircle, Snowflake, Wind } from 'lucide-react'
import { time } from '../types'
import type { Corridor, Metric } from '../types'

const labels: Record<Metric, string> = { wind: 'Wind', rain: 'Rain', snow: 'Snow' }
const scales: Record<Metric, string[]> = { wind: ['0', '25', '35', '45', '55+ mph'], rain: ['0', '.10', '.25', '.50', '1+ in/hr'], snow: ['0', '.5', '1', '2', '3+ in/hr'] }
export default function ForecastSlider({ corridor, hour, setHour, metric, setMetric, visible, setVisible, loading, error, retry }: {
  corridor: Corridor | null; hour: number; setHour: (h: number) => void; metric: Metric; setMetric: (m: Metric) => void
  visible: boolean; setVisible: (v: boolean) => void; loading: boolean; error: string; retry: () => void
}) {
  const icons = { wind: Wind, rain: CloudRain, snow: Snowflake }
  return <section className="forecast-panel" aria-label="Corridor weather forecast">
    <div className="forecast-heading"><div><span className="eyebrow">ALONG YOUR CORRIDOR</span><h2>Weather outlook <span>+{hour}h</span></h2></div><button className={`layer-toggle ${visible ? 'active' : ''}`} type="button" aria-pressed={visible} onClick={() => setVisible(!visible)} title="Toggle weather overlay"><Layers2 size={16} /><span>{visible ? 'Layer on' : 'Layer off'}</span></button></div>
    <div className="forecast-toolbar"><div className="weather-tabs" role="group" aria-label="Weather layer">{(['wind', 'rain', 'snow'] as Metric[]).map(value => { const Icon = icons[value]; return <button type="button" key={value} className={metric === value ? 'active' : ''} aria-pressed={metric === value} onClick={() => setMetric(value)}><Icon size={14} />{labels[value]}</button> })}</div><div className="forecast-date">{corridor ? time(corridor.timestamps[hour]) : loading ? <><LoaderCircle className="spin" size={13} /> Loading forecast</> : 'Forecast unavailable'}</div></div>
    <input className="forecast-range" type="range" min="0" max="48" step="1" value={hour} disabled={!corridor} onChange={e => setHour(Number(e.target.value))} aria-label="Forecast hours from base time" aria-valuetext={corridor ? time(corridor.timestamps[hour]) : undefined} />
    <div className="slider-labels"><span>Now</span><span>+12h</span><span>+24h</span><span>+36h</span><span>+48h</span></div>
    <div className="weather-scale"><div className="scale-gradient" /><div className="scale-labels">{scales[metric].map(value => <span key={value}>{value}</span>)}</div></div>
    {error ? <p className="forecast-error">{error} <button type="button" onClick={retry}>Retry</button></p> : <p className="forecast-footnote">{corridor ? <>Base {time(corridor.timestamps[0])} · ~{Math.round(corridor.resolution_miles)} mi cells · {corridor.cells.length} samples{corridor.unavailable_cells > 0 && ` · ${corridor.unavailable_cells} unavailable`}</> : 'Fetching a coarse forecast grid around your routes…'}<span>Route risks stay tied to arrival times.</span></p>}
  </section>
}
