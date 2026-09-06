"""Five interpretable descriptors per practice unit.


Deliberately not a learned model. Two reasons: a beginner cannot use a
score of 6.2/9, they need to know *what kind* of hard -- and ordering
units inside one piece is a far easier problem than predicting an
absolute Henle level, so hand-set descriptors are enough.

Reference ceilings below are the value at which a descriptor is treated
as maxed out. They are rough on purpose.

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
"""

from __future__ import annotations

from typing import Sequence

from .events import NoteEvent, Slice

CEILING = {
    "note_density": 8.0,  # notes per quarter note
    "pitch_range": 36.0,  # semitones between lowest and highest
    "hand_span": 12.0,  # widest simultaneous reach in one hand
    "position_shifts": 0.8,  # shifts per slice
    "hand_independence": 1.0,  # rhythmic dissimilarity between hands
}

WEIGHT = {
    "note_density": 1.0,
    "pitch_range": 0.6,
    "hand_span": 1.0,
    "position_shifts": 1.0,
    "hand_independence": 1.2,
}

# Reasons are stored as keys and translated at render time, so the same
# analysis can be read in either language.
LABEL = {k: f"why_{k}" for k in CEILING}


def _hand_slices(slices: Sequence[Slice], hand: str) -> list[tuple[int, ...]]:
    return [s.right if hand == "R" else s.left for s in slices]


def descriptors(
    unit_slices: Sequence[Slice], unit_events: Sequence[NoteEvent]
) -> dict[str, float]:
    if not unit_slices or not unit_events:
        return {k: 0.0 for k in CEILING}

    duration_q = max(
        sum(s.ioi_q for s in unit_slices), 1e-6
    )
    midis = [e.midi for e in unit_events]

    span = 0
    shifts = 0
    for hand in ("R", "L"):
        cols = [c for c in _hand_slices(unit_slices, hand) if c]
        for col in cols:
            span = max(span, col[-1] - col[0])
        for a, b in zip(cols, cols[1:]):
            if abs(b[0] - a[0]) > 5:
                shifts += 1

    right_onsets = {s.onset_q for s in unit_slices if s.right}
    left_onsets = {s.onset_q for s in unit_slices if s.left}
    union = right_onsets | left_onsets
    if right_onsets and left_onsets and union:
        disjoint = 1.0 - len(right_onsets & left_onsets) / len(union)
        # Onset disjointness alone is near 1.0 for almost all piano music
        # (a held bass under a running line looks maximally "independent"
        # but is easy). Scale it by how active the quieter hand actually
        # is -- two hands both busy on different rhythms is the hard case.
        balance = min(len(right_onsets), len(left_onsets)) / max(
            len(right_onsets), len(left_onsets)
        )
        independence = disjoint * balance
    else:
        independence = 0.0

    return {
        "note_density": len(unit_events) / duration_q,
        "pitch_range": float(max(midis) - min(midis)),
        "hand_span": float(span),
        "position_shifts": shifts / max(len(unit_slices), 1),
        "hand_independence": independence,
    }


def score_unit(
    unit_slices: Sequence[Slice], unit_events: Sequence[NoteEvent]
) -> dict:
    raw = descriptors(unit_slices, unit_events)
    normed = {k: min(raw[k] / CEILING[k], 1.0) for k in raw}
    total = sum(normed[k] * WEIGHT[k] for k in normed) / sum(WEIGHT.values())

    drivers = sorted(normed, key=lambda k: normed[k] * WEIGHT[k], reverse=True)[:2]
    return {
        "score": round(1 + total * 8, 2),  # 1..9, Henle-shaped but not calibrated
        "raw": {k: round(v, 3) for k, v in raw.items()},
        "normalised": {k: round(v, 3) for k, v in normed.items()},
        "drivers": drivers,
        "why": [LABEL[d] for d in drivers if normed[d] > 0.25],
    }


def techniques(unit_slices: Sequence[Slice]) -> list[str]:
    """Cheap surface heuristics -- enough to label a unit, not to teach it."""
    tags: set[str] = set()
    for hand in ("R", "L"):
        cols = [c for c in _hand_slices(unit_slices, hand) if c]
        if len(cols) < 4:
            continue
        steps = [abs(b[0] - a[0]) for a, b in zip(cols, cols[1:])]
        run = arp = 0
        for st in steps:
            run = run + 1 if st in (1, 2) else 0
            arp = arp + 1 if st in (3, 4, 5, 7, 8, 9) else 0
            if run >= 3:
                tags.add(f"scale_run_{hand}")
            if arp >= 3:
                tags.add(f"arpeggio_{hand}")
        if sum(1 for c in cols if len(c) >= 3) >= 3:
            tags.add(f"block_chords_{hand}")
        if any(len(c) >= 2 and c[-1] - c[0] == 12 for c in cols):
            tags.add(f"octaves_{hand}")
    return sorted(tags)
