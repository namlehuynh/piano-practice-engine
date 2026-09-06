"""Smoke test: run the engine end-to-end and assert the invariants hold.

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

Exits non-zero on failure. Run this after any change to the scoring
weights -- it is the cheapest guard against the segmenter silently
collapsing or shattering.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from piano_practice_engine import analyse
from piano_practice_engine.segment import Weights

HERE = Path(__file__).parent
FAILED = []


def check(label, condition, detail=""):
    mark = "ok  " if condition else "FAIL"
    print(f"  [{mark}] {label}{'  ' + detail if detail else ''}")
    if not condition:
        FAILED.append(label)


def build_fixtures(tmp: Path) -> list[Path]:
    out = []
    for script in ("make_ostinato.py", "make_ballad.py"):
        subprocess.run(
            [sys.executable, str(HERE / script)], cwd=tmp, check=True,
            capture_output=True,
        )
    for name in ("ostinato_test.musicxml", "ballad_test.musicxml"):
        p = tmp / name
        assert p.exists(), f"fixture {name} was not generated"
        out.append(p)
    return out


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        print("generating fixtures...")
        fixtures = build_fixtures(tmp)

        sources = ["bach/bwv846", "joplin/maple_leaf_rag"] + [str(p) for p in fixtures]
        for src in sources:
            name = Path(str(src)).stem
            print(f"\n{name}")
            r = analyse(src)
            u, c, m = r["units"], r["coverage"], r["meta"]

            check("parsed notes", m["notes"] > 50, f"{m['notes']} notes")
            check("measures detected", m["measures"] > 5, f"{m['measures']} bars")
            check("not collapsed", len(u) > 3, f"{len(u)} units")
            check("not shattered", len(u) < m["measures"], f"{len(u)} units")

            spans = [x["last_measure"] - x["first_measure"] + 1 for x in u]
            check("unit length window", max(spans) <= 4, f"max {max(spans)} bars")

            covered = sum(x["end_slice"] - x["start_slice"] for x in u)
            check("full coverage", covered == m["slices"],
                  f"{covered}/{m['slices']} slices")

            starts = sorted(x["start_slice"] for x in u)
            ends = sorted(x["end_slice"] for x in u)
            check("no gaps or overlaps", starts[1:] == ends[:-1])

            check("difficulty in range",
                  all(1.0 <= x["difficulty"]["score"] <= 9.0 for x in u))
            check("queue covers every group",
                  len(r["practice_queue"]) == c["distinct_groups"])

            # The naive baseline must also run -- it is the fallback path.
            rn = analyse(src, naive=True)
            check("naive baseline runs", len(rn["units"]) > 0,
                  f"{len(rn['units'])} units")

        print("\ncustom weights")
        r = analyse("bach/bwv846", weights=Weights(max_measures=8, min_measures=4))
        spans = [x["last_measure"] - x["first_measure"] + 1 for x in r["units"]]
        check("weights are honoured", max(spans) <= 8, f"max {max(spans)} bars")

    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed: {', '.join(FAILED)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
