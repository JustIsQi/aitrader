"""生成升级版 04_backtest_summary.md。"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional

import pandas as pd

from ..metrics.performance import PerformanceReport


def _format_perf_block(report: PerformanceReport) -> list[str]:
    rows = report.as_table_rows()
    lines = ["| 指标 | 数值 |", "|---|---:|"]
    for name, value in rows:
        lines.append(f"| {name} | {value} |")
    return lines


def _format_compare_block(
    title: str,
    base_label: str,
    base_report: PerformanceReport,
    others: Mapping[str, PerformanceReport],
) -> list[str]:
    lines = [f"## {title}", "", "| 策略 | 总收益 | 年化 | 夏普 | Sortino | 最大回撤 | Calmar |", "|---|---:|---:|---:|---:|---:|---:|"]
    rows = [(base_label, base_report)] + [(k, v) for k, v in others.items()]
    for name, r in rows:
        def pct(v):
            return "NA" if v != v else f"{v*100:+.2f}%"
        def num(v):
            return "NA" if v != v else f"{v:.2f}"
        lines.append(
            f"| {name} | {pct(r.total_return)} | {pct(r.cagr)} | {num(r.sharpe)} "
            f"| {num(r.sortino)} | {pct(r.max_drawdown)} | {num(r.calmar)} |"
        )
    return lines


def write_summary_markdown(
    output_path: Path,
    *,
    title: str,
    paper_id: str,
    paper_title: str,
    methodology: str,
    notes: list[str],
    strategy_report: PerformanceReport,
    baseline_reports: Mapping[str, PerformanceReport],
    train_holdout_reports: Optional[Mapping[str, PerformanceReport]] = None,
    ablation_top: Optional[pd.DataFrame] = None,
    artifacts: Optional[list[str]] = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# 回测摘要：{title}")
    lines.append("")
    lines.append(f"- 论文ID: `{paper_id}`")
    lines.append(f"- 论文标题: {paper_title}")
    lines.append(f"- 方法映射: {methodology}")
    lines.append("")

    lines.append("## 核心指标（Holdout / 全期）")
    lines.append("")
    lines.extend(_format_perf_block(strategy_report))
    lines.append("")

    if baseline_reports:
        lines.extend(
            _format_compare_block(
                "vs 基线",
                "策略",
                strategy_report,
                baseline_reports,
            )
        )
        lines.append("")

    if train_holdout_reports:
        lines.extend(
            _format_compare_block(
                "Train(2019-2021) vs Holdout(2022-2024)",
                "全期",
                strategy_report,
                train_holdout_reports,
            )
        )
        lines.append("")

    if ablation_top is not None and not ablation_top.empty:
        lines.append("## Grid Ablation Top-5（按 train sharpe 排序）")
        lines.append("")
        cols = list(ablation_top.columns)
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "|".join(["---"] * len(cols)) + "|")
        for _, row in ablation_top.iterrows():
            cells = []
            for c in cols:
                v = row[c]
                if isinstance(v, float):
                    if v != v:
                        cells.append("NA")
                    else:
                        cells.append(f"{v:.4f}" if abs(v) < 100 else f"{v:.2f}")
                else:
                    cells.append(str(v))
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    lines.append("## 结论")
    lines.append("")
    for note in notes:
        lines.append(f"- {note}")
    lines.append("")

    if artifacts:
        lines.append("## 产物清单")
        lines.append("")
        for artifact in artifacts:
            lines.append(f"- `{artifact}`")
        lines.append("")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
