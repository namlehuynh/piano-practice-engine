"""Synthetic pop ballad: C-G-Am-F loop, broken-chord verse vs block-chord chorus.

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
from music21.pitch import Pitch

LOOP = ["C3", "G2", "A2", "F2"]          # the four-chord pop loop
TRIAD = {"C3": [0,4,7], "G2": [0,4,7], "A2": [0,3,7], "F2": [0,4,7]}
VERSE  = ["E4","G4","A4","G4","E4","D4","C4","D4","E4","G4","E4","D4","C4","D4","E4","C4"]
CHORUS = ["G5","A5","G5","E5","D5","E5","G5","A5","G5","F5","E5","D5","C5","D5","E5","C5"]

def lh_broken(root):
    b = Pitch(root).midi; t = TRIAD[root]
    seq = [t[0], t[1], t[2], t[1], t[0]+12, t[1], t[2], t[1]]
    return [(b+o, 0.5) for o in seq]

def lh_block(root):
    b = Pitch(root).midi; t = TRIAD[root]
    return [("chord", [b+o for o in t], 2.0), ("chord", [b+o for o in t], 2.0)]

rh, lh = stream.Part(), stream.Part()
for p in (rh, lh):
    p.append(meter.TimeSignature("4/4")); p.append(key.Key("C"))
rh.append(tempo.MetronomeMark(number=72))

# (name, bars, lh_style, melody)
PLAN = [("intro",4,"broken",None), ("verse1",8,"broken",VERSE),
        ("chorus1",8,"block",CHORUS), ("verse2",8,"broken",VERSE),
        ("chorus2",8,"block",CHORUS)]

bar = 0
for name, bars, style, mel in PLAN:
    for b in range(bars):
        root = LOOP[b % 4]
        ml, mr = stream.Measure(number=bar+1), stream.Measure(number=bar+1)
        if style == "broken":
            for midi, ql in lh_broken(root):
                n = note.Note(midi); n.quarterLength = ql; ml.append(n)
        else:
            for _, midis, ql in lh_block(root):
                c = chord.Chord(midis); c.quarterLength = ql; ml.append(c)
        if mel is None:
            mr.append(note.Rest(quarterLength=4.0))
        elif style == "broken":
            for k in range(2):
                n = note.Note(mel[(b*2+k) % len(mel)]); n.quarterLength = 2.0; mr.append(n)
        else:
            for k in range(4):
                n = note.Note(mel[(b*4+k) % len(mel)]); n.quarterLength = 1.0; mr.append(n)
        lh.append(ml); rh.append(mr); bar += 1

sc = stream.Score(); sc.insert(0, rh); sc.insert(0, lh)
sc.write("musicxml", fp="ballad_test.musicxml")
print(f"bars: {bar} | notes: {len(sc.flatten().notes)}")
