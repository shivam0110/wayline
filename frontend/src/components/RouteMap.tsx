import { useEffect, useState } from 'react'
import { CircleMarker, MapContainer, Polygon, Polyline, Popup, TileLayer, ZoomControl, useMap } from 'react-leaflet'
import type { LatLngTuple } from 'leaflet'
import { Crosshair, Map, Navigation, ShieldCheck } from 'lucide-react'
import type { Coordinate, Corridor, Metric, Plan, Route } from '../types'
import { COLORS, LEVELS, riskColor, time } from '../types'

const latLng = ([lon, lat]: Coordinate): LatLngTuple => [lat, lon]

function FitRoutes({ plan, version }: { plan: Plan | null; version: number }) {
  const map = useMap()
  useEffect(() => {
    if (!plan) return
    map.fitBounds(plan.routes.flatMap(route => route.geometry.map(latLng)), {
      paddingTopLeft: [45, 85], paddingBottomRight: [45, Math.min(310, map.getSize().y * .45)], maxZoom: 11,
    })
  }, [map, plan, version])
  return null
}

function CheckpointMarkers({ route }: { route: Route }) {
  return route.checkpoints.map((p, index) => <CircleMarker key={index} center={latLng(p.coordinate)} radius={index === 0 || index === route.checkpoints.length - 1 ? 7 : 4}
    pathOptions={{ color: '#fff', weight: 2, fillColor: riskColor(p.risk.level), fillOpacity: 1 }}>
    <Popup><div className="checkpoint-popup"><strong>{route.name} · Mile {p.mile.toFixed(1)}</strong><span className="popup-risk" style={{ color: riskColor(p.risk.level) }}>{p.risk.label}</span><p>Arrival: {time(p.eta)}</p>
      {p.weather ? <><p>Wind: {p.weather.wind.toFixed(1)} mph</p><p>Rain: {p.weather.rain.toFixed(3)} in/hr</p><p>Snow: {p.weather.snow.toFixed(3)} in/hr</p><p>Forecast hour ending: {time(p.weather.forecast_time)}</p></> : <p>Weather unavailable</p>}
      {p.risk.reasons.map(reason => <p key={reason}>{reason}</p>)}
    </div></Popup>
  </CircleMarker>)
}

export default function RouteMap({ plan, selected, onSelect, corridor, hour, metric, overlay }: { plan: Plan | null; selected: string; onSelect: (id: string) => void; corridor: Corridor | null; hour: number; metric: Metric; overlay: boolean }) {
  const [fitVersion, setFitVersion] = useState(0)
  const ordered = [...(plan?.routes || [])].sort((a, b) => Number(a.id === selected) - Number(b.id === selected))
  const selectedRoute = plan?.routes.find(route => route.id === selected)
  const stops = metric === 'wind' ? [0, 25, 35, 45, 55] : metric === 'rain' ? [0, .1, .25, .5, 1] : [0, .5, 1, 2, 3]
  function weatherColor(value: number | undefined) {
    if (value === undefined) return '#9399a2'
    const colors = ['#d7e9dc', '#b4d6a9', '#e4d28a', '#e9a36c', '#ce6570']
    let index = 0
    while (index < stops.length - 1 && value >= stops[index + 1]) index++
    return colors[index]
  }
  return <>
    <MapContainer className="map-canvas" center={[40.8, -87]} zoom={5} zoomControl={false} preferCanvas>
      <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}" opacity={.65} attribution='Tiles &copy; Esri — Esri, HERE, Garmin, USGS, Intermap, INCREMENT P, NRCan, Esri Japan, METI, Esri China (Hong Kong), Esri Korea, Esri (Thailand), NGCC, &copy; OpenStreetMap contributors, GIS User Community' />
      <ZoomControl position="topright" />
      <FitRoutes plan={plan} version={fitVersion} />
      {overlay && corridor?.cells.map((cell, i) => <Polygon key={i} positions={cell.polygon.map(latLng)} interactive={false} pathOptions={{ stroke: false, fillColor: weatherColor(cell.values[hour]?.[metric]), fillOpacity: .4 }} />)}
      {ordered.map(route => <Polyline key={route.id} positions={route.geometry.map(latLng)} pathOptions={{ color: route.id === selected ? '#273b37' : '#fff', weight: route.id === selected ? 10 : 7, opacity: .9 }} eventHandlers={{ click: () => onSelect(route.id) }} />)}
      {ordered.flatMap(route => route.segments.map((segment, i) => <Polyline key={`${route.id}-${i}`} positions={segment.coordinates.map(latLng)} pathOptions={{ color: riskColor(segment.risk), weight: route.id === selected ? 6 : 4, opacity: route.id === selected ? 1 : .65 }} eventHandlers={{ click: () => onSelect(route.id) }} />))}
      {selectedRoute && <CheckpointMarkers key={selectedRoute.id} route={selectedRoute} />}
    </MapContainer>
    <div className="map-topline"><div className="map-label"><Map size={14} /><span>{plan ? 'Your journey, in perspective' : 'A little foresight. A better journey.'}</span></div><span className="map-region">{plan ? `${plan.routes.length} road options` : 'EXPLORE THE ROAD AHEAD'}</span></div>
    {plan && <button type="button" className="fit-button" onClick={() => setFitVersion(fitVersion + 1)}><Crosshair size={16} />Fit routes</button>}
    {!plan && <div className="map-empty"><span className="empty-icon"><Navigation size={26} strokeWidth={1.6} /></span><span className="eyebrow">GOOD JOURNEYS START HERE</span><h2>Know what’s<br />down the road.</h2><p>Compare real road routes.<br />Check the weather along the way.</p><div className="empty-badge"><ShieldCheck size={14} />Built around your journey</div></div>}
    <div className="risk-legend"><span className="legend-title">ROUTE RISK</span>{LEVELS.map((level, i) => <span key={level}><i style={{ background: COLORS[i] }} />{level}</span>)}<span><i style={{ background: '#89929e' }} />Unknown</span></div>
  </>
}
