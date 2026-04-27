"""端到端研究流程：拉数据 → 跑策略 + 基线 → ablation → 输出。"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from ..baselines.baseline_spec import BaselineSpec, build_baseline_targets
from ..data.dynamic_universe import DynamicLiquidUniverse
from ..data.panel_loader import PanelLoader, PricePanels
from ..data.tradability_mask import TradabilityMask
from ..engine.cost_model import AshareCostModel, CostModel
from ..engine.vectorized_simulator import VectorizedSimulator, SimulationResult
from ..io.csv_writer import dump_artifacts
from ..io.report_writer import write_summary_markdown
from ..io.chart_writer import save_equity_drawdown_chart
from ..metrics.performance import compute_performance, PerformanceReport
from ..signals.rebalance import rebalance_dates_for
from .grid_ablation import run_grid_ablation
from .specs import SelectFnContext, SelectionResult, StrategySpec


logger = logging.getLogger(__name__)


@dataclass
class ResearchOutcome:
    paper_id: str
    strategy_report: PerformanceReport
    baseline_reports: dict[str, PerformanceReport]
    train_holdout_reports: dict[str, PerformanceReport]
    ablation_train: pd.DataFrame
    ablation_holdout: pd.DataFrame
    best_params: dict
    artifacts: list[str] = field(default_factory=list)


def _report_to_dict(report: PerformanceReport) -> dict:
    d = asdict(report)
    cleaned: dict = {}
    for k, v in d.items():
        if isinstance(v, float) and not np.isfinite(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


def _dump_jsons(
    output_dir: Path,
    *,
    spec: StrategySpec,
    strat_report: PerformanceReport,
    baseline_reports: dict[str, PerformanceReport],
    train_holdout_reports: dict[str, PerformanceReport],
    best_params: dict,
) -> None:
    """落盘机器可读指标，给跨论文 aggregator 使用。"""
    meta = {
        "paper_id": spec.paper_id,
        "paper_title": spec.paper_title,
        "methodology": spec.methodology,
        "strategy_name": spec.strategy_name,
        "rebalance_freq": spec.rebalance.freq,
        "best_params": best_params,
    }
    (output_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    (output_dir / "performance.json").write_text(
        json.dumps(_report_to_dict(strat_report), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    if baseline_reports:
        baselines_payload = {name: _report_to_dict(rep) for name, rep in baseline_reports.items()}
        (output_dir / "baselines_metrics.json").write_text(
            json.dumps(baselines_payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    for label, rep in train_holdout_reports.items():
        if "Train" in label:
            fname = "performance_train.json"
        elif "Holdout" in label:
            fname = "performance_holdout.json"
        else:
            fname = f"performance_{label.lower()}.json"
        (output_dir / fname).write_text(
            json.dumps(_report_to_dict(rep), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )


def _setup_logger(paper_id: str) -> logging.Logger:
    lg = logging.getLogger(f"research.{paper_id}")
    if not lg.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(f"[{paper_id}] %(levelname)s %(message)s"))
        lg.addHandler(handler)
        lg.setLevel(logging.INFO)
        lg.propagate = False
    return lg


def _build_simulator(
    panels: PricePanels,
    *,
    cost_model: Optional[CostModel],
    cash_rate_annual: float,
    execution: str,
    max_single_weight: float,
) -> VectorizedSimulator:
    return VectorizedSimulator(
        panels=panels,
        tradability=TradabilityMask.from_panels(panels),
        cost_model=cost_model or AshareCostModel(),
        cash_rate_annual=cash_rate_annual,
        execution=execution,  # type: ignore[arg-type]
        max_single_weight=max_single_weight,
    )


def _build_benchmark_returns(
    spec: StrategySpec,
    panels: PricePanels,
    universe: DynamicLiquidUniverse,
    rebalance_dates: list[pd.Timestamp],
    simulator: VectorizedSimulator,
) -> pd.Series:
    """用"同池等权全持"作为默认基准。"""
    from ..baselines import equal_weight_universe_weights

    target = equal_weight_universe_weights(
        panels=panels,
        universe=universe,
        rebalance_dates=rebalance_dates,
    )
    res = simulator.simulate(target)
    return res.daily_returns


def run_research(
    spec: StrategySpec,
    *,
    output_dir: Path,
    panel_loader: Optional[PanelLoader] = None,
    universe: Optional[DynamicLiquidUniverse] = None,
    baselines: Optional[list[BaselineSpec]] = None,
    cost_model: Optional[CostModel] = None,
    cash_rate_annual: float = 0.02,
    execution: str = "next_open",
    risk_free_annual: float = 0.02,
    do_ablation: bool = True,
    ablation_top_k: int = 5,
) -> ResearchOutcome:
    paper_id = spec.paper_id
    lg = _setup_logger(paper_id)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    full_start = spec.train_holdout.train_start
    full_end = spec.train_holdout.holdout_end

    if universe is None:
        universe = DynamicLiquidUniverse(
            spec=spec.universe_spec,
            start_date=full_start,
            end_date=full_end,
        )

    lg.info("Step 1/6 构建动态股票池 (top_n=%d)", spec.universe_spec.top_n)
    union_symbols = universe.union_symbols()
    lg.info("Step 1/6 池子并集: %d 只股票", len(union_symbols))

    if panel_loader is None:
        panel_loader = PanelLoader()
    lg.info("Step 2/6 加载价格面板 %s ~ %s", full_start, full_end)
    panels = panel_loader.load_panels(union_symbols, full_start, full_end)
    lg.info("Step 2/6 面板大小 = %d 日 x %d 只", panels.close_adj.shape[0], panels.close_adj.shape[1])

    rebalance_dates = rebalance_dates_for(
        panels.close_adj.index,
        freq=spec.rebalance.freq,
        warmup_days=spec.rebalance.warmup_days,
    )
    lg.info("Step 3/6 调仓日: %d 次 (freq=%s)", len(rebalance_dates), spec.rebalance.freq)

    simulator = _build_simulator(
        panels,
        cost_model=cost_model,
        cash_rate_annual=cash_rate_annual,
        execution=execution,
        max_single_weight=spec.rebalance.max_single_weight,
    )

    benchmark_returns = _build_benchmark_returns(
        spec, panels, universe, rebalance_dates, simulator
    )

    context = SelectFnContext(
        panels=panels,
        universe=universe,
        rebalance_dates=rebalance_dates,
    )

    lg.info("Step 4/6 跑策略 (默认参数)")
    selection = spec.select_fn(context, dict(spec.select_params))
    if not isinstance(selection, SelectionResult):
        raise TypeError(
            f"{paper_id} select_fn 必须返回 SelectionResult，实际={type(selection).__name__}"
        )
    strat_result = simulator.simulate(selection.target_weights)
    strat_report = compute_performance(
        strat_result.daily_returns,
        benchmark_returns=benchmark_returns,
        risk_free_annual=risk_free_annual,
        holdings=strat_result.holdings,
        rebalance_log=strat_result.rebalance_log,
    )
    dump_artifacts(output_dir, strat_result, signal_df=selection.signal_df)

    lg.info("Step 5/6 跑基线对比")
    baseline_reports: dict[str, PerformanceReport] = {}
    baseline_results: dict[str, SimulationResult] = {}
    for baseline_spec in baselines or []:
        try:
            target = build_baseline_targets(
                baseline_spec,
                panels=panels,
                universe=universe,
                rebalance_dates=rebalance_dates,
            )
            res = simulator.simulate(target)
            baseline_results[baseline_spec.name] = res
            baseline_reports[baseline_spec.name] = compute_performance(
                res.daily_returns,
                benchmark_returns=benchmark_returns,
                risk_free_annual=risk_free_annual,
                holdings=res.holdings,
                rebalance_log=res.rebalance_log,
            )
            dump_artifacts(output_dir, res, prefix=f"baseline_{baseline_spec.name}_")
        except Exception as exc:  # noqa: BLE001
            lg.warning("基线 %s 失败: %s", baseline_spec.name, exc)

    # Train / Holdout 切分（只是把全期 daily_returns 做窗口报告）
    train_w = spec.train_holdout
    train_rets = strat_result.daily_returns.loc[
        (strat_result.daily_returns.index >= pd.Timestamp(train_w.train_start))
        & (strat_result.daily_returns.index <= pd.Timestamp(train_w.train_end))
    ]
    holdout_rets = strat_result.daily_returns.loc[
        (strat_result.daily_returns.index >= pd.Timestamp(train_w.holdout_start))
        & (strat_result.daily_returns.index <= pd.Timestamp(train_w.holdout_end))
    ]
    bench_train = benchmark_returns.loc[train_rets.index].dropna() if not train_rets.empty else None
    bench_holdout = benchmark_returns.loc[holdout_rets.index].dropna() if not holdout_rets.empty else None
    train_holdout_reports: dict[str, PerformanceReport] = {}
    if not train_rets.empty:
        train_holdout_reports["Train(2019-2021)"] = compute_performance(
            train_rets,
            benchmark_returns=bench_train,
            risk_free_annual=risk_free_annual,
            holdings=strat_result.holdings.loc[train_rets.index],
            rebalance_log=strat_result.rebalance_log[
                strat_result.rebalance_log["date"].between(
                    pd.Timestamp(train_w.train_start), pd.Timestamp(train_w.train_end)
                )
            ] if not strat_result.rebalance_log.empty else strat_result.rebalance_log,
        )
    if not holdout_rets.empty:
        train_holdout_reports["Holdout(2022-2024)"] = compute_performance(
            holdout_rets,
            benchmark_returns=bench_holdout,
            risk_free_annual=risk_free_annual,
            holdings=strat_result.holdings.loc[holdout_rets.index],
            rebalance_log=strat_result.rebalance_log[
                strat_result.rebalance_log["date"].between(
                    pd.Timestamp(train_w.holdout_start), pd.Timestamp(train_w.holdout_end)
                )
            ] if not strat_result.rebalance_log.empty else strat_result.rebalance_log,
        )

    ablation_train = pd.DataFrame()
    ablation_holdout = pd.DataFrame()
    best_params: dict = {}
    if do_ablation and spec.param_grid:
        lg.info("Step 6a/6 跑 Grid Ablation: %d 维", len(spec.param_grid))
        ablation_train, best_params, ablation_holdout = run_grid_ablation(
            base_params=dict(spec.select_params),
            grid=spec.param_grid,
            select_fn=spec.select_fn,
            context=context,
            simulator=simulator,
            train_window=(train_w.train_start, train_w.train_end),
            holdout_window=(train_w.holdout_start, train_w.holdout_end),
            benchmark_returns=benchmark_returns,
            risk_free_annual=risk_free_annual,
            grid_filter=spec.param_grid_filter,
            top_k=ablation_top_k,
        )
        if not ablation_train.empty:
            ablation_train.to_csv(output_dir / "ablation_train.csv", index=False)
        if not ablation_holdout.empty:
            ablation_holdout.to_csv(output_dir / "ablation_holdout.csv", index=False)

    lg.info("Step 6/6 写报告与图表")
    chart_path = output_dir / "equity_drawdown.png"
    save_equity_drawdown_chart(
        chart_path,
        equity_curve=strat_result.equity_curve,
        benchmark_equity=(1.0 + benchmark_returns).cumprod(),
        title=f"Paper {spec.paper_id} - Strategy vs Benchmark",
    )

    summary_path = output_dir / "04_backtest_summary.md"
    artifacts = [
        "equity_curve.csv",
        "daily_returns.csv",
        "holdings.csv",
        "invested_exposure.csv",
        "rebalance_log.csv",
        "equity_drawdown.png",
    ]
    if selection.signal_df is not None:
        artifacts.append("signals.csv")
    if not ablation_train.empty:
        artifacts.append("ablation_train.csv")
    if not ablation_holdout.empty:
        artifacts.append("ablation_holdout.csv")
    for bname in baseline_reports:
        artifacts.append(f"baseline_{bname}_equity_curve.csv")

    ablation_top_table = ablation_train.head(ablation_top_k) if not ablation_train.empty else None

    write_summary_markdown(
        summary_path,
        title=spec.strategy_name,
        paper_id=spec.paper_id,
        paper_title=spec.paper_title,
        methodology=spec.methodology,
        notes=spec.notes,
        strategy_report=strat_report,
        baseline_reports=baseline_reports,
        train_holdout_reports=train_holdout_reports,
        ablation_top=ablation_top_table,
        artifacts=artifacts,
    )
    lg.info("写入摘要: %s", summary_path)

    _dump_jsons(
        output_dir,
        spec=spec,
        strat_report=strat_report,
        baseline_reports=baseline_reports,
        train_holdout_reports=train_holdout_reports,
        best_params=best_params,
    )

    return ResearchOutcome(
        paper_id=paper_id,
        strategy_report=strat_report,
        baseline_reports=baseline_reports,
        train_holdout_reports=train_holdout_reports,
        ablation_train=ablation_train,
        ablation_holdout=ablation_holdout,
        best_params=best_params,
        artifacts=artifacts,
    )
