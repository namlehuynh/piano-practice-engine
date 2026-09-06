"""Synthetic stand-in for minimalist/pop piano: LH ostinato + RH melody, AA'BA form.

Piano Practice Engine — created and developed by Nam Le Huynh.
Copyright (C) 2026 Nam Le Huynh

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version. It is distributed WITHOUT ANY WARRANTY; see
the GNU General Public License for more details. You should have
received a copy of the licence with this program; if not, see
<https://www.gnu.org/licenses/>.
"""
from music21 import stream, note, chord, meter, key, tempo

LOOP = [("E3", [0,7,12,16,12,7,12,7]), ("C3", [0,7,12,16,12,7,12,7]),
        ("G2", [0,7,12,16,12,7,12,7]), ("D3", [0,7,12,16,12,7,12,7])]
M1 = ["E5","G5","B5","A5","G5","E5","D5","E5", "G5","A5","B5","A5","G5","E5","B4","E5"]
M2 = ["B5","A5","G5","F#5","E5","F#5","G5","A5", "B5","C6","B5","A5","G5","F#5","E5","D5"]

def lh_bar(root, offsets):
    from music21.pitch import Pitch
    base = Pitch(root).midi
    out = []
    for k, off in enumerate(offsets):
        n = note.Note(base + off); n.quarterLength = 0.5
        out.append(n)
    return out

rh, lh = stream.Part(), stream.Part()
rh.append(meter.TimeSignature("4/4")); rh.append(key.Key("e")); rh.append(tempo.MetronomeMark(number=80))
lh.append(meter.TimeSignature("4/4")); lh.append(key.Key("e"))

plan = [("intro", None), ("A", M1), ("Ap", M1), ("B", M2), ("A2", M1)]
for name, mel in plan:
    bars = 4 if name == "intro" else 8
    for b in range(bars):
        root, offs = LOOP[b % 4]
        m = stream.Measure()
        for n in lh_bar(root, offs): m.append(n)
        lh.append(m)
        mr = stream.Measure()
        if mel is None:
            mr.append(note.Rest(quarterLength=4.0))
        else:
            for k in range(2):
                p = mel[(b * 2 + k) % len(mel)]
                n = note.Note(p); n.quarterLength = 2.0
                mr.append(n)
        rh.append(mr)

sc = stream.Score(); sc.insert(0, rh); sc.insert(0, lh)
sc.write("musicxml", fp="ostinato_test.musicxml")
print("bars:", len(lh.getElementsByClass('Measure')), "| notes:", len(sc.flatten().notes))
