"""Step 1：从 arxiv 拉取近 N 天 q-fin 论文 → 下载 PDF → 解析为 Markdown。

产物：
- ``papers/arxiv/<arxiv_id>.pdf``
- ``papers/arxiv/processed/<arxiv_id>/01_paper.md``
- ``papers/arxiv/processed/<arxiv_id>/00_meta.json``
"""
from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..orchestrator import PipelineConfig
from ..state import PaperMeta, load_meta, save_meta


logger = logging.getLogger(__name__)


SEARCH_QUERIES: tuple[str, ...] = (
    'cat:q-fin.PM AND (machine learning OR deep learning OR neural network OR transformer OR LLM)',
    'cat:q-fin.PM AND (stock selection OR factor OR alpha OR portfolio optimization)',
    'cat:q-fin.TR AND (reinforcement learning OR deep learning OR stock prediction OR backtesting)',
    'cat:q-fin.CP AND (machine learning OR neural network OR stock selection OR factor model)',
    'cat:q-fin AND (AI stock selection OR machine learning trading OR deep learning portfolio)',
)


def _clean_arxiv_id(entry_id: str) -> str:
    return entry_id.split("/")[-1]


def _stable_arxiv_dir(arxiv_id: str) -> str:
    """目录名去掉版本号，保证 2604.07870v1 和 2604.07870v2 落到同一目录。"""
    if "v" in arxiv_id:
        head, _, tail = arxiv_id.rpartition("v")
        if tail.isdigit():
            return head
    return arxiv_id


def _download_pdf(paper, papers_dir: Path) -> Path:
    aid = _clean_arxiv_id(paper.entry_id)
    filename = f"{_stable_arxiv_dir(aid)}.pdf"
    target = papers_dir / filename
    if target.exists() and target.stat().st_size > 0:
        logger.info("PDF 已存在: %s", filename)
        return target
    logger.info("下载 PDF: %s", filename)
    paper.download_pdf(dirpath=str(papers_dir), filename=filename)
    return target


def _parse_pdf(pdf_path: Path, prefer_api: bool = True) -> str:
    """优先 docu_assistant（上传 US3 → 调接口）；失败回落 pdfplumber。"""
    if prefer_api:
        # 复用现有 .claude/skills/.../scripts/file_parse.py
        repo_root = pdf_path.resolve().parents[2]
        candidates = [
            repo_root / ".claude" / "skills" / "arxiv-paper-pipeline" / "scripts",
            repo_root.parent / ".claude" / "skills" / "arxiv-paper-pipeline" / "scripts",
        ]
        for cand in candidates:
            if cand.exists() and str(cand) not in sys.path:
                sys.path.insert(0, str(cand))
        try:
            from file_parse import parse_pdf_via_api  # type: ignore
            md = parse_pdf_via_api(pdf_path)
            if md and md.strip():
                return md
            logger.warning("docu_assistant 返回空 markdown，fallback pdfplumber")
        except Exception as exc:  # noqa: BLE001
            logger.warning("docu_assistant 失败 (%s)，fallback pdfplumber", exc)

    return _parse_pdf_pdfplumber(pdf_path)


def _parse_pdf_pdfplumber(pdf_path: Path) -> str:
    try:
        import pdfplumber  # noqa: WPS433
    except ImportError:
        return "[pdfplumber 未安装，且 docu_assistant API 解析失败]"
    pages: list[str] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    pages.append(f"<!-- page {i} -->\n{text.strip()}")
    except Exception as exc:  # noqa: BLE001
        return f"[PDF 解析失败: {exc}]"
    return "\n\n".join(pages)


def _build_paper_md(paper, body: str) -> str:
    aid = _clean_arxiv_id(paper.entry_id)
    authors = ", ".join(str(a) for a in paper.authors[:8])
    if len(paper.authors) > 8:
        authors += f" 等 {len(paper.authors)} 人"
    pub_str = paper.published.strftime("%Y-%m-%d") if paper.published else "N/A"
    return (
        f"# {paper.title}\n\n"
        "| 字段 | 内容 |\n|------|------|\n"
        f"| ArXiv ID | {aid} |\n"
        f"| 发布日期 | {pub_str} |\n"
        f"| 作者 | {authors} |\n"
        f"| 分类 | {', '.join(paper.categories)} |\n"
        f"| PDF | {paper.pdf_url} |\n\n"
        "## 摘要\n\n"
        f"{paper.summary}\n\n"
        "---\n\n"
        "## 正文\n\n"
        f"{body}\n"
    )


def _search_papers(config: PipelineConfig) -> list:
    try:
        import arxiv  # noqa: WPS433
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("arxiv 包未安装；请运行 `pip install arxiv`") from exc

    cutoff = datetime.now(timezone.utc) - config.since
    client = arxiv.Client(num_retries=3, delay_seconds=3)
    seen: set[str] = set()
    results: list = []
    for query in SEARCH_QUERIES:
        logger.info("搜索: %s", query[:80])
        try:
            search = arxiv.Search(
                query=query,
                max_results=max(config.max_papers * 2, 30),
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )
            for paper in client.results(search):
                aid = _clean_arxiv_id(paper.entry_id)
                stable = _stable_arxiv_dir(aid)
                if stable in seen:
                    continue
                pub = paper.published
                if pub is None:
                    continue
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
                if pub < cutoff:
                    continue
                seen.add(stable)
                results.append(paper)
            time.sleep(1)
        except Exception as exc:  # noqa: BLE001
            logger.warning("搜索失败 (%s): %s", query[:60], exc)
    results.sort(key=lambda p: p.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    logger.info("搜索完毕：共 %d 篇符合 %s 之后的 q-fin 论文", len(results), cutoff.date())
    return results


def run_fetch(config: PipelineConfig) -> list[tuple[Path, PaperMeta]]:
    """拉取 + 解析；返回 (paper_dir, meta) 列表（含已存在但 status=fetched 的）。"""
    out: list[tuple[Path, PaperMeta]] = []
    papers_dir = config.papers_dir
    papers_dir.mkdir(parents=True, exist_ok=True)

    papers = _search_papers(config)
    if not papers:
        logger.info("近 %s 内没有符合条件的论文", config.since)
        return out

    new_count = 0
    for paper in papers:
        if new_count >= config.max_papers:
            break
        aid = _clean_arxiv_id(paper.entry_id)
        stable = _stable_arxiv_dir(aid)
        paper_dir = config.processed_dir / stable
        existing = load_meta(paper_dir)
        if existing is not None and not config.rerun:
            logger.info("已处理过 %s，跳过 fetch", stable)
            out.append((paper_dir, existing))
            continue

        try:
            pdf_path = _download_pdf(paper, papers_dir)
            body = _parse_pdf(pdf_path, prefer_api=True)
            paper_md = _build_paper_md(paper, body)
            paper_dir.mkdir(parents=True, exist_ok=True)
            md_path = paper_dir / "01_paper.md"
            md_path.write_text(paper_md, encoding="utf-8")

            pub_str = paper.published.strftime("%Y-%m-%d") if paper.published else ""
            meta = existing or PaperMeta(arxiv_id=stable)
            meta.title = paper.title
            meta.authors = [str(a) for a in paper.authors]
            meta.categories = list(paper.categories)
            meta.published = pub_str
            meta.pdf_url = paper.pdf_url
            meta.pdf_path = str(pdf_path)
            meta.paper_md_path = str(md_path)
            meta.transition("fetched")
            save_meta(paper_dir, meta)

            new_count += 1
            out.append((paper_dir, meta))
            logger.info("[fetch] %s | %s | %s", stable, pub_str, paper.title[:60])
        except Exception as exc:  # noqa: BLE001
            logger.exception("fetch 失败 %s: %s", aid, exc)

    return out
