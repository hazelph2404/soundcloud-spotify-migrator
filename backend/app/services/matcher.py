"""Score Spotify candidates against a parsed SoundCloud track and pick a bucket.

Each candidate is scored on title, artist, and duration similarity. Candidates far
off on duration, or of the wrong version (e.g. a different remix), are dropped or
penalised. The best one then lands in one of four buckets:

  - auto_confirmed: confident match, right version
  - substituted:    confident match, but only the original exists when the
                    SoundCloud track was a remix/edit (``version_preference="settle"``)
  - needs_review:   plausible but not confident; the top candidates go to the review UI
  - unmatched:      nothing good enough (or a DJ set / mix)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from app.services.parser import FEAT, normalize

# Starting points, not tuned values: adjust against a labelled set.
TITLE_WEIGHT = 0.55
ARTIST_WEIGHT = 0.35
DURATION_WEIGHT = 0.10
DURATION_TOLERANCE_SEC = 15
UNKNOWN_ARTIST_SCORE = 0.5  # no parsed artist -> can't reach auto, lands in review
WRONG_VERSION_PENALTY = 0.5
VERSION_MATCH_MIN = 80  # fuzz score for "skrillex remix" vs "skrillex remix"
TOP_N = 5

# Words that make a recording a different version of the song.
VERSION_WORDS = re.compile(
    r"\b(remix|edit|rework|bootleg|flip|vip|extended|mix|dub|live|acoustic|"
    r"instrumental|sped up|slowed)\b"
)
# Labels Spotify adds that still mean the same recording -- dropped before comparing.
SAME_RECORDING = re.compile(
    r"\b(radio edit|original mix|(\d{4} )?remaster(ed)?( \d{4})?( version)?)\b"
)
BRACKETED = re.compile(r"[\(\[]([^\)\]]*)[\)\]]")
DASH_SUFFIX = re.compile(r"\s[-–—]\s(.*)$")


@dataclass
class Candidate:
    uri: str
    name: str
    artists: list[str]
    duration_sec: int
    popularity: int = 0


@dataclass
class MatchResult:
    status: str  # auto_confirmed | substituted | needs_review | unmatched
    chosen_uri: str | None
    confidence: float
    candidates: list[dict]  # top ~5, for the review UI


def decide(
    parsed,  # ParsedTrack
    q_duration_sec: int | None,
    candidates: list[Candidate],
    auto_threshold: float = 0.87,
    review_threshold: float = 0.60,
    version_preference: str = "settle",
) -> MatchResult:
    # DJ sets / long mixes aren't on Spotify as tracks.
    if parsed.kind == "mix" or not candidates:
        return MatchResult(status="unmatched", chosen_uri=None, confidence=0.0, candidates=[])

    scored = []
    for cand in candidates:
        result = _score(parsed, q_duration_sec, cand)
        if result is not None:
            scored.append(result)
    scored.sort(key=lambda s: s.score, reverse=True)
    top = [s.to_dict() for s in scored[:TOP_N]]

    if not scored:
        return MatchResult(status="unmatched", chosen_uri=None, confidence=0.0, candidates=top)

    best = next(
        (s for s in scored if s.version == "match" and s.score >= auto_threshold),
        scored[0],
    )
    confidence = round(best.score, 3)

    if best.score < review_threshold:
        status, chosen = "unmatched", None
    elif best.score < auto_threshold:
        status, chosen = "needs_review", None  # the user picks from `top` in the UI
    elif best.version == "original":
        if version_preference == "settle":
            status, chosen = "substituted", best.cand.uri
        else:
            status, chosen = "unmatched", None
    else:
        status, chosen = "auto_confirmed", best.cand.uri

    return MatchResult(status=status, chosen_uri=chosen, confidence=confidence, candidates=top)


@dataclass
class _Scored:
    score: float
    version: str  # match | original | wrong
    cand: Candidate

    def to_dict(self) -> dict:
        return {
            "uri": self.cand.uri,
            "name": self.cand.name,
            "artists": self.cand.artists,
            "duration_sec": self.cand.duration_sec,
            "score": round(self.score, 3),
            "version": self.version,
        }


def _score(parsed, q_duration_sec: int | None, cand: Candidate) -> _Scored | None:
    """Score one candidate from 0 to 1, or return None if it's disqualified."""
    sc_base, sc_version = _split_version(parsed.title)
    if parsed.version_tags:
        sc_version = normalize(" ".join(parsed.version_tags))
    cand_base, cand_version = _split_version(cand.name)

    version = _compare_versions(sc_version, cand_version)
    title = fuzz.token_sort_ratio(sc_base, cand_base) / 100
    artist = _artist_score(parsed, cand)

    if q_duration_sec is None:
        score = (TITLE_WEIGHT * title + ARTIST_WEIGHT * artist) / (TITLE_WEIGHT + ARTIST_WEIGHT)
    else:
        gap = abs(q_duration_sec - cand.duration_sec)
        # A remix and its original legitimately differ in length, so don't
        # filter the substitution candidate out on duration.
        if gap > DURATION_TOLERANCE_SEC and version != "original":
            return None
        duration = max(0.0, 1 - gap / DURATION_TOLERANCE_SEC)
        score = TITLE_WEIGHT * title + ARTIST_WEIGHT * artist + DURATION_WEIGHT * duration

    if version == "wrong":
        score *= WRONG_VERSION_PENALTY
    return _Scored(score=score, version=version, cand=cand)


def _split_version(raw: str) -> tuple[str, str]:
    """'Delilah (Skrillex Remix) [feat. X]' -> ('delilah', 'skrillex remix')."""
    s = normalize(FEAT.sub(" ", raw or ""))
    s = SAME_RECORDING.sub(" ", s)
    version_parts = []

    def pull_version(m: re.Match) -> str:
        if VERSION_WORDS.search(m.group(1)):
            version_parts.append(m.group(1))
            return " "
        return m.group(0)

    s = BRACKETED.sub(pull_version, s)
    s = DASH_SUFFIX.sub(pull_version, s)
    return _words(s), _words(" ".join(version_parts))


def _compare_versions(sc_version: str, cand_version: str) -> str:
    if not sc_version:
        return "wrong" if cand_version else "match"
    if not cand_version:
        return "original"
    if fuzz.token_sort_ratio(sc_version, cand_version) >= VERSION_MATCH_MIN:
        return "match"
    return "wrong"


def _artist_score(parsed, cand: Candidate) -> float:
    if not parsed.artist:
        return UNKNOWN_ARTIST_SCORE
    sc = _words(normalize(" ".join([parsed.artist, *parsed.features])))
    sp = _words(normalize(" ".join(cand.artists)))
    # set ratio: Spotify often lists extra artists (remixer, features).
    return fuzz.token_set_ratio(sc, sp) / 100


def _words(s: str) -> str:
    """Drop punctuation, keep letters/digits in any script: 'fred again..' -> 'fred again'."""
    return " ".join(re.findall(r"\w+", s))
