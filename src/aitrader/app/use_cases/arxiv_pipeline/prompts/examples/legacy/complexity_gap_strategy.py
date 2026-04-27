"""复杂度缺口风控（瘦身版本）。"""
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aitrader.research.baselines.baseline_spec import BaselineSpec
from aitrader.research.baselines import (
    buy_and_hold_weights,
    momentum_topk_weights,
    equal_weight_universe_weights,
)
from aitrader.research.data.dynamic_universe import UniverseSpec
from aitrader.research.runner import (
    RebalanceSpec,
    StrategySpec,
    TrainHoldoutWindow,
    run_research,
)

from select_fn import select_complexity_gap  # type: ignore


PAPER_ID = "2604.19107"
PAPER_TITLE = (
    "Structural Dynamics of G5 Stock Markets During Exogenous Shocks: "
    "A Random Matrix Theory-Based Complexity Gap Approach"
)
STRATEGY_NAME = "复杂度缺口风控（rebalance 点计算 + 风控/多头解耦）"
OUTPUT_DIR = Path(__file__).parent

DEFAULT_PARAMS = {
    "gap_window": 60,
    "momentum_lookback": 60,
    "risk_off_q": 0.35,
    "risk_on_q": 0.55,
    "history_window": 126,
    "min_history": 52,
    "top_k": 15,
    "full_weight": 1.0,
    "half_weight": 0.5,
}


def build_spec() -> StrategySpec:
    return StrategySpec(
        paper_id=PAPER_ID,
        paper_title=PAPER_TITLE,
        strategy_name=STRATEGY_NAME,
        methodology=(
            "60 日相关矩阵复杂度缺口（仅 rebalance 点计算）→ 多档风控仓位 → 60 日动量 Top-15"
        ),
        universe_spec=UniverseSpec(
            top_n=120,
            min_data_days=750,
            min_close=3.0,
            snapshot_window_days=45,
            refresh_freq="Q",
        ),
        rebalance=RebalanceSpec(freq="W", warmup_days=100, max_single_weight=0.20),
        select_fn=select_complexity_gap,
        select_params=dict(DEFAULT_PARAMS),
        notes=[
            "论文结论：复杂度缺口在外生冲击期会塌缩，预示组合波动。",
            "本次实现：风控开关与多头篮子解耦；缺口仅在调仓日算，复杂度从 O(T²) 降到 O(T)。",
            "已修复：look-ahead 选池 / O(T²) 计算 / 二元开关 / T+1 / 涨跌停 / 现金利率。",
        ],
        param_grid={
            "gap_window": [60, 120],
            "risk_off_q": [0.20, 0.35],
            "risk_on_q": [0.55, 0.70],
        },
        param_grid_filter=lambda c: c["risk_off_q"] < c["risk_on_q"],
        train_holdout=TrainHoldoutWindow(),
    )


def main() -> None:
    spec = build_spec()
    baselines = [
        BaselineSpec(
            name="buy_and_hold_top30",
            builder=buy_and_hold_weights,
            kwargs={"top_n": 30},
        ),
        BaselineSpec(
            name="momentum_top15_60d",
            builder=momentum_topk_weights,
            kwargs={"lookback_days": 60, "top_k": 15},
        ),
        BaselineSpec(
            name="equal_weight_universe",
            builder=equal_weight_universe_weights,
        ),
    ]
    run_research(spec, output_dir=OUTPUT_DIR, baselines=baselines)


if __name__ == "__main__":
    main()
