"""Prompt 模板加载工具。

模板使用 Python ``str.format`` 风格的 ``{paper_title}`` / ``{paper_md}`` 占位符。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


_PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str, **vars: Any) -> str:
    path = _PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"未找到 prompt 模板: {path}")
    template = path.read_text(encoding="utf-8")
    if not vars:
        return template
    # 用 .format_map 但要先把 {} 转义；我们模板里就用 {var}。
    return template.format(**vars)


def load_example(rel_path: str) -> str:
    path = _PROMPTS_DIR / "examples" / rel_path
    if not path.exists():
        raise FileNotFoundError(f"未找到示例文件: {path}")
    return path.read_text(encoding="utf-8")
