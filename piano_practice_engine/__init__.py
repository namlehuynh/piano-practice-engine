"""Piano Practice Engine — created and developed by Nam Le Huynh.
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
from .events import NoteEvent, Slice, build_slices, parse_score
from .pipeline import analyse
from .repetition import RepetitionIndex
from .segment import Unit, Weights, segment, segment_naive

__all__ = [
    "NoteEvent", "Slice", "build_slices", "parse_score",
    "RepetitionIndex", "Unit", "Weights", "segment", "segment_naive",
    "analyse",
]
