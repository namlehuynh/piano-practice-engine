"""Bar-level pattern vocabulary for one hand.

Piano Practice Engine — created and developed by Nam Le Huynh.
Copyright (C) 2026 Nam Le Huynh

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version. It is distributed WITHOUT ANY WARRANTY; see
the GNU General Public License for more details. You should have
received a copy of the licence with this program; if not, see
<https://www.gnu.org/licenses/>.

See AUTHORS.md. Direct questions about this engine to the author.

Separate from the unit segmenter on purpose. The segmenter works at
2-4 bars on the merged texture; accompaniment figures repeat at one bar
per hand. Amelie's left hand is five patterns covering 43 bars -- four
variants cycling plus two outliers -- and the segmenter finds none of it
because it never looks at that granularity.

This is the layer that answers "what do I actually play with my left
hand", which is the first thing a beginner needs.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Sequence

from .events import NoteEvent

TIERS = (
    "exact", "interval", "contour", "rhythm",
    "melody", "melody_interval", "gesture",
)

# Per-hand defaults. An accompaniment figure is defined by the actual keys
# under the hand, so the left hand matches on exact pitch. A melody is
# defined by the motion the hand makes, so the right hand matches on
# direction and thickness per onset with pitch discarded entirely -- the
# only tier that sees Amelie's bars 77 and 79 (one triad rolled upward,
# on two different chords in two different inversions) as one gesture
# played twice, which is exactly how a player describes them.
DEFAULT_TIER = {"L": "exact", "R": "gesture"}


@dataclass
class Pattern:
    pattern_id: str
    count: int
    measures: list[int]
    notes: list[str]  # note names of the first occurrence
    midis: list[int]
    intervals: list[int]  # semitones above the pattern's lowest note
    onsets: list[float]  # beat position within the bar
    durations: list[float]
    fingers: list[str]  # from the arrangement; empty when it carries none

    @property
    def n_notes(self) -> int:
        return len(self.midis)


def _melody_line(
    notes: Sequence[NoteEvent],
) -> tuple[list[int], tuple[int, ...], tuple[int, ...]]:
    """Top note at each onset -- the line the fingers actually follow.

    Collapsing simultaneities is what makes bars 17-20 of Amelie match
    bars 13-16: they are the same three-onset figure, harmonised into
    dyads. Counting individual notes sees 6 against 3 and never matches.
    """
    by_onset: dict[int, list[int]] = {}
    for n in notes:
        by_onset.setdefault(round(n.onset_q * 12), []).append(n.midi)
    keys = sorted(by_onset)
    tops = [max(by_onset[k]) for k in keys]
    spans = tuple(max(by_onset[k]) - min(by_onset[k]) for k in keys)
    return tops, tuple(k - keys[0] for k in keys), spans


def _bar_key(notes: Sequence[NoteEvent], tier: str) -> tuple:
    if tier == "gesture":
        # Direction and thickness only -- no pitch, no interval. Amelie's
        # bars 77 and 79 are the same motion (roll a triad upward through
        # its inversions) on different chords in different inversions, so
        # every interval-based tier misses them while a player sees one
        # gesture done twice.
        tops, rhythm, _ = _melody_line(notes)
        counts: dict[int, int] = {}
        for n in notes:
            counts[round(n.onset_q * 12)] = counts.get(round(n.onset_q * 12), 0) + 1
        thick = tuple(counts[k] for k in sorted(counts))
        contour = [0] + [
            (tops[i] > tops[i - 1]) - (tops[i] < tops[i - 1])
            for i in range(1, len(tops))
        ]
        return tuple(zip(contour, rhythm, thick))

    if tier in ("melody", "melody_interval"):
        tops, rhythm, spans = _melody_line(notes)
        if tier == "melody_interval":
            return tuple(zip((t - tops[0] for t in tops), rhythm, spans))
        contour = [0] + [
            (tops[i] > tops[i - 1]) - (tops[i] < tops[i - 1])
            for i in range(1, len(tops))
        ]
        return tuple(zip(contour, rhythm, spans))

    base = notes[0].midi
    t0 = notes[0].onset_q
    rhythm = tuple(round((n.onset_q - t0) * 12) for n in notes)
    if tier == "rhythm":
        return rhythm
    if tier == "exact":
        return tuple(zip((n.midi for n in notes), rhythm))
    if tier == "interval":
        return tuple(zip((n.midi - base for n in notes), rhythm))
    contour = []
    prev = None
    for n in notes:
        contour.append(0 if prev is None else (n.midi > prev) - (n.midi < prev))
        prev = n.midi
    return tuple(zip(contour, rhythm))


def vocabulary(
    events: Sequence[NoteEvent], hand: str, tier: str | None = None
) -> list[Pattern]:
    """Distinct one-bar figures for `hand`, most frequent first."""
    from music21 import pitch

    tier = tier or DEFAULT_TIER.get(hand, "exact")
    bars: dict[int, list[NoteEvent]] = defaultdict(list)
    for e in events:
        if e.hand == hand:
            bars[e.measure].append(e)
    for m in bars:
        bars[m].sort(key=lambda x: (x.onset_q, x.midi))

    keyed = {m: _bar_key(ns, tier) for m, ns in bars.items() if ns}
    counts = Counter(keyed.values())

    out: list[Pattern] = []
    for rank, (key, count) in enumerate(counts.most_common(), 1):
        measures = sorted(m for m, k in keyed.items() if k == key)
        ns = bars[measures[0]]
        base = ns[0].midi
        bar_start = min(n.onset_q for n in ns)
        out.append(
            Pattern(
                pattern_id=f"{hand}{rank}",
                count=count,
                measures=measures,
                notes=[pitch.Pitch(n.midi).nameWithOctave for n in ns],
                midis=[n.midi for n in ns],
                intervals=[n.midi - base for n in ns],
                onsets=[round(n.onset_q - bar_start, 3) for n in ns],
                durations=[round(n.dur_q, 3) for n in ns],
                fingers=[n.finger or "-" for n in ns]
                if any(n.finger for n in ns)
                else [],
            )
        )
    return out


def sequence(patterns: Sequence[Pattern]) -> list[tuple[int, str]]:
    """(measure, pattern_id) in bar order."""
    pairs = [(m, p.pattern_id) for p in patterns for m in p.measures]
    return sorted(pairs)


def detect_cycle(
    seq: Sequence[tuple[int, str]], min_agreement: float = 0.8
) -> dict | None:
    """Shortest period the pattern sequence repeats on.

    "Left hand cycles P1 -> P2 -> P3 -> P4" is far more useful to a
    learner than a list of five patterns with bar numbers.
    """
    ids = [pid for _, pid in seq]
    n = len(ids)
    if n < 4:
        return None
    for period in range(1, n // 2 + 1):
        pairs = [(ids[i], ids[i + period]) for i in range(n - period)]
        agree = sum(1 for a, b in pairs if a == b) / len(pairs)
        if agree >= min_agreement:
            return {
                "period": period,
                "agreement": round(agree, 3),
                "order": ids[:period],
                "first_measure": seq[0][0],
                "last_measure": seq[-1][0],
            }
    return None


def summarise(events: Sequence[NoteEvent], tier: str | None = None) -> dict:
    """Pattern vocabulary for both hands. tier=None uses DEFAULT_TIER."""
    out: dict = {}
    for hand in ("L", "R"):
        use = tier or DEFAULT_TIER[hand]
        pats = vocabulary(events, hand, use)
        if not pats:
            continue
        seq = sequence(pats)
        out[hand] = {
            "tier": use,
            "n_patterns": len(pats),
            "n_bars": len(seq),
            "cycle": detect_cycle(seq),
            "shortenings": shared_openings(events, hand, use),
            "loops": find_loops(events, hand, use),
            "patterns": pats,
            "sequence": seq,
        }
    return out


def technique_families(
    events: Sequence[NoteEvent], hand: str
) -> list[dict]:
    """Group exact patterns that share one contour and rhythm.

    Amelie's left hand has four exact patterns, but all four are the same
    physical gesture -- eight even eighths, x-y-z-y twice -- moved to four
    chord positions. Telling a beginner "one shape, four hand positions"
    is a different and much smaller task than "four patterns to learn".
    """
    exact = vocabulary(events, hand, "exact")
    coarse = {}
    bars: dict[int, str] = {}
    for p in vocabulary(events, hand, "contour"):
        for m in p.measures:
            bars[m] = p.pattern_id

    for p in exact:
        fam = bars.get(p.measures[0])
        coarse.setdefault(fam, []).append(p)

    out = []
    for rank, (fam, members) in enumerate(
        sorted(coarse.items(), key=lambda kv: -sum(p.count for p in kv[1])), 1
    ):
        out.append(
            {
                "family_id": f"{hand}F{rank}",
                "n_positions": len(members),
                "bars_covered": sum(p.count for p in members),
                "rhythm": members[0].durations,
                "shape": members[0].intervals,
                "members": members,
            }
        )
    return out


def shared_openings(
    events: Sequence[NoteEvent], hand: str, tier: str | None = None,
    min_shared: int = 3,
) -> list[dict]:
    """Bars that begin the same way and then diverge or stop.

    Amelie bar 8 opens exactly like bar 7 and then cuts short instead of
    completing the phrase. Strict prefix matching misses it, because the
    truncated bar still lands one final note in a different place -- so
    compare the longest common opening rather than requiring containment.

    Musically it is the same gesture; to a learner it is most of a bar
    they already know.
    """
    tier = tier or DEFAULT_TIER.get(hand, "exact")
    bars: dict[int, list[NoteEvent]] = defaultdict(list)
    for e in events:
        if e.hand == hand:
            bars[e.measure].append(e)
    for m in bars:
        bars[m].sort(key=lambda x: (x.onset_q, x.midi))

    keys = {m: _bar_key(ns, tier) for m, ns in bars.items() if ns}
    out = []
    for short in sorted(keys):
        sk = keys[short]
        best = None
        for other in sorted(keys):
            ok = keys[other]
            if other == short or ok == sk:
                continue
            n = 0
            for a, b in zip(sk, ok):
                if a != b:
                    break
                n += 1
            if n < min_shared or n < len(sk) / 2:
                continue
            # Prefer the nearest bar: a learner relates a passage to the
            # one they just played, not to bar 84.
            score = (-n, abs(other - short))
            if best is None or score < best[0]:
                best = (score, other, n)
        if best:
            _, other, n = best
            # Keep only genuine shortenings. Without this the relation is
            # symmetric and fires on ~85% of bars, which tells a learner
            # nothing.
            if len(keys[other]) <= len(sk):
                continue
            out.append(
                {
                    "bar": short,
                    "like_bar": other,
                    "shared": n,
                    "of": len(sk),
                    "full": len(keys[other]),
                }
            )
    return out


def find_loops(
    events: Sequence[NoteEvent],
    hand: str,
    tier: str | None = None,
    lengths: Sequence[int] = (8, 4, 2),
    min_occurrences: int = 2,
    similarity: float = 0.75,
) -> list[dict]:
    """Multi-bar blocks that recur, e.g. a four-bar harmonic loop.

    Global period detection only works when a piece loops all the way
    through. Amelie does -- one four-bar left-hand loop for 109 bars, 99%
    agreement. A pop ballad does not: Proud of You runs its four-bar loop
    at bars 1-4, again at 5-8, then leaves for twelve bars and returns at
    21-24. Averaged over the whole piece that reads as 15% agreement and
    looks like noise, which is why the periodic test reports nothing.

    So look for blocks that recur anywhere instead of one period that
    holds everywhere. Longest and most-repeated blocks claim their bars
    first; overlapping shorter ones are dropped.
    """
    tier = tier or DEFAULT_TIER.get(hand, "exact")
    bars: dict[int, list[NoteEvent]] = defaultdict(list)
    for e in events:
        if e.hand == hand:
            bars[e.measure].append(e)
    for m in bars:
        bars[m].sort(key=lambda x: (x.onset_q, x.midi))

    numbers = sorted(bars)
    keys = {m: _bar_key(bars[m], tier) for m in numbers}

    claimed: set[int] = set()
    loops: list[dict] = []

    for length in lengths:
        windows: list[tuple[int, tuple]] = []
        for i in range(len(numbers) - length + 1):
            window = numbers[i : i + length]
            if window[-1] - window[0] != length - 1:
                continue  # skip gaps in bar numbering
            windows.append((window[0], tuple(keys[m] for m in window)))

        # Cluster by near-equality, not equality. A repeat that adds one
        # colour note in one bar of four is still the same loop to a
        # learner, and demanding exact equality loses it entirely.
        groups: list[tuple[tuple, list[int]]] = []
        for start, key in windows:
            for gi, (gkey, starts) in enumerate(groups):
                same = sum(1 for a, b in zip(key, gkey) if a == b)
                if same / length >= similarity:
                    starts.append(start)
                    break
            else:
                groups.append((key, [start]))

        for _, starts in sorted(groups, key=lambda kv: -len(kv[1])):
            if len(starts) < min_occurrences:
                continue
            kept = []
            for s in starts:
                span = set(range(s, s + length))
                if span & claimed:
                    continue
                kept.append(s)
                claimed |= span
            if len(kept) >= min_occurrences:
                loops.append(
                    {
                        "length": length,
                        "starts": kept,
                        "occurrences": len(kept),
                        "bars_covered": len(kept) * length,
                    }
                )

    total = len(numbers)
    for lp in loops:
        lp["share"] = round(lp["bars_covered"] / total, 3) if total else 0
    return sorted(loops, key=lambda d: -d["bars_covered"])
