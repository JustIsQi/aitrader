"""绘制净值/回撤/信号时间线图。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd


logger = logging.getLogger(__name__)


_CJK_FONT_CANDIDATES = (
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "Source Han Sans CN",
    "Source Han Sans SC",
    "WenQuanYi Zen Hei",
    "WenQuanYi Micro Hei",
    "Microsoft YaHei",
    "PingFang SC",
    "Heiti SC",
    "SimHei",
    "AR PL UMing CN",
    "AR PL UKai CN",
)


def _configure_cjk_font(plt) -> None:
    try:
        from matplotlib import font_manager

        available = {f.name for f in font_manager.fontManager.ttflist}
        chosen = next((c for c in _CJK_FONT_CANDIDATES if c in available), None)
        if chosen is None:
            return
        cur = list(plt.rcParams.get("font.sans-serif", []))
        if chosen in cur:
            cur.remove(chosen)
        plt.rcParams["font.sans-serif"] = [chosen, *cur]
        plt.rcParams["axes.unicode_minus"] = False
    except Exception as exc:  # noqa: BLE001
        logger.debug("配置中文字体失败: %s", exc)


def _import_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        logger.warning("matplotlib 不可用，跳过绘图: %s", exc)
        return None, None
    _configure_cjk_font(plt)
    return matplotlib, plt


def save_equity_drawdown_chart(
    output_path: Path,
    *,
    equity_curve: pd.Series,
    benchmark_equity: Optional[pd.Series] = None,
    title: str = "策略净值",
) -> bool:
    matplotlib, plt = _import_matplotlib()
    if plt is None:
        return False
    if equity_curve.empty:
        return False

    fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax_eq, ax_dd = axes

    ax_eq.plot(equity_curve.index, equity_curve.values, label="strategy", linewidth=1.4)
    if benchmark_equity is not None and not benchmark_equity.empty:
        bench = benchmark_equity.reindex(equity_curve.index).ffill()
        ax_eq.plot(bench.index, bench.values, label="benchmark", linewidth=1.0, alpha=0.75)
    ax_eq.set_title(title)
    ax_eq.set_ylabel("Equity (start=1)")
    ax_eq.legend(loc="upper left")
    ax_eq.grid(True, linewidth=0.4, alpha=0.5)

    cummax = equity_curve.cummax()
    drawdown = equity_curve / cummax - 1.0
    ax_dd.fill_between(drawdown.index, drawdown.values, 0.0, alpha=0.4)
    ax_dd.set_ylabel("Drawdown")
    ax_dd.grid(True, linewidth=0.4, alpha=0.5)

    fig.tight_layout()
    fig.savefig(output_path, dpi=140)
    plt.close(fig)
    return True


def save_signal_timeline_chart(
    output_path: Path,
    *,
    signal_series: pd.Series,
    threshold_series: Optional[pd.DataFrame] = None,
    invested_series: Optional[pd.Series] = None,
    title: str = "信号时间线",
) -> bool:
    matplotlib, plt = _import_matplotlib()
    if plt is None:
        return False
    if signal_series.empty:
        return False
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(signal_series.index, signal_series.values, label="signal", linewidth=1.2)
    if threshold_series is not None and not threshold_series.empty:
        for col in threshold_series.columns:
            ax.plot(threshold_series.index, threshold_series[col].values, label=col, linewidth=0.8, linestyle="--")
    ax.set_title(title)
    ax.legend(loc="upper left")
    ax.grid(True, linewidth=0.4, alpha=0.5)
    if invested_series is not None and not invested_series.empty:
        ax2 = ax.twinx()
        ax2.fill_between(invested_series.index, invested_series.values, alpha=0.15, label="exposure")
        ax2.set_ylim(0, 1.05)
        ax2.set_ylabel("exposure")
    fig.tight_layout()
    fig.savefig(output_path, dpi=140)
    plt.close(fig)
    return True
