"""End-to-end: source file in, practice plan JSON out.

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

from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .difficulty import score_unit, techniques
from .events import NoteEvent, Slice, build_slices, events_in_span, parse_score
from .repetition import (
    RepetitionIndex,
    HandAwareIndex,
    absolute_key,
    levenshtein,
    signature,
    signature_tiers,
    hand_signature,
)
from .segment import Unit, Weights, segment, segment_naive

VARIANT_EDIT_CAP = 2


def group_units(slices: Sequence[Slice], units: list[Unit]) -> list[dict]:
    """Cluster units into identical / transposed / variant families."""
    sigs = {
        u.unit_id: signature(slices, u.start_slice, u.n_slices) for u in units
    }
    abskeys = {
        u.unit_id: absolute_key(slices, u.start_slice, u.n_slices) for u in units
    }

    groups: list[dict] = []
    assigned: dict[str, str] = {}

    for u in units:
        if u.unit_id in assigned:
            continue
        gid = f"g{len(groups) + 1:02d}"
        members = [{"unit_id": u.unit_id, "kind": "root"}]
        assigned[u.unit_id] = gid

        for v in units:
            if v.unit_id in assigned:
                continue
            if sigs[v.unit_id] == sigs[u.unit_id]:
                kind = (
                    "identical"
                    if abskeys[v.unit_id] == abskeys[u.unit_id]
                    else "transposed"
                )
            elif (
                levenshtein(sigs[v.unit_id], sigs[u.unit_id], VARIANT_EDIT_CAP)
                <= VARIANT_EDIT_CAP
            ):
                kind = "variant"
            else:
                continue
            members.append({"unit_id": v.unit_id, "kind": kind})
            assigned[v.unit_id] = gid

        groups.append({"group_id": gid, "members": members, "size": len(members)})

    for g in groups:
        for m in g["members"]:
            for u in units:
                if u.unit_id == m["unit_id"]:
                    u.group_id = g["group_id"]
                    u.match_kind = m["kind"]
    return groups


def attach_related(slices: Sequence[Slice], units: list[Unit]) -> None:
    """Tag units that merely *feel* familiar, at each coarseness tier."""
    tiers = {
        u.unit_id: signature_tiers(slices, u.start_slice, u.n_slices)
        for u in units
    }
    for u in units:
        related: dict[str, list[str]] = {}
        for tier in ("shape", "contour", "rhythm"):
            same = [
                v.unit_id
                for v in units
                if v.unit_id != u.unit_id
                and tiers[v.unit_id][tier] == tiers[u.unit_id][tier]
            ]
            if same:
                related[tier] = same
        u.related = related

    # Per-hand matching, reported separately: "your left hand already
    # knows this bar, only the right hand is new" is the single most
    # useful thing to tell a beginner.
    for hand in ("L", "R"):
        sigs = {
            u.unit_id: hand_signature(slices, u.start_slice, u.n_slices, hand)
            for u in units
        }
        for u in units:
            if sigs[u.unit_id] is None:
                continue
            same = [
                v.unit_id
                for v in units
                if v.unit_id != u.unit_id and sigs[v.unit_id] == sigs[u.unit_id]
            ]
            if same:
                u.hand_match[hand] = same


def analyse(
    source,
    weights: Weights | None = None,
    naive: bool = False,
) -> dict:
    events = parse_score(source)
    slices = build_slices(events)
    if not slices:
        raise ValueError("no notes found in score")

    w = weights or Weights()
    index = (
        HandAwareIndex(slices, max_n=w.max_slices)
        if w.hand_aware
        else RepetitionIndex(slices, max_n=w.max_slices)
    )
    units = segment_naive(slices) if naive else segment(slices, index, w)

    for u in units:
        us = slices[u.start_slice : u.end_slice]
        ue = events_in_span(events, u.start_q, u.end_q)
        u.difficulty = score_unit(us, ue)
        u.techniques = techniques(us)

    groups = group_units(slices, units)
    attach_related(slices, units)

    # Priority = how hard x how much of the piece it unlocks.
    sizes = {g["group_id"]: g["size"] for g in groups}
    order = sorted(
        units,
        key=lambda u: -(u.difficulty["score"] * sizes.get(u.group_id, 1)),
    )
    seen: set[str] = set()
    queue = []
    for u in order:
        if u.group_id in seen:
            continue
        seen.add(u.group_id)
        queue.append(
            {
                "unit_id": u.unit_id,
                "group_id": u.group_id,
                "unlocks": sizes.get(u.group_id, 1),
                "difficulty": u.difficulty["score"],
                "why": u.difficulty["why"],
            }
        )

    return {
        "score_id": Path(str(source)).stem,
        "meta": {
            "notes": len(events),
            "slices": len(slices),
            "measures": slices[-1].measure - slices[0].measure + 1,
            "segmenter": "naive" if naive else "dp",
        },
        "coverage": {
            "units": len(units),
            "distinct_groups": len(groups),
            "reduction": round(1 - len(groups) / max(len(units), 1), 3),
        },
        "units": [asdict(u) for u in units],
        "groups": groups,
        "practice_queue": queue,
    }
