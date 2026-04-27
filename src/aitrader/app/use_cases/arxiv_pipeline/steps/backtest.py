"""Step 4：用 importlib 加载 ``03_strategy_code.py`` 并执行回测。

默认按 ``backtest_window_days``（CLI 默认 365）把 spec.train_holdout 改成：
- train = today - N 天 → today - N/2 天
- holdout = today - N/2 天 → today
warmup_days 也调小到 60，避免短窗口里没有调仓日。
"""
from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from ..orchestrator import PipelineConfig
from ..state import PaperMeta, save_meta


logger = logging.getLogger(__name__)


def _build_recent_window(window_days: int) -> tuple[str, str, str, str]:
    today = datetime.now().date()
    half = max(window_days // 2, 30)
    train_start = today - timedelta(days=window_days)
    train_end = today - timedelta(days=half + 1)
    holdout_start = today - timedelta(days=half)
    holdout_end = today
    fmt = lambda d: d.strftime("%Y-%m-%d")  # noqa: E731
    return fmt(train_start), fmt(train_end), fmt(holdout_start), fmt(holdout_end)


def _load_strategy_module(strategy_path: Path):
    """临时把 paper_dir 加进 sys.path 使 ``from select_fn import ...`` 可用。"""
    paper_dir = strategy_path.parent
    if str(paper_dir) not in sys.path:
        sys.path.insert(0, str(paper_dir))
    # 防 importlib 缓存：每次重新构造 module spec
    mod_name = f"arxiv_pipeline_paper_{paper_dir.name.replace('.', '_').replace('-', '_')}"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    spec_obj = importlib.util.spec_from_file_location(mod_name, strategy_path)
    if spec_obj is None or spec_obj.loader is None:
        raise RuntimeError(f"无法加载 strategy module: {strategy_path}")
    module = importlib.util.module_from_spec(spec_obj)
    sys.modules[mod_name] = module
    spec_obj.loader.exec_module(module)
    return module


def run_backtest(config: PipelineConfig, meta: PaperMeta, paper_dir: Path) -> PaperMeta:
    strategy_path = paper_dir / "03_strategy_code.py"
    if not strategy_path.exists():
        raise FileNotFoundError(f"03_strategy_code.py 不存在: {strategy_path}")

    train_start, train_end, holdout_start, holdout_end = _build_recent_window(
        config.backtest_window_days
    )
    logger.info(
        "[backtest] %s 近 %d 天窗口: train=%s~%s holdout=%s~%s",
        meta.arxiv_id, config.backtest_window_days,
        train_start, train_end, holdout_start, holdout_end,
    )

    from aitrader.research.runner import TrainHoldoutWindow  # noqa: WPS433
    from aitrader.research.runner.run_research import run_research as _real_run  # noqa: WPS433

    override = TrainHoldoutWindow(
        train_start=train_start,
        train_end=train_end,
        holdout_start=holdout_start,
        holdout_end=holdout_end,
    )

    def patched_run(spec, **kwargs):
        spec.train_holdout = override
        # 短窗口下大 warmup 会把调仓日吃光
        try:
            spec.rebalance.warmup_days = min(spec.rebalance.warmup_days, 60)
        except AttributeError:
            pass
        return _real_run(spec, **kwargs)

    module = _load_strategy_module(strategy_path)
    if not hasattr(module, "main"):
        raise RuntimeError(f"03_strategy_code.py 缺少 main(): {strategy_path}")

    # patch 对象：模块自己 import 了 run_research
    targets = [(module, "run_research")] if hasattr(module, "run_research") else []
    patches = [patch.object(mod, attr, side_effect=patched_run) for mod, attr in targets]
    for p in patches:
        p.start()
    try:
        module.main()
    finally:
        for p in patches:
            p.stop()

    meta.transition("backtested")
    meta.extras["backtest_window"] = {
        "train_start": train_start,
        "train_end": train_end,
        "holdout_start": holdout_start,
        "holdout_end": holdout_end,
    }
    save_meta(paper_dir, meta)
    logger.info("[backtest] %s 完成", meta.arxiv_id)
    return meta
