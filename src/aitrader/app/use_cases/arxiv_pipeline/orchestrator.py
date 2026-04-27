"""端到端编排器。

调用顺序：fetch → judge → generate → backtest → aggregate。
每篇论文按 ``00_meta.json`` 的 status 决定从哪一步开始；任意一步失败只记录错误，
其它论文继续推进，aggregate 在最后无论如何都会跑（除非显式 ``--steps`` 排除）。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .state import PaperMeta, list_processed, load_meta, save_meta


logger = logging.getLogger(__name__)


DEFAULT_STEPS: tuple[str, ...] = ("fetch", "judge", "generate", "backtest", "aggregate")
ALL_STEPS = set(DEFAULT_STEPS)


_SINCE_RE = re.compile(r"^(?P<num>\d+)(?P<unit>[dhwmy])$", re.IGNORECASE)


def parse_since(value: str) -> timedelta:
    """支持 ``14d`` / ``2w`` / ``720h`` / ``1m``（=30d）/ ``1y``（=365d）。"""
    if not value:
        raise ValueError("--since 不能为空")
    m = _SINCE_RE.match(value.strip())
    if not m:
        raise ValueError(
            f"无法解析 --since={value!r}；支持格式如 14d / 2w / 720h / 1m / 1y"
        )
    num = int(m.group("num"))
    unit = m.group("unit").lower()
    if unit == "d":
        return timedelta(days=num)
    if unit == "h":
        return timedelta(hours=num)
    if unit == "w":
        return timedelta(weeks=num)
    if unit == "m":
        return timedelta(days=num * 30)
    if unit == "y":
        return timedelta(days=num * 365)
    raise ValueError(f"未知时间单位: {unit}")


def find_repo_root(start: Path) -> Path:
    """向上查找 pyproject.toml；找不到时返回 start 本身。"""
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return start


@dataclass
class PipelineConfig:
    """编排器配置。"""

    repo_root: Path
    steps: tuple[str, ...] = DEFAULT_STEPS
    since: timedelta = timedelta(days=14)
    max_papers: int = 20
    paper_ids: list[str] = field(default_factory=list)
    rerun: bool = False
    rerun_legacy: bool = False
    no_llm: bool = False
    dry_run: bool = False
    backtest_window_days: int = 365
    min_rating: int = 3

    @property
    def papers_dir(self) -> Path:
        return self.repo_root / "papers" / "arxiv"

    @property
    def processed_dir(self) -> Path:
        return self.repo_root / "papers" / "arxiv" / "processed"

    @property
    def aggregate_dir(self) -> Path:
        return self.processed_dir / "_aggregate"


# ── Step 协议 ─────────────────────────────────────────────────────────────────
# 各 step 是 callable: (config, meta, paper_dir) -> PaperMeta
# fetch 是特例：不接受 meta 参数（输出新的 meta）；放在 orchestrator 里特殊处理。


class Orchestrator:
    """主编排逻辑。"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.config.processed_dir.mkdir(parents=True, exist_ok=True)
        self.config.papers_dir.mkdir(parents=True, exist_ok=True)
        self.config.aggregate_dir.mkdir(parents=True, exist_ok=True)

    # ── 入口 ──
    def run(self) -> dict:
        cfg = self.config
        logger.info(
            "Pipeline 启动: steps=%s since=%s max_papers=%d rerun=%s no_llm=%s dry_run=%s",
            cfg.steps, cfg.since, cfg.max_papers, cfg.rerun, cfg.no_llm, cfg.dry_run,
        )

        targets: list[tuple[Path, PaperMeta]] = []

        if cfg.paper_ids:
            # 用户显式指定论文 → 只处理这些（fetch 也跳过，避免无关下载）
            targets.extend(self._collect_explicit_papers())
        else:
            # 1. fetch（除非显式排除；dry-run 时跳过真实下载/解析，只罗列已有论文）
            if "fetch" in cfg.steps and not cfg.dry_run:
                fetched = self._step_fetch()
                targets.extend(fetched)
            # 2. rerun-legacy 模式或不跑 fetch / dry-run：把 processed_dir 下已有论文都加进 targets
            if cfg.rerun_legacy or "fetch" not in cfg.steps or cfg.dry_run:
                for entry in self._collect_all_existing():
                    if entry not in targets:
                        targets.append(entry)

        if cfg.dry_run:
            return self._dry_run_summary(targets)

        # 4. judge / generate / backtest 逐篇处理
        results = {"processed": 0, "skipped": 0, "quarantined": 0, "errors": 0}
        for paper_dir, meta in targets:
            try:
                meta = self._step_judge(meta, paper_dir)
                if meta.status == "skipped":
                    results["skipped"] += 1
                    continue
                meta = self._step_generate(meta, paper_dir)
                if meta.status == "quarantined":
                    results["quarantined"] += 1
                    continue
                meta = self._step_backtest(meta, paper_dir)
                results["processed"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("处理 %s 失败: %s", meta.arxiv_id, exc)
                meta.last_error = str(exc)
                save_meta(paper_dir, meta)
                results["errors"] += 1

        # 5. aggregate 总是兜底跑（如果在 steps 里）
        if "aggregate" in cfg.steps:
            self._step_aggregate()

        logger.info("Pipeline 完成: %s", results)
        return results

    # ── 内部 step 包装 ──
    def _step_fetch(self) -> list[tuple[Path, PaperMeta]]:
        from .steps.fetch import run_fetch
        return run_fetch(self.config)

    def _step_judge(self, meta: PaperMeta, paper_dir: Path) -> PaperMeta:
        if "judge" not in self.config.steps or self.config.no_llm:
            return meta
        if meta.status not in {"new", "fetched"} and not self.config.rerun:
            return meta
        from .steps.judge import run_judge
        return run_judge(self.config, meta, paper_dir)

    def _step_generate(self, meta: PaperMeta, paper_dir: Path) -> PaperMeta:
        if "generate" not in self.config.steps or self.config.no_llm:
            return meta
        if meta.status not in {"judged", "skipped"} and not self.config.rerun:
            return meta
        if meta.status == "skipped":
            return meta
        from .steps.generate import run_generate
        return run_generate(self.config, meta, paper_dir)

    def _step_backtest(self, meta: PaperMeta, paper_dir: Path) -> PaperMeta:
        if "backtest" not in self.config.steps:
            return meta
        if meta.status not in {"generated", "backtested"} and not self.config.rerun:
            return meta
        from .steps.backtest import run_backtest
        return run_backtest(self.config, meta, paper_dir)

    def _step_aggregate(self) -> None:
        from .steps.aggregate import run_aggregate
        run_aggregate(self.config)

    # ── 收集 targets 的辅助 ──
    def _collect_explicit_papers(self) -> list[tuple[Path, PaperMeta]]:
        out: list[tuple[Path, PaperMeta]] = []
        for paper_id in self.config.paper_ids:
            paper_dir = self.config.processed_dir / paper_id
            meta = load_meta(paper_dir)
            if meta is None:
                logger.warning("paper_id=%s 在 processed_dir 下未找到，需要先 fetch", paper_id)
                continue
            out.append((paper_dir, meta))
        return out

    def _collect_all_existing(self) -> list[tuple[Path, PaperMeta]]:
        out: list[tuple[Path, PaperMeta]] = []
        for meta in list_processed(self.config.processed_dir):
            paper_dir = self.config.processed_dir / meta.arxiv_id
            out.append((paper_dir, meta))
        return out

    def _dry_run_summary(self, targets: list[tuple[Path, PaperMeta]]) -> dict:
        logger.info("[dry-run] 共计划处理 %d 篇论文", len(targets))
        for _, meta in targets:
            logger.info(
                "[dry-run]   %s status=%s published=%s title=%s",
                meta.arxiv_id, meta.status, meta.published, meta.title[:60],
            )
        logger.info("[dry-run] 计划 steps=%s", self.config.steps)
        return {"dry_run": True, "targets": len(targets)}

    # ── 工厂 ──
    @classmethod
    def from_args(cls, args) -> "Orchestrator":
        repo_root = find_repo_root(Path.cwd())
        # 也支持外部把 repo_root 作为参数传，CLI 入口没暴露这个口。
        steps_raw = (args.steps or ",".join(DEFAULT_STEPS)).split(",")
        steps = tuple(s.strip() for s in steps_raw if s.strip())
        for s in steps:
            if s not in ALL_STEPS:
                raise ValueError(f"未知 step={s}; 允许={sorted(ALL_STEPS)}")
        config = PipelineConfig(
            repo_root=repo_root,
            steps=steps,
            since=parse_since(args.since),
            max_papers=args.max_papers,
            paper_ids=list(args.paper or []),
            rerun=args.rerun,
            rerun_legacy=getattr(args, "rerun_legacy", False),
            no_llm=args.no_llm,
            dry_run=args.dry_run,
            backtest_window_days=getattr(args, "backtest_window_days", 365),
            min_rating=getattr(args, "min_rating", 3),
        )
        return cls(config)
