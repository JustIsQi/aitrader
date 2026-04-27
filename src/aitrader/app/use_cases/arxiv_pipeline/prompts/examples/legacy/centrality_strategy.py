"""网络中心性选股（瘦身版本）。"""
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

from select_fn import select_centrality  # type: ignore


PAPER_ID = "2604.12197"
PAPER_TITLE = "Emergence of Statistical Financial Factors by a Diffusion Process"
STRATEGY_NAME = "网络中心性选股（Perron + 行业中性可选）"
OUTPUT_DIR = Path(__file__).parent

DEFAULT_PARAMS = {
    "corr_window": 60,
    "centrality_weight": 0.5,
    "edge_quantile": 0.60,
    "momentum_lookback": 20,
    "top_k": 12,
    "industry_neutralize": False,
    "min_network_size": 12,
}


def build_spec() -> StrategySpec:
    return StrategySpec(
        paper_id=PAPER_ID,
        paper_title=PAPER_TITLE,
        strategy_name=STRATEGY_NAME,
        methodology=(
            "60日相关网络 → Perron 特征向量中心性 + 20日动量 → 周频等权 12 只"
        ),
        universe_spec=UniverseSpec(
            top_n=120,
            min_data_days=750,
            min_close=3.0,
            snapshot_window_days=45,
            refresh_freq="Q",
        ),
        rebalance=RebalanceSpec(freq="W", warmup_days=90, max_single_weight=0.20),
        select_fn=select_centrality,
        select_params=dict(DEFAULT_PARAMS),
        notes=[
            "论文主旨：因子可从资产网络结构中涌现。",
            "本次实现：Perron 特征向量做中心性、与 20 日动量按 alpha 线性融合。",
            "已修复：look-ahead 选池 / Perron 语义 / 中心性-动量解耦 / T+1 / 涨跌停 / 现金利率。",
        ],
        param_grid={
            "corr_window": [60, 120, 250],
            "centrality_weight": [0.0, 0.5, 1.0],
            "top_k": [12, 20],
        },
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
