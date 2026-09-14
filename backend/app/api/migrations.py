

from __future__ import annotations

import json
from sqlalchemy import select

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.db import get_session
from app.models import Migration, SourceItem, SourceType, VersionPreference
from app.schemas import (
    CreateMigration,
    ItemOut,
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
    
    source_type = SourceType(body.source)
    version_preference = VersionPreference(body.version_preference)
    
    url = body.url
    auto_commit = body.auto_commit 
    username = body.username
    migration = Migration(user_id=user_id,source_username=username, source_type=source_type, source_url=url, auto_commit=auto_commit,  version_preference=version_preference)

    db.add(migration)
    await db.commit()
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    await pool.enqueue_job("run_migration", migration.id)
    return MigrationCreated(id = migration.id, status=migration.status.value)

@router.get("/{migration_id}", response_model=MigrationStatusOut)
async def get_migration(
    migration_id: str,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> MigrationStatusOut:
    migration = await db.get(
        Migration, migration_id, options=[selectinload(Migration.target_playlist)]
    )
    if migration is None or migration.user_id != user_id:
        raise HTTPException(404, "migration not found")
    source_type = SourceType(migration.source_type)
    source_name = migration.source_name
    target_playlist_url = migration.target_playlist.url if migration.target_playlist else None
    status = migration.status.value
    progress = {"done" : migration.done_items, "total": migration.total_items}
    buckets = {"matched": migration.count_matched, "substituted": migration.count_substituted, "review": migration.count_review, "unmatched": migration.count_unmatched, "skipped" : migration.count_skipped}
    error = migration.error
    return MigrationStatusOut(id=migration_id, 
                              source_type= source_type,
                              source_name = source_name, 
                              status= status, 
                              buckets=buckets,
                              progress=progress,
                              target_playlist_url= target_playlist_url, 
                              error = error 
                                 )




@router.get("/{migration_id}/items", response_model=ItemsPage)
async def get_items(
    migration_id: str,
    bucket: str | None = None,
    limit: int = 50,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> ItemsPage:
    migration = await db.get(Migration, migration_id)
    if migration is None or migration.user_id != user_id:
        raise HTTPException(404, "migration not found")
    stmt = select(SourceItem).where(SourceItem.migration_id == migration_id)
    if bucket:
        stmt = stmt.where(SourceItem.match_status == bucket)
    stmt = stmt.order_by(SourceItem.position).limit(min(limit, 200))
    result = await db.execute(stmt)
    rows = result.scalars().all()
    items = [
        ItemOut(
            id=row.id,
            position=row.position,
            raw_title=row.raw_title,
            raw_uploader=row.raw_uploader,
            raw_duration_sec=row.raw_duration_sec,
            sc_url=row.sc_url,
            parsed_artist=row.parsed_artist,
            parsed_title=row.parsed_title,
            parsed_version_tags=row.parsed_version_tags,
            kind=row.kind.value,
            match_status=row.match_status.value,
            chosen_spotify_uri=row.chosen_spotify_uri,
            confidence=float(row.confidence) if row.confidence is not None else None,
            candidates=row.candidates,
        )
        for row in rows
    ]
    return ItemsPage(items=items)


