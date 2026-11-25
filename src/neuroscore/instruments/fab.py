"""Frontal Assessment Battery (FAB; Dubois et al., 2000).

Six subtests scored 0-3 (total 0-18). Lexical fluency is entered as the
number of valid words produced and converted to points:
more than 9 -> 3, 6-9 -> 2, 3-5 -> 1, fewer than 3 -> 0.
"""

from __future__ import annotations

from .base import Instrument, Item


def fluency_points(words: float) -> float:
    """Convert the number of words in FAB lexical fluency to points (0-3)."""
    if words > 9:
        return 3
    if words >= 6:
        return 2
    if words >= 3:
        return 1
    return 0


class FAB(Instrument):
    name = "fab"
    full_name = "Frontal Assessment Battery"
    items = (
        Item("similarities", "Similarities", 0, 3, "conceptualization"),
        Item("fluency_words", "Lexical fluency: number of words", 0, 99, "mental_flexibility", in_total=False),
        Item("fluency", "Lexical fluency (points)", 0, 3, "mental_flexibility", computed=True),
        Item("motor_series", "Motor series (Luria)", 0, 3, "motor_programming"),
        Item("conflicting", "Conflicting instructions", 0, 3, "interference_sensitivity"),
        Item("go_nogo", "Go-No Go", 0, 3, "inhibitory_control"),
        Item("prehension", "Prehension behaviour", 0, 3, "environmental_autonomy"),
    )

    def preprocess(self, values: dict[str, float]) -> dict[str, float]:
        values["fluency"] = fluency_points(values["fluency_words"])
        return values
