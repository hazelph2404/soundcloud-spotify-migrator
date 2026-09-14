"""Spotify Web API — OAuth (Authorization Code + PKCE), search, playlist creation.

The dataclasses, the httpx client skeleton, and `build_search_queries()` are set up.
Implement the marked functions.

Nudges:
  - OAuth: `make_pkce()` creates the verifier + its SHA-256 challenge;
    `authorize_url()` builds the consent-screen URL; `exchange_code()` and
    `refresh_token()` POST to `{AUTH_BASE}/api/token` (form-encoded).
    Docs: https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow
  - `SpotifyClient` wraps the authed calls: `/me`, `/search?type=track`,
    create playlist, add tracks (100 URIs per request).
    A search result's length is `duration_ms` — the matcher wants seconds.
  - Spotify returns 429 with a `Retry-After` header when you go too fast.
    Decide where that's handled.
  - `refresh_token()`: Spotify sometimes returns a new refresh token, sometimes
    not — handle both.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

import httpx

from app.config import get_settings
from app.services.matcher import Candidate

settings = get_settings()

AUTH_BASE = "https://accounts.spotify.com"
API_BASE = "https://api.spotify.com/v1"


@dataclass
class TokenBundle:
    access_token: str
    refresh_token: str
    expires_at: float  # unix timestamp


def make_pkce() -> tuple[str, str]:
    raise NotImplementedError


def authorize_url(state: str, challenge: str) -> str:
    raise NotImplementedError


async def exchange_code(code: str, verifier: str) -> TokenBundle:
    raise NotImplementedError


async def refresh_token(refresh: str) -> TokenBundle:
    raise NotImplementedError


class SpotifyClient:
    def __init__(self, access_token: str):
        self._c = httpx.AsyncClient(
            base_url=API_BASE,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._c.aclose()

    async def me(self) -> dict:
        raise NotImplementedError

    async def search_tracks(self, query: str, limit: int = 10) -> list[Candidate]:
        raise NotImplementedError

    async def create_playlist(self, user_id: str, name: str, public: bool = False) -> dict:
        raise NotImplementedError

    async def add_tracks(self, playlist_id: str, uris: list[str]) -> None:
        raise NotImplementedError


def build_search_queries(artist: str | None, title: str) -> list[str]:
    """Three query variants — union the results, dedupe by URI, then score."""
    queries: list[str] = []
    if artist:
        queries.append(f"{artist} {title}")
        queries.append(f'track:"{title}" artist:"{artist}"')
    queries.append(title)
    return queries
