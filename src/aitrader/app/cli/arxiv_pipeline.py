"""ArXiv → A 股回测端到端 pipeline 的统一 CLI 入口。

用法：

    python -m aitrader.app.cli.arxiv_pipeline                    # 默认 14 天 / 全 5 步
    python -m aitrader.app.cli.arxiv_pipeline --since 30d --max-papers 5
    python -m aitrader.app.cli.arxiv_pipeline --paper 2604.99999 --rerun
    python -m aitrader.app.cli.arxiv_pipeline --steps fetch,aggregate --no-llm
    python -m aitrader.app.cli.arxiv_pipeline --rerun-legacy --steps generate,backtest,aggregate
"""
from __future__ import annotations

import argparse
import logging
import sys


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aitrader.app.cli.arxiv_pipeline",
        description="统一 ArXiv → A 股回测 Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--since", default="14d",
                   help="拉取窗口（默认 14d）。支持 14d / 2w / 720h / 1m / 1y")
    p.add_argument("--max-papers", type=int, default=20,
                   help="单次最多处理的新论文数量（默认 20）")
    p.add_argument("--steps", default="fetch,judge,generate,backtest,aggregate",
                   help="逗号分隔的子步骤；默认全跑")
    p.add_argument("--paper", action="append", default=None,
                   help="只处理指定 arxiv id（可多次提供）")
    p.add_argument("--rerun", action="store_true",
                   help="对已有产物的论文也强制重跑")
    p.add_argument("--rerun-legacy", action="store_true",
                   help="对 processed 目录下所有已存在论文都重跑后续步骤")
    p.add_argument("--no-llm", action="store_true",
                   help="跳过 judge / generate（用于调试 fetch / aggregate）")
    p.add_argument("--dry-run", action="store_true",
                   help="只打印将要处理的论文与计划，不写任何产物")
    p.add_argument("--backtest-window-days", type=int, default=365,
                   help="回测总窗口天数（默认 365；前半段为 train，后半段为 holdout）")
    p.add_argument("--min-rating", type=int, default=3,
                   help="LLM 适用性评级低于该值时直接 skipped（默认 3）")
    p.add_argument("--log-level", default="INFO",
                   help="日志级别（默认 INFO）")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    from aitrader.app.use_cases.arxiv_pipeline import Orchestrator

    orchestrator = Orchestrator.from_args(args)
    result = orchestrator.run()
    if result.get("errors", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
