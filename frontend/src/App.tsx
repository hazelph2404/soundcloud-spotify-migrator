import { useEffect, useState, type CSSProperties } from 'react'
import './App.css'
import * as realApi from './api'
import type { Item, MigrationStatus } from './api'
import * as demoApi from './demo'
import { DEMO, DEMO_URL } from './demo'
import Hallway from './hallway/Hallway'
import { Cursor, Preloader, SplitText } from './fx/fx'
import { reducedMotion } from './fx/motion'

/**
 * P0 UI — you walk down a hallway of old memories (Hallway), open the door, and the
 * app is the room behind it:
 *   1. "Connect Spotify" button
 *   2. a form: paste a public SoundCloud playlist URL -> start migration
 *   3. a poller that shows status + bucket counts while the worker runs
 * The room's color goes from orange (SoundCloud side) to green as tracks get matched.
 */
const TERMINAL = ['done', 'failed']
// Demo mode swaps the real API for a recorded run (see demo.ts), so the UI is identical.
const api = DEMO ? demoApi : realApi

export default function App() {
  const params = new URLSearchParams(window.location.search)
  const [connected] = useState(DEMO || params.get('connected') === '1')
  const [url, setUrl] = useState(DEMO ? DEMO_URL : '')
  const [migrationId, setMigrationId] = useState<string | null>(null)
  const [status, setStatus] = useState<MigrationStatus | null>(null)
  const [items, setItems] = useState<Item[]>([])
  const [error, setError] = useState<string | null>(params.get('auth_error'))
  // Coming back from Spotify (success or error) lands you inside the room, not the hallway.
  const [entered, setEntered] = useState((connected && !DEMO) || error !== null)
  const [preloading, setPreloading] = useState(() => !entered && !reducedMotion())

  // Poll while a migration is running.
  useEffect(() => {
    if (!migrationId) return
    const tick = async () => {
      try {
        const s = await api.getMigration(migrationId)
        setStatus(s)
        if (TERMINAL.includes(s.status)) {
          clearInterval(timer)
          if (s.status === 'done') setItems((await api.getItems(migrationId)).items)
        }
      } catch (e) {
        setError(String(e))
      }
    }
    const timer = setInterval(tick, DEMO ? 700 : 2000)
    tick()
    return () => clearInterval(timer)
  }, [migrationId])

  const start = async () => {
    setError(null)
    setStatus(null)
    setItems([])
    try {
      const { id } = await api.createMigration({ source: 'playlist', url })
      setMigrationId(id)
    } catch (e) {
      setError(String(e))
    }
  }

  if (!entered) {
    return (
      <>
        <Cursor />
        {preloading && <Preloader onDone={() => setPreloading(false)} />}
        <Hallway
          introDelay={preloading ? 1900 : 0}
          onEnter={() => {
            setEntered(true)
            window.scrollTo(0, 0)
          }}
        />
      </>
    )
  }

  const running = !!migrationId && !(status && TERMINAL.includes(status.status))
  const progress = status && status.progress.total ? status.progress.done / status.progress.total : 0

  return (
    <main className="room" style={{ '--p': progress } as CSSProperties}>
      <Cursor />
      <div className="room__grain" aria-hidden="true" />
      <header className="room__head">
        <p className="room__kicker">hello kitty decaf</p>
        <h1>
          <SplitText text="Move a SoundCloud playlist to Spotify." delay={250} />
        </h1>
      </header>

      {error && <p className="room__error">{error}</p>}

      {!connected ? (
        <section className="card">
          <p className="card__hand">first, let me in</p>
          <button className="btn btn--big" onClick={realApi.connectSpotify} data-cursor="let me in">
            Connect Spotify
          </button>
          <p className="card__small">You'll log in on Spotify's own page. This app never sees your password.</p>
        </section>
      ) : (
        <section className="card">
          {DEMO ? (
            <p className="card__ok card__ok--demo">demo: a real recorded run, no login needed</p>
          ) : (
            <p className="card__ok">✓ Spotify connected</p>
          )}
          <label className="card__hand" htmlFor="sc-url">
            now, the soundcloud link
          </label>
          <div className="row">
            <input
              id="sc-url"
              className="input"
              placeholder="https://soundcloud.com/you/sets/your-playlist"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <button className="btn" onClick={start} disabled={!url || running} data-cursor="go">
              {running ? 'Moving…' : 'Migrate'}
            </button>
          </div>
        </section>
      )}

      {status && (
        <section className="card result">
          <h2>
            {status.source_name ?? 'Migration'} <span className={`pill pill--${status.status}`}>{status.status}</span>
          </h2>
          <div className="meter" aria-label="progress">
            <div className="meter__fill" style={{ transform: `scaleX(${progress})` }} />
          </div>
          <p className="result__count">
            {status.progress.done} / {status.progress.total} tracks
          </p>
          <ul className="buckets">
            <li><b>{status.buckets.matched}</b> matched</li>
            <li><b>{status.buckets.substituted}</b> matched (different version)</li>
            <li><b>{status.buckets.review}</b> needs review</li>
            <li><b>{status.buckets.unmatched}</b> not found</li>
            <li><b>{status.buckets.skipped}</b> skipped (mix/podcast)</li>
          </ul>
          {status.status === 'failed' && status.error && <p className="room__error">{status.error}</p>}
          {items.length > 0 && (
            <ol className="report">
              {items.map((it) => {
                const best = it.candidates.find((c) => c.uri === it.chosen_spotify_uri) ?? it.candidates[0]
                return (
                  <li key={it.id} className={`report__row report__row--${it.match_status}`}>
                    <span className="report__from">{it.raw_title}</span>
                    <span className="report__arrow" aria-hidden="true">→</span>
                    <span className="report__to">
                      {it.chosen_spotify_uri && best
                        ? `${best.name} · ${best.artists.join(', ')}`
                        : best
                          ? `not found (closest: ${best.name}, ${Math.round((it.confidence ?? 0) * 100)}%)`
                          : 'not found'}
                    </span>
                  </li>
                )
              })}
            </ol>
          )}
          {status.target_playlist_url && (
            <a className="btn btn--big" href={status.target_playlist_url} target="_blank" rel="noreferrer">
              Open Spotify playlist →
            </a>
          )}
        </section>
      )}

      {/* TODO: review table for needs_review items */}
    </main>
  )
}
