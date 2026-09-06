"""Grouping bars the way a player hears them, not the way a hash does.

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

Three ideas, each addressing a way exact matching fails on real pop
arrangements:

1. Compare bars pairwise with a tolerance instead of hashing them. Two
   bars differing by one note are the same bar to a learner. Proud of
   You drops from 24 left-hand groups to 15, and bars 1-4 / 5-8 / 21-24
   finally register as the same four-bar phrase. Amelie is unaffected --
   it was already exact -- so the tolerance costs nothing where it is
   not needed.

2. Say which notes are chord tones and which are colour. "Remember these
   five keys" is not something a beginner can hold. "These three are the
   chord, these two are passing and you can leave them out at first" is.

3. Respect the meter. Phrase boundaries land on bar and hypermeasure
   lines, so candidate blocks are aligned to them rather than slid freely
   across the piece.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from .chords import NAMES, QUALITIES
from .events import NoteEvent


def bar_length(events: Sequence[NoteEvent]) -> float:
    """Quarter notes per bar, inferred from where bars actually start."""
    starts: dict[int, float] = {}
    for e in events:
        starts[e.measure] = min(starts.get(e.measure, e.onset_q), e.onset_q)
    ms = sorted(starts)
    gaps = [starts[b] - starts[a] for a, b in zip(ms, ms[1:])]
    if not gaps:
        return 4.0
    gaps.sort()
    return round(gaps[len(gaps) // 2], 3) or 4.0


def _by_bar(events: Sequence[NoteEvent], hand: str) -> dict[int, list[NoteEvent]]:
    bars: dict[int, list[NoteEvent]] = defaultdict(list)
    for e in events:
        if e.hand == hand:
            bars[e.measure].append(e)
    for m in bars:
        bars[m].sort(key=lambda x: (x.onset_q, x.midi))
    return bars


def _fingerprint(notes: Sequence[NoteEvent], grid: int = 12) -> set[tuple[int, int]]:
    """Which pitches sound when, on a grid of `grid` slots per quarter.

    Coarsening the grid is what makes bars 69-72 match 73-76 in Amelie:
    they hold the same pitches over the same beats, and differ only in
    which notes are struck together and which are split across adjacent
    onsets. At 1/12 resolution that reads as a completely different bar;
    at beat resolution the difference disappears, which is how a player
    hears it.
    """
    t0 = min(n.onset_q for n in notes)
    return {(int((n.onset_q - t0) * grid), n.midi) for n in notes}


def _seq_distance(a: tuple, b: tuple) -> int:
    """Positions that differ, plus the length gap."""
    return sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))


def cluster_bars(
    events: Sequence[NoteEvent],
    hand: str,
    tolerance: int = 1,
    scale: frozenset[int] | None = None,
    tier: str | None = None,
    ratio: float = 0.15,
) -> list[dict]:
    """Group bars that differ by at most `tolerance` notes.

    Returns clusters ordered by size, each with the bars it covers and a
    representative -- the bar whose notes are most fully chord tones, so
    what the learner memorises is the plain version rather than one that
    happens to carry an ornament.
    """
    bars = _by_bar(events, hand)
    if not bars:
        return []

    # The left hand is defined by which keys are under it, so it clusters
    # on absolute pitch. The right hand is a melody, defined by the shape
    # the fingers trace, so it clusters on that instead. Using raw pitch
    # for both hid the whole of Amelie's climax: bars 53-68 are one figure
    # repeated, and absolute matching saw sixteen unrelated bars.
    from .patterns import DEFAULT_TIER, _bar_key

    tier = tier or DEFAULT_TIER.get(hand, "exact")

    reps: list[tuple, list[int]] = []
    for m in sorted(bars):
        if tier == "exact":
            fp = _fingerprint(bars[m])
            coarse = _fingerprint(bars[m], grid=1)
            for existing, members in reps:
                # Tolerance scales with bar length: one note in a bar of
                # four is a different bar, one note in a bar of sixteen is
                # the same bar with an ornament.
                fine, rough = existing
                allow = max(tolerance, ratio * max(len(fp), len(fine)))
                if (
                    len(fp ^ fine) / 2 <= allow
                    or len(coarse ^ rough) / 2 <= allow
                ):
                    members.append(m)
                    break
            else:
                reps.append(((fp, coarse), [m]))
        else:
            key = _bar_key(bars[m], tier)
            coarse = _fingerprint(bars[m], grid=1)
            for existing, members in reps:
                shape, rough = existing
                allow = max(tolerance, ratio * max(len(key), len(shape)))
                # Either the figure matches, or the same pitches simply
                # land on the same beats grouped differently. Both are one
                # bar to a player; only together do they cover Amelie's
                # bars 69-84.
                if (
                    _seq_distance(key, shape) <= allow
                    or len(coarse ^ rough) / 2
                    <= max(tolerance, ratio * max(len(coarse), len(rough)))
                ):
                    members.append(m)
                    break
            else:
                reps.append(((key, coarse), [m]))

    out = []
    for i, (_, members) in enumerate(
        sorted(reps, key=lambda r: -len(r[1])), 1
    ):
        # The bar the learner reaches first. Choosing on chord purity sent
        # them to bar 15 of a cluster starting at bar 3; nobody opens a
        # piece from the middle. The cleanest bar is reported separately.
        scores = {m: purity(events, bars[m], scale) for m in members}
        best = min(members)
        cleanest = max(members, key=lambda m: (scores[m], -m))
        out.append(
            {
                "cluster_id": f"{hand}{i}",
                "bars": sorted(members),
                "count": len(members),
                "representative": best,
                "cleanest": cleanest,
                "purity": round(scores[best], 2),
                "notes": bars[best],
            }
        )
    return out


def harmony_at(
    events: Sequence[NoteEvent],
    notes: Sequence[NoteEvent],
    scale: frozenset[int] | None = None,
) -> dict | None:
    """Best chord over the span of `notes`, using BOTH hands.

    The left hand of a pop arrangement often plays only root and fifth --
    Proud of You never states a third in the left hand at all -- so major
    against minor is decided by the right hand or not at all.
    """
    lo = min(n.onset_q for n in notes)
    hi = max(n.onset_q + n.dur_q for n in notes)
    # Only notes that START inside the span. Letting sustained notes bleed
    # in makes the second half of a bar get judged against the first
    # half's chord, which turns perfectly good chord tones into "colour".
    pool = [e for e in events if lo - 1e-6 <= e.onset_q < hi]
    if not pool:
        return None

    weight: dict[int, float] = defaultdict(float)
    for n in pool:
        weight[n.midi % 12] += max(n.dur_q, 0.25) * (1.4 if n.hand == "L" else 1.0)
    total = sum(weight.values()) or 1.0
    bass = min(pool, key=lambda n: (n.onset_q, n.midi)).midi % 12

    best = None
    for quality, suffix, size in QUALITIES:
        if "sus" in suffix or size > 4:
            continue
        for root in list(weight):
            pcs = {(root + iv) % 12 for iv in quality}
            if not pcs <= set(weight):
                continue
            cover = sum(weight[p] for p in pcs) / total
            score = cover + (0.1 if root == bass else 0)
            if scale is not None:
                # Chords built from notes in the key are far likelier than
                # ones that are not. Without this prior the pass kept
                # picking chromatic fits over the obvious diatonic one.
                inside = sum(1 for p in pcs if p in scale) / len(pcs)
                score += 0.12 * inside
            cand = (round(score, 3), -size, root, suffix, pcs, cover)
            if best is None or cand > best:
                best = cand
    if best is None:
        return None
    _, _, root, suffix, pcs, cover = best
    return {
        "name": NAMES[root] + suffix,
        "root": root,
        "pcs": pcs,
        "coverage": round(cover, 3),
        "confident": cover >= 0.6,
    }


def purity(
    events: Sequence[NoteEvent],
    notes: Sequence[NoteEvent],
    scale: frozenset[int] | None = None,
) -> float:
    """Fraction of these notes that belong to the prevailing chord."""
    h = harmony_at(events, notes, scale)
    if not h:
        return 0.0
    return sum(1 for n in notes if n.midi % 12 in h["pcs"]) / len(notes)


def label_tones(
    events: Sequence[NoteEvent],
    notes: Sequence[NoteEvent],
    scale: frozenset[int] | None = None,
) -> list[dict]:
    """Mark each note as a chord tone or a colour note that can be dropped."""
    from music21 import pitch

    out = []
    # Chords change inside the bar, so ask per half-bar rather than once.
    lo = min(n.onset_q for n in notes)
    hi = max(n.onset_q for n in notes)
    mid = (lo + hi) / 2 + 1e-6
    halves = [
        [n for n in notes if n.onset_q <= mid],
        [n for n in notes if n.onset_q > mid],
    ]
    for half in halves:
        if not half:
            continue
        h = harmony_at(events, half, scale)
        for n in half:
            core = bool(h and n.midi % 12 in h["pcs"])
            out.append(
                {
                    "midi": n.midi,
                    "note": pitch.Pitch(n.midi).nameWithOctave,
                    "role": "chính" if core else "phụ",
                    "chord": h["name"] if h and h["confident"] else None,
                }
            )
    return out


def phrase_blocks(
    events: Sequence[NoteEvent], hand: str, clusters: Sequence[dict],
    lengths: Sequence[int] = (8, 4, 2),
) -> list[dict]:
    """Repeated blocks, aligned to the meter instead of slid freely.

    A four-bar phrase starts on a phrase line, so candidate blocks start
    at bars 1, 5, 9 ... Sliding windows find blocks straddling the
    boundary that a player would never perceive as a unit.
    """
    label: dict[int, str] = {}
    for c in clusters:
        for m in c["bars"]:
            label[m] = c["cluster_id"]
    numbers = sorted(label)
    if not numbers:
        return []
    origin = numbers[0]

    claimed: set[int] = set()
    out = []
    for length in lengths:
        groups: dict[tuple, list[int]] = defaultdict(list)
        for start in range(origin, numbers[-1] + 1, length):
            window = list(range(start, start + length))
            if not all(m in label for m in window):
                continue
            groups[tuple(label[m] for m in window)].append(start)
        for key, starts in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            kept = [s for s in starts if not (set(range(s, s + length)) & claimed)]
            if len(kept) < 2:
                continue
            for s in kept:
                claimed |= set(range(s, s + length))
            out.append(
                {
                    "length": length,
                    "starts": kept,
                    "occurrences": len(kept),
                    "bars_covered": len(kept) * length,
                    "shape": list(key),
                }
            )
    return sorted(out, key=lambda d: -d["bars_covered"])
