"""extract_playlist tests: one broken track must not sink the whole playlist.

Defines "done" for Task 1 in docs/TASKS.md. Runs offline: `YoutubeDL` is
replaced with a fake that behaves like the real one on a playlist with a DRM track.

    uv run pytest -q tests/test_soundcloud.py
"""

import pytest
from yt_dlp.utils import DownloadError

from app.services import soundcloud
from app.services.soundcloud import extract_playlist

PLAYLIST_URL = "https://soundcloud.com/hazelhpham/sets/fake-march20"

# What a flat (list-only) pass returns: ids + urls, no titles or durations.
FLAT_ENTRIES = [
    {"id": "1", "url": "https://soundcloud.com/a/one", "title": None, "duration": None},
    {"id": "2", "url": "https://soundcloud.com/b/drm-track", "title": None, "duration": None},
    {"id": "3", "url": "https://api-v2.soundcloud.com/tracks/3", "title": None, "duration": None},
]

# What loading one track on its own returns.
FULL_TRACKS = {
    "https://soundcloud.com/a/one": {
        "id": 1,
        "title": "Artist A - One",
        "uploader": "A",
        "artist": None,
        "duration": 200.0,
        "webpage_url": "https://soundcloud.com/a/one",
    },
    "https://api-v2.soundcloud.com/tracks/3": {
        "id": 3,
        "title": "Artist C - Three",
        "uploader": "C",
        "artist": "Artist C",
        "duration": 180.0,
        "webpage_url": "https://soundcloud.com/c/three",
    },
}
DRM_URL = "https://soundcloud.com/b/drm-track"


class FakeYDL:
    """Mimics yt_dlp.YoutubeDL just enough: flat playlist pass, single-track loads,
    and a full (non-flat) playlist load that dies on the DRM track like the real one."""

    def __init__(self, opts=None):
        self.opts = opts or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=False):
        if url.split("?")[0] == PLAYLIST_URL:
            if self.opts.get("extract_flat"):
                return {"title": "march'20", "entries": [dict(e) for e in FLAT_ENTRIES]}
            raise DownloadError("ERROR: [soundcloud] 2: This track is DRM protected")
        if url == DRM_URL:
            raise DownloadError("ERROR: [soundcloud] 2: This track is DRM protected")
        return dict(FULL_TRACKS[url])


@pytest.fixture(autouse=True)
def fake_ydl(monkeypatch):
    monkeypatch.setattr(soundcloud, "YoutubeDL", FakeYDL)


async def test_playlist_finishes_despite_drm_track():
    playlist = await extract_playlist(PLAYLIST_URL)
    assert playlist.name == "march'20"
    assert len(playlist.tracks) == 3, "the DRM track must be reported, not dropped"


async def test_order_is_kept():
    playlist = await extract_playlist(PLAYLIST_URL)
    assert [t.sc_track_id for t in playlist.tracks] == ["1", "2", "3"]


async def test_good_tracks_are_loaded_fully():
    playlist = await extract_playlist(PLAYLIST_URL)
    one, _, three = playlist.tracks
    assert one.title == "Artist A - One" and one.duration_sec == 200 and one.error is None
    assert three.sc_artist == "Artist C" and three.sc_url == "https://soundcloud.com/c/three"


async def test_drm_track_is_marked_with_a_reason():
    playlist = await extract_playlist(PLAYLIST_URL)
    drm = playlist.tracks[1]
    assert drm.error, "a failed track needs a reason the report can show"
    assert "DRM" in drm.error
    assert drm.sc_url == DRM_URL, "keep the link so the report can point at the track"


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("ERROR: [soundcloud] 2: This track is DRM protected", "This track is DRM protected"),
        (
            "ERROR: [soundcloud] Unable to download JSON metadata: HTTP Error 404: Not Found",
            "Unable to download JSON metadata: HTTP Error 404: Not Found",
        ),
        ("ERROR: This track is private", "This track is private"),
        ("something unexpected", "something unexpected"),
    ],
)
def test_error_reason_is_cleaned_for_people(raw, clean):
    assert soundcloud._clean_error(DownloadError(raw)) == clean


async def test_drm_reason_is_readable():
    playlist = await extract_playlist(PLAYLIST_URL)
    assert playlist.tracks[1].error == "This track is DRM protected"
