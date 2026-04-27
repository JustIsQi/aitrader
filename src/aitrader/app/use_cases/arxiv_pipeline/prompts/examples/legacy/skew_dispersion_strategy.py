"""偏度分散度择时（瘦身版本）。

策略主体已迁移到 `select_fn.py`，本文件只声明配置 + 调用统一 runner。
"""
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

from select_fn import select_skew_dispersion  # type: ignore


PAPER_ID = "2604.07870"
PAPER_TITLE = "Skewness Dispersion and Stock Market Returns"
STRATEGY_NAME = "偏度分散度择时（信号池/持仓池解耦版）"
OUTPUT_DIR = Path(__file__).parent

DEFAULT_PARAMS = {
    "skew_window": 20,
    "smooth_window": 5,
    "risk_on_q": 0.45,
    "risk_off_q": 0.70,
    "history_window": 252,
    "min_history": 126,
    "holding_top_n": 30,
    "on_weight": 1.0,
    "half_weight": 0.5,
}


def build_spec() -> StrategySpec:
    return StrategySpec(
        paper_id=PAPER_ID,
        paper_title=PAPER_TITLE,
        strategy_name=STRATEGY_NAME,
        methodology=(
            "宽口径动态池估计偏度横截面 std → 月频多档仓位 → 持仓池前 30 只主板高流动性股票"
        ),
        universe_spec=UniverseSpec(
            top_n=120,
            min_data_days=750,
            min_close=3.0,
            snapshot_window_days=45,
            refresh_freq="Q",
        ),
        rebalance=RebalanceSpec(freq="M", warmup_days=140, max_single_weight=0.20),
        select_fn=select_skew_dispersion,
        select_params=dict(DEFAULT_PARAMS),
        notes=[
            "论文发现：偏度分散度越高，未来市场回报越弱。",
            "本次实现：信号池=动态池前 120 只，持仓池=前 30 只；多档仓位（满/半/空）。",
            "已修复：look-ahead 选池 / T+1 时序 / 涨跌停回退 / 现金利率 / 分项交易成本。",
        ],
        param_grid={
            "skew_window": [20, 60],
            "risk_on_q": [0.30, 0.45, 0.60],
            "risk_off_q": [0.55, 0.70, 0.85],
        },
        param_grid_filter=lambda c: c["risk_on_q"] < c["risk_off_q"],
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
