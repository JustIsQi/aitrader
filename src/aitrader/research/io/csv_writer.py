"""把 SimulationResult 各组件落地为 csv。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from ..engine.vectorized_simulator import SimulationResult


logger = logging.getLogger(__name__)


def dump_artifacts(
    output_dir: Path,
    result: SimulationResult,
    *,
    signal_df: Optional[pd.DataFrame] = None,
    prefix: str = "",
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    p = (lambda name: output_dir / f"{prefix}{name}") if prefix else (lambda name: output_dir / name)

    result.equity_curve.rename("equity").to_csv(p("equity_curve.csv"))
    result.daily_returns.rename("ret").to_csv(p("daily_returns.csv"))
    result.holdings.to_csv(p("holdings.csv"))
    result.invested_exposure.to_csv(p("invested_exposure.csv"))
    if not result.rebalance_log.empty:
        result.rebalance_log.to_csv(p("rebalance_log.csv"), index=False)
    if signal_df is not None and not signal_df.empty:
        signal_df.to_csv(p("signals.csv"), index=False)
    logger.info("产物已落地到 %s (prefix=%r)", output_dir, prefix)
