"""Readable per-patient report in Markdown."""

from __future__ import annotations

from typing import Mapping

from .instruments import REGISTRY

_ES_SYMBOL = {0: "ES 0 - impaired", 1: "ES 1 - borderline", 2: "ES 2", 3: "ES 3", 4: "ES 4"}


def _fmt(value: object) -> str:
    if isinstance(value, float):
        if value != value:  # NaN
            return "-"
        return f"{value:g}"
    return "-" if value is None else str(value)


def patient_report(result: Mapping[str, object]) -> str:
    """Build a Markdown report from one row returned by ``score_row``."""
    lines = [f"# Scoring report - {result.get('patient_id', 'unknown')}", ""]
    lines.append(
        f"Age: {_fmt(result.get('age'))} | Education (years): {_fmt(result.get('education_years'))}"
        f" | Sex: {_fmt(result.get('sex'))}"
    )
    norms = result.get("norms")
    if isinstance(norms, str):
        lines.append(f"Norms: {norms}")
    lines.append("")

    for name, inst in REGISTRY.items():
        error = result.get(f"{name}_error")
        total = result.get(f"{name}_total")
        if error is None and total is None:
            continue
        lines.append(f"## {inst.full_name} ({name.upper()})")
        if isinstance(error, str):
            lines.extend([f"**Not scored:** {error}", ""])
            continue

        lines.append("| Score | Raw | Adjusted | Equivalent score |")
        lines.append("|---|---|---|---|")
        prefix = f"{name}_"
        for key, value in result.items():
            if not key.startswith(prefix) or key.endswith(("_adjusted", "_es", "_class", "_error", "_notes", "_norm_error")):
                continue
            label = key[len(prefix):]
            adjusted = result.get(f"{key}_adjusted")
            es = result.get(f"{key}_es")
            es_text = _ES_SYMBOL.get(int(es), "-") if isinstance(es, (int, float)) and es == es else "-"
            label_text = f"**{label}** / {inst.max_total:g}" if label == "total" else label
            lines.append(f"| {label_text} | {_fmt(value)} | {_fmt(adjusted)} | {es_text} |")
        notes = result.get(f"{name}_notes")
        if isinstance(notes, str):
            lines.append(f"\n_Notes: {notes}_")
        lines.append("")

    lines.append(
        "_Automatically generated. Scores must be reviewed by the clinician; "
        "the report is not a diagnosis._"
    )
    return "\n".join(lines) + "\n"
