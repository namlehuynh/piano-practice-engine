"""Run the engine on a MusicXML file or a music21 corpus name.
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
import argparse, json, sys
from piano_practice_engine import analyse, parse_score
from piano_practice_engine.metadata import describe, score_meta
from piano_practice_engine.patterns import summarise
from piano_practice_engine.html_report import build_html, load_known, save_known
from piano_practice_engine.report import build_report
from piano_practice_engine.segment import Weights

def main() -> int:
    ap = argparse.ArgumentParser(description="Piano practice-unit engine")
    ap.add_argument("source", help="path to .musicxml/.mxl, or a music21 corpus name")
    ap.add_argument("--out", help="write JSON here (default: stdout summary only)")
    ap.add_argument("--naive", action="store_true", help="use the rest/barline baseline")
    ap.add_argument("--max-measures", type=int, default=4)
    ap.add_argument("--hand-aware", action="store_true",
                    help="score cuts on per-hand repetition too (see README)")
    ap.add_argument("--html", metavar="FILE.html",
                    help="write the learner-facing HTML report with keyboards")
    ap.add_argument("--lang", choices=["vi", "en", "bi"], default=None,
                    help="report language: vi, en, or bi for bilingual "
                         "(default: shell locale, then vi)")
    ap.add_argument("--known", metavar="PROGRESS.json",
                    help="chord vocabulary carried across pieces; updated in place")
    ap.add_argument("--report", metavar="FILE.md",
                    help="write a human-readable markdown report for validation")
    ap.add_argument("--tier", default=None,
                    choices=["exact", "interval", "contour", "rhythm"],
                    help="match tier for one-bar hand patterns "
                         "(default: exact for the left hand, melody for the right)")
    args = ap.parse_args()

    w = Weights(max_measures=args.max_measures, hand_aware=args.hand_aware)
    result = analyse(args.source, weights=w, naive=args.naive)

    m, c = result["meta"], result["coverage"]
    print(f"{result['score_id']}  [{m['segmenter']}]")
    print(f"  {m['notes']} notes, {m['slices']} slices, {m['measures']} measures")
    print(f"  {c['units']} units -> {c['distinct_groups']} distinct "
          f"({c['reduction']:.0%} less to learn)")
    print("\n  practice queue (top 8):")
    for i, q in enumerate(result["practice_queue"][:8], 1):
        why = ", ".join(q["why"]) or "-"
        print(f"    {i}. {q['unit_id']}  diff {q['difficulty']:.1f}  "
              f"unlocks {q['unlocks']}x  ({why})")

    events = parse_score(args.source)
    meta = score_meta(args.source, events)
    if describe(meta):
        print(f"\n  {describe(meta)}")
    vocab = summarise(events, args.tier)
    for hand in ("L", "R"):
        if hand not in vocab:
            continue
        v = vocab[hand]
        label = "tay trái" if hand == "L" else "tay phải"
        line = (f"\n  {label}: {v['n_patterns']} kiểu / {v['n_bars']} ô nhịp"
                f"  [{v['tier']}]")
        if v["cycle"]:
            c = v["cycle"]
            line += (f"  | chu kỳ {c['period']} ô: "
                     f"{' -> '.join(c['order'])} ({c['agreement']:.0%})")
        print(line)
        for p in v["patterns"][:4]:
            print(f"      {p.pattern_id}  {p.count:2d}x  {' '.join(p.notes)}")

    if args.html:
        known = load_known(args.known)
        doc, new_chords = build_html(result, events, known,
                                     score_meta(args.source, events),
                                     lang=args.lang)
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(doc)
        print(f"\n  wrote {args.html}")
        if new_chords:
            print(f"  hợp âm mới: {', '.join(new_chords)}")
        if args.known:
            save_known(args.known, known | set(new_chords))
            print(f"  vốn hợp âm: {len(known | set(new_chords))} (đã lưu)")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(build_report(result, events, args.tier, args.lang))
        print(f"\n  wrote {args.report}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n  wrote {args.out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
