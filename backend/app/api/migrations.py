"""Migration endpoints.

The routes, response models, and the session dependency are set up. Fill in the
handler bodies.

Nudges:
  - `POST /migrations`: create a Migration row, then enqueue an ARQ job for it.
    Enqueue pattern:  pool = await create_pool(RedisSettings.from_dsn(...));
    await pool.enqueue_job("run_migration", migration.id)
    Return 202 — the work hasn't happened yet.
  - `GET /migrations/{id}`: read the row, shape it into MigrationStatusOut.
    Check the row belongs to the caller (404 otherwise).
  - `GET /migrations/{id}/items`: filter SourceItem by `match_status` when
    `bucket` is given; order by position; cap the limit.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.schemas import (
    CreateMigration,
    ItemsPage,
    MigrationCreated,
    MigrationStatusOut,
)

settings = get_settings()
router = APIRouter(prefix="/migrations", tags=["migrations"])


async def current_user_id(hkd_session: str | None = Cookie(default=None)) -> str:
    """The auth cookie contract: a JSON blob with a `user_id`. Set by /auth/spotify/callback."""
    if not hkd_session:
        raise HTTPException(401, "not connected to Spotify")
    try:
        return json.loads(hkd_session)["user_id"]
    except (ValueError, KeyError):
        raise HTTPException(401, "bad session") from None


@router.post("", status_code=202, response_model=MigrationCreated)
async def create_migration(
    body: CreateMigration,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> MigrationCreated:
    raise NotImplementedError


@router.get("/{migration_id}", response_model=MigrationStatusOut)
async def get_migration(
    migration_id: str,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> MigrationStatusOut:
    raise NotImplementedError


@router.get("/{migration_id}/items", response_model=ItemsPage)
async def get_items(
    migration_id: str,
    bucket: str | None = None,
    limit: int = 50,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> ItemsPage:
    raise NotImplementedError
