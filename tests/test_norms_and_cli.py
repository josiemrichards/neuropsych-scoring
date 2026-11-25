import json
import math
from pathlib import Path

import pandas as pd
import pytest

from neuroscore import NormSet, score_table, template_columns
from neuroscore.cli import main
from neuroscore.norms import NormsError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "data" / "example_patients.csv"
DEMO_NORMS = ROOT / "norms" / "demo_norms.json"


def write_norms(tmp_path, entries, is_demo=False):
    path = tmp_path / "norms.json"
    path.write_text(json.dumps({"name": "test", "is_demo": is_demo, "norms": entries}))
    return path


def regression_entry(**kw):
    entry = {
        "instrument": "moca", "score": "total", "range": [0, 30], "clip": True,
        "correction": {"type": "regression", "terms": [
            {"variable": "age", "transform": "identity", "coef": -0.1, "center": 60},
            {"variable": "education_years", "transform": "identity", "coef": 0.5, "center": 10},
        ]},
        "equivalent_scores": [17, 19, 21, 23],
    }
    entry.update(kw)
    return entry


# ------------------------------------------------------------ adjustment
def test_regression_adjustment_formula(tmp_path):
    norms = NormSet.from_json(write_norms(tmp_path, [regression_entry()]))
    # age 70: -(-0.1 * 10) = +1 ; edu 6: -(0.5 * -4) = +2  -> +3
    r = norms.apply("moca_total", 20, {"age": 70, "education_years": 6})
    assert r.adjustment == 3
    assert r.adjusted == 23
    assert r.equivalent_score == 3


def test_regression_with_transforms(tmp_path):
    entry = regression_entry(correction={"type": "regression", "terms": [
        {"variable": "age", "transform": "log100minus", "coef": 2.0, "center": 0.0},
    ]}, clip=False)
    norms = NormSet.from_json(write_norms(tmp_path, [entry]))
    r = norms.apply("moca_total", 20, {"age": 50})
    assert r.adjusted == round(20 - 2.0 * math.log(50), 2)


def test_clipping_keeps_score_in_range(tmp_path):
    norms = NormSet.from_json(write_norms(tmp_path, [regression_entry()]))
    r = norms.apply("moca_total", 30, {"age": 90, "education_years": 0})
    assert r.adjusted == 30
    assert r.equivalent_score == 4


def test_table_adjustment(tmp_path):
    entry = regression_entry(correction={
        "type": "table",
        "age_bands": [[50, 69], [70, 89]],
        "education_bands": [[0, 7], [8, 30]],
        "values": [[1.0, 0.0], [2.5, 1.0]],
    })
    norms = NormSet.from_json(write_norms(tmp_path, [entry]))
    assert norms.apply("moca_total", 20, {"age": 75, "education_years": 5}).adjusted == 22.5
    assert norms.apply("moca_total", 20, {"age": 55, "education_years": 13}).adjusted == 20
    with pytest.raises(NormsError, match="outside the normative bands"):
        norms.apply("moca_total", 20, {"age": 30, "education_years": 13})


@pytest.mark.parametrize("score, es", [(16, 0), (17, 0), (17.5, 1), (19, 1), (20, 2), (22, 3), (23, 3), (23.1, 4)])
def test_equivalent_score_boundaries_are_inclusive(tmp_path, score, es):
    entry = regression_entry(correction={"type": "none"}, clip=False)
    norms = NormSet.from_json(write_norms(tmp_path, [entry]))
    assert norms.apply("moca_total", score, {}).equivalent_score == es


def test_lower_is_better(tmp_path):
    entry = regression_entry(score="errors", correction={"type": "none"},
                             lower_is_better=True, equivalent_scores=[10, 8, 6, 4])
    norms = NormSet.from_json(write_norms(tmp_path, [entry]))
    assert norms.apply("moca_errors", 12, {}).equivalent_score == 0
    assert norms.apply("moca_errors", 7, {}).equivalent_score == 2
    assert norms.apply("moca_errors", 2, {}).equivalent_score == 4


def test_cutoffs_must_be_ordered(tmp_path):
    with pytest.raises(NormsError, match="increasing"):
        NormSet.from_json(write_norms(tmp_path, [regression_entry(equivalent_scores=[17, 21, 19, 23])]))


def test_missing_demographics_raises(tmp_path):
    norms = NormSet.from_json(write_norms(tmp_path, [regression_entry()]))
    with pytest.raises(NormsError, match="'education_years' is required"):
        norms.apply("moca_total", 20, {"age": 70})


def test_demo_norms_emit_warning():
    with pytest.warns(UserWarning, match="DEMO"):
        NormSet.from_json(DEMO_NORMS)


# ---------------------------------------------------------- batch + CLI
def test_example_file_end_to_end():
    with pytest.warns(UserWarning):
        norms = NormSet.from_json(DEMO_NORMS)
    df = pd.read_csv(EXAMPLE)
    results = score_table(df, norms=norms).set_index("patient_id")

    assert results.loc["SIM001", "moca_total"] == 29
    assert results.loc["SIM005", "mmse_total"] == 30
    assert results.loc["SIM004", "ravlt_total"] == 16
    # SIM007 has an invalid repetition score (4 > 2) and no other tests
    assert "moca_repetition=4" in results.loc["SIM007", "moca_error"]
    assert pd.isna(results.loc["SIM007", "mmse_total"])
    # every scored total got an equivalent score
    scored = results["moca_total"].notna()
    assert results.loc[scored, "moca_total_es"].between(0, 4).all()
    assert results["norms"].str.contains("DEMO").all()


def test_template_contains_all_columns():
    cols = template_columns()
    assert cols[:4] == ["patient_id", "age", "education_years", "sex"]
    assert "moca_serial7_correct" in cols and "moca_serial7" not in cols  # computed items are not inputs
    assert "ravlt_recog_fp" in cols


def test_cli_score_writes_csv_and_reports(tmp_path, capsys):
    out = tmp_path / "results.csv"
    reports = tmp_path / "reports"
    code = main(["score", str(EXAMPLE), "-n", str(DEMO_NORMS), "-o", str(out), "-r", str(reports)])
    assert code == 0
    assert len(pd.read_csv(out)) == 7
    report = (reports / "SIM002.md").read_text()
    assert "Montreal Cognitive Assessment" in report
    assert "DEMO" in report
    assert "Not scored" in (reports / "SIM007.md").read_text()
    assert "WARNING" in capsys.readouterr().err


def test_cli_semicolon_csv(tmp_path):
    src = tmp_path / "semicolon.csv"
    pd.read_csv(EXAMPLE).head(2).to_csv(src, sep=";", index=False)
    out = tmp_path / "out.csv"
    assert main(["score", str(src), "-o", str(out)]) == 0
    assert list(pd.read_csv(out)["moca_total"]) == [29, 16]
