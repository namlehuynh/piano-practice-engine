"""MusicXML -> flat event stream -> simultaneity slices.


This is the only module that knows about music21. Everything downstream
works on plain dataclasses, so swapping the parser (or feeding events
straight from an OMR engine) touches nothing else.

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

from dataclasses import dataclass
from typing import Iterable, Sequence

# Onsets are quantised to this grid before grouping into slices.
# 1/12 of a quarter note handles triplets and 32nd notes without
# float comparison pain.
GRID = 48


def _q(x: float) -> int:
    """Quantise a quarter-note position to the integer grid."""
    return int(round(float(x) * GRID))


@dataclass(frozen=True)
class NoteEvent:
    """One sounding note."""

    onset_q: float
    midi: int
    dur_q: float
    hand: str  # 'R' or 'L'
    measure: int
    voice: int = 1
    tied_from_prev: bool = False
    finger: str | None = None  # from the arrangement, when it carries one

    @property
    def end_q(self) -> float:
        return self.onset_q + self.dur_q


@dataclass(frozen=True)
class Slice:
    """All notes starting at the same instant, plus local context.

    A slice is the unit the segmenter reasons about. Working in slices
    rather than notes means a four-note chord is one step, not four.
    """

    index: int
    onset_q: float
    measure: int
    midis: tuple[int, ...]  # sorted low -> high, all hands
    right: tuple[int, ...]
    left: tuple[int, ...]
    ioi_q: float  # distance to the next slice
    after_rest: bool  # full-texture silence immediately before
    starts_measure: bool

    @property
    def bass(self) -> int:
        return self.midis[0]


def parse_score(source) -> list[NoteEvent]:
    """Parse MusicXML/MXL/KRN, MuseScore .mscz/.mscx, a corpus name, or a Stream."""
    from music21 import converter, corpus, stream

    from .mscz import is_musescore, parse_musescore

    if isinstance(source, str) and is_musescore(source):
        return parse_musescore(source)

    if isinstance(source, stream.Stream):
        score = source
    else:
        src = str(source)
        try:
            score = converter.parse(src)
        except Exception:
            score = corpus.parse(src)

    parts = list(score.parts) if hasattr(score, "parts") else []
    if not parts:
        parts = [score]

    events: list[NoteEvent] = []
    if len(parts) >= 2:
        # Grand staff: first part is the upper staff.
        assignments = [(parts[0], "R")] + [(p, "L") for p in parts[1:]]
        for part, hand in assignments:
            events.extend(_events_from_part(part, hand))
    else:
        # Single part: split at middle C as a fallback.
        raw = _events_from_part(parts[0], "R")
        events = [
            NoteEvent(
                e.onset_q,
                e.midi,
                e.dur_q,
                "R" if e.midi >= 60 else "L",
                e.measure,
                e.voice,
                e.tied_from_prev,
            )
            for e in raw
        ]

    events = _repair_measures(events, score)
    events.sort(key=lambda e: (e.onset_q, e.midi))
    return events


def _repair_measures(events: list[NoteEvent], score) -> list[NoteEvent]:
    """Derive bar numbers from onsets when the source has none.

    Hand-built streams and real OMR output both produce scores where
    measureNumber is missing or constant. The segmenter's length window
    is expressed in bars, so without this the whole piece collapses into
    a single unit.
    """
    if len({e.measure for e in events}) > 1:
        return events

    bar_q = 4.0
    try:
        from music21 import meter

        ts = score.flatten().getElementsByClass(meter.TimeSignature)
        if ts:
            bar_q = float(ts[0].barDuration.quarterLength)
    except Exception:
        pass

    from dataclasses import replace

    return [
        replace(e, measure=int(e.onset_q // bar_q) + 1) for e in events
    ]


def _events_from_part(part, hand: str) -> list[NoteEvent]:
    out: list[NoteEvent] = []
    flat = part.flatten()
    for el in flat.notes:
        tied = bool(getattr(el, "tie", None)) and el.tie.type in ("stop", "continue")
        measure = el.measureNumber or 0
        voice = 1
        onset = float(el.offset)
        dur = float(el.quarterLength)
        if dur <= 0:
            continue  # grace notes carry no duration; skip for now
        pitches = el.pitches if el.isChord else [el.pitch]
        for p in pitches:
            out.append(
                NoteEvent(onset, int(p.midi), dur, hand, measure, voice, tied)
            )
    return out


def build_slices(events: Sequence[NoteEvent]) -> list[Slice]:
    """Group events into simultaneities and annotate rests / barlines."""
    if not events:
        return []

    buckets: dict[int, list[NoteEvent]] = {}
    for e in events:
        buckets.setdefault(_q(e.onset_q), []).append(e)

    keys = sorted(buckets)
    slices: list[Slice] = []
    sounding_until = float("-inf")  # latest end of anything heard so far

    for i, key in enumerate(keys):
        group = buckets[key]
        onset = key / GRID
        nxt = keys[i + 1] / GRID if i + 1 < len(keys) else None
        ioi = (nxt - onset) if nxt is not None else max(e.dur_q for e in group)

        after_rest = i > 0 and (onset - sounding_until) > 1e-6
        measure = min(e.measure for e in group)
        prev_measure = slices[-1].measure if slices else None
        starts_measure = prev_measure is not None and measure != prev_measure

        midis = tuple(sorted(e.midi for e in group))
        slices.append(
            Slice(
                index=i,
                onset_q=onset,
                measure=measure,
                midis=midis,
                right=tuple(sorted(e.midi for e in group if e.hand == "R")),
                left=tuple(sorted(e.midi for e in group if e.hand == "L")),
                ioi_q=ioi,
                after_rest=after_rest,
                starts_measure=starts_measure,
            )
        )
        sounding_until = max(sounding_until, max(e.end_q for e in group))

    return slices


def events_in_span(
    events: Iterable[NoteEvent], start_q: float, end_q: float
) -> list[NoteEvent]:
    return [e for e in events if start_q - 1e-6 <= e.onset_q < end_q - 1e-6]
