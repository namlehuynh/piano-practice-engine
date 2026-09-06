"""Turning analysis into exercises.

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

The engine analysed well and generated nothing. Everything here is
mechanically derivable from data it already had, and all of it is
standard practice technique that was sitting in the report as prose
advice instead of as something to play.

The transition drill is the one that was properly missing. Amelie's left
hand is four positions, and the hard part is not any of them — it is the
move between them, which had no representation anywhere.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from .events import NoteEvent


def _by_bar(events: Sequence[NoteEvent], hand: str) -> dict[int, list[NoteEvent]]:
    bars: dict[int, list[NoteEvent]] = defaultdict(list)
    for e in events:
        if e.hand == hand:
            bars[e.measure].append(e)
    for m in bars:
        bars[m].sort(key=lambda x: (x.onset_q, x.midi))
    return bars


def transitions(
    events: Sequence[NoteEvent],
    hand: str,
    clusters: Sequence[dict],
    context: int = 2,
    limit: int = 6,
) -> list[dict]:
    """The few notes spanning a change of hand position.

    A chunk does not have to be a bar. Where the hand moves, the chunk is
    the last notes of one position plus the first of the next -- that
    join is the thing that actually fails in performance.
    """
    where: dict[int, str] = {}
    for c in clusters:
        for m in c["bars"]:
            where[m] = c["cluster_id"]
    bars = _by_bar(events, hand)

    seen: set[tuple[str, str]] = set()
    out = []
    for m in sorted(bars):
        nxt = m + 1
        if nxt not in bars or m not in where or nxt not in where:
            continue
        pair = (where[m], where[nxt])
        if pair[0] == pair[1] or pair in seen:
            continue
        seen.add(pair)
        notes = bars[m][-context:] + bars[nxt][:context]
        moved = len(set(n.midi for n in bars[nxt]) - set(n.midi for n in bars[m]))
        out.append(
            {
                "from_cluster": pair[0],
                "to_cluster": pair[1],
                "bars": (m, nxt),
                "notes": notes,
                "keys_moved": moved,
            }
        )
        if len(out) >= limit:
            break
    return out


def is_even_run(notes: Sequence[NoteEvent], minimum: int = 6) -> bool:
    if len(notes) < minimum:
        return False
    durs = {round(n.dur_q, 3) for n in notes}
    return len(durs) == 1 and next(iter(durs)) <= 0.5


def rhythm_variants(notes: Sequence[NoteEvent]) -> list[dict]:
    """Long-short and short-long versions of an even run.

    Classic finger-independence work: the notes and fingering stay put,
    only the timing changes, so every note gets a turn at being the one
    that has to arrive on time.
    """
    if not is_even_run(notes):
        return []
    unit = round(notes[0].dur_q, 3)
    return [
        {
            "name": "rhythm_long_short",
            "pattern": [unit * 1.5, unit * 0.5],
            "note": "rhythm_long_short_note",
        },
        {
            "name": "rhythm_short_long",
            "pattern": [unit * 0.5, unit * 1.5],
            "note": "rhythm_short_long_note",
        },
        {
            "name": "rhythm_pairs",
            "pattern": [unit * 2],
            "note": "rhythm_pairs_note",
        },
    ]


def block_chord(notes: Sequence[NoteEvent], divisions: int = 2) -> list[list[int]]:
    """Collapse a broken figure into the chords it outlines.

    Playing the notes together teaches the hand the distances in one go,
    far faster than rolling through them. The keyboard diagram already
    showed every key at once -- this just names it as the exercise.
    """
    if not notes:
        return []
    lo = min(n.onset_q for n in notes)
    hi = max(n.onset_q for n in notes)
    span = (hi - lo) or 1e-6
    out = []
    for k in range(divisions):
        seg = [
            n
            for n in notes
            if lo + span * k / divisions <= n.onset_q
            <= lo + span * (k + 1) / divisions + 1e-6
        ]
        if seg:
            block = sorted({n.midi for n in seg})
            if block not in out:
                out.append(block)
    return out


def overlap_pairs(clusters: Sequence[dict], limit: int = 6) -> list[dict]:
    """Chunk A carried through to the first note of chunk B.

    Stopping on the last note of a chunk trains a gap exactly where the
    music needs none. Every chunk is practised with one note of the next
    attached.
    """
    ordered = sorted(clusters, key=lambda c: c["bars"][0])
    out = []
    for a, b in zip(ordered, ordered[1:]):
        out.append(
            {
                "from": a["cluster_id"],
                "to": b["cluster_id"],
                "from_bar": a["representative"],
                "to_bar": b["representative"],
            }
        )
        if len(out) >= limit:
            break
    return out


def tempo_ladder(bpm: int | None, steps: int = 5) -> list[int]:
    """Slow-practice ladder from half speed up to the marked tempo."""
    if not bpm:
        return []
    start = max(int(bpm * 0.5), 40)
    if steps < 2:
        return [bpm]
    gap = (bpm - start) / (steps - 1)
    return [int(round(start + gap * i)) for i in range(steps)]
