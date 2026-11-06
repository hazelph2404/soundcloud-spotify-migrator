"""The `hkd_session` auth cookie: a signed, expiring token carrying the user id.

The cookie is signed with `SESSION_SECRET`, so the server can tell it issued it.
A cookie that was edited, forged, or signed with another secret is rejected.
"""

from __future__ import annotations

from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import get_settings

settings = get_settings()

COOKIE_NAME = "hkd_session"
MAX_AGE_SEC = 30 * 24 * 3600  # 30 days

if settings.session_secret == "dev-insecure-change-me":
    print("[session] SESSION_SECRET is the default — set a random one in .env before sharing the app")

_serializer = URLSafeTimedSerializer(settings.session_secret, salt="hkd-session")


def make_session_cookie(user_id: str) -> str:
    return _serializer.dumps({"user_id": user_id})


def read_session_cookie(value: str) -> str | None:
    """The user id inside a valid cookie, or None if it's forged, tampered, or expired."""
    try:
        data = _serializer.loads(value, max_age=MAX_AGE_SEC)
    except BadSignature:  # also covers SignatureExpired
        return None
    return data.get("user_id") if isinstance(data, dict) else None
