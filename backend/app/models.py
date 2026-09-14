"""Database models — mirrors the data-model design doc.

users → migrations → (source_items, target_playlists)
Match is 1:1 with SourceItem, so it lives as columns on source_items.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class SourceType(str, enum.Enum):
    likes = "likes"
    playlist = "playlist"


class MigrationStatus(str, enum.Enum):
    queued = "queued"
    extracting = "extracting"
    classifying = "classifying"
    matching = "matching"
    needs_review = "needs_review"
    committing = "committing"
    done = "done"
    failed = "failed"


class VersionPreference(str, enum.Enum):
    settle = "settle"  # substitute the original when the exact version isn't found
    strict = "strict"  # exact version only, else unmatched


class TrackKind(str, enum.Enum):
    song = "song"
    mix = "mix"
    unsure = "unsure"


class MatchStatus(str, enum.Enum):
    pending = "pending"
    auto_confirmed = "auto_confirmed"
    substituted = "substituted"  # matched a different (usually original) version
    needs_review = "needs_review"
    user_confirmed = "user_confirmed"
    unmatched = "unmatched"
    skipped = "skipped"  # kind != song


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    spotify_user_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    spotify_display_name: Mapped[str | None] = mapped_column(String)
    spotify_access_token_enc: Mapped[bytes] = mapped_column()
    spotify_refresh_token_enc: Mapped[bytes] = mapped_column()
    spotify_token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    migrations: Mapped[list[Migration]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Migration(Base):
    __tablename__ = "migrations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType, name="source_type"))
    source_url: Mapped[str | None] = mapped_column(Text)
    source_username: Mapped[str | None] = mapped_column(String)
    source_name: Mapped[str | None] = mapped_column(String)

    status: Mapped[MigrationStatus] = mapped_column(
        Enum(MigrationStatus, name="migration_status"), default=MigrationStatus.queued
    )
    version_preference: Mapped[VersionPreference] = mapped_column(
        Enum(VersionPreference, name="version_preference"), default=VersionPreference.settle
    )
    auto_commit: Mapped[bool] = mapped_column(default=True)

    total_items: Mapped[int] = mapped_column(Integer, default=0)
    done_items: Mapped[int] = mapped_column(Integer, default=0)
    count_matched: Mapped[int] = mapped_column(Integer, default=0)
    count_substituted: Mapped[int] = mapped_column(Integer, default=0)
    count_review: Mapped[int] = mapped_column(Integer, default=0)
    count_unmatched: Mapped[int] = mapped_column(Integer, default=0)
    count_skipped: Mapped[int] = mapped_column(Integer, default=0)

    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="migrations")
    items: Mapped[list[SourceItem]] = relationship(
        back_populates="migration", cascade="all, delete-orphan"
    )
    target_playlist: Mapped[TargetPlaylist | None] = relationship(
        back_populates="migration", cascade="all, delete-orphan", uselist=False
    )


class SourceItem(Base):
    __tablename__ = "source_items"
    __table_args__ = (Index("ix_source_items_migration_status", "migration_id", "match_status"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    migration_id: Mapped[str] = mapped_column(
        ForeignKey("migrations.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)

    # raw — straight from yt-dlp, never mutated
    raw_title: Mapped[str] = mapped_column(Text)
    raw_uploader: Mapped[str | None] = mapped_column(String)
    raw_sc_artist: Mapped[str | None] = mapped_column(String)
    raw_duration_sec: Mapped[int | None] = mapped_column(Integer)
    sc_url: Mapped[str | None] = mapped_column(Text)
    sc_track_id: Mapped[str | None] = mapped_column(String)

    # parsed — from parse()
    parsed_artist: Mapped[str | None] = mapped_column(String)
    parsed_title: Mapped[str | None] = mapped_column(String)
    parsed_features: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    parsed_version_tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    kind: Mapped[TrackKind] = mapped_column(
        Enum(TrackKind, name="track_kind"), default=TrackKind.song
    )

    # match — from rank()
    match_status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, name="match_status"), default=MatchStatus.pending
    )
    chosen_spotify_uri: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    candidates: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    migration: Mapped[Migration] = relationship(back_populates="items")


class TargetPlaylist(Base):
    __tablename__ = "target_playlists"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    migration_id: Mapped[str] = mapped_column(
        ForeignKey("migrations.id", ondelete="CASCADE"), unique=True
    )
    spotify_playlist_id: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(Text)
    track_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    migration: Mapped[Migration] = relationship(back_populates="target_playlist")
