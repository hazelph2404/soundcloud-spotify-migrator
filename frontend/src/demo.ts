// Demo mode: replays a REAL recorded run (my may'20 playlist, Nov 2026) with no backend and
// no Spotify login. On by default when the site is built with VITE_DEMO=1 (the free static
// deploy), or locally by adding ?demo to the URL.
//
// It has the same function shapes as ./api, so the UI can't tell the difference.

import type { Item, MigrationStatus } from './api'

export const DEMO =
  import.meta.env.VITE_DEMO === '1' || new URLSearchParams(window.location.search).has('demo')

export const DEMO_URL = 'https://soundcloud.com/hazelhpham/sets/w0rk-m0r3-may20'

// Recorded from the real run. Candidate names/artists are what Spotify actually returned.
const ITEMS: Item[] = [
  item(
    0,
    'Amindi K. Fro$t, Tessellated & Valleyz ~ Pine & Ginger',
    'auto_confirmed',
    0.993,
    'Pine & Ginger',
    ['Amindi', 'Tessellated', 'Valleyz'],
  ),
  item(1, 'FKJ feat. Tom Bailey - Drops', 'auto_confirmed', 1.0, 'Drops', ['FKJ', 'Tom Bailey']),
  item(2, 'Jinsang - Egyptian Pools', 'auto_confirmed', 1.0, 'Egyptian Pools', ['Jinsang']),
  item(3, "Masego - Isn't She Lovely", 'unmatched', 0.533, 'Prone', ['Masego']),
]

// TODO: swap in the real playlist link after re-running may'20 with the /items fix.
const PLAYLIST_URL: string | null = null

const STEP_MS = 1400 // time per track, so the progress bar has something to show
let startedAt = 0

export async function createMigration(): Promise<{ id: string; status: string }> {
  startedAt = Date.now()
  return { id: 'demo', status: 'queued' }
}

export async function getMigration(): Promise<MigrationStatus> {
  const elapsed = Date.now() - startedAt
  const done = Math.min(ITEMS.length, Math.max(0, Math.floor((elapsed - 1200) / STEP_MS)))
  const seen = ITEMS.slice(0, done)
  const count = (s: Item['match_status']) => seen.filter((i) => i.match_status === s).length
  const finished = done === ITEMS.length && elapsed > 1200 + ITEMS.length * STEP_MS + 800

  return {
    id: 'demo',
    source_type: 'playlist',
    source_name: "may'20",
    status:
      elapsed < 1200
        ? 'extracting'
        : finished
          ? 'done'
          : done === ITEMS.length
            ? 'committing'
            : 'matching',
    progress: { done, total: ITEMS.length },
    buckets: {
      matched: count('auto_confirmed'),
      substituted: count('substituted'),
      review: count('needs_review'),
      unmatched: count('unmatched'),
      skipped: count('skipped'),
    },
    target_playlist_url: finished ? PLAYLIST_URL : null,
    error: null,
  }
}

export async function getItems(): Promise<{ items: Item[] }> {
  return { items: ITEMS }
}

function item(
  position: number,
  raw_title: string,
  match_status: Item['match_status'],
  confidence: number,
  name: string,
  artists: string[],
): Item {
  const uri = `spotify:track:demo-${position}`
  return {
    id: `demo-${position}`,
    position,
    raw_title,
    raw_uploader: null,
    raw_duration_sec: null,
    sc_url: null,
    parsed_artist: null,
    parsed_title: null,
    parsed_version_tags: [],
    kind: 'song',
    match_status,
    chosen_spotify_uri: match_status === 'auto_confirmed' ? uri : null,
    confidence,
    candidates: [{ uri, name, artists, duration_sec: 0, score: confidence, version: 'match' }],
  }
}
