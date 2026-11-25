"""Command-line interface.

Examples::

    neuroscore template -o my_patients.csv
    neuroscore score data/example_patients.csv -o results.csv
    neuroscore score data/example_patients.csv --norms norms/demo_norms.json \
        -o results.csv --reports reports/
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import pandas as pd

from .instruments import REGISTRY
from .norms import NormSet
from .report import patient_report
from .scoring import score_table, template_columns


def _cmd_template(args: argparse.Namespace) -> int:
    instruments = _select(args.instruments)
    pd.DataFrame(columns=template_columns(instruments)).to_csv(args.output, index=False)
    print(f"Empty input template written to {args.output}")
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    df = pd.read_csv(args.input, sep=None, engine="python")  # accepts ',' or ';'
    norms = None
    if args.norms:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            norms = NormSet.from_json(args.norms)
        for w in caught:
            print(f"WARNING: {w.message}", file=sys.stderr)

    results = score_table(df, _select(args.instruments), norms)
    results.to_csv(args.output, index=False)
    print(f"Scored {len(results)} patients -> {args.output}")

    errors = [c for c in results.columns if c.endswith("_error")]
    n_err = int(results[errors].notna().any(axis=1).sum()) if errors else 0
    if n_err:
        print(f"{n_err} patient(s) with errors: see the *_error columns.", file=sys.stderr)

    if args.reports:
        out_dir = Path(args.reports)
        out_dir.mkdir(parents=True, exist_ok=True)
        for record in results.to_dict(orient="records"):
            pid = str(record.get("patient_id", "patient"))
            (out_dir / f"{pid}.md").write_text(patient_report(record), encoding="utf-8")
        print(f"Reports written to {out_dir}/")
    return 0


def _select(names: list[str] | None):
    if not names:
        return list(REGISTRY.values())
    unknown = set(names) - set(REGISTRY)
    if unknown:
        raise SystemExit(f"Unknown instrument(s): {', '.join(sorted(unknown))}. Available: {', '.join(REGISTRY)}")
    return [REGISTRY[n] for n in names]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="neuroscore", description="Automatic scoring of neuropsychological tests.")
    sub = parser.add_subparsers(dest="command", required=True)

    t = sub.add_parser("template", help="write an empty CSV with all input columns")
    t.add_argument("-o", "--output", default="template.csv")
    t.add_argument("-i", "--instruments", nargs="+", help=f"subset of: {', '.join(REGISTRY)}")
    t.set_defaults(func=_cmd_template)

    s = sub.add_parser("score", help="score a CSV of patients")
    s.add_argument("input", help="CSV file, one row per patient")
    s.add_argument("-o", "--output", default="results.csv")
    s.add_argument("-n", "--norms", help="JSON file with normative data")
    s.add_argument("-r", "--reports", help="folder for one Markdown report per patient")
    s.add_argument("-i", "--instruments", nargs="+", help=f"subset of: {', '.join(REGISTRY)}")
    s.set_defaults(func=_cmd_score)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
