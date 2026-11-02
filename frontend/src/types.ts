export type Coordinate = [number, number]
export type Place = { label: string; coordinate: Coordinate }
export type Weather = { wind: number; rain: number; snow: number; forecast_time: string }
export type Metric = 'wind' | 'rain' | 'snow'
export type Risk = { level: number | null; label: string; reasons: string[] }
export type Checkpoint = { coordinate: Coordinate; mile: number; eta: string; weather: Weather | null; risk: Risk }
export type Segment = { coordinates: Coordinate[]; miles: number; risk: number | null }
export type Route = {
  id: string; name: string; geometry: Coordinate[]; distance_miles: number; duration_seconds: number; arrival: string
  checkpoints: Checkpoint[]; segments: Segment[]; risk_miles: Record<string, number>; unknown_miles: number
  average_risk: number | null; eligible: boolean; exclusion_reasons: string[]
}
export type PlanInput = { origin: Coordinate; destination: Coordinate; departure: string; load_lb: number; interval_miles: number }
export type Plan = { routes: Route[]; recommendation_id: string | null; provider: string; warnings: string[]; departure: string; generated_at: string }
export type Corridor = {
  cells: { coordinate: Coordinate; polygon: Coordinate[]; values: (Weather | null)[] }[]
  timestamps: string[]; resolution_miles: number; buffer_miles: number; units: Record<Metric, string>; unavailable_cells: number
}
export const LEVELS = ['Low', 'Moderate', 'High', 'Severe', 'No Travel']
export const COLORS = ['#278569', '#c7aa35', '#e28a37', '#d75b43', '#9d3556']
export const riskColor = (level: number | null) => level === null ? '#89929e' : COLORS[level]
export const time = (value: string) => new Date(value).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
export const duration = (seconds: number) => `${Math.floor(Math.round(seconds / 60) / 60)}h ${Math.round(seconds / 60) % 60}m`
