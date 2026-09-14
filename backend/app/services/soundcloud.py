"""Extract track metadata from a public SoundCloud playlist / profile.

P0: no SoundCloud account — yt-dlp maintains the web-player client_id for us.

Nudges:
  - `yt-dlp` has a Python API: `from yt_dlp import YoutubeDL`. `extract_info(url,
    download=False)` with `skip_download` gives you a dict; a playlist has an
    `entries` list.
  - You want per-track title + duration, so don't use `extract_flat` — that
    skips resolving each track (it's also why a big library is slow, which is
    why this runs in the worker).
  - Fields per entry: `id`, `title`, `uploader`, `artist`, `duration`,
    `webpage_url`. `duration` is seconds (float).
  - Strip the `?si=...&utm_...` share junk off the URL first.
  - yt-dlp is blocking — run it off the event loop (`asyncio.to_thread`).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawTrack:
    sc_track_id: str | None
    title: str
    uploader: str | None
    sc_artist: str | None
    duration_sec: int | None
    sc_url: str | None


@dataclass
class RawPlaylist:
    name: str
    tracks: list[RawTrack] = field(default_factory=list)


async def extract_playlist(url: str) -> RawPlaylist:
    raise NotImplementedError
