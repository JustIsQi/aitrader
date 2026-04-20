"""
ArXiv Paper Pipeline
====================
从 arxiv q-fin 分类拉取 2026-03 起的论文，解析 PDF 为 Markdown，
再由上层（Claude）判断是否含 A 股可用策略 + 生成回测代码。

PDF 解析优先调 docu_assistant API（经 US3 中转），失败时自动回落到 pdfplumber。

用法:
    python arxiv_paper_pipeline.py              # 处理下一篇未处理论文
    python arxiv_paper_pipeline.py --list       # 列出已处理论文
    python arxiv_paper_pipeline.py --reset ID   # 重置某篇论文状态
    python arxiv_paper_pipeline.py --no-api     # 跳过 API，直接用 pdfplumber
"""

import sys
import json
import time
import argparse
import arxiv
from pathlib import Path
from datetime import datetime, timezone

# ── 目录配置 ──────────────────────────────────────────────────────────────────
def _find_project_root(start: Path) -> Path:
    """向上查找 pyproject.toml 所在目录；作为 skill 内脚本时可仍定位到仓库根。"""
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return start


BASE_DIR    = _find_project_root(Path(__file__).resolve().parent)
PAPERS_DIR  = BASE_DIR / "papers" / "arxiv"
OUTPUTS_DIR = BASE_DIR / "outputs" / "arxiv"
INDEX_FILE  = OUTPUTS_DIR / "processed.json"

# 让同目录的 file_parse / us3_tools 可 import
sys.path.insert(0, str(Path(__file__).resolve().parent))

from file_parse import parse_pdf_via_api  # noqa: E402

PAPERS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# ── 搜索关键词组合 ─────────────────────────────────────────────────────────────
SEARCH_QUERIES = [
    # AI 选股 / 因子挖掘
    'cat:q-fin.PM AND (machine learning OR deep learning OR neural network OR transformer OR LLM)',
    'cat:q-fin.PM AND (stock selection OR factor OR alpha OR portfolio optimization)',
    # 智能回测 / 强化学习交易
    'cat:q-fin.TR AND (reinforcement learning OR deep learning OR stock prediction OR backtesting)',
    # 计算金融 / 量化策略
    'cat:q-fin.CP AND (machine learning OR neural network OR stock selection OR factor model)',
    # 跨类别宽泛搜索
    'cat:q-fin AND (AI stock selection OR machine learning trading OR deep learning portfolio)',
]

START_YM = "2026-03"   # 只处理此月份之后（含）的论文


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def load_index() -> dict:
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    return {}


def save_index(index: dict):
    INDEX_FILE.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def clean_arxiv_id(entry_id: str) -> str:
    """从 entry_id URL 中提取干净的 arxiv ID，如 2503.12345v1"""
    return entry_id.split("/")[-1]


def search_papers(start_ym: str = START_YM, max_per_query: int = 30) -> list:
    """搜索 arxiv，返回满足日期条件的论文列表（去重）"""
    client = arxiv.Client(num_retries=3, delay_seconds=3)
    seen, papers = set(), []

    for query in SEARCH_QUERIES:
        print(f"  搜索: {query[:80]}...")
        try:
            search = arxiv.Search(
                query=query,
                max_results=max_per_query,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )
            for paper in client.results(search):
                aid = clean_arxiv_id(paper.entry_id)
                if aid in seen:
                    continue
                pub = paper.published
                if pub is None:
                    continue
                # 统一为 naive datetime 比较
                if pub.tzinfo is not None:
                    pub = pub.astimezone(timezone.utc).replace(tzinfo=None)
                pub_ym = pub.strftime("%Y-%m")
                if pub_ym >= start_ym:
                    papers.append(paper)
                    seen.add(aid)
            time.sleep(1)   # 礼貌性延迟
        except Exception as e:
            print(f"  搜索出错: {e}")

    # 按发布日期降序排列
    papers.sort(key=lambda p: p.published or datetime.min, reverse=True)
    print(f"\n共找到 {len(papers)} 篇符合条件的论文 (>= {start_ym})\n")
    return papers


def download_pdf(paper: arxiv.Result) -> Path:
    """下载 PDF，返回本地路径"""
    aid = clean_arxiv_id(paper.entry_id).replace("/", "_")
    filename = f"{aid}.pdf"
    filepath = PAPERS_DIR / filename
    if not filepath.exists():
        print(f"  下载 PDF: {filename} ...")
        paper.download_pdf(dirpath=str(PAPERS_DIR), filename=filename)
    else:
        print(f"  PDF 已存在: {filename}")
    return filepath


def _parse_pdf_pdfplumber(pdf_path: Path) -> str:
    """fallback：用 pdfplumber 把 PDF 解析为 Markdown。"""
    try:
        import pdfplumber
    except ImportError:
        return "[pdfplumber 未安装，且 docu_assistant API 解析失败]"

    pages = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    pages.append(f"<!-- page {i} -->\n{text.strip()}")
    except Exception as e:
        return f"[PDF 解析失败: {e}]"
    return "\n\n".join(pages)


def parse_pdf_to_md(pdf_path: Path, prefer_api: bool = True) -> str:
    """
    优先走 docu_assistant API（US3 中转），失败时自动 fallback 到 pdfplumber。
    设置 prefer_api=False 可跳过 API，直接用 pdfplumber。
    """
    if prefer_api:
        try:
            print("  解析 PDF 经 docu_assistant API（US3 中转）...")
            md = parse_pdf_via_api(pdf_path)
            if md and md.strip():
                return md
            print("  [warn] API 返回空 markdown，fallback 到 pdfplumber")
        except Exception as e:
            print(f"  [warn] API 解析失败 ({e})，fallback 到 pdfplumber")
    return _parse_pdf_pdfplumber(pdf_path)


def build_markdown(paper: arxiv.Result, body: str) -> str:
    """拼装完整 Markdown 文档"""
    aid = clean_arxiv_id(paper.entry_id)
    authors = ", ".join(str(a) for a in paper.authors[:8])
    if len(paper.authors) > 8:
        authors += f" 等 {len(paper.authors)} 人"
    pub_str = paper.published.strftime("%Y-%m-%d") if paper.published else "N/A"

    return f"""# {paper.title}

| 字段 | 内容 |
|------|------|
| ArXiv ID | {aid} |
| 发布日期 | {pub_str} |
| 作者 | {authors} |
| 分类 | {', '.join(paper.categories)} |
| PDF | {paper.pdf_url} |

## 摘要

{paper.summary}

---

## 正文

{body}
"""


def process_next_paper(start_ym: str = START_YM, prefer_api: bool = True) -> tuple:
    """
    拉取并处理下一篇未处理的论文。
    返回 (arxiv_id, md_path, full_md) 或 (None, None, None)。
    """
    index = load_index()
    papers = search_papers(start_ym)

    for paper in papers:
        aid = clean_arxiv_id(paper.entry_id)
        if aid in index:
            continue   # 已处理，跳过

        print(f"{'='*65}")
        print(f"论文标题: {paper.title}")
        print(f"ArXiv ID: {aid}")
        pub_str = paper.published.strftime("%Y-%m-%d") if paper.published else "N/A"
        print(f"发布日期: {pub_str}")
        print(f"分类:     {', '.join(paper.categories)}")
        print(f"{'='*65}\n")

        # 1. 下载 PDF
        pdf_path = download_pdf(paper)

        # 2. 解析 PDF → Markdown
        body = parse_pdf_to_md(pdf_path, prefer_api=prefer_api)

        # 3. 拼装完整 Markdown
        full_md = build_markdown(paper, body)

        # 4. 保存 Markdown
        md_name = f"{aid.replace('/', '_')}.md"
        md_path = OUTPUTS_DIR / md_name
        md_path.write_text(full_md, encoding="utf-8")
        print(f"  Markdown 已保存: {md_path}\n")

        # 5. 更新索引
        index[aid] = {
            "title":      paper.title,
            "published":  pub_str,
            "categories": paper.categories,
            "pdf_path":   str(pdf_path),
            "md_path":    str(md_path),
            "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_index(index)

        # 6. 打印摘要供快速判断
        print("\n" + "─"*65)
        print("【摘要】")
        print(paper.summary[:1500])
        print("─"*65)
        print(f"\nMarkdown 全文路径: {md_path}")
        print(f"字符数: {len(full_md):,}")

        return aid, md_path, full_md

    print("没有新论文需要处理。")
    return None, None, None


def list_processed():
    index = load_index()
    if not index:
        print("尚未处理任何论文。")
        return
    print(f"\n已处理 {len(index)} 篇论文:\n")
    for aid, meta in index.items():
        print(f"  [{meta['published']}] {aid}")
        print(f"    {meta['title'][:70]}")
        print(f"    md: {meta['md_path']}\n")


def reset_paper(arxiv_id: str):
    index = load_index()
    if arxiv_id in index:
        del index[arxiv_id]
        save_index(index)
        print(f"已重置: {arxiv_id}")
    else:
        print(f"未找到: {arxiv_id}")


# ── 入口 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ArXiv q-fin 论文处理流水线")
    parser.add_argument("--list",  action="store_true", help="列出已处理论文")
    parser.add_argument("--reset", metavar="ID",        help="重置某篇论文处理状态")
    parser.add_argument("--start", default=START_YM,    help="起始年月 (默认 2026-03)")
    parser.add_argument("--no-api", action="store_true", help="跳过 docu_assistant API，直接用 pdfplumber")
    args = parser.parse_args()

    if args.list:
        list_processed()
    elif args.reset:
        reset_paper(args.reset)
    else:
        process_next_paper(start_ym=args.start, prefer_api=not args.no_api)
