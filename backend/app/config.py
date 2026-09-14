from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres
    database_url: str = "postgresql+asyncpg://localhost/hello_kitty_decaf"

    # Redis (ARQ)
    redis_url: str = "redis://localhost:6379"

    # Spotify OAuth — https://developer.spotify.com/dashboard
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://127.0.0.1:8000/auth/spotify/callback"
    spotify_scopes: str = "playlist-modify-private playlist-modify-public"

    # App
    session_secret: str = "dev-insecure-change-me"
    token_encryption_key: str = ""  # Fernet key; generated on first run if blank
    frontend_origin: str = "http://localhost:5173"

    # Matching thresholds (tunable — see notes)
    match_auto_threshold: float = 0.87
    match_review_threshold: float = 0.60
    mix_max_duration_sec: int = 900


@lru_cache
def get_settings() -> Settings:
    return Settings()
