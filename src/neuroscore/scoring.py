"""Batch scoring of a table of patients."""

from __future__ import annotations

from typing import Iterable, Mapping

import pandas as pd

from .instruments import REGISTRY, Instrument, ScoringError
from .norms import NormSet, NormsError

DEMOGRAPHIC_COLUMNS = ("patient_id", "age", "education_years", "sex")


def template_columns(instruments: Iterable[Instrument] | None = None) -> list[str]:
    """All input columns, in order: demographics first, then each instrument."""
    cols = list(DEMOGRAPHIC_COLUMNS)
    for inst in instruments or REGISTRY.values():
        cols.extend(inst.columns())
    return cols


def score_row(
    row: Mapping[str, object],
    instruments: Iterable[Instrument] | None = None,
    norms: NormSet | None = None,
) -> dict[str, object]:
    """Score every instrument present in ``row``.

    Errors are reported in ``<instrument>_error`` instead of interrupting the
    batch, so one wrong cell does not block the whole file.
    """
    out: dict[str, object] = {c: row.get(c) for c in DEMOGRAPHIC_COLUMNS if c in row}
    demographics = {
        k: _to_float(row.get(k)) for k in ("age", "education_years") if _to_float(row.get(k)) is not None
    }

    for inst in instruments or REGISTRY.values():
        if not inst.has_data(row):
            continue
        try:
            result = inst.score(row, **demographics)
        except ScoringError as exc:
            out[f"{inst.name}_error"] = str(exc)
            continue

        flat = result.as_flat_dict()
        out.update(flat)

        if norms is None:
            continue
        for column, value in flat.items():
            if not isinstance(value, (int, float)):
                continue
            try:
                norm = norms.apply(column, float(value), demographics)
            except NormsError as exc:
                out[f"{column}_norm_error"] = str(exc)
                continue
            if norm is not None:
                out[f"{column}_adjusted"] = norm.adjusted
                out[f"{column}_es"] = norm.equivalent_score
                out[f"{column}_class"] = norm.classification
    return out


def score_table(
    df: pd.DataFrame,
    instruments: Iterable[Instrument] | None = None,
    norms: NormSet | None = None,
) -> pd.DataFrame:
    """Score every row of ``df`` and return one row of results per patient."""
    instruments = list(instruments or REGISTRY.values())
    records = [score_row(r, instruments, norms) for r in df.to_dict(orient="records")]
    result = pd.DataFrame.from_records(records)
    if norms is not None:
        result["norms"] = norms.name + (" (DEMO - not for clinical use)" if norms.is_demo else "")
    return result


def _to_float(value: object) -> float | None:
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN check
