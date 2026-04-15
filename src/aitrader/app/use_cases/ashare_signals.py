"""
A股策略信号生成 Use Case

功能:
1. 运行所有A股选股策略回测
2. 存储回测结果到数据库
3. 生成当前交易信号
4. 将信号与回测报告关联
"""

from __future__ import annotations

import importlib
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from aitrader.infrastructure.config.logging import logger

from aitrader.domain.backtest.engine import Engine
from aitrader.domain.backtest.utils import extract_backtest_metrics
from aitrader.domain.strategy.loader import StrategyLoader
from aitrader.infrastructure.db.db_manager import get_db
from aitrader.domain.signal.generator import MultiStrategySignalGenerator


def run_single_strategy_backtest(strategy_info: Tuple[str, str, str, str]) -> Optional[Dict]:
    """
    运行单个策略的回测（用于线程池并发执行）

    Args:
        strategy_info: (display_name, module_name, func_name, version)

    Returns:
        包含回测结果的字典，失败返回 None
    """
    display_name, module_name, func_name, version = strategy_info
    start_time = time.time()

    try:
        logger.info(f"▶ [{display_name}] 开始回测...")

        module = importlib.import_module(module_name)
        strategy_func = getattr(module, func_name)

        task = strategy_func()

        backtest_start = time.time()
        engine = Engine()
        result = engine.run(task)
        backtest_elapsed = time.time() - backtest_start
        logger.info(f"  [{display_name}] 回测完成, 耗时 {backtest_elapsed:.2f}秒")

        metrics = extract_backtest_metrics(result, task)
        metrics['strategy_name'] = display_name
        metrics['strategy_version'] = version
        metrics['asset_type'] = 'ashare'

        db = get_db()
        backtest_id = db.save_backtest_result(**metrics)

        total_elapsed = time.time() - start_time

        if backtest_id:
            logger.success(
                f"✓ [{display_name}] 完成! 耗时 {total_elapsed:.2f}秒 | "
                f"收益率={metrics.get('total_return', 0):.2f}% | "
                f"夏普比率={metrics.get('sharpe_ratio', 0):.2f} | "
                f"回撤={metrics.get('max_drawdown', 0):.2f}%"
            )
            return {
                'display_name': display_name,
                'backtest_id': backtest_id,
                'metrics': metrics,
                'success': True,
            }
        else:
            logger.error(f"✗ [{display_name}] 数据库保存失败")
            return None

    except Exception as e:
        total_elapsed = time.time() - start_time
        logger.error(f"✗ [{display_name}] 回测失败 ({total_elapsed:.2f}秒): {e}")
        logger.debug(f"  错误详情:\n{traceback.format_exc()}")
        return None


class AShareSignalPipeline:
    """A股策略信号生成管道"""

    def __init__(
        self,
        mode: str = 'all',
        force_backtest: bool = False,
        max_workers: int | None = None,
        enable_smart_filter: bool = True,
        filter_config=None,
        adjust_type: str = 'qfq',
    ):
        self.db = get_db()
        self.signal_generator = MultiStrategySignalGenerator(
            enable_smart_filter=enable_smart_filter,
            filter_config=filter_config,
            adjust_type=adjust_type,
        )
        self.force_backtest = force_backtest
        self.mode = mode
        self.enable_smart_filter = enable_smart_filter
        self.filter_config = filter_config
        self.adjust_type = adjust_type

        if max_workers is None:
            self.max_workers = 2
        else:
            self.max_workers = min(max_workers, 3)

        self.backtest_results: Dict = {}
        logger.info(f"A股策略管道初始化: 并发线程数={self.max_workers}")

    def _load_existing_backtests(self, strategy_names: List[str]) -> Dict:
        existing = {}
        for strategy_name in strategy_names:
            try:
                backtest = self.db.get_latest_backtest(strategy_name, asset_type='ashare')
                if backtest:
                    existing[strategy_name] = {
                        'backtest_id': backtest['id'],
                        'metrics': backtest,
                    }
                    logger.info(f"  ✓ 找到现有回测: {strategy_name} (ID: {backtest['id']})")
                else:
                    logger.warning(f"  ✗ 未找到回测: {strategy_name}")
            except Exception as e:
                logger.warning(f"  ✗ 查询回测失败 {strategy_name}: {e}")
        return existing

    def run_ashare_backtests(self, version_filter: str | None = None) -> Dict:
        overall_start = time.time()

        logger.info("=" * 70)
        if version_filter:
            logger.info(f"开始运行A股策略回测 (版本: {version_filter})...")
        else:
            logger.info("开始运行A股策略回测...")
        logger.info("=" * 70)

        loader = StrategyLoader()
        if version_filter:
            strategies = loader.load_ashare_strategies_by_version(version_filter)
        else:
            strategies = loader.load_ashare_strategies()

        if not strategies:
            logger.warning(f"未发现匹配的策略 (version={version_filter})")
            return {}

        total = len(strategies)
        logger.info(f"✓ 发现 {total} 个A股策略, 使用 {self.max_workers} 线程并发")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_strategy = {
                executor.submit(run_single_strategy_backtest, info): info[0]
                for info in strategies
            }

            completed, success_count = 0, 0
            failed: List[str] = []

            for future in as_completed(future_to_strategy):
                name = future_to_strategy[future]
                completed += 1
                try:
                    result = future.result()
                    if result and result.get('success'):
                        success_count += 1
                        self.backtest_results[result['display_name']] = {
                            'backtest_id': result['backtest_id'],
                            'metrics': result['metrics'],
                        }
                    else:
                        failed.append(name)
                except Exception:
                    failed.append(name)

                logger.info(f"进度: [{completed}/{total}] 成功={success_count} 失败={len(failed)}")

        elapsed = time.time() - overall_start
        logger.info(f"回测完成! {total}策略 成功{success_count} 失败{len(failed)} "
                     f"耗时{elapsed:.1f}秒")
        return self.backtest_results

    def generate_and_save_signals(self, version_filter: str | None = None):
        logger.info("开始生成交易信号...")

        try:
            current_positions = self.db.get_positions()
            all_signals = self.signal_generator.generate_signals(
                current_positions=current_positions,
                version_filter=version_filter,
            )

            if not all_signals:
                logger.warning("  没有生成任何信号")
                return

            if version_filter:
                all_signals = self._filter_signals_by_version(all_signals, version_filter)
                if not all_signals:
                    logger.warning(f"  没有找到 {version_filter} 版本的信号")
                    return

            signal_date = datetime.now().strftime('%Y-%m-%d')
            buy_count = sell_count = 0

            for strategy_name, signals in all_signals.items():
                backtest_info = self.backtest_results.get(strategy_name, {})
                backtest_id = backtest_info.get('backtest_id')

                for buy_signal in signals.buy_signals:
                    trader_id = self.db.insert_trader_signal(
                        symbol=buy_signal.symbol,
                        signal_type='buy',
                        strategies=[strategy_name],
                        signal_date=signal_date,
                        price=buy_signal.price,
                        score=buy_signal.score,
                        rank=buy_signal.rank,
                        quantity=buy_signal.suggested_quantity,
                        asset_type='ashare',
                    )
                    if trader_id and backtest_id:
                        self.db.associate_signal_with_backtest(
                            trader_id=trader_id,
                            backtest_id=backtest_id,
                            strategy_name=strategy_name,
                        )
                    buy_count += 1

                for sell_signal in signals.sell_signals:
                    trader_id = self.db.insert_trader_signal(
                        symbol=sell_signal.symbol,
                        signal_type='sell',
                        strategies=[strategy_name],
                        signal_date=signal_date,
                        price=sell_signal.current_price,
                        asset_type='ashare',
                    )
                    if trader_id and backtest_id:
                        self.db.associate_signal_with_backtest(
                            trader_id=trader_id,
                            backtest_id=backtest_id,
                            strategy_name=strategy_name,
                        )
                    sell_count += 1

            logger.success(f"  ✓ 保存信号: {buy_count}个买入, {sell_count}个卖出")

        except Exception as e:
            logger.error(f"  信号生成失败: {e}")
            traceback.print_exc()

    def _filter_signals_by_version(self, signals: Dict, version: str) -> Dict:
        loader = StrategyLoader()
        strategies = loader.load_ashare_strategies()
        name_to_version = {s[0]: s[3] for s in strategies}
        filtered = {
            name: sigs
            for name, sigs in signals.items()
            if name_to_version.get(name) == version
        }
        logger.info(f"过滤信号: {len(signals)} -> {len(filtered)} (version={version})")
        return filtered

    def _run_signal_only_mode(self, version_filter: str | None = None):
        loader = StrategyLoader()
        if version_filter:
            strategies = loader.load_ashare_strategies_by_version(version_filter)
        else:
            strategies = loader.load_ashare_strategies()

        strategy_names = [s[0] for s in strategies]
        self.backtest_results = self._load_existing_backtests(strategy_names)
        self.generate_and_save_signals(version_filter=version_filter)

    def _run_version_mode(self, version: str):
        logger.info(f"【{version.upper()}策略模式】回测 + 信号生成")
        self.run_ashare_backtests(version_filter=version)
        self.generate_and_save_signals(version_filter=version)

    def run(self):
        logger.info("=" * 60)
        logger.info(f"A股策略信号生成管道启动 (mode={self.mode})")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        if self.mode == 'signal-weekly':
            self._run_signal_only_mode(version_filter='weekly')
        elif self.mode == 'signal-all':
            self._run_signal_only_mode(version_filter=None)
        elif self.mode in ['weekly', 'monthly']:
            self._run_version_mode(self.mode)
        else:
            self.run_ashare_backtests()
            self.generate_and_save_signals()

        logger.info("=" * 60)
        logger.info("A股策略管道执行完成")
        logger.info("=" * 60)
