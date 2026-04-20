"""
文档解析：封装 docu_assistant HTTP 接口 + US3 中转。

两个入口：
- docu_assistant(...)          保持原始 HTTP 调用，供其它脚本复用
- parse_pdf_via_api(pdf_path)  arxiv 流水线用，完整走「上传 US3 → 调接口 → 删 US3」

环境变量（均可覆盖默认值）:
    DOCU_API_URL        接口地址，默认内网
    DOCU_API_TOKEN      鉴权 token
    DOCU_US3_PREFIX     上传到 US3 的 key 前缀，默认 doc_parser/arxiv_pipeline
"""
from __future__ import annotations

import os
import sys
import json
import uuid
from pathlib import Path

import requests

# 同目录的 us3_tools。直接 python file_parse.py 时脚本目录已自动在 sys.path[0]；
# 被 arxiv_paper_pipeline.py 导入时那里也会把本目录加进去。
try:
    from us3_tools import US3Client
except ImportError:  # pragma: no cover
    US3Client = None  # type: ignore


# ── 默认值（可被 env 覆盖） ────────────────────────────────────────────────────
_DEFAULT_API_URL = "http://10.100.0.24:60307/docu_assistant"
_DEFAULT_API_TOKEN = "9NRR2ObzdC2x7K6BOXouvEtqvOdJ2AjR"
_DEFAULT_US3_PREFIX = "doc_parser/arxiv_pipeline"


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value else default


def docu_assistant(file_type: str, file_content: str,
                   api_url: str | None = None, token: str | None = None) -> dict:
    """调用 docu_assistant 接口，返回解析后的 JSON（含 data.markdown）。"""
    api_url = api_url or _env("DOCU_API_URL", _DEFAULT_API_URL)
    token   = token   or _env("DOCU_API_TOKEN", _DEFAULT_API_TOKEN)

    request_data = {
        "file_type": file_type,
        "file_content": file_content,
        "title_level_parser": False,
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.post(url=api_url, json=request_data, headers=headers, timeout=900)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"接口请求失败: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("接口返回的不是合法 JSON 数据") from exc


def parse_pdf_via_api(pdf_path: Path,
                      us3_prefix: str | None = None,
                      keep_remote: bool = False) -> str:
    """
    arxiv 流水线专用：上传本地 PDF 到 US3 → 调 docu_assistant → 删除 US3 → 返回 markdown。

    失败时抛 RuntimeError，上层可以 fallback 到 pdfplumber。
    """
    if US3Client is None:
        raise RuntimeError("us3_tools.US3Client 不可用：请先 pip install ufile")

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise RuntimeError(f"PDF 不存在: {pdf_path}")

    prefix = us3_prefix or _env("DOCU_US3_PREFIX", _DEFAULT_US3_PREFIX)
    object_key = f"{prefix.rstrip('/')}/{uuid.uuid4().hex}_{pdf_path.name}"

    client = US3Client()

    # 1. 上传
    ok = client.upload_file(str(pdf_path), object_key)
    if not ok:
        raise RuntimeError(f"上传 US3 失败: {object_key}")

    try:
        # 2. 调接口
        resp = docu_assistant(file_type="pdf", file_content=object_key)
        code = resp.get("code")
        markdown = (resp.get("data") or {}).get("markdown", "")
        if code not in (0, 200, "0", "200") or not markdown:
            raise RuntimeError(f"接口返回异常 code={code}, markdown 长度={len(markdown)}")
        return markdown
    finally:
        # 3. 删除 US3 上的临时文件（失败只告警，不影响返回）
        if not keep_remote:
            try:
                client.delete_dir(object_key)
            except Exception as exc:
                print(f"  [warn] 删除 US3 对象失败 {object_key}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    # 最小 smoke test：python file_parse.py <local_pdf>
    if len(sys.argv) < 2:
        print("用法: python file_parse.py <local_pdf>")
        sys.exit(1)
    md = parse_pdf_via_api(Path(sys.argv[1]))
    print(f"解析成功，字符数 {len(md):,}")
    print(md[:500])
