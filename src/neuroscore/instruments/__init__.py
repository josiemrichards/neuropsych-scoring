from .base import Instrument, Item, ScoreResult, ScoringError
from .fab import FAB
from .mmse import MMSE
from .moca import MoCA
from .ravlt import RAVLT

#: All available instruments, keyed by their short name.
REGISTRY: dict[str, Instrument] = {inst.name: inst for inst in (MoCA(), MMSE(), FAB(), RAVLT())}

__all__ = ["Instrument", "Item", "ScoreResult", "ScoringError", "MoCA", "MMSE", "FAB", "RAVLT", "REGISTRY"]
