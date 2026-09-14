"""Parse a messy SoundCloud title into structured fields."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

MIX_PATTERNS = re.compile(
    r"\b(dj set|live set|guest mix|essential mix|boiler room|"
    r"mixset|radio show|podcast|episode \d+|b2b)\b",
    re.IGNORECASE,
)

SEPARATOR = re.compile(r"\s+[-~–—|]\s+")
FEAT = re.compile(
    r"[\(\[]?(?:feat\.?|ft\.?|featuring)\s+([^\)\]\-~–—|]+)[\)\]]?",
    re.I,
)


@dataclass
class ParsedTrack:
    artist: str | None
    title: str
    features: list[str] = field(default_factory=list)
    version_tags: list[str] = field(default_factory=list)
    kind: str = "song"  # song | mix | unsure


def normalize(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    if not s:
        return ""
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    res = []
    s = s.split(" ")
    dict = {
        '$': 's',
        '&': 'and',
        '@': 'at'
    }
    for word in s:
        word_res = []
        for char in word:
            if char in dict:
                word_res.append(dict[char])
            elif char == "'":
                continue
            else:
                word_res.append(char)
        res.append(''.join(word_res))
    return ' '.join(res)


def classify(title: str, duration_sec: int | None, mix_max_sec: int = 900) -> str:
    has_mix_keyword = bool(MIX_PATTERNS.search(title))

    if duration_sec is not None and duration_sec > mix_max_sec:
        return "mix"
    if has_mix_keyword:
        return "mix"
    if duration_sec and duration_sec > 0:
        return "song"
    return "unsure"


def parse(title, uploader=None, sc_artist=None, duration_sec=None, mix_max_sec=900):
    kind = classify(title, duration_sec, mix_max_sec)
    if not title or not title.strip():
        return ParsedTrack(artist=None, title="", kind=kind)

    working = title.strip()

    features = []
    m = FEAT.search(working)
    if m:
        features = [n.strip() for n in re.split(r",|&| and ", m.group(1)) if n.strip()]
        working = FEAT.sub("", working).strip()

    version_tags = []

    parts = SEPARATOR.split(working, maxsplit=1)
    if len(parts) == 2:
        artist, song = parts[0].strip(), parts[1].strip()
    else:
        artist, song = None, working.strip()

    return ParsedTrack(artist=artist, title=song, features=features,
                       version_tags=version_tags, kind=kind)
