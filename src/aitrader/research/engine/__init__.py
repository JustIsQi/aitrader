"""向量化研究回测引擎。"""

from .cost_model import AshareCostModel, CostModel, ZeroCostModel
from .position_policies import (
    PositionPolicy,
    equal_weight,
    tiered_weight,
    signal_weighted,
)
from .vectorized_simulator import (
    SimulationResult,
    VectorizedSimulator,
    simulate,
)

__all__ = [
    "AshareCostModel",
    "CostModel",
    "ZeroCostModel",
    "PositionPolicy",
    "equal_weight",
    "tiered_weight",
    "signal_weighted",
    "SimulationResult",
    "VectorizedSimulator",
    "simulate",
]
