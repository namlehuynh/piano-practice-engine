"""Segmentation by dynamic programming.


A good cut is one that makes the resulting span recur elsewhere in the
piece -- that is exactly the value proposition for the learner, so it is
the objective function.

There is no `k` and no target unit count: the number and size of units
falls out of the optimum. The only knobs are the weights below, which are
set by hand and are meant to stay that way until real users start
dragging boundaries around.

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

from dataclasses import dataclass, field
from typing import Sequence

from .events import Slice
from .repetition import RepetitionIndex

NEG_INF = float("-inf")


@dataclass
class Weights:
    repetition: float = 1.0
    boundary: float = 4.0
    length: float = 2.0
    min_measures: int = 2
    max_measures: int = 4
    min_slices: int = 4
    max_slices: int = 48
    # Score cuts on per-hand repetition as well as the merged texture.
    # Off by default: measured across six pieces it helps ostinato pop
    # (Amelie 85% -> 72% hand-separate load) but badly hurts others
    # (C. Schumann 63% -> 94%). Taking max() over three views means
    # almost every span scores occ > 1, so the repetition term stops
    # discriminating and cuts fall back to boundary bonus alone.
    hand_aware: bool = False


@dataclass
class Unit:
    unit_id: str
    start_slice: int
    end_slice: int  # exclusive
    start_q: float
    end_q: float
    first_measure: int
    last_measure: int
    occurrences: int
    score: float
    group_id: str | None = None
    match_kind: str | None = None
    difficulty: dict = field(default_factory=dict)
    techniques: list[str] = field(default_factory=list)
    related: dict = field(default_factory=dict)
    hand_match: dict = field(default_factory=dict)

    @property
    def n_slices(self) -> int:
        return self.end_slice - self.start_slice


def boundary_bonus(slices: Sequence[Slice], position: int) -> float:
    """How natural is a cut immediately before `position`?"""
    if position <= 0 or position >= len(slices):
        return 1.0  # the very start and end of the piece are free cuts
    s = slices[position]
    if s.after_rest:
        return 1.0
    if s.starts_measure:
        return 0.6
    return 0.0


def strict_ok(measures: int, is_final: bool, w: Weights) -> bool:
    """Is this unit length acceptable? The last unit may be short."""
    if measures > w.max_measures:
        return False
    return is_final or measures >= w.min_measures


def span_score(
    slices: Sequence[Slice],
    index: RepetitionIndex,
    j: int,
    i: int,
    w: Weights,
) -> tuple[float, int]:
    n = i - j
    occ = index.occurrences(j, n)

    # Raw saving from a repeated span is n * (occ - 1) slices not learnt,
    # but the DP sums over every occurrence, so divide by occ. Without
    # this, a 4-slice figure recurring 20 times beats a real 2-bar phrase.
    rep_gain = w.repetition * n * (occ - 1) / occ

    edges = boundary_bonus(slices, j) + boundary_bonus(slices, i)
    edge_gain = w.boundary * edges

    measures = slices[i - 1].measure - slices[j].measure + 1
    over = max(0, measures - w.max_measures, w.min_measures - measures)
    length_cost = w.length * (over**1.5)

    return rep_gain + edge_gain - length_cost, occ


def segment(
    slices: Sequence[Slice],
    index: RepetitionIndex,
    w: Weights | None = None,
) -> list[Unit]:
    """Return the highest-scoring partition of the whole slice stream."""
    w = w or Weights()
    n = len(slices)
    if n == 0:
        return []

    best = [NEG_INF] * (n + 1)
    back = [0] * (n + 1)
    best[0] = 0.0

    for i in range(1, n + 1):
        lo = max(0, i - w.max_slices)
        # The final segment is allowed to be short -- a piece rarely ends
        # on an exact multiple of the minimum unit length.
        hi = i - 1 if i == n else i - w.min_slices
        for j in range(lo, hi + 1):
            if best[j] == NEG_INF:
                continue
            measures = slices[i - 1].measure - slices[j].measure + 1
            # Hard window on unit length. The soft penalty alone loses to
            # the boundary bonus and the piece shatters into fragments.
            if not strict_ok(measures, i == n, w):
                continue
            value, _ = span_score(slices, index, j, i, w)
            total = best[j] + value
            if total > best[i]:
                best[i] = total
                back[i] = j

    if best[n] == NEG_INF:
        # No partition satisfies the window (very short or odd piece).
        return segment_naive(slices, w.max_measures)

    cuts = [n]
    while cuts[-1] > 0:
        cuts.append(back[cuts[-1]])
    cuts.reverse()

    units: list[Unit] = []
    for k in range(len(cuts) - 1):
        j, i = cuts[k], cuts[k + 1]
        value, occ = span_score(slices, index, j, i, w)
        end_q = slices[i].onset_q if i < n else slices[i - 1].onset_q + slices[i - 1].ioi_q
        units.append(
            Unit(
                unit_id=f"u{k + 1:02d}",
                start_slice=j,
                end_slice=i,
                start_q=slices[j].onset_q,
                end_q=end_q,
                first_measure=slices[j].measure,
                last_measure=slices[i - 1].measure,
                occurrences=occ,
                score=round(value, 3),
            )
        )
    return units


def segment_naive(slices: Sequence[Slice], max_measures: int = 4) -> list[Unit]:
    """Baseline: cut at rests and barlines, cap at `max_measures`.

    Kept deliberately. Run it beside the DP version on the same pieces --
    if the DP output is not visibly better by eye, ship this one.
    """
    if not slices:
        return []
    units: list[Unit] = []
    start = 0
    for i in range(1, len(slices) + 1):
        at_end = i == len(slices)
        if not at_end:
            s = slices[i]
            spans = s.measure - slices[start].measure + 1
            natural = s.after_rest or s.starts_measure
            if not (natural and spans > max_measures) and not (
                s.after_rest and spans >= 2
            ):
                continue
        j, k = start, i
        end_q = (
            slices[k].onset_q
            if k < len(slices)
            else slices[k - 1].onset_q + slices[k - 1].ioi_q
        )
        units.append(
            Unit(
                unit_id=f"n{len(units) + 1:02d}",
                start_slice=j,
                end_slice=k,
                start_q=slices[j].onset_q,
                end_q=end_q,
                first_measure=slices[j].measure,
                last_measure=slices[k - 1].measure,
                occurrences=1,
                score=0.0,
            )
        )
        start = i
    return units
