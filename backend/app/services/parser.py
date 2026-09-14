"""Parse a messy SoundCloud title into structured fields.

This is the harder half of P0 — the matcher can only be as good as this.
Build it against tests/test_parser.py (5 real tracks from playlist 'may'20').

Nudges:
  - Input is the raw title string. `uploader` / `sc_artist` are weak fallbacks —
    in real data the uploader is usually a curator, not the artist.
  - Titles use different separators between artist and song. Real examples you
    have: "Artist ~ Song", "Artist - Song", and "just a title" with no separator.
  - A "version tag" is anything meaning *not the plain original*: remix, edit,
    bootleg, slowed, sped up, live, acoustic, instrumental... You'll want these
    as a set, separate from the clean title.
  - `classify()` decides song vs mix vs unsure — mostly a duration + keyword call.
    A DJ set is an hour long; a song isn't.
  - `normalize()` is the shared cleanup (case, accents, punctuation, "$"->"s")
    used by both the parser and the matcher, so keep it consistent.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedTrack:
    artist: str | None
    title: str
    features: list[str] = field(default_factory=list)
    version_tags: list[str] = field(default_factory=list)
    kind: str = "song"  # song | mix | unsure


def normalize(s: str) -> str:
    raise NotImplementedError


def classify(title: str, duration_sec: int | None, mix_max_sec: int = 900) -> str:
    raise NotImplementedError


def parse(
    title: str,
    uploader: str | None = None,
    sc_artist: str | None = None,
    duration_sec: int | None = None,
    mix_max_sec: int = 900,
) -> ParsedTrack:
    raise NotImplementedError
