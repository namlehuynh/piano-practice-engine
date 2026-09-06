"""Repetition detection over slice signatures.


Computed on the raw slice stream, independent of any segmentation --
that is what breaks the chicken-and-egg between "where to cut" and
"what repeats".

The signature is transposition-invariant by construction: every pitch is
expressed relative to the bass of the n-gram's first slice, so the same
figure in C and in G hashes identically.

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

from collections import defaultdict
from typing import Sequence

from .events import Slice

IOI_GRID = 12  # quantise inter-onset intervals to 1/12 quarter note


def _ioi_token(ioi_q: float) -> int:
    return int(round(ioi_q * IOI_GRID))


def signature(slices: Sequence[Slice], start: int, length: int) -> tuple:
    """Transposition-invariant signature of slices[start:start+length]."""
    origin = slices[start].bass
    out = []
    for k in range(start, start + length):
        s = slices[k]
        out.append(
            (
                s.bass - origin,  # bass motion relative to the span's start
                tuple(m - s.bass for m in s.midis),  # chord shape
                _ioi_token(s.ioi_q),
            )
        )
    return tuple(out)


def absolute_key(slices: Sequence[Slice], start: int, length: int) -> tuple:
    """Signature plus starting pitch -- distinguishes literal from transposed."""
    return (slices[start].bass, signature(slices, start, length))


class RepetitionIndex:
    """Maps every n-gram signature to the positions where it occurs.

    `sig_fn` selects the view: merged texture by default, or one hand.
    """

    def __init__(
        self,
        slices: Sequence[Slice],
        min_n: int = 4,
        max_n: int = 48,
        sig_fn=None,
    ) -> None:
        self.slices = slices
        self.min_n = min_n
        self.max_n = min(max_n, len(slices))
        self._sig = sig_fn or signature
        self._index: dict[tuple, list[int]] = defaultdict(list)
        for n in range(self.min_n, self.max_n + 1):
            for p in range(0, len(slices) - n + 1):
                key = self._sig(slices, p, n)
                if key is not None:
                    self._index[key].append(p)

    def positions(self, start: int, length: int) -> list[int]:
        if length < self.min_n or length > self.max_n:
            return [start]
        key = self._sig(self.slices, start, length)
        if key is None:
            return [start]
        return self._index.get(key, [start])

    def occurrences(self, start: int, length: int) -> int:
        """Non-overlapping occurrence count.

        Overlapping matches are discarded greedily: an ostinato that
        shifts by one slice would otherwise report a huge, meaningless
        count and swamp the segmentation objective.
        """
        positions = self.positions(start, length)
        if len(positions) <= 1:
            return 1
        count, last_end = 0, float("-inf")
        for p in sorted(positions):
            if p >= last_end:
                count += 1
                last_end = p + length
        return max(count, 1)


def levenshtein(a: Sequence, b: Sequence, cap: int) -> int:
    """Edit distance, abandoned early once it exceeds `cap`."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, y in enumerate(b, 1):
            cur[j] = min(
                prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (0 if x == y else 1)
            )
        if min(cur) > cap:
            return cap + 1
        prev = cur
    return prev[-1]


def signature_tiers(slices: Sequence[Slice], start: int, length: int) -> dict:
    """Progressively coarser views of the same span.

    Exact repetition is rarer in real repertoire than it looks. What a
    beginner actually transfers between passages is hand shape and
    rhythm, not literal pitch -- so matching at these coarser tiers finds
    far more usable familiarity. Measured on the WTC C major prelude:
    45% of units have an exact twin, 77% share a contour, 86% share a
    rhythm.

    Only `full` means "learn once, get the others free". The coarser
    tiers mean "this will feel familiar", which is a different and
    weaker promise -- keep them in separate fields.
    """
    full = signature(slices, start, length)
    return {
        "full": full,
        "shape": tuple((x[1], x[2]) for x in full),
        "contour": tuple(((x[0] > 0) - (x[0] < 0), x[2]) for x in full),
        "rhythm": tuple(x[2] for x in full),
    }


def hand_signature(
    slices: Sequence[Slice], start: int, length: int, hand: str
) -> tuple | None:
    """Signature of one hand only, ignoring what the other hand does.

    Beginners practise hands separately, so this is the match that
    actually transfers. It also catches the commonest structure in
    beginner repertoire -- an unchanged left-hand ostinato under a new
    right-hand melody -- which merged-texture matching misses entirely.
    """
    cols = []
    for k in range(start, start + length):
        s = slices[k]
        c = s.right if hand == "R" else s.left
        if c:
            cols.append((c[0], tuple(m - c[0] for m in c), _ioi_token(s.ioi_q)))
    if not cols:
        return None
    origin = cols[0][0]
    return tuple((c[0] - origin, c[1], c[2]) for c in cols)


class HandAwareIndex:
    """Repetition seen three ways: merged texture, left hand, right hand.

    Necessary, not a refinement. Measured on a real Amelie transcription:
    the merged texture's longest repeat is 29 slices occurring twice,
    while the left hand alone repeats 64 slices three times and the right
    hand six times. Scoring cuts on the merged view alone found zero
    reusable material in a piece built entirely on an ostinato.

    Since a beginner practises hands separately, a cut that makes the
    left hand repeat is worth taking even when the right hand differs.
    """

    def __init__(
        self, slices: Sequence[Slice], min_n: int = 4, max_n: int = 48
    ) -> None:
        self.merged = RepetitionIndex(slices, min_n, max_n)
        self.left = RepetitionIndex(
            slices, min_n, max_n, lambda sl, p, n: hand_signature(sl, p, n, "L")
        )
        self.right = RepetitionIndex(
            slices, min_n, max_n, lambda sl, p, n: hand_signature(sl, p, n, "R")
        )

    def occurrences(self, start: int, length: int) -> int:
        return max(
            self.merged.occurrences(start, length),
            self.left.occurrences(start, length),
            self.right.occurrences(start, length),
        )

    def breakdown(self, start: int, length: int) -> dict[str, int]:
        return {
            "merged": self.merged.occurrences(start, length),
            "L": self.left.occurrences(start, length),
            "R": self.right.occurrences(start, length),
        }
