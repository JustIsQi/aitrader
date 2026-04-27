"""OpenAI 兼容 LLM 客户端。

配置优先级：
1. ``LLM_API_KEY`` / ``LLM_BASE_URL`` / ``LLM_MODEL`` 环境变量
2. 仓库根目录 ``model.py`` 里 hardcode 的兜底（小蝶 AI gpt-5.4）

支持指数退避重试 + JSON / Python 代码两种 response 类型。
"""
from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


_FALLBACK_API_KEY = "sk-qnmG4UoLjPmJ8BfQ3iXPxPngOEQeQGGKwJY06hAij1qC92HD"
_FALLBACK_BASE_URL = "https://api.xiaocaseai.com/v1"
_FALLBACK_MODEL = "gpt-5.4"


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    timeout: int = 600
    max_completion_tokens: int = 32768
    temperature: float = 1.0

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            api_key=os.environ.get("LLM_API_KEY") or _FALLBACK_API_KEY,
            base_url=os.environ.get("LLM_BASE_URL") or _FALLBACK_BASE_URL,
            model=os.environ.get("LLM_MODEL") or _FALLBACK_MODEL,
            timeout=int(os.environ.get("LLM_TIMEOUT", "600")),
            max_completion_tokens=int(os.environ.get("LLM_MAX_TOKENS", "32768")),
            temperature=float(os.environ.get("LLM_TEMPERATURE", "1.0")),
        )


class LLMClient:
    """OpenAI Python SDK 兼容封装。"""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            try:
                from openai import OpenAI  # noqa: WPS433
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError(
                    "openai 包未安装；请运行 `pip install openai>=1.0`"
                ) from exc
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
        return self._client

    def chat(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        json_mode: bool = False,
        max_retries: int = 3,
        backoff_seconds: float = 5.0,
    ) -> str:
        """单轮 chat completion。

        - ``json_mode=True`` 时设置 ``response_format={"type":"json_object"}`` 强制 JSON。
        - 出错（含 RateLimit / Timeout / 5xx）按指数退避重试。
        """
        client = self._ensure_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_completion_tokens": self.config.max_completion_tokens,
            "timeout": self.config.timeout,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_exc: Optional[BaseException] = None
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "[llm] chat attempt %d/%d (model=%s, json=%s, prompt_len=%d)",
                    attempt, max_retries, self.config.model, json_mode, len(prompt),
                )
                response = client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                if not content.strip():
                    raise RuntimeError("LLM returned empty content")
                return content
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                wait = backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "[llm] attempt %d failed: %s; sleeping %.1fs",
                    attempt, exc, wait,
                )
                if attempt < max_retries:
                    time.sleep(wait)
        raise RuntimeError(f"LLM 调用 {max_retries} 次后仍失败: {last_exc}") from last_exc


_PY_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


def extract_python_block(text: str) -> Optional[str]:
    """从 LLM 输出里抽 ```python ... ``` 代码块；找不到返回 None。"""
    match = _PY_FENCE.search(text)
    if not match:
        return None
    return match.group(1).strip()


def extract_all_python_blocks(text: str) -> list[str]:
    """抽出全部 ```python ... ``` 代码块。"""
    return [m.group(1).strip() for m in _PY_FENCE.finditer(text)]
