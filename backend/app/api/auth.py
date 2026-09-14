"""Spotify OAuth endpoints.

Router, Redis handle, and models are set up. Wire the two halves.

Nudges:
  - `/login`: make a `state` (CSRF guard) and a PKCE pair, stash the verifier in
    Redis keyed by state (short TTL), redirect the user to Spotify's consent URL.
  - `/callback`: Spotify sends back `code` + `state` (or `error`). Look the
    verifier back up, exchange the code for tokens, fetch `/me`, upsert a User
    (encrypt the tokens with `app.crypto`), and give the browser a session
    cookie. `app/api/migrations.py:current_user_id` shows what the cookie needs.
  - On any failure, redirect to `{frontend_origin}/?auth_error=...` rather than
    500 — the frontend reads that query param.
"""

from __future__ import annotations

import redis.asyncio as aioredis
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth/spotify", tags=["auth"])

_redis = aioredis.from_url(settings.redis_url)
_PKCE_TTL = 600  # seconds


@router.get("/login")
async def login() -> RedirectResponse:
    raise NotImplementedError


@router.get("/callback")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    raise NotImplementedError
