"""Mini-Mental State Examination (MMSE; Folstein et al., 1975).

Items are entered as points per section. The attention section accepts the
score of either serial 7s or spelling "WORLD" backwards (0-5), according to
the version used in your setting.
"""

from __future__ import annotations

from .base import Instrument, Item


class MMSE(Instrument):
    name = "mmse"
    full_name = "Mini-Mental State Examination"
    items = (
        Item("orientation_time", "Orientation to time", 0, 5, "orientation"),
        Item("orientation_place", "Orientation to place", 0, 5, "orientation"),
        Item("registration", "Registration (3 words)", 0, 3, "registration"),
        Item("attention", "Attention and calculation", 0, 5, "attention"),
        Item("recall", "Recall (3 words)", 0, 3, "recall"),
        Item("naming", "Naming", 0, 2, "language"),
        Item("repetition", "Repetition", 0, 1, "language"),
        Item("command", "Three-stage command", 0, 3, "language"),
        Item("reading", "Reading", 0, 1, "language"),
        Item("writing", "Writing", 0, 1, "language"),
        Item("copying", "Copying pentagons", 0, 1, "visuoconstruction"),
    )
