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
    monthly_rebalance_dates,
    pick_liquid_symbols,
    previous_trading_date,
    simulate_equal_weight_strategy,
    write_markdown_summary,
    load_panels,
)


PAPER_ID = "2604.07870"
PAPER_TITLE = "Skewness Dispersion and Stock Market Returns"
STRATEGY_NAME = "偏度分散度择时"
OUTPUT_PATH = Path(__file__).with_name("04_backtest_summary.md")


def run_backtest(
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
) -> tuple:
    print(f"[{PAPER_ID}] 1/5 构建流动性股票池...")
    basket = pick_liquid_symbols(end_date=end_date, max_symbols=30)
    print(f"[{PAPER_ID}] 股票池完成: {len(basket)} 只, 示例={basket[:8]}")

    print(f"[{PAPER_ID}] 2/5 读取 Wind 价格面板...")
    panels = load_panels(basket, start_date=start_date, end_date=end_date, fields=["close", "return"])
    close = panels["close"]
    returns = panels["return"]
    print(f"[{PAPER_ID}] 面板完成: {close.shape[0]} 个交易日 x {close.shape[1]} 只股票")

    print(f"[{PAPER_ID}] 3/5 计算偏度分散度信号...")
    realized_skew = returns.rolling(20, min_periods=15).skew()
    skew_dispersion = realized_skew.std(axis=1, ddof=0).rolling(5, min_periods=3).mean()
    rebalance_dates = monthly_rebalance_dates(close.index, warmup_days=140)
    print(f"[{PAPER_ID}] 候选调仓点: {len(rebalance_dates)}")

    print(f"[{PAPER_ID}] 4/5 生成月频择时计划...")
    selections_by_date: dict[pd.Timestamp, list[str]] = {}
    invested = False
    signal_rows: list[dict] = []

    for dt in rebalance_dates:
        prior = previous_trading_date(close.index, dt)
        if prior is None:
            continue

        history = skew_dispersion.loc[:prior].dropna().tail(252)
        if len(history) < 126:
            continue

        current_value = float(skew_dispersion.loc[prior])
        if not pd.notna(current_value):
            continue

        risk_on_threshold = float(history.quantile(0.45))
        risk_off_threshold = float(history.quantile(0.70))

        if current_value <= risk_on_threshold:
            invested = True
        elif current_value >= risk_off_threshold:
            invested = False

        selections_by_date[dt] = basket if invested else []
        signal_rows.append(
            {
                "rebalance_date": dt.strftime("%Y-%m-%d"),
                "signal_date": prior.strftime("%Y-%m-%d"),
                "skew_dispersion": current_value,
                "risk_on_threshold": risk_on_threshold,
                "risk_off_threshold": risk_off_threshold,
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
        "论文发现: 个股已实现偏度分散度越高, 后续市场回报越弱。",
        "A股映射: 用主板高流动性股票篮子代表市场暴露, 月频根据偏度分散度做开/关仓。",
        f"本次实现: 20日个股收益偏度, 横截面标准差作为分散度, 阈值取近252日的45%/70%分位形成迟滞带。",
        "解读方式: 若结果稳定优于始终持有, 说明论文中的宏观信息扩散逻辑在A股也能转化为择时信号。",
    ]
    write_markdown_summary(
        output_path=OUTPUT_PATH,
        title=STRATEGY_NAME,
        paper_id=PAPER_ID,
        paper_title=PAPER_TITLE,
        methodology="市场偏度分散度 -> 月频风险开关 -> 等权持有30只高流动性主板股票",
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
