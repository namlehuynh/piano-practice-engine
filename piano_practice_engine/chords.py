"""Name the chord under a hand pattern, and find what stays put between them.

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

Chord names are the compact handle -- but for a beginner the more useful
fact is usually physical: which finger does NOT move when the hand
changes position. Amelie's left hand changes chord four times while the
little finger stays on the same key for three of them. That is the thing
worth putting on screen; the chord name is the label underneath it.
"""

from __future__ import annotations

from typing import Sequence

NAMES = ["C", "C#", "D", "E-", "E", "F", "F#", "G", "A-", "A", "B-", "B"]

QUALITIES = [
    (frozenset({0, 4, 7}), "", 3),
    (frozenset({0, 3, 7}), "m", 3),
    (frozenset({0, 3, 6}), "dim", 3),
    (frozenset({0, 4, 8}), "aug", 3),
    (frozenset({0, 5, 7}), "sus4", 3),
    (frozenset({0, 2, 7}), "sus2", 3),
    (frozenset({0, 4, 7, 10}), "7", 4),
    (frozenset({0, 3, 7, 10}), "m7", 4),
    (frozenset({0, 4, 7, 11}), "maj7", 4),
    (frozenset({0, 3, 7, 10, 2}), "m9", 5),
    (frozenset({0, 4, 7, 9}), "6", 4),
    (frozenset({0, 3, 7, 9}), "m6", 4),
]


def name_chord(midis: Sequence[int]) -> dict | None:
    """Best triad/seventh fit for a set of pitches, with slash bass."""
    if not midis:
        return None
    pcs = frozenset(m % 12 for m in midis)
    bass_pc = min(midis) % 12

    for quality, suffix, size in QUALITIES:
        if len(pcs) != size:
            continue
        for root in pcs:
            if frozenset((p - root) % 12 for p in pcs) == quality:
                name = NAMES[root] + suffix
                inverted = bass_pc != root
                # Only plain triads (and root-position sevenths) survive
                # for the learner. Measured over these scores, sus and
                # ninth matches are almost all artefacts of pooling a
                # bar's worth of passing notes into one pitch-class set:
                # Amelie yields four clean triads, while the two ballads
                # yield zero triads and a dozen spurious sus4 / m9 names.
                # Naming a chord wrong is worse than not naming it.
                confident = suffix in ("", "m") or (
                    suffix in ("7", "m7", "maj7") and bass_pc == root
                )
                return {
                    "confident": confident,
                    "name": name,
                    "root": NAMES[root],
                    "quality": suffix or "maj",
                    "bass": NAMES[bass_pc],
                    "inverted": inverted,
                    "display": f"{name}/{NAMES[bass_pc]}" if inverted else name,
                }
    return {
        "confident": False,
        "name": "/".join(NAMES[p] for p in sorted(pcs)),
        "root": None,
        "quality": "unknown",
        "bass": NAMES[bass_pc],
        "inverted": False,
        "display": " ".join(NAMES[p] for p in sorted(pcs)),
    }


def anchors(patterns: Sequence) -> dict:
    """Which keys are shared across every position, and which move.

    Takes Pattern objects from patterns.vocabulary().
    """
    keysets = [frozenset(p.midis) for p in patterns]
    if not keysets:
        return {}
    shared = frozenset.intersection(*keysets)
    basses = [min(p.midis) for p in patterns]
    tops = [max(p.midis) for p in patterns]

    def _common(values: Sequence[int]) -> dict:
        counts: dict[int, int] = {}
        for v in values:
            counts[v] = counts.get(v, 0) + 1
        key, n = max(counts.items(), key=lambda kv: kv[1])
        return {"midi": key, "note": NAMES[key % 12], "holds": n, "of": len(values)}

    return {
        "shared_keys": sorted(shared),
        "shared_notes": [NAMES[m % 12] for m in sorted(shared)],
        "bass": _common(basses),
        "top": _common(tops),
    }
