from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, migrations
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Hello Kitty Decaf")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(migrations.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
