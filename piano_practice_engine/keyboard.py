"""Render a piano keyboard as SVG with keys marked and numbered.

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

For a beginner the keyboard IS the notation. They do not read intervals
or note names; they look for which keys to press and in what order. Every
analysis this engine produces has to land here or it does not land.
"""

from __future__ import annotations

from typing import Iterable, Mapping

WHITE_OF_PC = [0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6]
BLACK_PCS = {1, 3, 6, 8, 10}

W = 22.0  # white key width
BW = 13.0  # black key width
H = 58.0  # white key height
BH = 36.0  # black key height

FILLS = {
    "base": ("#F0997B", "#993C1D", "#FFFFFF"),
    "held": ("#F5C4B3", "#993C1D", "#993C1D"),
    "changed": ("#D85A30", "#4A1B0C", "#FFFFFF"),
    "known": ("#9FE1CB", "#0F6E56", "#04342C"),
}


def _white_index(midi: int) -> int:
    return 7 * (midi // 12) + WHITE_OF_PC[midi % 12]


def _is_black(midi: int) -> bool:
    return midi % 12 in BLACK_PCS


def _range(midis: Iterable[int], octaves: int = 2) -> tuple[int, int]:
    """A fixed two-octave window, snapped to C, centred on the marked keys.

    A window sized to the notes alone gets clipped just past the last key,
    so a figure that steps outside looks like it falls off the edge and
    there is no landmark to orient against.
    """
    lo, hi = min(midis), max(midis)
    # Two octaves is the default frame, but never at the cost of clipping:
    # widen a whole octave at a time until everything marked fits.
    while 12 * octaves <= hi - lo:
        octaves += 1
    span = 12 * octaves
    centre = (lo + hi) // 2
    start = ((centre - span // 2) // 12) * 12  # snap down to a C
    start = min(start, (lo // 12) * 12)
    while start + span - 1 < hi:
        start += 12
    return start, start + span - 1


def keyboard_svg(
    marks: Mapping[int, str],
    badges: Mapping[int, str] | None = None,
    pad_white: int = 1,
) -> str:
    """SVG for a keyboard spanning the marked keys plus a little context.

    `marks` maps midi -> one of base / held / changed / known.
    `badges` maps midi -> short label drawn on the key (press order).
    """
    if not marks:
        return ""
    badges = badges or {}
    lo, hi = _range(marks)
    w0 = _white_index(lo)
    n_white = _white_index(hi) - w0 + 1 + pad_white
    width = n_white * W

    parts = [
        f'<svg viewBox="0 0 {width:.0f} {H:.0f}" width="{width:.0f}" '
        f'height="{H:.0f}" role="img" aria-label="Sơ đồ phím đàn">'
    ]

    whites, blacks = [], []
    for midi in range(lo, hi + 1):
        state = marks.get(midi)
        if _is_black(midi):
            x = (_white_index(midi - 1) - w0 + 1) * W - BW / 2
            fill = FILLS[state][0] if state else "#2C2C2A"
            blacks.append(
                f'<rect x="{x:.1f}" y="0" width="{BW}" height="{BH}" rx="2" '
                f'fill="{fill}"/>'
            )
            if midi in badges:
                col = FILLS[state][2] if state else "#FFFFFF"
                blacks.append(
                    f'<circle cx="{x + BW / 2:.1f}" cy="{BH - 11:.1f}" r="7.5" '
                    f'fill="{"#FFFFFF" if state else "#5F5E5A"}"/>'
                    f'<text x="{x + BW / 2:.1f}" y="{BH - 11:.1f}" '
                    f'text-anchor="middle" dominant-baseline="central" '
                    f'font-size="11" fill="{FILLS[state][1] if state else col}">'
                    f"{badges[midi]}</text>"
                )
        else:
            x = (_white_index(midi) - w0) * W
            fill, stroke = ("#FFFFFF", "#B4B2A9")
            if state:
                fill, stroke = FILLS[state][0], FILLS[state][1]
            whites.append(
                f'<rect x="{x:.1f}" y="0" width="{W}" height="{H}" rx="2" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="0.5"/>'
            )
            if midi in badges:
                whites.append(
                    f'<circle cx="{x + W / 2:.1f}" cy="{H - 14:.1f}" r="7.5" '
                    f'fill="{FILLS[state][1] if state else "#5F5E5A"}"/>'
                    f'<text x="{x + W / 2:.1f}" y="{H - 14:.1f}" '
                    f'text-anchor="middle" dominant-baseline="central" '
                    f'font-size="11" fill="#FFFFFF">{badges[midi]}</text>'
                )

    parts.extend(whites)
    parts.extend(blacks)
    parts.append("</svg>")
    return "".join(parts)


def press_order(midis: list[int]) -> dict[int, str]:
    """Badge each distinct key with the order it is first played."""
    order: dict[int, str] = {}
    n = 0
    for m in midis:
        if m not in order:
            n += 1
            order[m] = str(n)
    return order


def diff_marks(current: list[int], previous: list[int] | None) -> dict[int, str]:
    """Mark keys held from the previous position vs newly moved to.

    The point a beginner needs is not what the new position is, but how
    little of it is new. Three of Amelie's four left-hand positions
    differ from their predecessor by a single key.
    """
    if previous is None:
        return {m: "base" for m in set(current)}
    prev = set(previous)
    return {m: ("held" if m in prev else "changed") for m in set(current)}


def roll_svg(notes, width: float = 300.0, height: float = 84.0) -> str:
    """A pitch-against-time strip of the actual bar, above the keyboard.

    The keyboard says which keys; this says when, and how many at once.
    Neither alone is enough: a bar of dyads and a bar of single notes mark
    the same keys, and only the strip shows they are different to play.
    """
    if not notes:
        return ""
    t0 = min(n.onset_q for n in notes)
    t1 = max(n.onset_q + n.dur_q for n in notes)
    lo, hi = _range([n.midi for n in notes])
    span_t = max(t1 - t0, 1e-6)
    span_p = max(hi - lo, 1)
    rh = max(height / (span_p + 1), 3.0)

    parts = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" '
        f'height="{height:.0f}" role="img" aria-label="Trích đoạn bản nhạc">'
    ]
    # Beat lines, so the eye can count.
    beats = int(span_t) + 1
    for b in range(beats + 1):
        x = width * b / span_t if span_t else 0
        if x <= width:
            parts.append(
                f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{height}" '
                f'stroke="#D3D1C7" stroke-width="0.5"/>'
            )
    for n in notes:
        x = width * (n.onset_q - t0) / span_t
        w = max(width * n.dur_q / span_t - 1.5, 2.5)
        y = height - (n.midi - lo + 1) * (height / (span_p + 1))
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{rh - 1:.1f}" '
            f'rx="1.5" fill="#D85A30"/>'
        )
    parts.append("</svg>")
    return "".join(parts)
