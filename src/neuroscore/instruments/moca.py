"""Montreal Cognitive Assessment (MoCA), version 7.x.

Scoring follows the official MoCA administration and scoring instructions
(Nasreddine et al., 2005). Three tasks are entered as *raw performance* and
converted to points automatically, because that is where hand-scoring errors
happen most often:

* ``letters_errors``  - number of errors in the letter-tapping task
  (1 point if errors <= 1)
* ``serial7_correct`` - number of correct subtractions out of 5
  (4-5 -> 3 points, 2-3 -> 2, 1 -> 1, 0 -> 0)
* ``fluency_words``   - number of valid F-words in one minute
  (1 point if >= 11)

The original "+1 point if education <= 12 years" rule is reported separately
as ``total_plus_edu_point`` and never overwrites the raw total, because
population norms (e.g. the Italian ones) apply their own education
correction to the raw score.
"""

from __future__ import annotations

from .base import Instrument, Item, ScoreResult


def serial7_points(correct: float) -> float:
    """Convert the number of correct serial-7 subtractions (0-5) to points."""
    if correct >= 4:
        return 3
    if correct >= 2:
        return 2
    if correct == 1:
        return 1
    return 0


class MoCA(Instrument):
    name = "moca"
    full_name = "Montreal Cognitive Assessment"
    items = (
        # Visuospatial / executive (5)
        Item("trail", "Alternating trail making", 0, 1, "visuospatial_executive"),
        Item("cube", "Cube copy", 0, 1, "visuospatial_executive"),
        Item("clock_contour", "Clock: contour", 0, 1, "visuospatial_executive"),
        Item("clock_numbers", "Clock: numbers", 0, 1, "visuospatial_executive"),
        Item("clock_hands", "Clock: hands", 0, 1, "visuospatial_executive"),
        # Naming (3)
        Item("naming", "Animal naming", 0, 3, "naming"),
        # Attention (6)
        Item("digits_forward", "Digit span forward", 0, 1, "attention"),
        Item("digits_backward", "Digit span backward", 0, 1, "attention"),
        Item("letters_errors", "Letter tapping: number of errors", 0, 30, "attention", in_total=False),
        Item("letters", "Letter tapping (points)", 0, 1, "attention", computed=True),
        Item("serial7_correct", "Serial 7s: correct subtractions", 0, 5, "attention", in_total=False),
        Item("serial7", "Serial 7s (points)", 0, 3, "attention", computed=True),
        # Language (3)
        Item("repetition", "Sentence repetition", 0, 2, "language"),
        Item("fluency_words", "Verbal fluency: number of words", 0, 99, "language", in_total=False),
        Item("fluency", "Verbal fluency (points)", 0, 1, "language", computed=True),
        # Abstraction (2)
        Item("abstraction", "Abstraction", 0, 2, "abstraction"),
        # Delayed recall (5)
        Item("delayed_recall", "Delayed recall (free)", 0, 5, "delayed_recall"),
        # Orientation (6)
        Item("orientation", "Orientation", 0, 6, "orientation"),
    )

    def preprocess(self, values: dict[str, float]) -> dict[str, float]:
        values["letters"] = 1 if values["letters_errors"] <= 1 else 0
        values["serial7"] = serial7_points(values["serial7_correct"])
        values["fluency"] = 1 if values["fluency_words"] >= 11 else 0
        return values

    def postprocess(self, result: ScoreResult, **context: object) -> None:
        education = context.get("education_years")
        if education is None:
            result.notes.append("education not provided: no education adjustment")
            return
        bonus = 1 if float(education) <= 12 and result.total < 30 else 0
        result.derived["total_plus_edu_point"] = result.total + bonus
