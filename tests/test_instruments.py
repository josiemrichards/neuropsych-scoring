import math

import pytest

from neuroscore import FAB, MMSE, RAVLT, MoCA, ScoringError
from neuroscore.instruments.fab import fluency_points
from neuroscore.instruments.moca import serial7_points


def moca_row(**overrides):
    row = {
        "moca_trail": 1, "moca_cube": 1, "moca_clock_contour": 1, "moca_clock_numbers": 1,
        "moca_clock_hands": 1, "moca_naming": 3, "moca_digits_forward": 1, "moca_digits_backward": 1,
        "moca_letters_errors": 0, "moca_serial7_correct": 5, "moca_repetition": 2,
        "moca_fluency_words": 15, "moca_abstraction": 2, "moca_delayed_recall": 5, "moca_orientation": 6,
    }
    row.update(overrides)
    return row


# ----------------------------------------------------------------- MoCA
def test_moca_perfect_score_is_30():
    result = MoCA().score(moca_row())
    assert result.total == 30
    assert result.max_total == 30
    assert result.subscores == {
        "visuospatial_executive": 5, "naming": 3, "attention": 6,
        "language": 3, "abstraction": 2, "delayed_recall": 5, "orientation": 6,
    }


@pytest.mark.parametrize("correct, points", [(5, 3), (4, 3), (3, 2), (2, 2), (1, 1), (0, 0)])
def test_moca_serial7_conversion(correct, points):
    assert serial7_points(correct) == points


def test_moca_conversions_of_raw_counts():
    result = MoCA().score(moca_row(moca_letters_errors=2, moca_serial7_correct=3, moca_fluency_words=10))
    assert result.items["letters"] == 0
    assert result.items["serial7"] == 2
    assert result.items["fluency"] == 0
    assert result.subscores["attention"] == 4
    assert result.total == 30 - 1 - 1 - 1


def test_moca_one_letter_error_still_scores():
    assert MoCA().score(moca_row(moca_letters_errors=1)).items["letters"] == 1


def test_moca_education_adjustment_is_separate_from_raw_total():
    low = MoCA().score(moca_row(moca_delayed_recall=2), education_years=8)
    assert low.total == 27
    assert low.derived["total_plus_edu_point"] == 28
    high = MoCA().score(moca_row(moca_delayed_recall=2), education_years=13)
    assert high.derived["total_plus_edu_point"] == 27


def test_moca_education_adjustment_never_exceeds_30():
    assert MoCA().score(moca_row(), education_years=5).derived["total_plus_edu_point"] == 30


def test_moca_out_of_range_item_raises():
    with pytest.raises(ScoringError, match="moca_repetition=3"):
        MoCA().score(moca_row(moca_repetition=3))


def test_moca_missing_item_raises():
    row = moca_row()
    del row["moca_orientation"]
    with pytest.raises(ScoringError, match="missing items moca_orientation"):
        MoCA().score(row)


def test_non_integer_item_raises():
    with pytest.raises(ScoringError, match="whole number"):
        MoCA().score(moca_row(moca_naming=2.5))


def test_text_item_raises():
    with pytest.raises(ScoringError, match="not a number"):
        MoCA().score(moca_row(moca_naming="tre"))


# ----------------------------------------------------------------- MMSE
def test_mmse_total_and_domains():
    row = {
        "mmse_orientation_time": 4, "mmse_orientation_place": 5, "mmse_registration": 3,
        "mmse_attention": 3, "mmse_recall": 1, "mmse_naming": 2, "mmse_repetition": 1,
        "mmse_command": 3, "mmse_reading": 1, "mmse_writing": 1, "mmse_copying": 0,
    }
    result = MMSE().score(row)
    assert result.total == 24
    assert result.max_total == 30
    assert result.subscores["orientation"] == 9
    assert result.subscores["language"] == 8
    assert result.subscores["visuoconstruction"] == 0


# ------------------------------------------------------------------ FAB
@pytest.mark.parametrize("words, points", [(15, 3), (10, 3), (9, 2), (6, 2), (5, 1), (3, 1), (2, 0), (0, 0)])
def test_fab_fluency_conversion(words, points):
    assert fluency_points(words) == points


def test_fab_total():
    row = {"fab_similarities": 2, "fab_fluency_words": 7, "fab_motor_series": 3,
           "fab_conflicting": 2, "fab_go_nogo": 1, "fab_prehension": 3}
    result = FAB().score(row)
    assert result.total == 2 + 2 + 3 + 2 + 1 + 3
    assert result.max_total == 18


# ---------------------------------------------------------------- RAVLT
def ravlt_row(**overrides):
    row = {"ravlt_t1": 5, "ravlt_t2": 7, "ravlt_t3": 9, "ravlt_t4": 10, "ravlt_t5": 12,
           "ravlt_tb": 4, "ravlt_t6": 10, "ravlt_delayed": 9}
    row.update(overrides)
    return row


def test_ravlt_immediate_total_and_derived_measures():
    result = RAVLT().score(ravlt_row())
    assert result.total == 43
    assert result.max_total == 75
    d = result.derived
    assert d["delayed_recall"] == 9
    assert d["best_trial"] == 12
    assert d["learning_t5_minus_t1"] == 7
    assert d["proactive_interference_t1_minus_tb"] == 1
    assert d["retroactive_interference_t5_minus_t6"] == 2
    assert d["forgetting_t5_minus_delayed"] == 3
    assert d["percent_retention"] == 75.0
    assert "recognition_accuracy" not in d


def test_ravlt_recognition_optional():
    result = RAVLT().score(ravlt_row(ravlt_recog_hits=13, ravlt_recog_fp=2))
    assert result.derived["recognition_accuracy"] == 11


def test_ravlt_incomplete_recognition_is_noted_not_fatal():
    result = RAVLT().score(ravlt_row(ravlt_recog_hits=13))
    assert "recognition incomplete" in result.notes[0]
    assert result.total == 43


def test_ravlt_zero_trial5_retention_is_nan():
    result = RAVLT().score(ravlt_row(ravlt_t5=0, ravlt_delayed=0))
    assert math.isnan(result.derived["percent_retention"])
