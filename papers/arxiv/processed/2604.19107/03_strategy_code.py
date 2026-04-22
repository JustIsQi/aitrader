from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from papers.arxiv.processed.common.ashare_research_utils import (
    DEFAULT_END_DATE,
    DEFAULT_START_DATE,
    complexity_gap,
    load_panels,
    pick_liquid_symbols,
    previous_trading_date,
    simulate_equal_weight_strategy,
    weekly_rebalance_dates,
    write_markdown_summary,
)


PAPER_ID = "2604.19107"
PAPER_TITLE = "Structural Dynamics of G5 Stock Markets During Exogenous Shocks: A Random Matrix Theory-Based Complexity Gap Approach"
STRATEGY_NAME = "复杂度缺口风控"
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
    momentum_60 = close.pct_change(60)
    rebalance_dates = weekly_rebalance_dates(close.index, warmup_days=100)
    print(f"[{PAPER_ID}] 面板完成: {close.shape[0]} 个交易日 x {close.shape[1]} 只股票")

    print(f"[{PAPER_ID}] 3/5 计算复杂度缺口序列...")
    gap_values: dict[pd.Timestamp, float] = {}
    for dt in close.index:
        window = returns.loc[:dt].tail(60).dropna(axis=1, thresh=45)
        if window.shape[1] < 15:
            continue
        gap_values[dt] = complexity_gap(window)
    gap_series = pd.Series(gap_values).sort_index()
    print(f"[{PAPER_ID}] 有效复杂度缺口观测: {len(gap_series)}")

    print(f"[{PAPER_ID}] 4/5 生成周频风控持仓...")
    selections_by_date: dict[pd.Timestamp, list[str]] = {}
    signal_rows: list[dict] = []
    invested = False

    for dt in rebalance_dates:
        prior = previous_trading_date(close.index, dt)
        if prior is None or prior not in gap_series.index:
            continue

        history = gap_series.loc[:prior].dropna().tail(126)
        if len(history) < 52:
            continue

        current_gap = float(gap_series.loc[prior])
        risk_off_threshold = float(history.quantile(0.35))
        risk_on_threshold = float(history.quantile(0.55))
        recent_mean = float(history.tail(4).mean())

        if current_gap <= risk_off_threshold:
            invested = False
        elif current_gap >= risk_on_threshold and current_gap >= recent_mean:
            invested = True

        if invested:
            momentum_scores = momentum_60.loc[prior].dropna().sort_values(ascending=False)
            selected = momentum_scores.head(15).index.tolist()
        else:
            selected = []

        selections_by_date[dt] = selected
        signal_rows.append(
            {
                "rebalance_date": dt.strftime("%Y-%m-%d"),
                "signal_date": prior.strftime("%Y-%m-%d"),
                "complexity_gap": current_gap,
                "risk_off_threshold": risk_off_threshold,
                "risk_on_threshold": risk_on_threshold,
                "recent_mean": recent_mean,
                "invested": invested,
            }
        )

    signal_df = pd.DataFrame(signal_rows)
    print(
        f"[{PAPER_ID}] 有效调仓计划: {len(signal_df)} 次, "
        f"风险开启占比={signal_df['invested'].mean():.2%}" if not signal_df.empty else
        f"[{PAPER_ID}] 未生成有效调仓计划"
    )

    print(f"[{PAPER_ID}] 5/5 运行回测...")
    result = simulate_equal_weight_strategy(close, selections_by_date)
    result.strategy = STRATEGY_NAME

    notes = [
        "论文结论: 复杂度缺口在外生冲击期会塌缩, 较低缺口对应更高的后续组合波动。",
        "A股映射: 用高流动性主板股票构造60日相关矩阵, 将复杂度缺口作为周频风险状态变量。",
        "实盘化改造: 仅在复杂度缺口重新回到高位且高于近期均值时持有60日强势股票, 其余时间空仓。",
        "若该策略能显著降低回撤, 说明复杂度缺口更适合作为A股风控开关而非独立收益因子。",
    ]
    write_markdown_summary(
        output_path=OUTPUT_PATH,
        title=STRATEGY_NAME,
        paper_id=PAPER_ID,
        paper_title=PAPER_TITLE,
        methodology="60日相关矩阵复杂度缺口 -> 周频风险开关 -> 持有15只60日动量最强股票",
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
