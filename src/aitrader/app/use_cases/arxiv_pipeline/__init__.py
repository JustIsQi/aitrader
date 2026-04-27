"""ArXiv → A 股回测 端到端 pipeline。

提供统一编排器与 5 个步骤：fetch / judge / generate / backtest / aggregate。
入口：``aitrader.app.cli.arxiv_pipeline``。
"""
from __future__ import annotations

from .orchestrator import Orchestrator, PipelineConfig, parse_since

__all__ = ["Orchestrator", "PipelineConfig", "parse_since"]
