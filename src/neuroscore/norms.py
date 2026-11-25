"""Normative adjustment and equivalent scores.

Italian neuropsychological norms usually follow the same two-step logic
(Capitani & Laiacona, 1997):

1. **Adjustment.** The raw score is corrected for age, education and
   sometimes sex, either with a regression formula or with a correction grid
   (age band x education band).
2. **Equivalent scores (ES, 0-4).** The adjusted score is compared with four
   cut-offs: ES 0 means at or below the outer tolerance limit (impaired),
   ES 4 means at or above the median of the normative sample.

This module implements both steps *generically*. The actual coefficients and
cut-offs live in a JSON file, so they can be copied from the original
publication without touching the code. See ``norms/README.md`` for the file
format.

Nothing in this module contains real normative values.
"""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping

TRANSFORMS: dict[str, Callable[[float], float]] = {
    "identity": lambda x: x,
    "log": math.log,
    "sqrt": math.sqrt,
    "square": lambda x: x * x,
    "log100minus": lambda x: math.log(100 - x),
}

ES_LABELS = {
    0: "impaired",
    1: "borderline",
    2: "within normal limits",
    3: "within normal limits",
    4: "within normal limits",
}


class NormsError(ValueError):
    """Raised when a norms file is malformed or demographics are missing."""


@dataclass
class NormEntry:
    instrument: str
    score: str
    correction: dict
    equivalent_scores: list[float]
    source: str = ""
    score_range: tuple[float, float] | None = None
    clip: bool = False
    lower_is_better: bool = False
    decimals: int = 2

    # ---------------------------------------------------------- adjustment
    def adjustment(self, demographics: Mapping[str, float]) -> float:
        """Amount to add to the raw score."""
        kind = self.correction.get("type")
        if kind == "none":
            return 0.0
        if kind == "regression":
            return self._regression_adjustment(demographics)
        if kind == "table":
            return self._table_adjustment(demographics)
        raise NormsError(f"{self.key}: unknown correction type '{kind}'")

    def _regression_adjustment(self, demographics: Mapping[str, float]) -> float:
        # Adjusted = raw - sum(coef * (transform(x) - center))
        total = 0.0
        for term in self.correction["terms"]:
            var = term["variable"]
            x = _require(demographics, var, self.key)
            transform = TRANSFORMS.get(term.get("transform", "identity"))
            if transform is None:
                raise NormsError(f"{self.key}: unknown transform '{term['transform']}'")
            total += term["coef"] * (transform(x) - term.get("center", 0.0))
        return -total

    def _table_adjustment(self, demographics: Mapping[str, float]) -> float:
        age = _require(demographics, "age", self.key)
        edu = _require(demographics, "education_years", self.key)
        row = _band_index(self.correction["age_bands"], age, "age", self.key)
        col = _band_index(self.correction["education_bands"], edu, "education_years", self.key)
        return float(self.correction["values"][row][col])

    # ------------------------------------------------------ equivalent score
    def equivalent_score(self, adjusted: float) -> int:
        cuts = self.equivalent_scores
        for es, cut in enumerate(cuts):
            if (adjusted >= cut) if self.lower_is_better else (adjusted <= cut):
                return es
        return 4

    @property
    def key(self) -> str:
        return f"{self.instrument}_{self.score}"


@dataclass
class NormResult:
    raw: float
    adjustment: float
    adjusted: float
    equivalent_score: int
    classification: str


@dataclass
class NormSet:
    name: str
    entries: dict[str, NormEntry] = field(default_factory=dict)
    is_demo: bool = False

    @classmethod
    def from_json(cls, path: str | Path) -> "NormSet":
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        norm_set = cls(name=data.get("name", Path(path).stem), is_demo=bool(data.get("is_demo", False)))
        for raw in data["norms"]:
            entry = NormEntry(
                instrument=raw["instrument"],
                score=raw["score"],
                correction=raw.get("correction", {"type": "none"}),
                equivalent_scores=list(raw["equivalent_scores"]),
                source=raw.get("source", ""),
                score_range=tuple(raw["range"]) if "range" in raw else None,
                clip=bool(raw.get("clip", False)),
                lower_is_better=bool(raw.get("lower_is_better", False)),
                decimals=int(raw.get("decimals", 2)),
            )
            _check_entry(entry)
            norm_set.entries[entry.key] = entry
        if norm_set.is_demo:
            warnings.warn(
                f"Norm set '{norm_set.name}' contains DEMO values: results are not valid for clinical use.",
                stacklevel=2,
            )
        return norm_set

    def apply(self, column: str, raw: float, demographics: Mapping[str, float]) -> NormResult | None:
        """Adjust ``raw`` and assign an equivalent score; ``None`` if no norms exist."""
        entry = self.entries.get(column)
        if entry is None:
            return None
        adj = entry.adjustment(demographics)
        adjusted = raw + adj
        if entry.clip and entry.score_range is not None:
            lo, hi = entry.score_range
            adjusted = min(max(adjusted, lo), hi)
        adjusted = round(adjusted, entry.decimals)
        es = entry.equivalent_score(adjusted)
        return NormResult(raw, round(adj, entry.decimals), adjusted, es, ES_LABELS[es])


# --------------------------------------------------------------------- utils
def _require(demographics: Mapping[str, float], var: str, key: str) -> float:
    value = demographics.get(var)
    if value is None or (isinstance(value, float) and math.isnan(value)):
        raise NormsError(f"{key}: '{var}' is required for the normative adjustment")
    return float(value)


def _band_index(bands: list[list[float]], value: float, var: str, key: str) -> int:
    for i, (lo, hi) in enumerate(bands):
        if lo <= value <= hi:
            return i
    raise NormsError(f"{key}: {var}={value:g} is outside the normative bands")


def _check_entry(entry: NormEntry) -> None:
    cuts = entry.equivalent_scores
    if len(cuts) != 4:
        raise NormsError(f"{entry.key}: 'equivalent_scores' needs exactly 4 cut-offs (ES0-ES3)")
    ordered = sorted(cuts, reverse=entry.lower_is_better)
    if cuts != ordered:
        direction = "decreasing" if entry.lower_is_better else "increasing"
        raise NormsError(f"{entry.key}: equivalent score cut-offs must be {direction}")
