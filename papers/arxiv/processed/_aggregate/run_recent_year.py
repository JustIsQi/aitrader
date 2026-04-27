"""跑单篇论文的"近一年"回测。

用法：
    PYTHONPATH=/data/datavol/yy/code/aitrader/src python \
        papers/arxiv/processed/_aggregate/run_recent_year.py 2604.07870

回测窗口默认 2025-04-23 至 2026-04-23（恰好近一年），train=H1 / holdout=H2 作为
参数稳定性检验；ablation 仍在该 1 年窗口跑。
"""
from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aitrader.research.runner import TrainHoldoutWindow  # noqa: E402
from aitrader.research.runner import run_research as _runner_module  # noqa: E402
from aitrader.research.runner.run_research import run_research as _real_run  # noqa: E402


PAPER_DIRS = {
    "2604.07870": REPO_ROOT / "papers" / "arxiv" / "processed" / "2604.07870",
    "2604.12197": REPO_ROOT / "papers" / "arxiv" / "processed" / "2604.12197",
    "2604.19107": REPO_ROOT / "papers" / "arxiv" / "processed" / "2604.19107",
}


def _load_paper_module(paper_dir: Path):
    """动态加载论文目录下的 03_strategy_code.py。"""
    sys.path.insert(0, str(paper_dir))
    try:
        spec_obj = importlib.util.spec_from_file_location(
            f"paper_{paper_dir.name.replace('.', '_')}",
            paper_dir / "03_strategy_code.py",
        )
        module = importlib.util.module_from_spec(spec_obj)
        spec_obj.loader.exec_module(module)  # type: ignore[union-attr]
        return module
    finally:
        sys.path.remove(str(paper_dir))


def run(
    paper_id: str,
    train_start: str,
    train_end: str,
    holdout_start: str,
    holdout_end: str,
    warmup_days: int = 60,
) -> None:
    paper_dir = PAPER_DIRS[paper_id]
    module = _load_paper_module(paper_dir)

    override = TrainHoldoutWindow(
        train_start=train_start,
        train_end=train_end,
        holdout_start=holdout_start,
        holdout_end=holdout_end,
    )

    def patched_run(spec, **kwargs):
        spec.train_holdout = override
        spec.rebalance.warmup_days = warmup_days
        logging.info(
            "[%s] 覆盖窗口: data=%s~%s train=%s~%s holdout=%s~%s warmup_days=%d",
            paper_id, train_start, holdout_end, train_start, train_end,
            holdout_start, holdout_end, warmup_days,
        )
        return _real_run(spec, **kwargs)

    targets = []
    if hasattr(module, "run_research"):
        targets.append((module, "run_research"))

    patches = [patch.object(mod, attr, side_effect=patched_run) for mod, attr in targets]
    for p in patches:
        p.start()
    try:
        module.main()
    finally:
        for p in patches:
            p.stop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paper_id", choices=list(PAPER_DIRS.keys()))
    parser.add_argument("--train-start", default="2024-10-01")
    parser.add_argument("--train-end", default="2025-10-31")
    parser.add_argument("--holdout-start", default="2025-11-01")
    parser.add_argument("--holdout-end", default="2026-04-23")
    parser.add_argument("--warmup-days", type=int, default=60)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    run(
        args.paper_id,
        args.train_start,
        args.train_end,
        args.holdout_start,
        args.holdout_end,
        warmup_days=args.warmup_days,
    )


if __name__ == "__main__":
    main()
