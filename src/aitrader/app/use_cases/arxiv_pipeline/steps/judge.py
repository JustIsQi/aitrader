"""Step 2：用 LLM 判断论文在 A 股的适用性。

输入：``01_paper.md``
输出：``02_applicability.md`` + 把 rating / suitable 写回 ``00_meta.json``
低评级（rating < min_rating）→ status=skipped，pipeline 后续步骤跳过该篇。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..llm_client import LLMClient
from ..orchestrator import PipelineConfig
from ..prompts import load_prompt
from ..state import PaperMeta, save_meta


logger = logging.getLogger(__name__)


_MAX_PAPER_CHARS = 60_000  # 防止超大 PDF 撑爆 prompt


def _trim(md: str, limit: int = _MAX_PAPER_CHARS) -> str:
    if len(md) <= limit:
        return md
    head = md[: limit // 2]
    tail = md[-limit // 2 :]
    return head + "\n\n[... 中段省略 ...]\n\n" + tail


def _call_judge(client: LLMClient, paper_id: str, paper_title: str, paper_md: str) -> dict:
    prompt = load_prompt(
        "judge.md",
        paper_id=paper_id,
        paper_title=paper_title,
        paper_md=_trim(paper_md),
    )
    last_exc: Exception | None = None
    for attempt in range(1, 3):
        raw = client.chat(prompt, json_mode=True, max_retries=2)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            last_exc = exc
            logger.warning("judge JSON 解析失败 attempt=%d: %s", attempt, exc)
    raise RuntimeError(f"judge 步骤无法解析 JSON（已重试 2 次）: {last_exc}")


def _build_md(paper_id: str, paper_title: str, judgment: dict) -> str:
    rating = judgment.get("rating", "?")
    suitable = judgment.get("suitable", "?")
    core_idea = judgment.get("core_idea", "")
    reasons = judgment.get("reasons", []) or []
    data_req = judgment.get("data_requirements", []) or []
    adjustments = judgment.get("ashare_adjustments", []) or []
    risks = judgment.get("risks", []) or []

    lines = [
        f"# A 股适用性判断：{paper_id}",
        "",
        f"- 论文标题：{paper_title}",
        f"- ArXiv：`{paper_id}`",
        f"- 适用性评级：{'⭐' * int(rating) if isinstance(rating, int) else rating}",
        f"- 是否适合：{suitable}",
        "",
        "## 核心思想",
        "",
        core_idea or "_LLM 未输出_",
        "",
        "## 评分理由",
        "",
    ]
    if reasons:
        lines.extend(f"- {r}" for r in reasons)
    else:
        lines.append("_LLM 未输出_")
    lines += ["", "## 数据需求", ""]
    if data_req:
        lines.extend(f"- {r}" for r in data_req)
    else:
        lines.append("_LLM 未输出_")
    lines += ["", "## A 股改造建议", ""]
    if adjustments:
        lines.extend(f"- {r}" for r in adjustments)
    else:
        lines.append("_LLM 未输出_")
    lines += ["", "## 风险与限制", ""]
    if risks:
        lines.extend(f"- {r}" for r in risks)
    else:
        lines.append("_LLM 未输出_")
    return "\n".join(lines) + "\n"


def run_judge(config: PipelineConfig, meta: PaperMeta, paper_dir: Path) -> PaperMeta:
    paper_md_path = Path(meta.paper_md_path) if meta.paper_md_path else paper_dir / "01_paper.md"
    if not paper_md_path.exists():
        raise FileNotFoundError(f"01_paper.md 不存在: {paper_md_path}")

    paper_md = paper_md_path.read_text(encoding="utf-8")
    client = LLMClient()

    judgment = _call_judge(client, meta.arxiv_id, meta.title, paper_md)
    rating = judgment.get("rating")
    try:
        rating_int = int(rating)
    except (TypeError, ValueError):
        rating_int = 0
        logger.warning("[%s] LLM rating=%r 非整数，按 0 处理", meta.arxiv_id, rating)
    suitable = bool(judgment.get("suitable", rating_int >= config.min_rating))

    md_path = paper_dir / "02_applicability.md"
    md_path.write_text(_build_md(meta.arxiv_id, meta.title, judgment), encoding="utf-8")

    meta.rating = rating_int
    meta.suitable = suitable
    meta.extras["judgment"] = judgment

    if rating_int < config.min_rating or not suitable:
        meta.transition("skipped")
        logger.info(
            "[judge] %s rating=%d < %d → 标记 skipped",
            meta.arxiv_id, rating_int, config.min_rating,
        )
    else:
        meta.transition("judged")
        logger.info("[judge] %s rating=%d → 进入 generate", meta.arxiv_id, rating_int)

    save_meta(paper_dir, meta)
    return meta
