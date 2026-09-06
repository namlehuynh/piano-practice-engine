"""Self-contained HTML practice report.

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

Two layouts, chosen from the data rather than forced on every piece:

- Cycle layout, when one hand repeats on a fixed period (Amelie: four
  positions on a four-bar cycle, 99% agreement). Shows a baseline shape,
  then each position marking only what changed from the one before.
- Family layout, when it does not (Proud of You: 24 left-hand patterns,
  no cycle). Groups patterns that share a hand shape, positions inside.

Chord vocabulary accumulates across pieces: pass --known to carry what
the learner already met, and each new piece reports how few chords are
actually new.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Sequence

from .analysis import bar_length, cluster_bars, label_tones, phrase_blocks
from .exercises import (
    block_chord,
    overlap_pairs,
    rhythm_variants,
    tempo_ladder,
    transitions,
)
from .metadata import describe, score_meta
from .structure import form_string, sections, summary as form_summary
from .chords import anchors, name_chord
from .i18n import Translator
from .keyboard import diff_marks, keyboard_svg, press_order, roll_svg
from .patterns import (
    DEFAULT_TIER,
    Pattern,
    shared_openings,
    summarise,
    technique_families,
)

CSS = """
:root{--ink:#2C2C2A;--mute:#5F5E5A;--line:#D3D1C7;--bg:#FAF9F5;--card:#FFF;
--warm:#993C1D;--warmbg:#FAECE7;--cool:#0F6E56;--coolbg:#E1F5EE}
*{box-sizing:border-box}
body{margin:0;padding:24px 16px 64px;background:var(--bg);color:var(--ink);
font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:760px;margin:0 auto}
h1{font-size:24px;font-weight:500;margin:0 0 4px}
h2{font-size:18px;font-weight:500;margin:32px 0 4px}
h3{font-size:15px;font-weight:500;margin:0 0 8px}
p.sub{color:var(--mute);font-size:14px;margin:0 0 8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:16px;margin:12px 0}
.card.base{border-color:var(--warm);border-width:2px}
.kb{overflow-x:auto;margin:10px 0 6px;-webkit-overflow-scrolling:touch}
.kb svg{display:block}
.chip{display:inline-block;padding:5px 12px;border-radius:999px;font-size:14px;
margin:0 6px 6px 0;border:1px solid}
.chip.new{background:var(--warmbg);border-color:var(--warm);color:var(--warm)}
.chip.known{background:var(--coolbg);border-color:var(--cool);color:var(--cool)}
.note{font-size:14px;color:var(--mute);margin:4px 0 0}
.bars{display:flex;flex-wrap:wrap;gap:3px;margin:10px 0}
.bar{width:16px;height:16px;border-radius:3px;border:1px solid var(--line)}
.legend{font-size:13px;color:var(--mute);margin:6px 0 0}
.key{display:inline-block;width:11px;height:11px;border-radius:3px;
vertical-align:-1px;margin-right:5px;border:1px solid var(--line)}
footer{margin-top:48px;padding-top:16px;border-top:1px solid var(--line);
font-size:13px;color:var(--mute)}
@media(prefers-color-scheme:dark){:root{--ink:#E8E6DF;--mute:#9C9A92;
--line:#444441;--bg:#1C1C1A;--card:#262624;--warmbg:#3A1F14;--coolbg:#12332A;
--warm:#F0997B;--cool:#5DCAA5}}
"""

PALETTE = ["#F0997B", "#9FE1CB", "#B5D4F4", "#FAC775", "#F4C0D1", "#CECBF6"]


_T = Translator()


def _esc(s) -> str:
    return html.escape(str(s))


def _chord_of(p: Pattern) -> str | None:
    c = name_chord(p.midis)
    if not c or not c["confident"]:
        return None
    # Slash bass is information for someone who reads theory. A beginner
    # already sees where the little finger goes from the diagram.
    return c["name"]


def _pattern_card(
    p: Pattern, prev: Pattern | None, total_bars: int, is_base: bool
) -> str:
    marks = diff_marks(p.midis, prev.midis if prev else None)
    svg = keyboard_svg(marks, press_order(p.midis))
    chord = _chord_of(p)

    if prev is None:
        caption = f"{len(set(p.midis))} phím. Đây là dáng phải thuộc trước."
    else:
        moved = len(set(p.midis) - set(prev.midis))
        caption = (
            "Chỉ đổi 1 phím so với vị trí trên."
            if moved == 1
            else f"Đổi {moved} phím so với vị trí trên."
        )

    head = f"{_esc(p.pattern_id)}"
    if chord:
        head += f" · {_esc(chord)}"
    head += f" · {p.count} ô nhịp ({p.count / total_bars:.0%})"

    fingers = ""
    if p.fingers:
        fingers = f'<p class="note">{_T("fingering", fingers=_esc(" ".join(p.fingers)))}</p>'

    return (
        f'<div class="card{" base" if is_base else ""}">'
        f"<h3>{head}</h3>"
        f'<div class="kb">{svg}</div>'
        f'<p class="note">{caption}</p>{fingers}'
        f'<p class="note">Ô nhịp: {_esc(", ".join(str(m) for m in p.measures[:14]))}'
        f'{" …" if len(p.measures) > 14 else ""}</p>'
        f"</div>"
    )


def _cycle_layout(info: dict, pats: list[Pattern]) -> str:
    by_id = {p.pattern_id: p for p in pats}
    cycle = info["cycle"]
    # Start from the pattern that opens the piece, not the most frequent:
    # learning a shape you cannot start the piece with is a dead end.
    order = list(cycle["order"])
    first = min(pats, key=lambda p: p.measures[0]).pattern_id
    if first in order:
        i = order.index(first)
        order = order[i:] + order[:i]

    out = [
        f'<p class="sub">Chu kỳ {cycle["period"]} ô nhịp, khớp '
        f'{cycle["agreement"]:.0%} từ ô {cycle["first_measure"]} đến ô '
        f'{cycle["last_measure"]}. Thuộc chu kỳ này là thuộc gần hết phần tay '
        f"này.</p>"
    ]
    prev = None
    for k, pid in enumerate(order):
        p = by_id.get(pid)
        if not p:
            continue
        out.append(_pattern_card(p, prev, info["n_bars"], k == 0))
        prev = p

    a = anchors([by_id[i] for i in order if i in by_id])
    if a and a["bass"]["holds"] > 1:
        out.append(
            f'<p class="note">Ngón út giữ nguyên trên {_esc(a["bass"]["note"])} '
            f'ở {a["bass"]["holds"]}/{a["bass"]["of"]} vị trí — tay gần như '
            f"không phải rời chỗ.</p>"
        )
    return "".join(out)


def _family_layout(info: dict, families: list[dict]) -> str:
    out = [
        '<p class="sub">Phần tay này không có chu kỳ lặp. Thay vào đó các kiểu '
        "được gom theo dáng tay — cùng một cách bấm, khác vị trí.</p>"
    ]
    shown = 0
    for fam in families:
        if fam["n_positions"] < 2 or shown >= 3:
            continue
        shown += 1
        members = fam["members"][:5]
        out.append(
            f'<h3>{_esc(fam["family_id"])} — một dáng tay, '
            f'{fam["n_positions"]} vị trí, phủ {fam["bars_covered"]}/'
            f'{info["n_bars"]} ô nhịp</h3>'
        )
        prev = None
        for k, p in enumerate(members):
            out.append(_pattern_card(p, prev, info["n_bars"], k == 0))
            prev = p
        if fam["n_positions"] > 5:
            out.append(
                f'<p class="note">(còn {fam["n_positions"] - 5} vị trí nữa '
                f"trong họ này)</p>"
            )
    if shown == 0:
        out.append(
            '<p class="note">Không gom được thành họ dáng tay — phần này phải '
            "học theo từng đoạn.</p>"
        )
    return "".join(out)


def _piece_map(info: dict) -> str:
    colors = {}
    for i, p in enumerate(info["patterns"]):
        colors[p.pattern_id] = PALETTE[i % len(PALETTE)]
    cells = "".join(
        f'<div class="bar" style="background:{colors.get(pid, "#D3D1C7")}" '
        f'title="Ô {m} · {_esc(pid)}"></div>'
        for m, pid in info["sequence"]
    )
    return (
        f'<div class="bars">{cells}</div>'
        f'<p class="legend">{_T("map_note")}</p>'
    )


def _chord_section(events, known: set[str]) -> tuple[str, list[str]]:
    # Must come from the same pass that labels the cards, or the summary
    # says "1 chord" while the cards below list seven.
    found: list[str] = []
    for c in cluster_bars(events, "L", tolerance=1):
        for t in label_tones(events, c["notes"]):
            if t["chord"] and t["chord"] not in found:
                found.append(t["chord"])
    if not found:
        return (
            '<p class="note">Bài này không đặt tên hợp âm được — phần đệm '
            "không rải thành hợp âm rõ ràng. Cứ học theo hình phím.</p>",
            [],
        )

    new = [c for c in found if c not in known]
    chips = "".join(
        f'<span class="chip {"known" if c in known else "new"}">{_esc(c)}</span>'
        for c in found
    )
    if known:
        line = (
            f"Bài này có {len(found)} hợp âm, bạn đã biết "
            f"{len(found) - len(new)}. Học thêm {len(new)} là xong."
        )
    else:
        line = f"Bài này có {len(found)} hợp âm. Học xong là bạn có {len(found)}."
    return f'<p class="sub">{line}</p><div>{chips}</div>', new


def _cluster_card(events, cluster: dict, total_bars: int, first: bool,
                  hand: str = "L") -> str:
    tones = label_tones(events, cluster["notes"])
    core = [t for t in tones if t["role"] == "chính"]
    extra = [t for t in tones if t["role"] == "phụ"]
    chords = [c for c in dict.fromkeys(t["chord"] for t in tones) if c]

    marks = {t["midi"]: ("base" if t["role"] == "chính" else "held") for t in tones}
    order = press_order([n.midi for n in cluster["notes"]])
    svg = keyboard_svg(marks, order)

    head = _esc(cluster["cluster_id"])
    if chords:
        head += " · " + _esc(" → ".join(chords))
    head += (
        f' · {cluster["count"]} ô nhịp '
        f'({cluster["count"] / total_bars:.0%})'
    )

    lines = [
        f'<div class="card{" base" if first else ""}"><h3>{head}</h3>',
        f'<div class="kb">{roll_svg(cluster["notes"])}</div>',
        f'<div class="kb">{svg}</div>',
    ]
    # Only split into essential and optional when the harmony is clear
    # enough to trust. Below half chord tones the analysis was telling
    # learners to drop every note in the bar, which is worse than saying
    # nothing.
    trustworthy = core and len(core) >= len(tones) / 2
    if trustworthy:
        lines.append(
            f'<p class="note">{_T("core_tones", notes=_esc(" ".join(dict.fromkeys(t["note"] for t in core))))}</p>'
        )
        if extra and hand == "L":
            lines.append(
                f'<p class="note">{_T("colour_tones", notes=_esc(" ".join(dict.fromkeys(t["note"] for t in extra))))}</p>'
            )
    else:
        lines.append(
            f'<p class="note">{_T("all_keys", notes=_esc(" ".join(dict.fromkeys(t["note"] for t in tones))))}</p>'
        )
    lines.append(
        f'<p class="note">{_T("learn_bar", bar=cluster["representative"], bars=_esc(", ".join(str(b) for b in cluster["bars"][:14])))}'
        f'{" …" if len(cluster["bars"]) > 14 else ""}</p></div>'
    )
    return "".join(lines)


def _cluster_layout(events, hand: str, n_bars: int) -> str:
    # Ordered by where each group is first played, then renumbered, so the
    # first card is the one that opens the piece and the ids read in order.
    clusters = sorted(
        cluster_bars(events, hand, tolerance=1), key=lambda c: c["bars"][0]
    )
    for i, c in enumerate(clusters, 1):
        c["cluster_id"] = f"{hand}{i}"
    if not clusters:
        return ""
    blocks = phrase_blocks(events, hand, clusters)
    out = []
    if blocks:
        b = blocks[0]
        rng = f'{b["starts"][0]}–{b["starts"][0] + b["length"] - 1}'
        items = "".join(
            f'<li>Khối {x["length"]} ô lặp {x["occurrences"]} lần, bắt đầu ở ô '
            f'{", ".join(str(s) for s in x["starts"][:8])}.</li>'
            for x in blocks[:3]
        )
        out.append(
            f'<p class="sub">{_T("loop_intro", length=b["length"], range=rng, n=b["occurrences"])}</p><ul class="note">{items}</ul>'
        )
    out.append(
        f'<p class="sub">{_T("groups_intro", n=len(clusters))}</p>'
    )
    # Greedy set cover, not "the twelve most frequent groups".
    # Frequency-ranked selection dropped Amelie's climax (bars 53-85)
    # entirely: it is the most important passage in the piece and the
    # least repetitive, so it loses every popularity contest. Covering the
    # timeline instead means each stretch of the piece gets a card, and
    # the learner can play from start to finish.
    remaining = list(clusters)
    shown, covered_bars = [], set()
    while remaining and len(shown) < 12:
        best = max(remaining, key=lambda c: len(set(c["bars"]) - covered_bars))
        gain = set(best["bars"]) - covered_bars
        if not gain:
            break
        shown.append(best)
        covered_bars |= gain
        remaining.remove(best)
        if len(covered_bars) >= 0.92 * n_bars:
            break
    shown.sort(key=lambda c: c["bars"][0])
    for i, c in enumerate(shown):
        out.append(_cluster_card(events, c, n_bars, i == 0, hand))

    missing = sorted(set().union(*(set(c["bars"]) for c in clusters)) - covered_bars)
    if missing:
        runs, start = [], missing[0]
        for a, b in zip(missing, missing[1:] + [None]):
            if b != a + 1:
                runs.append((start, a))
                start = b
        # Distinguish "no card yet" from "never repeats". Labelling the
        # whole tail as unrepeated was simply false: bars 53-68 of Amelie
        # are one figure played sixteen times.
        repeated = {
            m for c in clusters if c["count"] > 1 for m in c["bars"]
        }
        n_rep = len([m for m in missing if m in repeated])
        n_once = len(missing) - n_rep
        parts = []
        if n_rep:
            parts.append(
                _T("rest_repeat", n=n_rep)
            )
        if n_once:
            parts.append(_T("rest_once", n=n_once))
        out.append(
            f'<h3>{_T("rest_heading", n=len(missing))}</h3>'
            f'<p class="note">{_T("rest_note", parts=_esc(", ".join(parts)))}</p>'
        )
        for lo, hi in runs:
            if hi - lo < 1:
                continue
            notes = [
                e for e in events
                if e.hand == hand and lo <= e.measure <= min(hi, lo + 3)
            ]
            if not notes:
                continue
            marks = {n.midi: "changed" for n in notes}
            label = f"Ô {lo}–{hi}" if hi != lo else f"Ô {lo}"
            out.append(
                f'<div class="card"><h3>{label} · {hi - lo + 1} ô nhịp</h3>'
                f'<div class="kb">{roll_svg(notes, height=110)}</div>'
                f'<div class="kb">{keyboard_svg(marks)}</div>'
                f'<p class="note">Vùng phím dùng trong đoạn này. Xem trích đoạn '
                f"phía trên để biết thứ tự và nhịp — {min(4, hi - lo + 1)} ô đầu.</p>"
                f"</div>"
            )
    return "".join(out)


def _form_section(events, hand: str, clusters) -> str:
    secs = sections(events, {hand: clusters})
    if not secs:
        return ""
    s = form_summary(secs)
    # Fourteen identical "A" chips say nothing. Only draw them when the
    # form actually varies.
    chips = ""
    if len({x["label"] for x in secs}) > 1:
        chips = "".join(
            f'<span class="chip {"known" if not x["unique"] else "new"}">'
            f'{x["label"]} · ô {x["first_bar"]}–{x["last_bar"]}</span>'
            for x in secs
        )
    if s["share_new"] <= 0.25:
        verdict = _T("form_static")
    elif s["share_new"] >= 0.8:
        verdict = _T("form_novel")
    else:
        verdict = _T("form_mixed", new=s["new_bars"], total=s["total_bars"])
    return (
        f'<p class="sub">{_T("form_prefix", form=_esc(form_string(secs)))} '
        f"{verdict}</p><div>{chips}</div>"
    )


def _exercise_section(events, hand: str, clusters, meta: dict) -> str:
    out = ["<h3>Bài tập nhỏ</h3>"]

    trans = transitions(events, hand, clusters)
    if trans:
        items = "".join(
            f'<li>{_T("transition_item", a=_esc(t["from_cluster"]), b=_esc(t["to_cluster"]), lo=t["bars"][0], hi=t["bars"][1], n=t["keys_moved"])}</li>'
            for t in trans[:5]
        )
        out.append(
            f"<p class='note'>{_T('transitions_intro')}</p><ul class='note'>{items}</ul>"
        )

    if clusters:
        rep = clusters[0]["notes"]
        blocks = block_chord(rep)
        if blocks:
            from music21 import pitch

            txt = " rồi ".join(
                "+".join(pitch.Pitch(m).nameWithOctave for m in b) for b in blocks
            )
            out.append(
                f'<p class="note"><b>Chặn hợp âm:</b> thay vì rải từng nốt, '
                f"bấm cùng lúc {_esc(txt)}. Tay nhớ cự ly phím nhanh hơn "
                f"nhiều so với rải. Thử nhắm mắt — tay phải tự đo được "
                f"khoảng cách mà không cần nhìn.</p>"
            )
        var = rhythm_variants(rep)
        if var:
            items = "".join(
                f'<li><b>{_T(v["name"])}:</b> {_T(v["note"])}</li>' for v in var
            )
            out.append(
                f"<p class='note'>{_T('rhythm_intro')}</p><ul class='note'>{items}</ul>"
            )

    laps = overlap_pairs(clusters)
    if laps:
        items = "".join(f'<li>{_T("overlap_item", a=x["from_bar"], b=x["to_bar"])}</li>' for x in laps[:4])
        out.append(
            f"<p class='note'>{_T('overlap_intro')}</p><ul class='note'>{items}</ul>"
        )

    ladder = tempo_ladder(meta.get("bpm"))
    if ladder:
        out.append(
            f'<p class="note">{_T("ladder", steps=" → ".join(str(b) for b in ladder))}</p>'
        )
    return "".join(out) if len(out) > 1 else ""


def _hotspot_section(result: dict) -> str:
    q = result.get("practice_queue") or []
    if not q:
        return ""
    by_id = {u["unit_id"]: u for u in result["units"]}
    rows = []
    for x in q[:6]:
        u = by_id.get(x["unit_id"])
        if not u:
            continue
        why = ", ".join(_T(w) for w in x["why"]) or "—"
        rows.append(
            f'<li>{_T("hotspot_item", lo=u["first_measure"], hi=u["last_measure"], why=_esc(why))}'
            f'{_T("hotspot_repeat", n=x["unlocks"]) if x["unlocks"] > 1 else ""}.</li>'
        )
    if not rows:
        return ""
    return (
        f"<h2>{_T('hotspots')}</h2>"
        f"<p class='sub'>{_T('hotspots_intro')}</p>"
        f"<ul class='note'>{''.join(rows)}</ul>"
    )


def _hand_verdict(events, meta: dict) -> str:
    """Say which hand is the work and which is a loop.

    On Amelie the left hand is five groups across 109 bars while the
    right is nineteen; the piece is one fixed accompaniment under a
    melody that develops. The engine computed both numbers from the
    start and never said the one sentence that follows from them, which
    is the sentence a learner most needs before they begin.
    """
    stats = {}
    for hand in ("L", "R"):
        secs = sections(events, {hand: cluster_bars(events, hand,
                                                   scale=meta.get("scale"))})
        if secs:
            stats[hand] = form_summary(secs)["share_new"]
    if len(stats) < 2:
        return ""
    loop, work = ("L", "R") if stats["L"] < stats["R"] else ("R", "L")
    if stats[loop] > 0.35 or stats[work] - stats[loop] < 0.25:
        return (
            f'<p class="sub">{_T("both_hands_work")}</p>'
        )
    names = {"L": _T("hand_left"), "R": _T("hand_right")}
    return (
        f'<p class="sub">'
        + _T("engine_hand", loop=names[loop], loop_pct=f"{stats[loop]:.0%}",
             work=names[work], work_pct=f"{stats[work]:.0%}")
        + "</p>"
    )


def _section_order(events, hand: str, clusters, result: dict) -> str:
    """Sections ordered easiest first, so there is somewhere to start."""
    secs = sections(events, {hand: clusters})
    if len(secs) < 3:
        return ""
    diff = {}
    for u in result.get("units", []):
        for m in range(u["first_measure"], u["last_measure"] + 1):
            diff.setdefault(m, []).append(u["difficulty"]["score"])
    scored = []
    for s in secs:
        vals = [
            v
            for m in range(s["first_bar"], s["last_bar"] + 1)
            for v in diff.get(m, [])
        ]
        if vals:
            scored.append((sum(vals) / len(vals), s))
    if len(scored) < 3:
        return ""
    scored.sort(key=lambda x: x[0])
    if len({s["label"] for _, s in scored}) < 3:
        return ""  # one or two distinct sections: nothing to order
    seen, order = set(), []
    for score, s in scored:
        if s["label"] in seen:
            continue
        seen.add(s["label"])
        order.append(f'{s["label"]} (ô {s["first_bar"]}–{s["last_bar"]})')
    return (
        f'<p class="note">{_T("order_easy_first", order=_esc(" → ".join(order[:6])))}</p>'
    )


def build_html(
    result: dict, events: Sequence, known: set[str] | None = None,
    meta: dict | None = None, lang: str | None = None,
) -> tuple[str, list[str]]:
    global _T
    _T = Translator(lang)
    known = known or set()
    meta = meta or {}
    # Left hand matches on exact keys, right hand on the melodic contour
    # of each onset -- see patterns.DEFAULT_TIER for why.
    # Left hand matches on exact keys, right hand on the melodic contour
    # of each onset -- see patterns.DEFAULT_TIER for why.
    vocab = summarise(events)
    for hand in vocab:
        vocab[hand]["families"] = technique_families(events, hand)

    chord_html, new_chords = _chord_section(events, known)

    body = [
        f"<h1>{_esc(result['score_id'])}</h1>",
        f'<p class="sub">{result["meta"]["measures"]} {_T("bars")} · '
        f'{result["meta"]["notes"]} {_T("notes")}'
        + (f' · {_esc(describe(meta, _T))}' if describe(meta, _T) else "")
        + "</p>",
        _hand_verdict(events, meta),
        f"<h2>{_T('chords_heading')}</h2>",
        chord_html,
    ]

    for hand, label in (("L", _T("left_hand")), ("R", _T("right_hand"))):
        if hand not in vocab:
            continue
        info = vocab[hand]
        body.append(f"<h2>{label}</h2>")
        hand_clusters = cluster_bars(events, hand, tolerance=1, scale=meta.get("scale"))
        body.append(_form_section(events, hand, hand_clusters))
        body.append(_section_order(events, hand, hand_clusters, result))
        if info.get("cycle") and info["cycle"]["agreement"] >= 0.9:
            # A piece that loops all the way through: show one baseline
            # shape and how little changes at each position.
            body.append(_cycle_layout(info, info["patterns"]))
        else:
            # Everything else: group bars with a one-note tolerance and
            # say which notes are the chord and which are colour.
            body.append(_cluster_layout(events, hand, info["n_bars"]))
        body.append(_piece_map(info))
        body.append(_exercise_section(events, hand, hand_clusters, meta))

    body.append(_hotspot_section(result))
    body.append(
        f"<h2>{_T('how_to')}</h2><ol class='note'>"
        + "".join(f"<li>{_T(f'how_{i}')}</li>" for i in range(1, 6))
        + f"</ol><p class='note'>{_T('trust_the_score')}</p>"
        + f"<footer>{_T('attribution')}</footer>"
    )

    doc = (
        f"<!doctype html><html lang='{_T.lang}'>"
        "<head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{_esc(result['score_id'])} — {_T('title_suffix')}</title>"
        f"<style>{CSS}</style></head><body><div class='wrap'>"
        + "".join(body)
        + "</div></body></html>"
    )
    return doc, new_chords


def load_known(path: str | None) -> set[str]:
    if not path or not Path(path).exists():
        return set()
    return set(json.loads(Path(path).read_text(encoding="utf-8")).get("chords", []))


def save_known(path: str, chords: set[str]) -> None:
    Path(path).write_text(
        json.dumps({"chords": sorted(chords)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
