"""Score Spotify candidates against a parsed SoundCloud track and pick a bucket.

Nudges:
  - Given one `ParsedTrack` and a list of `Candidate`s (Spotify search results),
    return the best match + a confidence + a bucket.
  - Buckets: auto_confirmed / substituted / needs_review / unmatched.
    High confidence + right version -> auto. High confidence but only the
    *original* exists when the user wanted a remix -> substituted (that's the
    "settle for original" decision). Genuinely unsure -> needs_review.
  - Three signals worth combining: title similarity, artist similarity, and how
    close the durations are. `rapidfuzz` gives you the string scores; duration
    is your tiebreaker and your false-positive filter.
  - Decide what disqualifies a candidate outright vs. just lowers its score.
  - Don't guess the weights/thresholds — tune them against a labelled set
    (correct Spotify URI or "none" for ~50-100 real tracks).
  - Keep the top ~5 scored candidates on the result — the review UI needs them.
"""

from __future__ import annotations

from dataclasses import dataclass


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
    raise NotImplementedError
