"""基准策略库（用于和论文复现的策略做横向对比）。"""

from .buy_and_hold import buy_and_hold_weights
from .momentum_topk import momentum_topk_weights
from .equal_weight_universe import equal_weight_universe_weights
from .baseline_spec import BaselineSpec, build_baseline_targets

__all__ = [
    "BaselineSpec",
    "buy_and_hold_weights",
    "momentum_topk_weights",
    "equal_weight_universe_weights",
    "build_baseline_targets",
]
