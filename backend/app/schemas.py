from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class CreateMigration(BaseModel):
    source: str = Field(pattern="^(likes|playlist)$")
    url: str | None = None
    username: str | None = None
    version_preference: str = Field(default="settle", pattern="^(settle|strict)$")
    auto_commit: bool = True

    @model_validator(mode="after")
    def _check(self) -> CreateMigration:
        if self.source == "playlist" and not self.url:
            raise ValueError("url is required when source is 'playlist'")
        if self.source == "likes" and not self.username:
            raise ValueError("username is required when source is 'likes'")
        return self


class MigrationCreated(BaseModel):
    id: str
    status: str


class MigrationStatusOut(BaseModel):
    id: str
    source_type: str
    source_name: str | None
    status: str
    progress: dict[str, int]
    buckets: dict[str, int]
    target_playlist_url: str | None
    error: str | None


class ItemOut(BaseModel):
    id: str
    position: int
    raw_title: str
    raw_uploader: str | None
    raw_duration_sec: int | None
    sc_url: str | None
    parsed_artist: str | None
    parsed_title: str | None
    parsed_version_tags: list[str]
    kind: str
    match_status: str
    chosen_spotify_uri: str | None
    confidence: float | None
    candidates: list[dict]


class ItemsPage(BaseModel):
    items: list[ItemOut]
    next_cursor: str | None = None

class ChooseCandidate(BaseModel):
    spotify_uri: str | None  # None = "none of these candidates is right"
