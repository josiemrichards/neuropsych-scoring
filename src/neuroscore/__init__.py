"""neuroscore - automatic scoring of neuropsychological screening tests."""

from .instruments import FAB, MMSE, RAVLT, REGISTRY, MoCA, ScoringError
from .norms import NormSet
from .scoring import score_row, score_table, template_columns

__version__ = "0.1.0"

__all__ = [
    "FAB", "MMSE", "MoCA", "RAVLT", "REGISTRY", "ScoringError",
    "NormSet", "score_row", "score_table", "template_columns",
]
