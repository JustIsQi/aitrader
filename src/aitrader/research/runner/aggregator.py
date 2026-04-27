"""跨论文比较汇总器。

扫描 ``papers/arxiv/processed/<paper>/04_backtest_summary.md`` 以及同目录下的
``equity_curve.csv``、``ablation_holdout.csv``，输出一份
``papers/arxiv/processed/_aggregate/cross_paper_comparison.md``。

设计目标：所有数值都从落盘产物里读，避免在汇总环节再重复一遍回测，确保汇总
表与论文目录里的数字 1:1 对齐。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


@dataclass
class PaperRunSummary:
    paper_id: str
    title: str
    methodology: str
    metrics: dict
    holdout_metrics: dict
    train_metrics: dict
    baselines: dict[str, dict]


def _safe_read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("无法解析 %s", path)
        return {}


def _format_pct(value) -> str:
    if value is None or not isinstance(value, (int, float)) or not np.isfinite(value):
        return "NA"
    return f"{value * 100:+.2f}%"


def _format_num(value, digits: int = 2) -> str:
    if value is None or not isinstance(value, (int, float)) or not np.isfinite(value):
        return "NA"
    return f"{value:.{digits}f}"


def collect_paper_summary(paper_dir: Path) -> Optional[PaperRunSummary]:
    metrics_path = paper_dir / "performance.json"
    holdout_path = paper_dir / "performance_holdout.json"
    train_path = paper_dir / "performance_train.json"
    baselines_path = paper_dir / "baselines_metrics.json"
    meta_path = paper_dir / "meta.json"

    if not metrics_path.exists():
        logger.info("跳过 %s（performance.json 缺失，可能尚未跑回测）", paper_dir.name)
        return None

    meta = _safe_read_json(meta_path)
    return PaperRunSummary(
        paper_id=meta.get("paper_id", paper_dir.name),
        title=meta.get("paper_title", ""),
        methodology=meta.get("methodology", ""),
        metrics=_safe_read_json(metrics_path),
        holdout_metrics=_safe_read_json(holdout_path),
        train_metrics=_safe_read_json(train_path),
        baselines=_safe_read_json(baselines_path),
    )


def render_comparison(summaries: Iterable[PaperRunSummary]) -> str:
    summaries = list(summaries)
    lines = ["# 跨论文回测汇总", ""]
    if not summaries:
        lines.append("> 当前没有可汇总的论文产物。请先在每个 paper 目录下跑 `python 03_strategy_code.py`。")
        return "\n".join(lines)

    lines.append("> 本文件由 `aitrader.research.runner.aggregator` 自动生成，不要手工编辑。")
    lines.append("")

    lines.append("## 1. 全期表现")
    lines.append("")
    lines.append("| 论文ID | 标题 | 方法 | 总收益 | 年化 | 夏普 | 最大回撤 | Calmar |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|")
    for s in summaries:
        m = s.metrics
        lines.append(
            "| `{pid}` | {title} | {meth} | {tr} | {cagr} | {sh} | {dd} | {ca} |".format(
                pid=s.paper_id,
                title=s.title or "-",
                meth=s.methodology or "-",
                tr=_format_pct(m.get("total_return")),
                cagr=_format_pct(m.get("cagr")),
                sh=_format_num(m.get("sharpe")),
                dd=_format_pct(m.get("max_drawdown")),
                ca=_format_num(m.get("calmar")),
            )
        )

    lines.append("")
    lines.append("## 2. Train(2019-2021) vs Holdout(2022-2024)")
    lines.append("")
    lines.append("| 论文ID | Train 总收益 | Train 夏普 | Train 回撤 | Holdout 总收益 | Holdout 夏普 | Holdout 回撤 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for s in summaries:
        tr = s.train_metrics
        ho = s.holdout_metrics
        lines.append(
            "| `{pid}` | {ttr} | {tsh} | {tdd} | {htr} | {hsh} | {hdd} |".format(
                pid=s.paper_id,
                ttr=_format_pct(tr.get("total_return")),
                tsh=_format_num(tr.get("sharpe")),
                tdd=_format_pct(tr.get("max_drawdown")),
                htr=_format_pct(ho.get("total_return")),
                hsh=_format_num(ho.get("sharpe")),
                hdd=_format_pct(ho.get("max_drawdown")),
            )
        )

    lines.append("")
    lines.append("## 3. 基线对比（同池）")
    lines.append("")
    baseline_names = sorted(
        {name for s in summaries for name in s.baselines.keys()}
    )
    if baseline_names:
        header = ["论文ID", "策略", *baseline_names]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        for s in summaries:
            row = [
                f"`{s.paper_id}`",
                _format_pct(s.metrics.get("total_return")),
            ]
            for name in baseline_names:
                bm = s.baselines.get(name, {})
                row.append(_format_pct(bm.get("total_return")))
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        lines.append("（数值为总收益）")
    else:
        lines.append("（缺少基线数据。）")

    return "\n".join(lines) + "\n"


def aggregate_processed(
    processed_dir: Path,
    output_path: Optional[Path] = None,
) -> Path:
    """扫描 processed 目录下所有论文子目录，合成跨论文比较 markdown。"""
    processed_dir = Path(processed_dir)
    paper_dirs = sorted(
        d for d in processed_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_") and d.name != "common"
    )
    summaries = [s for s in (collect_paper_summary(d) for d in paper_dirs) if s is not None]

    output_path = output_path or processed_dir / "_aggregate" / "cross_paper_comparison.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = render_comparison(summaries)
    output_path.write_text(content, encoding="utf-8")
    logger.info("写出 %s", output_path)
    return output_path
