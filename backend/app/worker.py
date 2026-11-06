"""ARQ worker: runs a SoundCloud -> Spotify migration end to end.

The migration runs here, not in the HTTP request, because it's slow (minutes for a
big playlist) and must survive an API redeploy. `POST /migrations` only enqueues
`run_migration(migration_id)`; this process does the work and reports progress by
committing to the Migration row, which the frontend polls via `GET /migrations/{id}`.

Phases (each one sets `Migration.status` and commits before the slow part):
  extracting  -> pull tracks from SoundCloud, one SourceItem per track
  classifying -> parse titles; DJ sets / mixes are skipped
  matching    -> search Spotify per track, score with the matcher, store the bucket
  committing  -> create the Spotify playlist and add the chosen tracks in order
  done | needs_review (auto_commit off and some tracks need a human) | failed

`max_jobs` caps concurrent migrations: Spotify rate-limits per app, shared by every
user, and each track costs up to three searches.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from arq.connections import RedisSettings
from sqlalchemy import delete
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.crypto import decrypt, encrypt
from app.db import SessionLocal
from app.models import (
    MatchStatus,
    Migration,
    MigrationStatus,
    SourceItem,
    SourceType,
    TargetPlaylist,
    TrackKind,
    User,
)
from app.services.matcher import decide
from app.services.parser import ParsedTrack, parse
from app.services.soundcloud import extract_playlist
from app.services.spotify import SpotifyClient, build_search_queries, refresh_token

settings = get_settings()

ADD_TRACKS_BATCH = 100  # Spotify's max URIs per add-tracks request
TOKEN_REFRESH_MARGIN = timedelta(minutes=5)

# Which Migration counter each final match status bumps.
COUNTER_FOR_STATUS = {
    MatchStatus.auto_confirmed: "count_matched",
    MatchStatus.substituted: "count_substituted",
    MatchStatus.needs_review: "count_review",
    MatchStatus.unmatched: "count_unmatched",
    MatchStatus.skipped: "count_skipped",
}


async def run_migration(ctx: dict, migration_id: str) -> None:
    async with SessionLocal() as db:
        migration = await db.get(
            Migration, migration_id, options=[selectinload(Migration.user)]
        )
        # Already finished (e.g. the job was delivered twice): don't build a second playlist.
        if migration is None or migration.status == MigrationStatus.done:
            return
        try:
            await _reset(db, migration)

            migration.status = MigrationStatus.extracting
            await db.commit()
            items = await _extract(db, migration)

            migration.status = MigrationStatus.classifying
            await db.commit()
            songs = await _classify(db, migration, items)

            migration.status = MigrationStatus.matching
            await db.commit()
            access_token = await _access_token(db, migration.user)
            async with SpotifyClient(access_token) as client:
                await _match(db, migration, client, songs)

                if migration.count_review and not migration.auto_commit:
                    # The review UI finishes this migration later.
                    migration.status = MigrationStatus.needs_review
                    await db.commit()
                    return

                migration.status = MigrationStatus.committing
                await db.commit()
                await _commit_playlist(db, migration, client, items)

            migration.status = MigrationStatus.done
            await db.commit()

        except Exception as e:
            await db.rollback()
            migration.status = MigrationStatus.failed
            migration.error = str(e)
            await db.commit()
            raise


async def _reset(db, migration: Migration) -> None:
    """Make a re-run start clean: drop items and counters from any earlier attempt."""
    await db.execute(delete(SourceItem).where(SourceItem.migration_id == migration.id))
    await db.execute(delete(TargetPlaylist).where(TargetPlaylist.migration_id == migration.id))
    migration.error = None
    migration.total_items = 0
    migration.done_items = 0
    for counter in COUNTER_FOR_STATUS.values():
        setattr(migration, counter, 0)


async def _extract(db, migration: Migration) -> list[SourceItem]:
    if migration.source_type == SourceType.playlist:
        url = migration.source_url
    else:
        url = f"https://soundcloud.com/{migration.source_username}/likes"
    playlist = await extract_playlist(url)

    migration.source_name = playlist.name
    migration.total_items = len(playlist.tracks)

    items = []
    for i, track in enumerate(playlist.tracks):
        item = SourceItem(
            migration_id=migration.id,
            position=i,
            raw_title=track.title,
            raw_uploader=track.uploader,
            raw_sc_artist=track.sc_artist,
            raw_duration_sec=track.duration_sec,
            sc_url=track.sc_url,
            sc_track_id=track.sc_track_id,
        )
        db.add(item)
        items.append(item)
    await db.commit()
    return items


async def _classify(
    db, migration: Migration, items: list[SourceItem]
) -> list[tuple[SourceItem, ParsedTrack]]:
    """Parse every item. Returns the ones worth matching, paired with their parse."""
    songs = []
    for item in items:
        parsed = parse(
            item.raw_title,
            uploader=item.raw_uploader,
            sc_artist=item.raw_sc_artist,
            duration_sec=item.raw_duration_sec,
            mix_max_sec=settings.mix_max_duration_sec,
        )
        item.parsed_artist = parsed.artist
        item.parsed_title = parsed.title
        item.parsed_features = parsed.features
        item.parsed_version_tags = parsed.version_tags
        item.kind = TrackKind(parsed.kind)

        if item.kind == TrackKind.mix:
            _finish_item(migration, item, MatchStatus.skipped)
        else:
            songs.append((item, parsed))
    await db.commit()
    return songs


async def _access_token(db, user: User) -> str:
    """The user's Spotify access token, refreshed first if it's about to expire."""
    expires_soon = datetime.now(timezone.utc) + TOKEN_REFRESH_MARGIN
    if user.spotify_token_expires_at > expires_soon:
        return decrypt(user.spotify_access_token_enc)

    tokens = await refresh_token(decrypt(user.spotify_refresh_token_enc))
    user.spotify_access_token_enc = encrypt(tokens.access_token)
    user.spotify_refresh_token_enc = encrypt(tokens.refresh_token)
    user.spotify_token_expires_at = datetime.fromtimestamp(tokens.expires_at, tz=timezone.utc)
    await db.commit()
    return tokens.access_token


async def _match(
    db,
    migration: Migration,
    client: SpotifyClient,
    songs: list[tuple[SourceItem, ParsedTrack]],
) -> None:
    for item, parsed in songs:
        # The query variants overlap, so dedupe candidates by URI.
        by_uri = {}
        for query in build_search_queries(parsed.artist, parsed.title):
            for cand in await client.search_tracks(query):
                by_uri.setdefault(cand.uri, cand)

        result = decide(
            parsed,
            item.raw_duration_sec,
            list(by_uri.values()),
            auto_threshold=settings.match_auto_threshold,
            review_threshold=settings.match_review_threshold,
            version_preference=migration.version_preference.value,
        )
        item.chosen_spotify_uri = result.chosen_uri
        item.confidence = result.confidence
        item.candidates = result.candidates
        _finish_item(migration, item, MatchStatus(result.status))
        await db.commit()  # one commit per track keeps the progress bar moving


async def _commit_playlist(
    db, migration: Migration, client: SpotifyClient, items: list[SourceItem]
) -> None:
    # `items` is already in playlist order, so the Spotify playlist keeps it too.
    uris = [
        item.chosen_spotify_uri
        for item in items
        if item.match_status in (MatchStatus.auto_confirmed, MatchStatus.substituted)
    ]
    if not uris:
        return

    created = await client.create_playlist(migration.source_name or "SoundCloud import")
    for start in range(0, len(uris), ADD_TRACKS_BATCH):
        await client.add_tracks(created["id"], uris[start : start + ADD_TRACKS_BATCH])

    db.add(
        TargetPlaylist(
            migration_id=migration.id,
            spotify_playlist_id=created["id"],
            name=created["name"],
            url=created["external_urls"]["spotify"],
            track_count=len(uris),
        )
    )
    await db.commit()


def _finish_item(migration: Migration, item: SourceItem, status: MatchStatus) -> None:
    item.match_status = status
    counter = COUNTER_FOR_STATUS[status]
    setattr(migration, counter, getattr(migration, counter) + 1)
    migration.done_items += 1


class WorkerSettings:
    functions = [run_migration]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 4
