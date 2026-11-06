// Thin API client. Endpoints match app/api/*.py on the FastAPI backend.

// Mirrors MigrationStatus / MatchStatus in backend app/models.py.
export type MigrationPhase =
  | 'queued'
  | 'extracting'
  | 'classifying'
  | 'matching'
  | 'needs_review'
  | 'committing'
  | 'done'
  | 'failed'

export type MatchStatus =
  | 'pending'
  | 'auto_confirmed'
  | 'substituted'
  | 'needs_review'
  | 'user_confirmed'
  | 'unmatched'
  | 'skipped'

export type MigrationStatus = {
  id: string
  source_type: string
  source_name: string | null
  status: MigrationPhase
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

// One scored Spotify match, as built by the backend matcher.
export type Candidate = {
  uri: string
  name: string
  artists: string[]
  duration_sec: number
  score: number
  version: 'match' | 'original' | 'wrong'
}

export type Item = {
  id: string
  position: number
  raw_title: string
  raw_uploader: string | null
  raw_duration_sec: number | null
  sc_url: string | null
  parsed_artist: string | null
  parsed_title: string | null
  parsed_version_tags: string[]
  kind: 'song' | 'mix' | 'unsure'
  match_status: MatchStatus
  chosen_spotify_uri: string | null
  confidence: number | null
  candidates: Candidate[]
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

export async function getItems(id: string, bucket?: MatchStatus): Promise<{ items: Item[] }> {
  const qs = bucket ? `?bucket=${bucket}` : ''
  const r = await fetch(`/migrations/${id}/items${qs}`, { credentials: 'include' })
  if (!r.ok) throw new Error(`getItems: ${r.status}`)
  return r.json()
}

// spotifyUri = one of the item's candidate URIs, or null for "none of these".
export async function chooseCandidate(
  migrationId: string,
  itemId: string,
  spotifyUri: string | null,
): Promise<Item> {
  const r = await fetch(`/migrations/${migrationId}/items/${itemId}`, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ spotify_uri: spotifyUri }),
  })
  if (!r.ok) throw new Error(`chooseCandidate: ${r.status}`)
  return r.json()
}
