from __future__ import annotations
import asyncio
from dataclasses import dataclass, field

from yt_dlp import YoutubeDL

_YDL_OPTS = {
    "skip_download": True,
    "quiet": True,
    "extract_flat": False,
}


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

def _extract_sync(url: str) -> dict:
    with YoutubeDL(_YDL_OPTS) as ydl:
        return ydl.extract_info(url, download=False)


async def extract_playlist(url: str) -> RawPlaylist:
    if not url:
        raise ValueError("no playlist URL")
    url = url.split("?")[0]

    info = await asyncio.to_thread(_extract_sync, url)
    tracks: list[RawTrack] = []
    for song in info.get("entries") or []:
        if not song: continue
        song_id = song.get("id")
        duration = song.get("duration")
        tracks.append(RawTrack(
            sc_track_id=str(song_id) if song_id is not None else None,
            title=song.get("title") or "",
            uploader=song.get("uploader"),
            sc_artist=song.get("artist"),
            duration_sec=int(duration) if duration is not None else None,
            sc_url=song.get("webpage_url"),
        ))

    return RawPlaylist(name=info.get("title") or "playlist", tracks=tracks)