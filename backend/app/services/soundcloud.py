from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

_YDL_OPTS = {
    "skip_download": True,
    "quiet": True,
    "extract_flat": False,
}

# yt-dlp's prefix on error messages: "ERROR: [soundcloud] 2: <message>". The extractor name
# and the track id are optional, and the id never contains spaces, so a message that itself
# has colons ("HTTP Error 404: Not Found") is left whole.
_YDL_ERROR_PREFIX = re.compile(r"^ERROR:\s*(?:\[[^\]]*\]\s*)?(?:[\w-]+:\s+)?")


def _clean_error(e: DownloadError) -> str:
    """'ERROR: [soundcloud] 2: This track is DRM protected' -> 'This track is DRM protected'."""
    message = _YDL_ERROR_PREFIX.sub("", str(e)).strip()
    return message or str(e)


@dataclass
class RawTrack:
    sc_track_id: str | None
    title: str | None
    uploader: str | None
    sc_artist: str | None
    duration_sec: int | None
    sc_url: str | None
    error: str | None = None


@dataclass
class RawPlaylist:
    name: str
    tracks: list[RawTrack] = field(default_factory=list)


def _extract_sync(url: str) -> RawPlaylist:
    with YoutubeDL({**_YDL_OPTS, "extract_flat": "in_playlist"}) as ydl:
        listing = ydl.extract_info(url, download=False)
    tracks = []
    with YoutubeDL(_YDL_OPTS) as ydl:
        for entry in listing.get("entries") or []:
            try:
                song = ydl.extract_info(entry["url"], download=False)
                song_id = song.get("id")
                duration = song.get("duration")
                tracks.append(
                    RawTrack(
                        sc_track_id=str(song_id) if song_id is not None else None,
                        title=song.get("title"),
                        uploader=song.get("uploader"),
                        sc_artist=song.get("artist"),
                        duration_sec=int(duration) if duration is not None else None,
                        sc_url=song.get("webpage_url"),
                    )
                )
            except DownloadError as e:
                tracks.append(
                    RawTrack(
                        sc_track_id=str(entry["id"]),
                        title=None,
                        uploader=None,
                        sc_artist=None,
                        duration_sec=None,
                        sc_url=entry["url"],
                        error=_clean_error(e),
                    )
                )

    return RawPlaylist(name=listing.get("title") or "playlist", tracks=tracks)


async def extract_playlist(url: str) -> RawPlaylist:
    if not url:
        raise ValueError("no playlist URL")
    url = url.split("?")[0]
    return await asyncio.to_thread(_extract_sync, url)
