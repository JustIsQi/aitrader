from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from papers.arxiv.processed.common.ashare_research_utils import (
    DEFAULT_END_DATE,
    DEFAULT_START_DATE,
    leading_eigenvector_scores,
    load_panels,
    pick_liquid_symbols,
    previous_trading_date,
    simulate_equal_weight_strategy,
    weekly_rebalance_dates,
    write_markdown_summary,
)


PAPER_ID = "2604.12197"
PAPER_TITLE = "Emergence of Statistical Financial Factors by a Diffusion Process"
STRATEGY_NAME = "网络中心性选股"
OUTPUT_PATH = Path(__file__).with_name("04_backtest_summary.md")


def run_backtest(
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
) -> tuple:
    print(f"[{PAPER_ID}] 1/5 构建流动性股票池...")
    universe = pick_liquid_symbols(end_date=end_date, max_symbols=40)
    print(f"[{PAPER_ID}] 股票池完成: {len(universe)} 只, 示例={universe[:8]}")

    print(f"[{PAPER_ID}] 2/5 读取 Wind 价格面板...")
    panels = load_panels(universe, start_date=start_date, end_date=end_date, fields=["close", "return"])
    close = panels["close"]
    returns = panels["return"]
    print(f"[{PAPER_ID}] 面板完成: {close.shape[0]} 个交易日 x {close.shape[1]} 只股票")

    print(f"[{PAPER_ID}] 3/5 计算网络中心性...")
    rebalance_dates = weekly_rebalance_dates(close.index, warmup_days=90)
    momentum_20 = close.pct_change(20)
    selections_by_date: dict[pd.Timestamp, list[str]] = {}
    signal_rows: list[dict] = []

    print(f"[{PAPER_ID}] 4/5 生成周频持仓...")
    for dt in rebalance_dates:
        prior = previous_trading_date(close.index, dt)
        if prior is None:
            continue

        window = returns.loc[:prior].tail(60)
        valid = window.dropna(axis=1, thresh=45)
        if valid.shape[1] < 12:
            continue

        corr = valid.corr().clip(lower=0.0).fillna(0.0)
        mask = ~np.eye(len(corr), dtype=bool)
        off_diag = corr.where(mask).stack()
        positive = off_diag[off_diag > 0]
        threshold = float(positive.quantile(0.60)) if not positive.empty else 0.0
        adjacency = corr.where(corr >= threshold, 0.0)
        scores = leading_eigenvector_scores(adjacency)
        if scores.empty:
            continue

        momentum_scores = momentum_20.loc[prior].reindex(scores.index).fillna(0.0)
        composite = scores.rank(pct=True).mul(0.7).add(momentum_scores.rank(pct=True).mul(0.3), fill_value=0.0)
        selected = composite.sort_values(ascending=False).head(12).index.tolist()
        selections_by_date[dt] = selected
        signal_rows.append(
            {
                "rebalance_date": dt.strftime("%Y-%m-%d"),
                "signal_date": prior.strftime("%Y-%m-%d"),
                "network_size": int(valid.shape[1]),
                "edge_threshold": threshold,
                "top_symbol": selected[0] if selected else "",
                "top_score": float(composite.loc[selected[0]]) if selected else float("nan"),
            }
        )

    signal_df = pd.DataFrame(signal_rows)
    print(
        f"[{PAPER_ID}] 有效调仓计划: {len(signal_df)} 次, "
        f"平均网络规模={signal_df['network_size'].mean():.1f}" if not signal_df.empty else
        f"[{PAPER_ID}] 未生成有效调仓计划"
    )

    print(f"[{PAPER_ID}] 5/5 运行回测...")
    result = simulate_equal_weight_strategy(close, selections_by_date)
    result.strategy = STRATEGY_NAME

    notes = [
        "论文主旨: 因子可以从资产交互网络中自然涌现, 而非预先手工指定。",
        "A股映射: 用60日收益相关矩阵构造网络, 以特征向量中心性表示市场核心因子暴露。",
        "实盘化改造: 加入20日动量做轻度排序融合, 避免中心性过强但趋势明显转弱的股票。",
        "若该策略优于简单等权, 说明网络结构信息在A股横截面选股上具备可操作性。",
    ]
    write_markdown_summary(
        output_path=OUTPUT_PATH,
        title=STRATEGY_NAME,
        paper_id=PAPER_ID,
        paper_title=PAPER_TITLE,
        methodology="60日收益相关网络 -> 特征向量中心性 + 20日动量融合 -> 周频等权持有12只股票",
        result=result,
        notes=notes,
    )

    print(
        f"[{PAPER_ID}] 回测完成: total_return={result.total_return:+.2%}, "
        f"cagr={result.cagr:+.2%}, sharpe={result.sharpe:.2f}, "
        f"max_drawdown={result.max_drawdown:+.2%}"
    )
    return result, signal_df


if __name__ == "__main__":
    run_backtest()
