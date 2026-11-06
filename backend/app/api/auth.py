"""Spotify OAuth endpoints (Authorization Code + PKCE)."""

from __future__ import annotations
import secrets
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.crypto import encrypt
from app.db import get_session
from app.models import User
from app.services.spotify import SpotifyClient, authorize_url, exchange_code, make_pkce
from app.session import COOKIE_NAME, MAX_AGE_SEC, make_session_cookie

settings = get_settings()
router = APIRouter(prefix="/auth/spotify", tags=["auth"])

_redis = aioredis.from_url(settings.redis_url, decode_responses=True)
_PKCE_TTL = 600  # seconds


@router.get("/login")
async def login() -> RedirectResponse:
    state = secrets.token_urlsafe()
    verifier, challenge = make_pkce()
    await _redis.set(state, verifier, ex = _PKCE_TTL)
    url = authorize_url(state, challenge)
    return RedirectResponse(url)


@router.get("/callback")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    if error:
        return RedirectResponse(f"{settings.frontend_origin}/?auth_error={error}")
    verifier = await _redis.get(state)
    if verifier is None:
        return RedirectResponse(f"{settings.frontend_origin}/?auth_error=invalid_state")
    try:
        tokens = await exchange_code(code, verifier)
    except ValueError:
        return RedirectResponse(f"{settings.frontend_origin}/?auth_error=exchange_failed")

    async with SpotifyClient(tokens.access_token) as client:
        profile = await client.me()

    result = await db.execute(select(User).where(User.spotify_user_id == profile["id"]))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(spotify_user_id=profile["id"])
        db.add(user)

    user.spotify_display_name = profile.get("display_name")
    user.spotify_access_token_enc = encrypt(tokens.access_token)
    user.spotify_refresh_token_enc = encrypt(tokens.refresh_token)
    user.spotify_token_expires_at = datetime.fromtimestamp(tokens.expires_at, tz=timezone.utc)
    await db.commit()

    response = RedirectResponse(f"{settings.frontend_origin}/?connected=1")
    response.set_cookie(
        COOKIE_NAME,
        make_session_cookie(user.id),
        max_age=MAX_AGE_SEC,
        httponly=True,  # page JS can't read it, so an XSS bug can't steal the session
        samesite="lax",
        secure=settings.frontend_origin.startswith("https://"),
    )
    return response
