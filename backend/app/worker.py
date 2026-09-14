"""ARQ worker.

The migration runs here (not in the HTTP request) because it's slow and must
survive a redeploy. The ARQ wiring is set up; `run_migration` is yours.

Nudges:
  - `run_migration(ctx, migration_id)` is called by ARQ after `POST /migrations`
    enqueues it. Load the Migration row, do the work, update it as you go.
  - The frontend polls `GET /migrations/{id}` — so `status`, `done_items`,
    `total_items`, and the `count_*` columns need to move while you run.
  - Pieces you'll call: `services.soundcloud`, `services.parser`,
    `services.spotify`, `services.matcher`. None of them know about the DB —
    that's your job here.
  - Wrap the body so any exception lands as `status=failed` + `error=...`
    instead of a silent dead job.
  - `max_jobs` below is the global concurrency cap. Think about why that
    matters for Spotify's rate limit.
"""

from __future__ import annotations

from arq.connections import RedisSettings

from app.config import get_settings

settings = get_settings()


async def run_migration(ctx: dict, migration_id: str) -> None:
    raise NotImplementedError


class WorkerSettings:
    functions = [run_migration]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 4
