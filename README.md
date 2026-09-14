# Hello Kitty Decaf

Migrate your SoundCloud likes and playlists to Spotify — with a matching engine that
handles messy SoundCloud titles, and an honest report of what it couldn't find.

> Working codename. Real name TBD.

## Why

SoundCloud is where a lot of us found our music growing up — indie, remixes, bootlegs,
tracks by artists who never made it onto Spotify. Moving to Spotify means either losing
that history or re-searching thousands of songs by hand. This does it for you, and tells
you exactly what didn't transfer.

## How it works

1. Connect Spotify (OAuth).
2. Point it at your SoundCloud likes or a public playlist URL.
3. It scrapes the track list (`yt-dlp`), parses each messy title into `{artist, title,
   version}`, searches Spotify, and scores each candidate for confidence.
4. High-confidence matches are added automatically. The rest go to a review list.
5. You get a report: **matched · matched (different version) · needs review · not found · skipped**.

## Stack

| layer | tech |
|---|---|
| API | FastAPI (async) |
| Worker | ARQ + Redis — the migration runs here, not in the request |
| DB | Postgres (SQLAlchemy 2.0 async + Alembic) |
| Extraction | `yt-dlp` (no SoundCloud account needed for public data) |
| Matching | `rapidfuzz` + a custom title parser |
| Frontend | React (Vite) — thin: connect button, progress bar, review table |

## Scope

**P0 (now):** public likes + public playlists, Spotify OAuth only, auto-commit high
confidence, report the rest.
**Out of scope:** DJ mixes / podcasts / anything > 15 min, private playlists without a
share link, tracks genuinely not on Spotify.
**P1:** review-and-fix UI, official SoundCloud OAuth, LLM-assisted parsing.

## Local dev

```bash
# services (macOS)
brew services start postgresql@14 redis
createdb hello_kitty_decaf

# backend
cd backend
uv sync
cp .env.example .env          # fill in SPOTIFY_CLIENT_ID / SECRET
uv run alembic upgrade head
uv run uvicorn app.main:app --reload      # API on :8000
uv run arq app.worker.WorkerSettings      # worker (separate terminal)

# frontend
cd frontend
npm install
npm run dev                               # on :5173
```
