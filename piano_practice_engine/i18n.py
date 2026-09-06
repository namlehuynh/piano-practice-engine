"""Vietnamese and English strings for the learner-facing report.

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

Only the report a learner reads is translated. The markdown report and
the CLI stay in Vietnamese: they exist for checking the engine against a
printed score, and their audience is whoever is developing it.

Language is chosen explicitly with --lang, falling back to the shell
locale and then to Vietnamese. Never guessed from the score: a French
film theme carries no hint of what its player reads.
"""

from __future__ import annotations

import os

DEFAULT = "vi"

STRINGS: dict[str, dict[str, str]] = {
    "vi": {
        "title_suffix": "bài tập",
        "bars": "ô nhịp",
        "notes": "nốt",
        "key_of": "giọng {key}",
        "major": "trưởng",
        "minor": "thứ",
        "meter": "nhịp {ts}",
        "tempo": "tốc độ {bpm} bpm",
        "left_hand": "Tay trái",
        "right_hand": "Tay phải",
        "hand_left": "trái",
        "hand_right": "phải",
        "engine_hand": (
            "<b>Tay {loop} là cỗ máy.</b> Nó gần như không đổi suốt bài "
            "({loop_pct} chất liệu mới), nên tập cho tới khi chơi được mà "
            "không cần nghĩ. Toàn bộ độ khó nằm ở tay {work} ({work_pct} mới) "
            "— khi ghép hai tay, dồn hết chú ý vào tay đó."
        ),
        "both_hands_work": (
            "Hai tay đều có phần thay đổi đáng kể — chia thời gian tập cho "
            "cả hai."
        ),
        "chords_heading": "Hợp âm trong bài",
        "chords_none": (
            "Bài này không đặt tên hợp âm được — phần đệm không rải thành hợp "
            "âm rõ ràng. Cứ học theo hình phím."
        ),
        "chords_first": "Bài này có {n} hợp âm. Học xong là bạn có {n}.",
        "chords_known": (
            "Bài này có {n} hợp âm, bạn đã biết {known}. Học thêm {new} là xong."
        ),
        "form_prefix": "Cấu trúc: <b>{form}</b>.",
        "form_static": "Phần tay này gần như không đổi suốt bài — học một lần là xong.",
        "form_novel": (
            "Phần tay này hầu như không lặp lại — phải học lần lượt từng đoạn "
            "theo bản nhạc."
        ),
        "form_mixed": (
            "Chỉ {new}/{total} ô là chất liệu mới; phần còn lại là các đoạn "
            "quay lại."
        ),
        "order_easy_first": (
            "<b>Thứ tự nên tập, dễ trước:</b> {order}. Đừng tập từ đầu đến "
            "cuối — bắt đầu ở đoạn dễ nhất để có đà."
        ),
        "groups_intro": "{n} nhóm ô nhịp, xếp theo thứ tự bạn gặp khi chơi.",
        "loop_intro": (
            "Vòng lặp {length} ô nhịp: học ô {range} là mở được {n} chỗ."
        ),
        "core_tones": "Âm chính (thuộc hợp âm): {notes}",
        "colour_tones": "Âm phụ, bỏ được lúc đầu: {notes}",
        "all_keys": "Các phím: {notes} — chưa tách được âm chính, tập cả ô.",
        "learn_bar": "Học ô {bar}, dùng được cho ô: {bars}",
        "fingering": "Ngón tay: {fingers}",
        "rest_heading": "Các đoạn còn lại — {n} ô nhịp",
        "rest_repeat": "{n} ô có lặp lại nhưng chưa đủ chỗ làm thẻ riêng",
        "rest_once": "{n} ô chỉ xuất hiện một lần",
        "rest_note": (
            "{parts}. Ở nhạc phim và ballad đoạn không lặp thường là cao trào "
            "— phần đáng học nhất, và phải học thẳng từ bản nhạc."
        ),
        "map_note": (
            "Mỗi ô vuông là một ô nhịp, màu theo kiểu bấm. Chu kỳ lặp hiện ra "
            "thành sọc."
        ),
        "exercises": "Bài tập nhỏ",
        "transitions_intro": (
            "Chỗ khó thật sự không phải từng vị trí, mà là lúc chuyển giữa chúng:"
        ),
        "transition_item": (
            "<b>{a} → {b}</b> (ô {lo}–{hi}, {n} phím đổi): chỉ tập bốn nốt "
            "quanh chỗ chuyển, đi đi lại lại cho tới khi tay tự tìm đúng vị trí."
        ),
        "block_chords": (
            "<b>Chặn hợp âm:</b> thay vì rải từng nốt, bấm cùng lúc {chords}. "
            "Tay nhớ cự ly phím nhanh hơn nhiều so với rải. Thử nhắm mắt — tay "
            "phải tự đo được khoảng cách mà không cần nhìn."
        ),
        "rhythm_intro": (
            "<b>Biến đổi tiết tấu</b> — giữ nguyên nốt và ngón, chỉ đổi nhịp:"
        ),
        "rhythm_long_short": "Dài – ngắn",
        "rhythm_short_long": "Ngắn – dài",
        "rhythm_pairs": "Chặn theo cặp",
        "rhythm_long_short_note": "Nốt lẻ ngân dài, nốt chẵn nảy nhanh.",
        "rhythm_short_long_note": "Ngược lại. Chỗ nào vấp sẽ lộ ra ngay.",
        "rhythm_pairs_note": "Đánh từng cặp nốt cùng lúc, dừng, rồi cặp tiếp.",
        "overlap_intro": (
            "<b>Nối đè</b> — đừng bao giờ dừng ở nốt cuối của một cụm:"
        ),
        "overlap_item": (
            "Chơi hết ô {a}, không dừng, nối thẳng vào nốt đầu của ô {b}."
        ),
        "ladder": (
            "<b>Thang tốc độ:</b> {steps} bpm. Chỉ lên bậc sau khi chơi sạch "
            "ba lần liên tiếp ở bậc hiện tại."
        ),
        "hotspots": "Điểm nóng — tập những chỗ này trước",
        "hotspots_intro": (
            "Xếp theo độ khó nhân với số lần gặp lại. Giải quyết xong mấy chỗ "
            "này là phần còn lại trôi."
        ),
        "hotspot_item": "Ô {lo}–{hi} — {why}",
        "hotspot_repeat": " (gặp lại {n} lần)",
        "how_to": "Cách tập",
        "how_1": (
            "Bắt đầu bằng thẻ <b>tay trái đầu tiên</b> — nó là chỗ bài mở đầu. "
            "Bấm các phím tô đậm theo số 1, 2, 3… trên sơ đồ."
        ),
        "how_2": (
            "Chỉ tập <b>âm chính</b> trước. Âm phụ bỏ được, thêm vào sau khi "
            "tay đã quen."
        ),
        "how_3": (
            "Tập chậm, khoảng một nửa tốc độ bài hát. Tăng dần khi chơi sạch "
            "ba lần liên tiếp."
        ),
        "how_4": (
            "Thuộc một thẻ rồi thì áp dụng cho <b>tất cả các ô nhịp ghi ở cuối "
            "thẻ</b> — đó là những chỗ bấm giống hệt."
        ),
        "how_5": (
            "Xong hết tay trái mới sang tay phải. Ghép hai tay sau cùng, từng "
            "đoạn ngắn một."
        ),
        "trust_the_score": (
            "Nếu một thẻ ghi nốt không khớp với bản nhạc bạn đang cầm, tin bản "
            "nhạc — báo lại để sửa, đừng tập theo thẻ."
        ),
        "attribution": (
            "Piano Practice Engine — do Nam Le Huynh sáng tạo và phát triển. "
            "Phát hành theo giấy phép GPL-3.0-or-later."
        ),
        "why_note_density": "nhiều nốt trong thời gian ngắn",
        "why_pitch_range": "tầm âm rộng",
        "why_hand_span": "phải duỗi tay xa",
        "why_position_shifts": "tay phải đổi vị trí nhiều lần",
        "why_hand_independence": "hai tay chơi tiết tấu khác nhau",
        "rep_intro": (
            "Báo cáo này để **kiểm chứng**: mọi khẳng định đều dẫn số ô nhịp và "
            "tên nốt thật, đối chiếu được với bản nhạc giấy trong vài phút. Nếu "
            "một kiểu ghi sai nốt hoặc sai ô, engine đã phân tích sai — đừng "
            "dùng nó để luyện tập."
        ),
        "rep_stats": (
            "{notes} nốt, {measures} ô nhịp. Cắt thành {units} unit, "
            "{groups} nhóm khác nhau."
        ),
        "rep_hand_head": "{hand} — {n} kiểu trên {bars} ô nhịp",
        "rep_cycle": "**Chu kỳ {period} ô nhịp:** {order}",
        "rep_cycle_note": (
            "Khớp {agree} từ ô {first} đến ô {last}. Tập xong chu kỳ này là tập "
            "xong gần hết phần tay này."
        ),
        "rep_no_cycle": (
            "Không tìm thấy chu kỳ lặp rõ ràng — phần tay này phải học theo "
            "từng đoạn."
        ),
        "rep_family_head": "**Rút gọn về cách đánh:**",
        "rep_family_item": (
            "`{fid}`: {n} kiểu ({ids}) thật ra là **cùng một dáng tay**, chỉ "
            "đổi vị trí — phủ {covered}/{bars} ô nhịp."
        ),
        "rep_family_note": (
            "Nghĩa là học **một** cách đánh rồi chuyển vị trí tay, không phải "
            "học từng kiểu riêng."
        ),
        "rep_top4": (
            "4 kiểu phổ biến nhất phủ {covered}/{bars} ô ({pct}). Còn {rest} "
            "kiểu lẻ ở cuối."
        ),
        "rep_pattern_head": "{pid} — {count} ô nhịp ({pct})",
        "rep_notes": "Nốt",
        "rep_intervals": "Quãng từ nốt thấp nhất",
        "rep_rhythm": "Tiết tấu",
        "rep_fingering": "Ngón tay (từ bản soạn)",
        "rep_occurs": "Xuất hiện ở ô",
        "rep_more_patterns": "_(còn {n} kiểu nữa, tổng {bars} ô nhịp — xem JSON để có đủ)_",
        "rep_more_measures": "{head}, ... (+{n} ô nữa)",
        "rep_queue_head": "Thứ tự luyện tập đề xuất",
        "rep_col_unit": "unit",
        "rep_col_bars": "ô nhịp",
        "rep_col_diff": "khó",
        "rep_col_unlocks": "mở khoá",
        "rep_col_why": "vì sao khó",
        "rep_col_tech": "kỹ thuật",
        "rep_howto_head": "Cách dùng để tập",
        "rep_howto_1": (
            "Tập từng kiểu tay trái ở trên cho tới khi thuộc — đó là phần lặp "
            "lại nhiều nhất, học một lần dùng cả bài."
        ),
        "rep_howto_2": (
            "Sau đó ghép chồng lấn theo bảng thứ tự: unit 1, rồi unit 1+2, rồi "
            "1+2+3. Đừng học rời hết rồi mới nối."
        ),
        "rep_howto_3": "Bắt đầu ở 50% tốc độ, tăng 10% sau mỗi 3 lần chơi sạch.",
        "dur_whole": "nốt tròn",
        "dur_half": "nốt trắng",
        "dur_quarter": "nốt đen",
        "dur_eighth": "nốt móc đơn",
        "dur_16th": "nốt móc kép",
        "dur_even": "{n} {unit} đều",
        "dur_mixed": "{n} nốt, trường độ {list}",
        "dur_beats": "nốt {q} phách",
    },
    "en": {
        "title_suffix": "practice plan",
        "bars": "bars",
        "notes": "notes",
        "key_of": "key of {key}",
        "major": "major",
        "minor": "minor",
        "meter": "{ts} time",
        "tempo": "{bpm} bpm",
        "left_hand": "Left hand",
        "right_hand": "Right hand",
        "hand_left": "left",
        "hand_right": "right",
        "engine_hand": (
            "<b>The {loop} hand is the engine.</b> It barely changes across "
            "the whole piece ({loop_pct} new material), so drill it until you "
            "can play it without thinking. All the difficulty is in the {work} "
            "hand ({work_pct} new) — put your attention there when you put the "
            "hands together."
        ),
        "both_hands_work": (
            "Both hands change substantially — split your practice time "
            "between them."
        ),
        "chords_heading": "Chords in this piece",
        "chords_none": (
            "No chord names could be read here — the accompaniment does not "
            "spell out clear chords. Work from the keyboard diagrams instead."
        ),
        "chords_first": "This piece uses {n} chords. Learn it and you know {n}.",
        "chords_known": (
            "This piece uses {n} chords and you already know {known}. Only "
            "{new} to go."
        ),
        "form_prefix": "Form: <b>{form}</b>.",
        "form_static": (
            "This hand barely changes across the piece — learn it once."
        ),
        "form_novel": (
            "This hand almost never repeats — you will have to learn it "
            "section by section from the score."
        ),
        "form_mixed": (
            "Only {new} of {total} bars are new material; the rest are "
            "sections coming back."
        ),
        "order_easy_first": (
            "<b>Practice order, easiest first:</b> {order}. Don't play from "
            "start to finish — begin with the easiest section to build "
            "momentum."
        ),
        "groups_intro": "{n} bar groups, in the order you meet them.",
        "loop_intro": (
            "A {length}-bar loop: learn bars {range} and you unlock {n} places."
        ),
        "core_tones": "Chord tones: {notes}",
        "colour_tones": "Colour notes, safe to leave out at first: {notes}",
        "all_keys": (
            "Keys used: {notes} — chord tones could not be separated here, so "
            "learn the whole bar."
        ),
        "learn_bar": "Learn bar {bar}; it covers bars: {bars}",
        "fingering": "Fingering: {fingers}",
        "rest_heading": "Remaining passages — {n} bars",
        "rest_repeat": "{n} bars repeat but did not fit as their own card",
        "rest_once": "{n} bars appear only once",
        "rest_note": (
            "{parts}. In film themes and ballads the unrepeated stretch is "
            "usually the climax — the part most worth learning, and it has to "
            "come straight from the score."
        ),
        "map_note": (
            "One square per bar, coloured by which figure it uses. A repeating "
            "cycle shows up as stripes."
        ),
        "exercises": "Micro-exercises",
        "transitions_intro": (
            "The hard part is not any single position, it is the move between "
            "them:"
        ),
        "transition_item": (
            "<b>{a} → {b}</b> (bars {lo}–{hi}, {n} keys change): drill just "
            "the four notes around the change, back and forth, until the hand "
            "finds the position on its own."
        ),
        "block_chords": (
            "<b>Block chords:</b> instead of rolling the notes, press "
            "{chords} together. The hand learns the distances far faster this "
            "way. Try it with your eyes shut — it should find them unaided."
        ),
        "rhythm_intro": (
            "<b>Rhythm variations</b> — same notes, same fingering, only the "
            "timing changes:"
        ),
        "rhythm_long_short": "Long – short",
        "rhythm_short_long": "Short – long",
        "rhythm_pairs": "In pairs",
        "rhythm_long_short_note": "Odd notes held, even notes snapped short.",
        "rhythm_short_long_note": "The reverse. Any weak finger shows up here.",
        "rhythm_pairs_note": "Play each pair together, stop, then the next pair.",
        "overlap_intro": "<b>Overlap</b> — never stop on the last note of a chunk:",
        "overlap_item": (
            "Play bar {a} through and carry straight on into the first note of "
            "bar {b}."
        ),
        "ladder": (
            "<b>Tempo ladder:</b> {steps} bpm. Only move up a rung after three "
            "clean run-throughs at the current one."
        ),
        "hotspots": "Hotspots — drill these first",
        "hotspots_intro": (
            "Ranked by difficulty times how often the passage comes back. "
            "Clear these and the rest follows."
        ),
        "hotspot_item": "Bars {lo}–{hi} — {why}",
        "hotspot_repeat": " (recurs {n} times)",
        "how_to": "How to practise",
        "how_1": (
            "Start with the <b>first left-hand card</b> — that is where the "
            "piece opens. Press the highlighted keys in the order 1, 2, 3…"
        ),
        "how_2": (
            "Play only the <b>chord tones</b> at first. Add the colour notes "
            "once the shape is comfortable."
        ),
        "how_3": (
            "Play slowly, around half the marked tempo. Speed up after three "
            "clean run-throughs."
        ),
        "how_4": (
            "Once a card is solid, apply it to <b>every bar listed at the "
            "bottom of it</b> — those are the identical ones."
        ),
        "how_5": (
            "Finish the left hand before starting the right. Put the hands "
            "together last, a short passage at a time."
        ),
        "trust_the_score": (
            "If a card shows notes that do not match the score in front of "
            "you, trust the score — report it rather than practising the card."
        ),
        "attribution": (
            "Piano Practice Engine — created and developed by Nam Le Huynh. For "
            "questions or ideas about developing it further, contact the "
            "author directly."
        ),
        "why_note_density": "a lot of notes in a short time",
        "why_pitch_range": "a wide pitch range",
        "why_hand_span": "a wide stretch",
        "why_position_shifts": "the hand shifts position repeatedly",
        "why_hand_independence": "the hands play different rhythms",
        "rep_intro": (
            "This report exists to be **checked**: every claim cites real bar "
            "numbers and note names, so it can be verified against the printed "
            "score in a few minutes. If a figure lists the wrong notes or the "
            "wrong bars, the analysis is wrong — do not practise from it."
        ),
        "rep_stats": (
            "{notes} notes, {measures} bars. Cut into {units} units in "
            "{groups} distinct groups."
        ),
        "rep_hand_head": "{hand} — {n} figures across {bars} bars",
        "rep_cycle": "**{period}-bar cycle:** {order}",
        "rep_cycle_note": (
            "Agrees {agree} from bar {first} to bar {last}. Learn this cycle "
            "and you have learnt nearly all of this hand."
        ),
        "rep_no_cycle": (
            "No clear repeating cycle — this hand has to be learnt section by "
            "section."
        ),
        "rep_family_head": "**Reduced to hand shapes:**",
        "rep_family_item": (
            "`{fid}`: {n} figures ({ids}) are in fact **one hand shape** moved "
            "to different positions — covering {covered} of {bars} bars."
        ),
        "rep_family_note": (
            "That means learning **one** way of playing it and then moving the "
            "hand, not learning each figure separately."
        ),
        "rep_top4": (
            "The four commonest figures cover {covered} of {bars} bars ({pct}). "
            "{rest} rarer figures remain."
        ),
        "rep_pattern_head": "{pid} — {count} bars ({pct})",
        "rep_notes": "Notes",
        "rep_intervals": "Intervals above the lowest note",
        "rep_rhythm": "Rhythm",
        "rep_fingering": "Fingering (from the arrangement)",
        "rep_occurs": "Occurs in bars",
        "rep_more_patterns": "_({n} further figures, {bars} bars in total — see the JSON)_",
        "rep_more_measures": "{head}, ... (+{n} more)",
        "rep_queue_head": "Suggested practice order",
        "rep_col_unit": "unit",
        "rep_col_bars": "bars",
        "rep_col_diff": "difficulty",
        "rep_col_unlocks": "unlocks",
        "rep_col_why": "why it is hard",
        "rep_col_tech": "technique",
        "rep_howto_head": "How to use this",
        "rep_howto_1": (
            "Drill each left-hand figure above until it is solid — it is the "
            "most repeated material, learnt once and used throughout."
        ),
        "rep_howto_2": (
            "Then join them with overlap, following the order table: unit 1, "
            "then units 1+2, then 1+2+3. Do not learn them all separately and "
            "join at the end."
        ),
        "rep_howto_3": "Start at 50% tempo, add 10% after every three clean runs.",
        "dur_whole": "whole notes",
        "dur_half": "half notes",
        "dur_quarter": "quarter notes",
        "dur_eighth": "eighth notes",
        "dur_16th": "sixteenth notes",
        "dur_even": "{n} even {unit}",
        "dur_mixed": "{n} notes, durations {list}",
        "dur_beats": "{q}-beat notes",
    },
}


def resolve(lang: str | None) -> str:
    """Explicit flag, then shell locale, then Vietnamese."""
    if lang and lang in STRINGS:
        return lang
    env = (os.environ.get("LANG") or os.environ.get("LC_ALL") or "")[:2].lower()
    return env if env in STRINGS else DEFAULT


class Translator:
    """Look up a string, optionally in both languages at once.

    Bilingual mode exists for the verification report: it is read by
    whoever is checking the analysis against a printed score, and lives
    in a public repository where that person may not read Vietnamese.
    Short labels are joined inline; longer prose gets the second language
    on its own italic line, because a wall of slash-separated sentences
    is worse than either language alone.
    """

    INLINE_LIMIT = 60

    def __init__(self, lang: str | None = None, bilingual: bool = False) -> None:
        self.lang = resolve(None if lang == "bi" else lang)
        self.bilingual = bilingual or lang == "bi"
        self._table = STRINGS[self.lang]
        self._fallback = STRINGS[DEFAULT]
        self._other = STRINGS["en" if self.lang != "en" else "vi"]

    def __call__(self, name: str, **kw) -> str:
        # The positional parameter shadows any format placeholder of the
        # same name, so `key` and `unit` are deliberately avoided here.
        text = self._table.get(name) or self._fallback.get(name) or name
        out = text.format(**kw) if kw else text
        if not self.bilingual:
            return out
        alt = self._other.get(name)
        if not alt or alt == text:
            return out
        alt = alt.format(**kw) if kw else alt
        if len(out) <= self.INLINE_LIMIT and len(alt) <= self.INLINE_LIMIT:
            return f"{out} / {alt}"
        return f"{out}\n\n*{alt}*"
