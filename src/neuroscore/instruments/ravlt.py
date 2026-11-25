"""Rey Auditory Verbal Learning Test (RAVLT, 15-word version).

Input: words recalled on trials 1-5 (list A), the interference trial (list B),
trial 6 (immediate recall of list A after interference), the delayed recall
and, optionally, recognition hits and false positives.

The "total" is the classic immediate recall score (sum of trials 1-5, 0-75).
Process measures commonly reported in the literature are added as derived
scores. Recognition is optional: leave both recognition columns empty if it
was not administered.
"""

from __future__ import annotations

from typing import Mapping

from .base import Instrument, Item, ScoreResult, _is_missing


class RAVLT(Instrument):
    name = "ravlt"
    full_name = "Rey Auditory Verbal Learning Test"
    items = (
        Item("t1", "Trial 1", 0, 15, "immediate_recall"),
        Item("t2", "Trial 2", 0, 15, "immediate_recall"),
        Item("t3", "Trial 3", 0, 15, "immediate_recall"),
        Item("t4", "Trial 4", 0, 15, "immediate_recall"),
        Item("t5", "Trial 5", 0, 15, "immediate_recall"),
        Item("tb", "Interference list B", 0, 15, "interference", in_total=False),
        Item("t6", "Trial 6 (post-interference)", 0, 15, "post_interference", in_total=False),
        Item("delayed", "Delayed recall", 0, 15, "delayed_recall", in_total=False),
    )
    optional_items = (
        Item("recog_hits", "Recognition: hits", 0, 15, "recognition", in_total=False),
        Item("recog_fp", "Recognition: false positives", 0, 35, "recognition", in_total=False),
    )

    def columns(self) -> list[str]:
        return super().columns() + [f"{self.name}_{i.key}" for i in self.optional_items]

    def score(self, row: Mapping[str, object], **context: object) -> ScoreResult:
        result = super().score(row, **context)
        self._score_recognition(row, result)
        return result

    def postprocess(self, result: ScoreResult, **context: object) -> None:
        v = result.items
        d = result.derived
        d["delayed_recall"] = v["delayed"]
        d["best_trial"] = max(v[f"t{i}"] for i in range(1, 6))
        d["learning_t5_minus_t1"] = v["t5"] - v["t1"]
        d["proactive_interference_t1_minus_tb"] = v["t1"] - v["tb"]
        d["retroactive_interference_t5_minus_t6"] = v["t5"] - v["t6"]
        d["forgetting_t5_minus_delayed"] = v["t5"] - v["delayed"]
        d["percent_retention"] = round(100 * v["delayed"] / v["t5"], 1) if v["t5"] > 0 else float("nan")

    def _score_recognition(self, row: Mapping[str, object], result: ScoreResult) -> None:
        cols = [f"{self.name}_{i.key}" for i in self.optional_items]
        present = [not _is_missing(row.get(c)) for c in cols]
        if not any(present):
            return
        if not all(present):
            result.notes.append("recognition incomplete: hits and false positives are both required")
            return
        values = {i.key: float(row[c]) for i, c in zip(self.optional_items, cols)}  # type: ignore[arg-type]
        for item in self.optional_items:
            if not item.min <= values[item.key] <= item.max:
                result.notes.append(
                    f"{self.name}_{item.key}={values[item.key]:g} outside [{item.min:g}, {item.max:g}]: recognition skipped"
                )
                return
        result.items.update(values)
        result.derived["recognition_hits"] = values["recog_hits"]
        result.derived["recognition_false_positives"] = values["recog_fp"]
        result.derived["recognition_accuracy"] = values["recog_hits"] - values["recog_fp"]
