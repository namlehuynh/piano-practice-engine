"""Form analysis — the A / B / A map of a piece.

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

A card-per-pattern layout has nowhere to put material that never
repeats, so a through-composed climax disappears from it entirely. A
section map fixes that structurally: name the sections, mark which
recur, and an unrepeated passage becomes section C rather than a gap.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from .events import NoteEvent

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _bar_labels(events: Sequence[NoteEvent], clusters_by_hand: dict) -> dict[int, tuple]:
    label: dict[int, dict] = defaultdict(dict)
    for hand, clusters in clusters_by_hand.items():
        for c in clusters:
            for m in c["bars"]:
                label[m][hand] = c["cluster_id"]
    return {m: (v.get("L"), v.get("R")) for m, v in label.items()}


def sections(
    events: Sequence[NoteEvent],
    clusters_by_hand: dict,
    block: int = 8,
    similarity: float = 0.5,
) -> list[dict]:
    """Group bars into hypermeasures and letter them by what recurs.

    Pass ONE hand at a time. Merging both gives the worst of each: on
    Amelie the combined form reads as 81% new material, while the hands
    apart read correctly as a left hand that never changes (A A A A …,
    7% new) under a right hand that develops (A B C D B C E …). That
    contrast is the piece's whole structure, and merging hides it.
    """
    labels = _bar_labels(events, clusters_by_hand)
    if not labels:
        return []
    numbers = sorted(labels)
    origin = numbers[0]

    windows: list[tuple[int, int, tuple]] = []
    start = origin
    while start <= numbers[-1]:
        end = min(start + block - 1, numbers[-1])
        key = tuple(labels.get(m) for m in range(start, end + 1))
        windows.append((start, end, key))
        start = end + 1

    letters: list[tuple] = []
    out = []
    for lo, hi, key in windows:
        idx = None
        for i, known in enumerate(letters):
            pairs = list(zip(key, known))
            if not pairs:
                continue
            same = sum(1 for a, b in pairs if a == b and a is not None)
            if same / max(len(pairs), 1) >= similarity:
                idx = i
                break
        if idx is None:
            letters.append(key)
            idx = len(letters) - 1
        out.append(
            {
                "label": LETTERS[idx % 26],
                "first_bar": lo,
                "last_bar": hi,
                "bars": hi - lo + 1,
            }
        )

    counts: dict[str, int] = defaultdict(int)
    for s in out:
        counts[s["label"]] += 1
    for s in out:
        s["occurrences"] = counts[s["label"]]
        s["unique"] = counts[s["label"]] == 1
    return out


def form_string(secs: Sequence[dict]) -> str:
    return " ".join(s["label"] for s in secs)


def summary(secs: Sequence[dict]) -> dict:
    """How much of the piece is genuinely new material."""
    if not secs:
        return {}
    seen: set[str] = set()
    new_bars = 0
    for s in secs:
        if s["label"] not in seen:
            seen.add(s["label"])
            new_bars += s["bars"]
    total = sum(s["bars"] for s in secs)
    return {
        "sections": len(secs),
        "distinct": len(seen),
        "total_bars": total,
        "new_bars": new_bars,
        "share_new": round(new_bars / total, 3) if total else 0,
        "unique_sections": [s for s in secs if s["unique"]],
    }
