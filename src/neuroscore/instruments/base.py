"""Core building blocks shared by every instrument.

An *instrument* (MoCA, MMSE, ...) is described declaratively as a list of
items, each with an allowed range. Scoring then becomes a generic operation:
validate every item, sum them into subscales and totals, and let the
instrument add any test-specific derived measures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping


class ScoringError(ValueError):
    """Raised when item data are missing or out of range."""


@dataclass(frozen=True)
class Item:
    """A single scored item of a test.

    Attributes:
        key: column suffix used in the input data (e.g. ``"trail"`` becomes
            ``moca_trail`` in a CSV file).
        label: human-readable description.
        min: minimum allowed value.
        max: maximum allowed value.
        domain: cognitive domain / subscale the item contributes to.
        in_total: whether the item is summed into the total score. Raw
            counts that are converted into points by the instrument (for
            example the number of words in a fluency task) use ``False``.
        computed: the item is not read from the input but calculated by the
            instrument's ``preprocess`` step from other (raw count) items.
    """

    key: str
    label: str
    min: float
    max: float
    domain: str
    in_total: bool = True
    computed: bool = False


@dataclass
class ScoreResult:
    """Output of scoring one instrument for one person."""

    instrument: str
    items: dict[str, float]
    subscores: dict[str, float]
    total: float
    max_total: float
    derived: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_flat_dict(self) -> dict[str, float | str]:
        """Return one flat ``{column: value}`` mapping, convenient for tables."""
        p = self.instrument
        out: dict[str, float | str] = {f"{p}_total": self.total}
        out.update({f"{p}_{k}": v for k, v in self.subscores.items()})
        out.update({f"{p}_{k}": v for k, v in self.derived.items()})
        if self.notes:
            out[f"{p}_notes"] = "; ".join(self.notes)
        return out


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return math.isnan(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


class Instrument:
    """Base class: subclasses set ``name``, ``full_name`` and ``items``."""

    name: str = ""
    full_name: str = ""
    items: tuple[Item, ...] = ()

    # ------------------------------------------------------------------ API
    @property
    def max_total(self) -> float:
        return sum(i.max for i in self.items if i.in_total)

    def columns(self) -> list[str]:
        """Input column names expected for this instrument."""
        return [f"{self.name}_{i.key}" for i in self.items if not i.computed]

    def has_data(self, row: Mapping[str, object]) -> bool:
        """True if at least one item of this instrument is present in ``row``."""
        return any(not _is_missing(row.get(c)) for c in self.columns())

    def score(self, row: Mapping[str, object], **context: object) -> ScoreResult:
        """Score one person.

        Args:
            row: mapping containing the item columns (``<name>_<item key>``).
            **context: optional demographic information (``age``,
                ``education_years``) used by instruments that apply a
                built-in adjustment.
        """
        values = self._read_items(row)
        values = self.preprocess(values)
        self._validate(values)

        subscores: dict[str, float] = {}
        for item in self.items:
            if item.in_total:
                subscores[item.domain] = subscores.get(item.domain, 0) + values[item.key]
        total = sum(subscores.values())

        result = ScoreResult(
            instrument=self.name,
            items=values,
            subscores=subscores,
            total=total,
            max_total=self.max_total,
        )
        self.postprocess(result, **context)
        return result

    # ------------------------------------------------------- extension hooks
    def preprocess(self, values: dict[str, float]) -> dict[str, float]:
        """Convert raw counts into item points. Override when needed."""
        return values

    def postprocess(self, result: ScoreResult, **context: object) -> None:
        """Add derived scores or built-in adjustments. Override when needed."""

    # -------------------------------------------------------------- helpers
    def _read_items(self, row: Mapping[str, object]) -> dict[str, float]:
        values: dict[str, float] = {}
        missing: list[str] = []
        for item in self.items:
            if item.computed:
                continue
            col = f"{self.name}_{item.key}"
            raw = row.get(col)
            if _is_missing(raw):
                missing.append(col)
                continue
            try:
                values[item.key] = float(raw)  # type: ignore[arg-type]
            except (TypeError, ValueError) as exc:
                raise ScoringError(f"{col}: '{raw}' is not a number") from exc
        if missing:
            raise ScoringError(
                f"{self.full_name or self.name}: missing items {', '.join(missing)}"
            )
        return values

    def _validate(self, values: dict[str, float]) -> None:
        errors = []
        for item in self.items:
            v = values[item.key]
            if not (item.min <= v <= item.max):
                errors.append(
                    f"{self.name}_{item.key}={v:g} outside [{item.min:g}, {item.max:g}]"
                )
            elif v != int(v):
                errors.append(f"{self.name}_{item.key}={v:g} must be a whole number")
        if errors:
            raise ScoringError("; ".join(errors))
