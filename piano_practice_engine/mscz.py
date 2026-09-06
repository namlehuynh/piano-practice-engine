"""Read MuseScore .mscz / .mscx directly.

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

music21 has no MuseScore reader, and .mscz is where most of the pop
repertoire beginners actually want lives. The format is simple enough to
read directly: a zip holding one .mscx, which is XML with one <Staff>
block per staff, each holding <Measure> elements of <Chord> and <Rest>.

Bonus worth having: many arrangements carry <Fingering> on notes. That
is the one piece of guidance a beginner needs most and the engine cannot
compute, so it is carried through when present.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .events import NoteEvent

# durationType -> quarter notes
DURATIONS = {
    "long": 16.0, "breve": 8.0, "whole": 4.0, "half": 2.0,
    "quarter": 1.0, "eighth": 0.5, "16th": 0.25, "32nd": 0.125,
    "64th": 0.0625, "128th": 0.03125,
}


def is_musescore(path: str) -> bool:
    return str(path).lower().endswith((".mscz", ".mscx"))


def _load_xml(path: str) -> ET.Element:
    p = Path(path)
    if p.suffix.lower() == ".mscx":
        return ET.parse(p).getroot()
    with zipfile.ZipFile(p) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".mscx")]
        if not names:
            raise ValueError(f"no .mscx inside {p.name}")
        # Prefer the shortest path: MuseScore puts the score at the root
        # and excerpts (parts) in subfolders.
        with z.open(sorted(names, key=len)[0]) as f:
            return ET.parse(f).getroot()


def _dotted(base: float, dots: int) -> float:
    total, add = base, base
    for _ in range(dots):
        add /= 2
        total += add
    return total


def _chord_duration(el: ET.Element, bar_q: float) -> float:
    dt = el.findtext("durationType", "quarter")
    if dt == "measure":
        frac = el.findtext("duration")
        if frac and "/" in frac:
            n, d = frac.split("/")
            return 4.0 * int(n) / int(d)
        return bar_q
    base = DURATIONS.get(dt, 1.0)
    return _dotted(base, int(el.findtext("dots", "0") or 0))


def _events_of_staff(staff: ET.Element, hand: str) -> list[NoteEvent]:
    out: list[NoteEvent] = []
    bar_q = 4.0
    bar_start = 0.0

    for index, measure in enumerate(staff.findall("Measure"), 1):
        # MuseScore only writes `number` when it differs from the running
        # count, so the attribute is absent in most files.
        number = int(measure.get("number") or index)

        ts = measure.find(".//TimeSig")
        if ts is not None:
            n = int(ts.findtext("sigN", "4") or 4)
            d = int(ts.findtext("sigD", "4") or 4)
            bar_q = 4.0 * n / d

        # Voices may be wrapped in <voice> or sit directly in <Measure>.
        voices = measure.findall("voice") or [measure]
        measure_len = 0.0

        for vi, voice in enumerate(voices, 1):
            cursor = 0.0
            for el in voice:
                if el.tag not in ("Chord", "Rest"):
                    continue
                dur = _chord_duration(el, bar_q)
                if el.tag == "Chord":
                    for note in el.findall("Note"):
                        pitch = note.findtext("pitch")
                        if pitch is None:
                            continue
                        tied = any(
                            s.get("type") == "Tie" for s in note.findall("endSpanner")
                        )
                        out.append(
                            NoteEvent(
                                onset_q=bar_start + cursor,
                                midi=int(pitch),
                                dur_q=dur,
                                hand=hand,
                                measure=number,
                                voice=vi,
                                tied_from_prev=tied,
                                finger=note.findtext("Fingering/text"),
                            )
                        )
                cursor += dur
            measure_len = max(measure_len, cursor)

        # Pickup and irregular bars are shorter than the time signature.
        bar_start += measure_len if measure_len > 0 else bar_q

    return out


def parse_musescore(path: str) -> list[NoteEvent]:
    root = _load_xml(path)
    score = root.find("Score")
    if score is None:
        raise ValueError("no <Score> element -- not a MuseScore file?")

    staves = score.findall("Staff")
    if not staves:
        raise ValueError("no <Staff> blocks found")

    events: list[NoteEvent] = []
    for i, staff in enumerate(staves):
        hand = "R" if i == 0 else "L"
        events.extend(_events_of_staff(staff, hand))

    events.sort(key=lambda e: (e.onset_q, e.midi))
    return events
