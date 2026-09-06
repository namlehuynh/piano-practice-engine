"""Key, tempo and meter — the things you read before touching the keys.

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

Both source formats carry key and tempo alongside the time signature.
Knowing a piece is in E minor turns F# from "an odd black key" into "a
note in the key", and gives the harmony pass a diatonic prior.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

MAJOR_BY_SHARPS = {
    0: "C", 1: "G", 2: "D", 3: "A", 4: "E", 5: "B", 6: "F#", 7: "C#",
    -1: "F", -2: "B-", -3: "E-", -4: "A-", -5: "D-", -6: "G-", -7: "C-",
}
PC_OF = {
    "C": 0, "C#": 1, "D": 2, "D#": 3, "E-": 3, "E": 4, "F": 5, "F#": 6,
    "G": 7, "G#": 8, "A-": 8, "A": 9, "A#": 10, "B-": 10, "B": 11,
    "C-": 11, "D-": 1, "G-": 6,
}
NAMES = ["C", "C#", "D", "E-", "E", "F", "F#", "G", "A-", "A", "B-", "B"]

MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)


def _read_musescore(path: str) -> dict:
    import xml.etree.ElementTree as ET
    import zipfile

    p = Path(path)
    if p.suffix.lower() == ".mscx":
        root = ET.parse(p).getroot()
    else:
        with zipfile.ZipFile(p) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".mscx")]
            with z.open(sorted(names, key=len)[0]) as f:
                root = ET.parse(f).getroot()
    score = root.find("Score")
    out: dict = {}
    if score is None:
        return out

    for el in score.iter("KeySig"):
        acc = el.findtext("accidental")
        if acc is not None:
            out["sharps"] = int(acc)
            break
    for el in score.iter("Tempo"):
        val = el.findtext("tempo")
        if val:
            # MuseScore stores quarter notes per second.
            out["bpm"] = round(float(val) * 60)
            break
    for el in score.iter("TimeSig"):
        n, d = el.findtext("sigN"), el.findtext("sigD")
        if n and d:
            out["time_signature"] = f"{n}/{d}"
            break
    return out


def _read_music21(source) -> dict:
    from music21 import converter, corpus, key, meter, stream, tempo

    if isinstance(source, stream.Stream):
        sc = source
    else:
        try:
            sc = converter.parse(str(source))
        except Exception:
            sc = corpus.parse(str(source))
    flat = sc.flatten()
    out: dict = {}
    ks = flat.getElementsByClass(key.KeySignature)
    if ks:
        out["sharps"] = int(ks[0].sharps)
    mm = flat.getElementsByClass(tempo.MetronomeMark)
    if mm and mm[0].number:
        out["bpm"] = round(float(mm[0].number))
    ts = flat.getElementsByClass(meter.TimeSignature)
    if ts:
        out["time_signature"] = ts[0].ratioString
    return out


def score_meta(source, events=None) -> dict:
    """Key, tempo and meter, plus the scale the key implies."""
    from .mscz import is_musescore

    raw: dict = {}
    try:
        if isinstance(source, str) and is_musescore(source):
            raw = _read_musescore(source)
        else:
            raw = _read_music21(source)
    except Exception:
        raw = {}

    sharps = raw.get("sharps")
    out = {
        "sharps": sharps,
        "bpm": raw.get("bpm"),
        "time_signature": raw.get("time_signature"),
        "key": None,
        "mode": None,
        "tonic_pc": None,
        "scale": None,
    }
    if sharps is None:
        return out

    major = MAJOR_BY_SHARPS.get(sharps)
    if major is None:
        return out
    major_pc = PC_OF[major]
    minor_pc = (major_pc + 9) % 12

    # A key signature does not say major or minor. Decide from where the
    # bass settles: the last bar's lowest note is the tonic far more often
    # than not.
    mode = "major"
    if events:
        lows = [e for e in events if e.hand == "L"] or list(events)
        if lows:
            last_bar = max(e.measure for e in lows)
            finals = [e.midi % 12 for e in lows if e.measure >= last_bar - 1]
            if finals:
                winner = Counter(finals).most_common(1)[0][0]
                if winner == minor_pc:
                    mode = "minor"
                elif winner != major_pc:
                    # Fall back to whichever tonic is commoner in the bass.
                    allbass = Counter(e.midi % 12 for e in lows)
                    if allbass[minor_pc] > allbass[major_pc]:
                        mode = "minor"

    tonic = minor_pc if mode == "minor" else major_pc
    scale = MINOR_SCALE if mode == "minor" else MAJOR_SCALE
    out.update(
        {
            "key": NAMES[tonic] + ("m" if mode == "minor" else ""),
            "mode": mode,
            "tonic_pc": tonic,
            "scale": frozenset((tonic + i) % 12 for i in scale),
        }
    )
    return out


def describe(meta: dict, t=None) -> str:
    """One plain line for a learner, in the report's language."""
    if t is None:
        from .i18n import Translator

        t = Translator()
    bits = []
    if meta.get("key"):
        mode = t("minor") if meta["mode"] == "minor" else t("major")
        bits.append(f"{t('key_of', key=meta['key'])} ({mode})")
    if meta.get("time_signature"):
        bits.append(t("meter", ts=meta["time_signature"]))
    if meta.get("bpm"):
        bits.append(t("tempo", bpm=meta["bpm"]))
    return ", ".join(bits)
