# Piano Practice Engine

Turn a piano score into a practice plan: what actually repeats, what has to be
learned, which passages are hard and why.

Reads MusicXML, MuseScore (`.mscz`/`.mscx`), Humdrum `**kern` and MIDI. Outputs
a self-contained HTML report with keyboard diagrams, or structured JSON.

Copyright (C) 2026 Nam Le Huynh. Released under **GPL-3.0-or-later** — see
[`LICENSE`](LICENSE).

## Why

Beginner piano method is well established — chunk the piece, separate the
hands, drill the hard spots, reassemble with overlap. Doing it well means
reading a score analytically, which is exactly the skill a beginner does not
yet have. This engine does that reading for them.

The core observation is that far less of a piece is new than it looks. A film
theme may run 109 bars on five left-hand figures. Finding that automatically,
and saying it in terms of keys and fingers rather than intervals and pitch
classes, is the whole job.

## Install

```bash
pip install -r requirements.txt
```

Requires Python 3.10+ and [`music21`](https://www.music21.org/).

## Usage

```bash
python cli.py score.mscz --html plan.html          # learner-facing report
python cli.py score.musicxml --out plan.json       # structured output
python cli.py score.mid --html plan.html --lang en # English report
python cli.py bach/bwv846 --html plan.html         # music21 corpus name

python cli.py score.mscz --html a.html --known progress.json  # chord vocabulary
python cli.py score.mscz --report notes.md --lang bi  # bilingual verification report
python cli.py score.mscz --naive                   # baseline segmenter
python verify.py                                   # smoke test
```

| Flag | Effect |
|---|---|
| `--html FILE` | Self-contained HTML practice report |
| `--out FILE` | Full analysis as JSON |
| `--report FILE` | Markdown report for checking the analysis against a printed score |
| `--lang vi\|en\|bi` | Report language; `bi` renders both. Defaults to shell locale, then Vietnamese |
| `--known FILE` | Chord vocabulary carried across pieces, updated in place |
| `--tier` | Override the bar-matching tier (`exact`, `melody`, `gesture`, …) |
| `--hand-aware` | Score cuts on per-hand repetition (experimental) |
| `--naive` | Rest/barline baseline segmenter, for comparison |
| `--max-measures N` | Practice unit length ceiling |

## What it produces

**Per-hand pattern vocabulary.** The distinct one-bar figures each hand plays,
with the bars each covers. A left hand of five figures across 109 bars is five
cards, not 109.

**Form map.** An A–B–A section map, computed per hand. The hands are analysed
separately because merging them hides the most useful fact about many pieces:
a fixed accompaniment under a melody that develops reads as 81% new material
when merged, and correctly as 7% and 62% when kept apart.

**Chord tones and colour notes.** Which notes in a figure belong to the
prevailing chord and which can be left out at first, determined from both hands
at half-bar resolution — many arrangements never state a third in the left hand,
so the chord quality lives in the right.

**Micro-exercises**, generated from the analysis: position-transition drills,
block-chord reductions of broken figures, rhythm variations for even runs,
overlapping chunk pairs, and a tempo ladder from the marked tempo.

**Difficulty ranking** on five interpretable descriptors — note density, pitch
range, hand span, position shifts, hand independence — reported as reasons
rather than a bare score.

**Chord vocabulary that accumulates.** Pass `--known` and each new piece reports
how few of its chords are actually new.

## How it works

### Segmentation

Practice units are chosen by dynamic programming over the slice stream. The
objective is repetition: a good cut is one that makes the resulting span recur
elsewhere, because that is exactly its value to a learner.

```
best[i] = max over j of ( best[j] + score(j, i) )

score(j, i) = w_rep   * n * (occ - 1) / occ      # repetition gain
            + w_bound * (left edge + right edge) # rests, barlines
            - w_len   * (deviation from 2..4 bars) ^ 1.5
```

There is no `k`: the number and size of units falls out of the optimum. Two
details are load-bearing — dividing by `occ`, without which a four-slice figure
recurring twenty times outscores a real two-bar phrase, and a hard 2–4 bar
window, since the soft penalty alone loses to the boundary bonus.

### Bar matching

Bars are clustered by pairwise comparison with a tolerance proportional to bar
length, not by hashing. One note different in a bar of four is a different bar;
one note different in a bar of sixteen is the same bar with an ornament.

Each hand matches at its own tier, because they are different kinds of thing:

| Hand | Tier | Rationale |
|---|---|---|
| Left | `exact` | An accompaniment figure is defined by the keys under the hand |
| Right | `gesture` | A melody is defined by the motion — direction and thickness per onset, pitch discarded |

Two further relations that pitch-based matching cannot see:

- **Same notes, different articulation.** Bars holding the same pitches over the
  same beats but splitting them across onsets differently. Invisible at 1/12
  resolution, identical at beat resolution — so clustering checks both.
- **Same gesture, different chord.** A triad rolled upward through its
  inversions is one motion whether it is built on E minor or B minor. Every
  interval-based tier misses this; the `gesture` tier is what catches it.

### Loops and sections

`find_loops()` looks for blocks recurring anywhere rather than one period
holding everywhere. Global period detection works only for pieces that loop
end to end; a pop ballad may run its four-bar loop at bars 1–4, again at 5–8,
leave for twelve bars and return at 21–24, which averages out to noise.

Blocks are aligned to the meter — candidates start at bars 1, 5, 9 … A phrase
starts on a phrase line, and sliding windows find units straddling boundaries
that no player perceives as units.

## Modules

| File | Responsibility |
|---|---|
| `events.py` | Source → note events → simultaneity slices |
| `mscz.py` | MuseScore reader, including fingering when the arrangement carries it |
| `metadata.py` | Key, tempo, meter, and the scale the key implies |
| `patterns.py` | Bar signatures at six tiers, cycle detection, shared openings |
| `analysis.py` | Bar clustering, chord-tone labelling, meter-aligned phrase blocks |
| `repetition.py` | Transposition-invariant n-gram index |
| `segment.py` | DP segmenter plus a rest/barline baseline |
| `difficulty.py` | Five interpretable descriptors and technique tagging |
| `structure.py` | Per-hand A–B–A form analysis |
| `exercises.py` | Transition drills, block chords, rhythm variants, overlaps |
| `chords.py` | Chord naming, restricted to confident triads |
| `keyboard.py` | Keyboard and piano-roll SVG |
| `html_report.py` | Learner-facing HTML, layout chosen from the data |
| `report.py` | Markdown verification report, in either language or both |
| `i18n.py` | Vietnamese and English strings, plus a bilingual mode |

`music21` is used only in `events.py` and `metadata.py`; everything downstream
works on plain dataclasses.

## Measured results

Share of each piece that genuinely has to be learned, lower is better:

| Piece | DP | Baseline |
|---|---|---|
| C. Schumann, Polonaise op. 1/1 | 63% | 72% |
| Bach, WTC Prelude 1 | 72% | 100% |
| Chopin, Mazurka 6-2 | 79% | **72%** |
| Joplin, Maple Leaf Rag | 80% | 89% |

The DP segmenter wins on three of four; the margin is narrow enough that
`--naive` is kept for comparison on new repertoire.

Difficulty ranks pieces in the right order without calibration — a synthetic
ballad at 3.2, Bach's Prelude at 4.3, Maple Leaf Rag at 7.0 — and separates
verse from chorus within a piece, tagging them `arpeggio_L` and
`block_chords_L` respectively.

## Known limitations

- **Chord naming caps out around 60% on ballads.** Where the left hand plays
  only root and fifth, the chord quality lives in the right hand, which also
  carries non-chord tones occupying more than 40% of the weight. Duration
  weighting, strong-beat weighting and a diatonic prior each failed to move it.
  Names are only shown when confident; a wrong chord name is worse than none.
- **Difficulty is not calibrated** against CIPI or the Henle scale. It is
  reliable for ordering units within one piece, not for comparing pieces.
- **Weights are set by hand**, deliberately. The only ground truth worth
  optimising against is boundaries that real users move, which requires users.
- **"Hard" and "climax" are conflated.** Neither note density nor the five
  descriptors identify the emotional peak of a piece; peak register combined
  with texture thickness does, and is not yet wired in.
- Voice separation is per staff, not per voice within a staff.
- Grace notes (`quarterLength == 0`) are skipped.
- Cross-staff notes are assigned to a hand by staff, not by the hand that plays
  them.
- `_repair_measures()` derives bar numbers from onsets when the source omits
  them — necessary for OMR output, wrong for pieces that change time signature
  mid-piece.
- **No audio.** A beginner verifies by ear, and no amount of analysis
  substitutes for hearing the passage.

## Deliberately out of scope

Fingering generation, cross-piece motif retrieval, LBDM boundary detection,
Henle-scale calibration, and any training. All of them wait on data from real
users correcting real boundaries.

## Contributing

The project needs a Contributor Licence Agreement before accepting its first
pull request. Issues and discussion are welcome meanwhile — reports of a card
whose notes do not match the printed score are the single most useful kind.

## Author

Created and developed by **Nam Le Huynh**. See [`AUTHORS.md`](AUTHORS.md).
