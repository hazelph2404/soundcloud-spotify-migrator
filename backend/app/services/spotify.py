from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Self
from urllib.parse import urlencode

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
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def authorize_url(state: str, challenge: str) -> str:
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "scope": settings.spotify_scopes,
    }
    return f"{AUTH_BASE}/authorize?{urlencode(params)}"


async def exchange_code(code: str, verifier: str) -> TokenBundle:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{AUTH_BASE}/api/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.spotify_redirect_uri,
                "client_id": settings.spotify_client_id,
                "code_verifier": verifier,
            },
        )
    if resp.status_code != 200:
        raise ValueError(f"Spotify exchange_code failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    return TokenBundle(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=time.time() + data["expires_in"],
    )


async def refresh_token(refresh: str) -> TokenBundle:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{AUTH_BASE}/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh,
                "client_id": settings.spotify_client_id,
            },
        )
    if resp.is_error:
        raise ValueError(f"Spotify refresh_token failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    return TokenBundle(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", refresh),
        expires_at=time.time() + data["expires_in"],
    )


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
        resp = await self._c.get("/me")
        if resp.is_error:
            raise ValueError(f"Spotify /me failed ({resp.status_code}): {resp.text}")
        return resp.json()

    async def search_tracks(self, query: str, limit: int = 10) -> list[Candidate]:
        resp = await self._c.get("/search", params={"q": query, "type": "track", "limit": limit})
        if resp.is_error:
            raise ValueError(f"Spotify search failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        candidates = []
        for song in data["tracks"]["items"]:
            candidates.append(
                Candidate(
                    uri=song["uri"],
                    name=song["name"],
                    artists=[a["name"] for a in song["artists"]],
                    duration_sec=song["duration_ms"] // 1000,
                    popularity=song.get("popularity", 0),
                )
            )
        return candidates

    async def create_playlist(self, name: str, public: bool = False) -> dict:
        resp = await self._c.post("/me/playlists", json={"name": name, "public": public})
        if resp.is_error:
            raise ValueError(f"Spotify create_playlist failed ({resp.status_code}): {resp.text}")
        return resp.json()

    async def add_tracks(self, playlist_id: str, uris: list[str]) -> None:
        resp = await self._c.post(f"/playlists/{playlist_id}/tracks", json={"uris": uris})
        if resp.is_error:
            raise ValueError(f"Spotify add_tracks failed ({resp.status_code}): {resp.text}")


def build_search_queries(artist: str | None, title: str) -> list[str]:
    """Three query variants — union the results, dedupe by URI, then score."""
    queries: list[str] = []
    if artist:
        queries.append(f"{artist} {title}")
        queries.append(f'track:"{title}" artist:"{artist}"')
    queries.append(title)
    return queries
