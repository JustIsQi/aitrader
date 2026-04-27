"""Step 3：用 LLM 生成 ``select_fn.py`` + ``03_strategy_code.py``。

强制护栏：
- AST 解析 + ``compile`` 双校验
- 导入白名单（标准库子集 + numpy/pandas + aitrader.research.*）
- 禁词扫描（os / subprocess / open(..., "w") / exec / eval / __import__ / importlib / 网络）
- 必须存在 ``def select_<slug>(context, params) -> ...`` 函数
- 03_strategy_code.py 必须 import 同名 select_<slug>，并定义 ``main()``
失败重试 ≤3 次后将 status 置为 quarantined。
"""
from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import Optional

from ..llm_client import LLMClient, extract_all_python_blocks
from ..orchestrator import PipelineConfig
from ..prompts import load_example, load_prompt
from ..state import PaperMeta, save_meta


logger = logging.getLogger(__name__)


_MAX_PAPER_CHARS = 30_000


_ALLOWED_TOP_IMPORTS = {
    # 标准库
    "__future__", "logging", "math", "typing", "dataclasses", "collections", "itertools",
    "functools", "warnings", "abc", "enum",
    # 第三方
    "numpy", "pandas",
    # 项目内
    "aitrader",
}

_DENYLIST_PATTERNS = (
    re.compile(r"\bimport\s+os\b"),
    re.compile(r"\bimport\s+sys\b"),
    re.compile(r"\bimport\s+subprocess\b"),
    re.compile(r"\bimport\s+socket\b"),
    re.compile(r"\bimport\s+requests\b"),
    re.compile(r"\bimport\s+urllib\b"),
    re.compile(r"\bimport\s+importlib\b"),
    re.compile(r"\bimport\s+pickle\b"),
    re.compile(r"\bimport\s+ctypes\b"),
    re.compile(r"\bfrom\s+os\b"),
    re.compile(r"\bfrom\s+sys\b"),
    re.compile(r"\bfrom\s+subprocess\b"),
    re.compile(r"\bfrom\s+socket\b"),
    re.compile(r"\bfrom\s+requests\b"),
    re.compile(r"\bfrom\s+urllib\b"),
    re.compile(r"\bfrom\s+importlib\b"),
    re.compile(r"\bfrom\s+pickle\b"),
    re.compile(r"\bfrom\s+ctypes\b"),
    re.compile(r"\b__import__\b"),
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"open\s*\([^)]*['\"]w['\"]"),
    re.compile(r"open\s*\([^)]*['\"]a['\"]"),
)


_SLUG_RE = re.compile(r"def\s+select_([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")


class GenerationError(Exception):
    pass


def _trim(md: str, limit: int = _MAX_PAPER_CHARS) -> str:
    if len(md) <= limit:
        return md
    head = md[: limit // 2]
    tail = md[-limit // 2 :]
    return head + "\n\n[... 中段省略 ...]\n\n" + tail


def _check_denylist(code: str, label: str) -> None:
    for pat in _DENYLIST_PATTERNS:
        if pat.search(code):
            raise GenerationError(f"{label}: 违禁词命中 /{pat.pattern}/")


def _check_imports(code: str, label: str, *, extra_allowed: set[str] | None = None) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise GenerationError(f"{label}: 语法错误 {exc}") from exc

    allowed = set(_ALLOWED_TOP_IMPORTS) | (extra_allowed or set())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in allowed:
                    raise GenerationError(f"{label}: 禁止 import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            top = node.module.split(".")[0]
            if top not in allowed:
                raise GenerationError(f"{label}: 禁止 from {node.module}")


def _has_select_fn(code: str) -> Optional[str]:
    """返回检测到的 slug，没有则 None。"""
    matches = _SLUG_RE.findall(code)
    return matches[0] if matches else None


def _check_select_fn(code: str) -> str:
    slug = _has_select_fn(code)
    if not slug:
        raise GenerationError("select_fn.py: 找不到 def select_<slug>(context, params)")
    if not re.search(rf"def\s+select_{slug}\s*\(\s*context\s*[,:]", code):
        raise GenerationError(
            f"select_fn.py: select_{slug} 第一个参数必须叫 context（保持框架约定）"
        )
    return slug


def _check_strategy_code(code: str, expected_slug: str, paper_id: str) -> None:
    if "from select_fn import" not in code:
        raise GenerationError(
            "03_strategy_code.py: 必须 `from select_fn import select_<slug>`"
        )
    if f"select_{expected_slug}" not in code:
        raise GenerationError(
            f"03_strategy_code.py: 必须 import select_{expected_slug}"
        )
    if "def main(" not in code:
        raise GenerationError("03_strategy_code.py: 必须定义 def main()")
    if f'PAPER_ID = "{paper_id}"' not in code and f"PAPER_ID = '{paper_id}'" not in code:
        # 容忍版本号差异：例如 paper_id=2604.07870 但代码里写 2604.07870v1
        if paper_id not in code:
            raise GenerationError(
                f"03_strategy_code.py: 缺少 PAPER_ID 字面量 {paper_id}"
            )
    if "run_research(" not in code:
        raise GenerationError("03_strategy_code.py: main() 里必须调用 run_research(...)")
    # Strategy 代码允许 import sys（要把 SRC 加入 path），单独允许
    _check_denylist(code, "03_strategy_code.py")
    _check_imports(
        code,
        "03_strategy_code.py",
        extra_allowed={"sys", "pathlib"},  # path 操作允许
    )


def _build_prompt(meta: PaperMeta, paper_md: str, applicability_md: str) -> str:
    return load_prompt(
        "generate.md",
        paper_id=meta.arxiv_id,
        paper_title=meta.title,
        paper_md=_trim(paper_md),
        applicability_md=applicability_md.strip() or "_缺失，按论文摘要自行判断_",
        example_skew_select_fn=load_example("legacy/skew_dispersion_select_fn.py"),
        example_centrality_select_fn=load_example("legacy/centrality_select_fn.py"),
    )


def _parse_two_blocks(raw: str) -> tuple[str, str]:
    blocks = extract_all_python_blocks(raw)
    if len(blocks) < 2:
        raise GenerationError(
            f"LLM 未输出 2 个 ```python``` 代码块，实际={len(blocks)}"
        )
    select_fn_code, strategy_code = blocks[0], blocks[1]
    return select_fn_code, strategy_code


def _validate_pair(select_fn_code: str, strategy_code: str, paper_id: str) -> str:
    _check_denylist(select_fn_code, "select_fn.py")
    _check_imports(select_fn_code, "select_fn.py")
    slug = _check_select_fn(select_fn_code)
    _check_strategy_code(strategy_code, slug, paper_id)
    return slug


def run_generate(config: PipelineConfig, meta: PaperMeta, paper_dir: Path) -> PaperMeta:
    paper_md_path = Path(meta.paper_md_path) if meta.paper_md_path else paper_dir / "01_paper.md"
    applicability_path = paper_dir / "02_applicability.md"
    if not paper_md_path.exists():
        raise FileNotFoundError(f"01_paper.md 不存在: {paper_md_path}")

    paper_md = paper_md_path.read_text(encoding="utf-8")
    applicability_md = applicability_path.read_text(encoding="utf-8") if applicability_path.exists() else ""

    client = LLMClient()
    prompt = _build_prompt(meta, paper_md, applicability_md)

    last_error: Optional[str] = None
    for attempt in range(1, 4):
        try:
            logger.info("[generate] %s LLM attempt %d/3", meta.arxiv_id, attempt)
            raw = client.chat(prompt, max_retries=2)
            select_fn_code, strategy_code = _parse_two_blocks(raw)
            slug = _validate_pair(select_fn_code, strategy_code, meta.arxiv_id)

            select_fn_path = paper_dir / "select_fn.py"
            strategy_path = paper_dir / "03_strategy_code.py"
            select_fn_path.write_text(select_fn_code + "\n", encoding="utf-8")
            strategy_path.write_text(strategy_code + "\n", encoding="utf-8")

            meta.extras["slug"] = slug
            meta.extras["generate_attempt"] = attempt
            meta.transition("generated")
            save_meta(paper_dir, meta)
            logger.info("[generate] %s 成功，slug=%s", meta.arxiv_id, slug)
            return meta
        except (GenerationError, RuntimeError) as exc:
            last_error = str(exc)
            logger.warning("[generate] %s attempt %d 失败: %s", meta.arxiv_id, attempt, exc)

    meta.transition("quarantined")
    meta.last_error = last_error
    save_meta(paper_dir, meta)
    logger.error("[generate] %s 经 3 次重试仍失败，标记 quarantined", meta.arxiv_id)
    return meta
