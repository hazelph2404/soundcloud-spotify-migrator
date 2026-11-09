# Hello Kitty Decaf 🎧

Move a SoundCloud playlist to Spotify, even when the SoundCloud titles are a mess.

## Why is it called Hello Kitty Decaf?

If you're wondering about the name: I wrote this app drinking water from my Hello Kitty Owala bottle and decaf coffee. It took me 10+ cups of decaf to build P0. So, Hello Kitty Decaf. 🐱☕

## Why I built this

In 2016, I was always listening to EDM on SoundCloud: hidden, lowkey songs and sets mixed and produced by artists who weren't on the radio. Those sets are how I discovered so many artists I didn't even know existed. I found Mura Masa on SoundCloud long before I heard anyone around me talk about him.

Things changed. I'm not that high school girl with hours to dig for new music anymore. Life got busy, and I stopped discovering the way I used to. But a lot of times I still want to go back to those songs, and SoundCloud is one way to do that. The problem: listening on SoundCloud just isn't as smooth as Spotify, where the rest of my music lives now.

So I built a way to bring the old favorites over. You paste a SoundCloud playlist, and a few seconds later the same songs are in a Spotify playlist, with a full report of what made it and what didn't.

There's another reason to do it now: songs disappear. While I was testing this app, one track in my old playlist (a bootleg) got taken down from SoundCloud. My playlist had 5 songs when I started this project. Now SoundCloud only returns 4.

## How it works

You paste a public SoundCloud playlist link. Then the app:

1. **Reads the playlist** with `yt-dlp` (no SoundCloud account needed for public playlists).
2. **Sorts songs from DJ mixes/podcasts.** A 2-hour mix is never going to be one song on Spotify, so those get skipped instead of wasting searches.
3. **Figures out the real artist and title.** This is the hard part. SoundCloud titles look like `Amindi K. Fro$t, Tessellated & Valleyz ~ Pine & Ginger` or `FKJ feat. Tom Bailey - Drops`. On my test playlist, the uploader was the real artist only **1 time out of 5** (usually it's a repost account), so I parse the **title first** and only fall back to the uploader.
4. **Searches Spotify and scores each result**: title similarity + artist similarity + duration (within ±3 seconds is a strong sign it's the same recording).
5. **Puts every song in a bucket:** matched · matched (different version) · needs review · not found · skipped.
6. **Creates a Spotify playlist** and adds the matched songs.

So basically: we find the matching songs, then we build a new playlist with them, and you get an honest report of what didn't make it.

## Decisions I made (and why)

- **"Settle for the original."** A lot of SoundCloud tracks are edits or remixes, and Spotify often only has the original. I had two options: be strict (exact version or nothing) or settle (add the original and flag it). I chose settle as the default, because a missing song hurts more than a slightly different version. It shows up as its own bucket, "matched (different version)", so nothing is hidden, and there's a `strict` mode if you want exact versions. A *different* remix is never auto-picked; that goes to review.
- **The work runs in a background worker, not in the request.** Matching a big playlist means hundreds of Spotify searches, and Spotify rate-limits. That can take minutes, and a normal web request would time out (and die on every deploy). So the API just says "got it" (`202 Accepted`) and a worker (ARQ + Redis) does the job while the page polls for progress.
- **Re-running a migration has to be safe.** I ran the same job twice on purpose and found it would create a *second* playlist. Now a re-run cleans up the old rows first, and a finished job just returns.
- **Progress counters live on the migration row.** The page asks for status every 2 seconds, so reading 5 numbers is much cheaper than counting rows every time.
- **Spotify login uses OAuth (PKCE).** The app never sees your password. Tokens are encrypted in the database, and the session cookie is signed, so nobody can edit it to pretend to be someone else.

## Things that broke on the first real run (and what I learned)

The first time I ran the whole thing on a real playlist (Nov 2026), matching worked: **3 out of 4 songs matched** with confidence 0.99–1.00. Then it said "failed". Here's what happened:

- **Spotify returned `403 Forbidden` when adding songs.** In February 2026 Spotify changed the API for apps in Development Mode, and adding tracks moved from `/playlists/{id}/tracks` to `/playlists/{id}/items`. The search worked, creating the playlist worked, but the one "add all songs" call hit the old endpoint, so I ended up with an empty playlist. Fixed by switching to `/items`.
- **The UI made it look like it half worked.** It showed "matched: 3" next to "failed", which reads like "3 songs got added, then it broke". Actually 0 got added. Now the page shows the real error, and that's on my list to make clearer.
- **Login worked but the app didn't know I was logged in.** The Spotify callback runs on `127.0.0.1`, but the frontend was on `localhost`. Browsers treat those as two different sites, so the session cookie never reached the app. Fixed by using `127.0.0.1` for both in dev.
- **One DRM-protected track stopped a whole playlist.** `yt-dlp` throws an error on it and the extraction stops. Next fix: skip that one track and report it, instead of failing everything.

## The design: a hallway into a room

I didn't want this to look like a form. It's like walking into a hallway into a room. The hallway walls are full of old albums and photos from 2016, and you scroll for about 10 seconds, smoothly to the right, until you reach a door. You open the door, and inside the room you connect Spotify and paste your SoundCloud link.

- The room starts **orange** (the old SoundCloud side) and turns **green** as your songs get matched, so the color shows the migration happening.
- Coming back from the Spotify login drops you straight into the room, so you never walk the hallway twice.
- There's a "skip the hallway" button, and if your system has reduced motion turned on, you just get the door, with no scroll effects.

## Status

| | |
|---|---|
| ✅ Works | reading playlists, title parsing (tested on real tracks), Spotify login, search + scoring, the worker, progress polling, the hallway + room UI |
| 🛠️ Fixing next | skip DRM tracks instead of failing; reuse the playlist on retry instead of leaving an empty one; a clearer "failed while saving" message |
| 📝 Planned | the review screen for "needs review" songs (the API for saving a choice is done; the UI isn't), a `GET /auth/me` check instead of trusting `?connected=1`, deploying it |

## Stack

| Part | Tech |
|---|---|
| API | FastAPI (async) |
| Worker | ARQ + Redis |
| Database | Postgres (SQLAlchemy 2.0 async + Alembic) |
| Reading SoundCloud | `yt-dlp` |
| Matching | `rapidfuzz` + my own title parser |
| Frontend | React + Vite (no animation libraries: the hallway is CSS 3D + one `requestAnimationFrame` loop) |

## How I used AI on this project

I built this with Claude Code as a pair programmer, and I tried to be intentional about it. It helped me scaffold the project, explained things I didn't know yet (Python, async, OAuth), reviewed my code, and helped debug. It also built the hallway animation. For the core logic I asked it to give me hints instead of answers, so I'd actually understand what I was shipping. I check everything it suggests against tests and by running the real thing, and that's how the bugs above were found.

## Run it locally

```bash
# services (macOS)
brew services start postgresql@14 redis
createdb hello_kitty_decaf

# backend
cd backend
uv sync
cp .env.example .env     # fill in SPOTIFY_CLIENT_ID / SECRET; use 127.0.0.1 (not localhost) for FRONTEND_ORIGIN
uv run alembic upgrade head
uv run uvicorn app.main:app --reload     # API on :8000
uv run arq app.worker.WorkerSettings     # worker, in a second terminal

# frontend
cd frontend
npm install
npm run dev -- --host 127.0.0.1          # open http://127.0.0.1:5173

# tests
cd backend && uv run pytest
```

Spotify apps in Development Mode only work for users you add in the Spotify developer dashboard (and they need Premium).
