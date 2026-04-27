"""Step 5：扫所有 paper 目录，重新生成跨论文比较。

直接复用 ``aitrader.research.runner.aggregator.aggregate_processed``，并把
所有论文的 ``00_meta.json`` 状态写入一个 ``_aggregate/pipeline_status.json``，
方便后续运维查看哪篇 quarantined / skipped。
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from ..orchestrator import PipelineConfig
from ..state import list_processed


logger = logging.getLogger(__name__)


def _dump_pipeline_status(processed_dir: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    metas = list_processed(processed_dir)
    payload = {
        "total": len(metas),
        "by_status": {},
        "papers": [],
    }
    for meta in metas:
        payload["by_status"].setdefault(meta.status, 0)
        payload["by_status"][meta.status] += 1
        payload["papers"].append(asdict(meta))
    out_path = output_dir / "pipeline_status.json"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("写出 %s（共 %d 篇，by_status=%s）", out_path, payload["total"], payload["by_status"])
    return out_path


def run_aggregate(config: PipelineConfig) -> None:
    from aitrader.research.runner import aggregate_processed  # noqa: WPS433

    out = aggregate_processed(config.processed_dir)
    logger.info("[aggregate] 跨论文比较已写出: %s", out)
    _dump_pipeline_status(config.processed_dir, config.aggregate_dir)
