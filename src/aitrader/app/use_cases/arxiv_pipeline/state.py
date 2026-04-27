"""每篇论文的处理状态：persisted in ``papers/arxiv/processed/<id>/00_meta.json``。

状态机：
    new -> fetched -> judged -> generated -> backtested -> aggregated
                  └-> skipped (judge 评级过低)
                  └-> quarantined (LLM 生成代码反复失败)
任何步骤失败时把异常摘要写入 ``last_error``，``status`` 退回到失败前的最后稳定值。
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


logger = logging.getLogger(__name__)


VALID_STATUSES = {
    "new",
    "fetched",
    "judged",
    "skipped",
    "generated",
    "quarantined",
    "backtested",
    "aggregated",
}


@dataclass
class PaperMeta:
    """单篇论文的状态 + 元数据。"""

    arxiv_id: str
    title: str = ""
    authors: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    published: str = ""
    pdf_url: str = ""
    pdf_path: str = ""
    paper_md_path: str = ""
    status: str = "new"
    rating: Optional[int] = None
    suitable: Optional[bool] = None
    timestamps: dict[str, str] = field(default_factory=dict)
    last_error: Optional[str] = None
    extras: dict[str, Any] = field(default_factory=dict)

    def stamp(self, step: str) -> None:
        self.timestamps[step] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def transition(self, new_status: str) -> None:
        if new_status not in VALID_STATUSES:
            raise ValueError(f"未知 status={new_status}")
        self.status = new_status
        self.stamp(new_status)
        self.last_error = None


def meta_path(paper_dir: Path) -> Path:
    return paper_dir / "00_meta.json"


def load_meta(paper_dir: Path) -> Optional[PaperMeta]:
    """从 paper_dir/00_meta.json 加载，文件不存在返回 None。"""
    path = meta_path(paper_dir)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning("无法解析 %s: %s", path, exc)
        return None
    fields = {f.name for f in PaperMeta.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    cleaned = {k: v for k, v in raw.items() if k in fields}
    return PaperMeta(**cleaned)


def save_meta(paper_dir: Path, meta: PaperMeta) -> None:
    paper_dir.mkdir(parents=True, exist_ok=True)
    path = meta_path(paper_dir)
    path.write_text(
        json.dumps(asdict(meta), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def list_processed(processed_root: Path) -> list[PaperMeta]:
    """扫描 processed_root 下所有 paper 目录，返回元数据列表。"""
    out: list[PaperMeta] = []
    if not processed_root.exists():
        return out
    for child in sorted(processed_root.iterdir()):
        if not child.is_dir() or child.name.startswith("_") or child.name == "common":
            continue
        meta = load_meta(child)
        if meta is None:
            continue
        out.append(meta)
    return out
