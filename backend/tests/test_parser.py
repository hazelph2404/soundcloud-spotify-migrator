"""Parser tests — the 5 real tracks from playlist 'may'20'.

Each case is a real SoundCloud title with its expected parse. Add rows from more
playlists to grow the labelled set the matcher is tuned against.

    uv run pytest -q
"""

import pytest

from app.services.parser import parse

# (raw_title, uploader, sc_artist, duration_sec) -> expected (artist, title, version_tags, kind)
CASES = [
    (
        "Amindi K. Fro$t, Tessellated & Valleyz ~ Pine & Ginger",
        "Film Noir Sound", "Film Noir Sound", 188,
        {"title": "pine and ginger", "kind": "song", "version_tags": []},
    ),
    (
        "FKJ feat. Tom Bailey - Drops",
        "FKJ", None, 241,
        {"title": "drops", "kind": "song", "features": ["Tom Bailey"]},
    ),
    (
        "Jinsang - Egyptian Pools",
        "Vitaboy", "JinSang", 130,
        {"artist": "jinsang", "title": "egyptian pools", "kind": "song"},
    ),
    (
        "Masego - Isn't She Lovely",
        "Artistic Manifesto", None, 182,
        {"title": "isnt she lovely", "kind": "song"},
    ),
    (
        "why dont we talk anymore",
        "rage logic", "rage logic", 189,
        {"title": "why dont we talk anymore", "kind": "song"},
    ),
]


@pytest.mark.parametrize("title,uploader,sc_artist,dur,expected", CASES)
def test_parse(title, uploader, sc_artist, dur, expected):
    p = parse(title, uploader=uploader, sc_artist=sc_artist, duration_sec=dur)
    if "kind" in expected:
        assert p.kind == expected["kind"]
    if "title" in expected:
        from app.services.parser import normalize

        assert normalize(p.title) == expected["title"]
    if "artist" in expected:
        from app.services.parser import normalize

        assert p.artist and normalize(p.artist) == expected["artist"]
    if "features" in expected:
        assert [f.lower() for f in p.features] == [f.lower() for f in expected["features"]]
    if "version_tags" in expected:
        assert sorted(p.version_tags) == sorted(expected["version_tags"])


def test_dj_mix_is_classified_as_mix():
    p = parse("Nice Hair with The Chainsmokers 027 ft. Illenium", duration_sec=3595)
    assert p.kind == "mix"
