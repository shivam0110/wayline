export async function api<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body), signal,
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(data?.error || `Request failed (${response.status}). Please try again.`)
  return data
}
