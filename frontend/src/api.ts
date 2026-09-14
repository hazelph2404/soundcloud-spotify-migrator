// Thin API client. Endpoints match app/api/*.py on the FastAPI backend.

export type MigrationStatus = {
  id: string
  source_type: string
  source_name: string | null
  status: string
  progress: { done: number; total: number }
  buckets: {
    matched: number
    substituted: number
    review: number
    unmatched: number
    skipped: number
  }
  target_playlist_url: string | null
  error: string | null
}

export type Item = {
  id: string
  raw_title: string
  raw_uploader: string | null
  sc_url: string | null
  parsed_artist: string | null
  parsed_title: string | null
  match_status: string
  confidence: number | null
  candidates: Array<Record<string, unknown>>
}

export const connectSpotify = () => {
  window.location.href = '/auth/spotify/login'
}

export async function createMigration(body: {
  source: 'playlist' | 'likes'
  url?: string
  username?: string
  version_preference?: 'settle' | 'strict'
}): Promise<{ id: string; status: string }> {
  const r = await fetch('/migrations', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`createMigration: ${r.status}`)
  return r.json()
}

export async function getMigration(id: string): Promise<MigrationStatus> {
  const r = await fetch(`/migrations/${id}`, { credentials: 'include' })
  if (!r.ok) throw new Error(`getMigration: ${r.status}`)
  return r.json()
}

export async function getItems(id: string, bucket?: string): Promise<{ items: Item[] }> {
  const qs = bucket ? `?bucket=${bucket}` : ''
  const r = await fetch(`/migrations/${id}/items${qs}`, { credentials: 'include' })
  if (!r.ok) throw new Error(`getItems: ${r.status}`)
  return r.json()
}
