import { useEffect, useState } from 'react'
import './App.css'
import {
  connectSpotify,
  createMigration,
  getMigration,
  type MigrationStatus,
} from './api'

/**
 * P0 UI skeleton — three pieces:
 *   1. "Connect Spotify" button
 *   2. a form: paste a public SoundCloud playlist URL -> start migration
 *   3. a poller that shows status + bucket counts while the worker runs
 *
 * YOUR EXERCISE: the review table (list needs_review items, show candidates,
 * let the user pick) is P1 — stub is at the bottom.
 */
export default function App() {
  const params = new URLSearchParams(window.location.search)
  const [connected] = useState(params.get('connected') === '1')
  const [url, setUrl] = useState('')
  const [migrationId, setMigrationId] = useState<string | null>(null)
  const [status, setStatus] = useState<MigrationStatus | null>(null)
  const [error, setError] = useState<string | null>(params.get('auth_error'))

  // Poll while a migration is running.
  useEffect(() => {
    if (!migrationId) return
    const terminal = ['done', 'failed']
    const tick = async () => {
      try {
        const s = await getMigration(migrationId)
        setStatus(s)
        if (terminal.includes(s.status)) clearInterval(timer)
      } catch (e) {
        setError(String(e))
      }
    }
    const timer = setInterval(tick, 2000)
    tick()
    return () => clearInterval(timer)
  }, [migrationId])

  const start = async () => {
    setError(null)
    try {
      const { id } = await createMigration({ source: 'playlist', url })
      setMigrationId(id)
    } catch (e) {
      setError(String(e))
    }
  }

  return (
    <main style={{ maxWidth: 640, margin: '3rem auto', fontFamily: 'system-ui' }}>
      <h1>Hello Kitty Decaf</h1>
      <p>Move a SoundCloud playlist to Spotify.</p>

      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      {!connected ? (
        <button onClick={connectSpotify}>Connect Spotify</button>
      ) : (
        <>
          <p>✓ Spotify connected</p>
          <input
            style={{ width: '100%', padding: 8 }}
            placeholder="https://soundcloud.com/you/sets/your-playlist"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button onClick={start} disabled={!url || !!migrationId} style={{ marginTop: 8 }}>
            Migrate
          </button>
        </>
      )}

      {status && (
        <section style={{ marginTop: 24 }}>
          <h3>
            {status.source_name ?? 'Migration'} — {status.status}
          </h3>
          <progress value={status.progress.done} max={status.progress.total || 1} />
          <p>
            {status.progress.done} / {status.progress.total}
          </p>
          <ul>
            <li>matched: {status.buckets.matched}</li>
            <li>matched (different version): {status.buckets.substituted}</li>
            <li>needs review: {status.buckets.review}</li>
            <li>not found: {status.buckets.unmatched}</li>
            <li>skipped (mix/podcast): {status.buckets.skipped}</li>
          </ul>
          {status.target_playlist_url && (
            <a href={status.target_playlist_url} target="_blank" rel="noreferrer">
              Open Spotify playlist →
            </a>
          )}
        </section>
      )}

      {/* TODO(P1): review table — getItems(migrationId, 'needs_review'), render candidates,
          PATCH /migrations/{id}/items/{itemId} on selection. */}
    </main>
  )
}
