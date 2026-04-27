"""通用研究 runner。"""

from .specs import (
    RebalanceSpec,
    SelectFnContext,
    StrategySpec,
    TrainHoldoutWindow,
    SelectionResult,
)
from .splitter import split_by_window
from .aggregator import aggregate_processed, render_comparison
from .grid_ablation import run_grid_ablation
from .run_research import ResearchOutcome, run_research

__all__ = [
    "RebalanceSpec",
    "SelectFnContext",
    "StrategySpec",
    "TrainHoldoutWindow",
    "SelectionResult",
    "split_by_window",
    "run_grid_ablation",
    "run_research",
    "ResearchOutcome",
    "aggregate_processed",
    "render_comparison",
]
