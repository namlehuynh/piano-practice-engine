"""Markdown practice report.

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

The point is validation: every claim here cites bar numbers and real note
names, so it can be checked against the printed score in a few minutes.
JSON is for the app; this is for deciding whether the analysis is right
at all.
"""

from __future__ import annotations

from typing import Sequence

from .i18n import Translator
from .patterns import Pattern, summarise, technique_families

_T = Translator()


def _rhythm_label(onsets: Sequence[float], durations: Sequence[float]) -> str:
    if not durations:
        return "-"
    uniq = sorted(set(durations))
    if len(uniq) == 1:
        names = {
            4.0: "dur_whole", 2.0: "dur_half", 1.0: "dur_quarter",
            0.5: "dur_eighth", 0.25: "dur_16th",
        }
        key = names.get(uniq[0])
        unit = _T(key) if key else _T("dur_beats", q=uniq[0])
        return _T("dur_even", n=len(durations), unit=unit)
    return _T("dur_mixed", n=len(durations),
              list=", ".join(str(d) for d in durations))


def _compact_measures(measures: Sequence[int], limit: int = 12) -> str:
    if len(measures) <= limit:
        return ", ".join(str(m) for m in measures)
    head = ", ".join(str(m) for m in measures[:limit])
    return _T("rep_more_measures", head=head, n=len(measures) - limit)


def _pattern_block(p: Pattern, total_bars: int) -> list[str]:
    share = p.count / total_bars if total_bars else 0
    lines = [
        f"### {_T('rep_pattern_head', pid=p.pattern_id, count=p.count, pct=f'{share:.0%}')}",
        "",
        f"- {_T('rep_notes')}: `{' '.join(p.notes)}`",
        f"- {_T('rep_intervals')}: `{' '.join(f'{i:+d}' if i else '0' for i in p.intervals)}`",
        f"- {_T('rep_rhythm')}: {_rhythm_label(p.onsets, p.durations)}",
    ]
    if p.fingers:
        lines.append(f"- {_T('rep_fingering')}: `{' '.join(p.fingers)}`")
    lines += [
        f"- {_T('rep_occurs')}: {_compact_measures(p.measures)}",
        "",
    ]
    return lines


def hand_section(hand: str, info: dict) -> list[str]:
    pats: list[Pattern] = info["patterns"]
    hand_name = _T("left_hand") if hand == "L" else _T("right_hand")
    lines = [
        f"## {_T('rep_hand_head', hand=hand_name, n=info['n_patterns'], bars=info['n_bars'])}",
        "",
    ]
    cycle = info.get("cycle")
    if cycle:
        order = " → ".join(cycle["order"])
        lines += [
            _T("rep_cycle", period=cycle["period"], order=order),
            "",
            _T("rep_cycle_note", agree=f"{cycle['agreement']:.0%}",
               first=cycle["first_measure"], last=cycle["last_measure"]),
            "",
        ]
    else:
        lines += [_T("rep_no_cycle"), ""]

    fams = info.get("families") or []
    big = [f for f in fams if f["n_positions"] > 1]
    if big:
        lines += [_T("rep_family_head"), ""]
        for f in big:
            ids = ", ".join(m.pattern_id for m in f["members"])
            lines.append("- " + _T(
                "rep_family_item", fid=f["family_id"], n=f["n_positions"],
                ids=ids, covered=f["bars_covered"], bars=info["n_bars"]))
        lines += ["", _T("rep_family_note"), ""]

    covered = sum(p.count for p in pats[:4])
    if len(pats) > 4:
        lines += [
            _T("rep_top4", covered=covered, bars=info["n_bars"],
               pct=f"{covered / info['n_bars']:.0%}", rest=len(pats) - 4),
            "",
        ]

    for p in pats[:8]:
        lines += _pattern_block(p, info["n_bars"])
    if len(pats) > 8:
        rest = sum(p.count for p in pats[8:])
        lines += [_T("rep_more_patterns", n=len(pats) - 8, bars=rest), ""]
    return lines


def queue_section(result: dict, limit: int = 10) -> list[str]:
    by_id = {u["unit_id"]: u for u in result["units"]}
    lines = [
        f"## {_T('rep_queue_head')}",
        "",
        f"| # | {_T('rep_col_unit')} | {_T('rep_col_bars')} | "
        f"{_T('rep_col_diff')} | {_T('rep_col_unlocks')} | "
        f"{_T('rep_col_why')} | {_T('rep_col_tech')} |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, q in enumerate(result["practice_queue"][:limit], 1):
        u = by_id[q["unit_id"]]
        why = ", ".join(_T(w) for w in q["why"]) or "—"
        tech = ", ".join(u["techniques"]) or "—"
        lines.append(
            f"| {i} | `{q['unit_id']}` | {u['first_measure']}–{u['last_measure']} "
            f"| {q['difficulty']:.1f} | {q['unlocks']}× | {why} | {tech} |"
        )
    lines.append("")
    return lines


def build_report(
    result: dict, events, tier: str | None = None, lang: str | None = None
) -> str:
    global _T
    _T = Translator(lang)
    vocab = summarise(events, tier)
    for hand in vocab:
        vocab[hand]["families"] = technique_families(events, hand)
    m, c = result["meta"], result["coverage"]

    lines = [
        f"# {result['score_id']}",
        "",
        _T("rep_stats", notes=m["notes"], measures=m["measures"],
           units=c["units"], groups=c["distinct_groups"]),
        "",
        _T("rep_intro"),
        "",
    ]

    for hand in ("L", "R"):
        if hand in vocab:
            lines += hand_section(hand, vocab[hand])

    lines += queue_section(result)

    lines += [
        f"## {_T('rep_howto_head')}",
        "",
        f"1. {_T('rep_howto_1')}",
        f"2. {_T('rep_howto_2')}",
        f"3. {_T('rep_howto_3')}",
        "",
    ]
    return "\n".join(lines)
