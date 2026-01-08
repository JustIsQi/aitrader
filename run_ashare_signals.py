#!/usr/bin/env python3
"""
A股策略信号生成管道

功能:
1. 运行所有A股选股策略回测
2. 存储回测结果到数据库
3. 生成当前交易信号
4. 将信号与回测报告关联

使用方法:
    python run_ashare_signals.py [--force-backtest] [--workers N]

作者: AITrader
日期: 2026-01-06
"""

import sys
import argparse
import os
from pathlib import Path
from datetime import datetime
import importlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple, Optional, Dict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger

# 配置日志输出
logger.remove()  # 移除默认 handler
logger.add(sys.stderr, level='INFO', format='<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>')
logger.add(project_root / 'logs' / 'ashare_pipeline.log', level='DEBUG', rotation='10 MB', retention='7 days')

from core.backtrader_engine import Engine
from core.backtest_utils import extract_backtest_metrics
from core.strategy_loader import StrategyLoader
from database.pg_manager import get_db
from signals.multi_strategy_signals import MultiStrategySignalGenerator


def run_single_strategy_backtest(strategy_info: Tuple[str, str, str, str]) -> Optional[Dict]:
    """
    运行单个策略的回测（用于线程池并发执行）

    Args:
        strategy_info: (display_name, module_name, func_name, version)

    Returns:
        Dict: 包含回测结果的字典，失败返回 None
    """
    display_name, module_name, func_name, version = strategy_info
    import time
    start_time = time.time()

    try:
        logger.info(f"▶ [{display_name}] 开始回测...")

        # 步骤1: 导入策略函数
        logger.debug(f"  [{display_name}] 步骤1/4: 导入策略模块 {module_name}.{func_name}")
        module = importlib.import_module(module_name)
        strategy_func = getattr(module, func_name)

        # 步骤2: 创建策略配置
        logger.debug(f"  [{display_name}] 步骤2/4: 创建策略配置")
        task = strategy_func()
        logger.debug(f"  [{display_name}] 策略配置: {task.name}, 股票池={len(task.stocks) if hasattr(task, 'stocks') else 'N/A'}")

        # 步骤3: 运行回测
        logger.info(f"  [{display_name}] 步骤3/4: 执行回测 (可能需要较长时间)")
        backtest_start = time.time()
        engine = Engine()
        result = engine.run(task)
        backtest_elapsed = time.time() - backtest_start
        logger.info(f"  [{display_name}] 回测完成, 耗时 {backtest_elapsed:.2f}秒")

        # 步骤4: 提取指标并保存
        logger.debug(f"  [{display_name}] 步骤4/4: 提取指标并保存到数据库")
        metrics = extract_backtest_metrics(result, task)

        # 添加额外信息
        metrics['strategy_name'] = display_name
        metrics['strategy_version'] = version
        metrics['asset_type'] = 'ashare'

        # 保存到数据库（线程共享同一个连接池，但每个请求有自己的会话）
        db = get_db()
        backtest_id = db.save_backtest_result(**metrics)

        total_elapsed = time.time() - start_time

        if backtest_id:
            logger.success(f"✓ [{display_name}] 全部完成! 总耗时 {total_elapsed:.2f}秒 | "
                         f"收益率={metrics.get('total_return', 0):.2%} | "
                         f"夏普比率={metrics.get('sharpe_ratio', 0):.2f} | "
                         f"回撤={metrics.get('max_drawdown', 0):.2%}")
            return {
                'display_name': display_name,
                'backtest_id': backtest_id,
                'metrics': metrics,
                'success': True
            }
        else:
            logger.error(f"✗ [{display_name}] 数据库保存失败")
            return None

    except Exception as e:
        total_elapsed = time.time() - start_time
        logger.error(f"✗ [{display_name}] 回测失败 (耗时 {total_elapsed:.2f}秒): {e}")
        import traceback
        logger.debug(f"  错误详情:\n{traceback.format_exc()}")
        return None


class AShareSignalPipeline:
    """A股策略信号生成管道"""

    def __init__(self, mode='all', force_backtest=False, max_workers=None,
                 enable_smart_filter=True, filter_config=None):
        """
        初始化A股策略管道

        Args:
            mode: 运行模式 ('all', 'signal-only', 'weekly', 'monthly')
            force_backtest: 是否强制重新运行回测（忽略缓存）
            max_workers: 并发回测的最大线程数
            enable_smart_filter: 是否启用智能选股筛选 (默认True)
            filter_config: 筛选配置对象
        """
        self.db = get_db()
        self.signal_generator = MultiStrategySignalGenerator(
            enable_smart_filter=enable_smart_filter,
            filter_config=filter_config
        )
        self.force_backtest = force_backtest
        self.mode = mode
        self.enable_smart_filter = enable_smart_filter
        self.filter_config = filter_config

        # 使用线程池优化配置（针对I/O密集型任务）
        # 线程池可以安全地共享数据库连接池，不会有进程fork的问题
        # 计算公式：
        # - pool_size=5, max_overflow=10 → 每个进程最多15个连接
        # - 使用线程池：所有线程共享同一个连接池
        # - 推荐线程数：CPU核心数 × 2（对于I/O密集型任务）
        # - 最大限制：不超过 pool_size + max_overflow = 15
        # - 注意：由于数据加载较慢（使用代理），过多的并发会导致资源耗尽
        if max_workers is None:
            # 默认使用 3 个并发线程，避免数据加载时资源耗尽
            self.max_workers = 3
        else:
            # 用户指定时，最大不超过连接池大小
            self.max_workers = min(max_workers, 15)

        self.backtest_results = {}  # {strategy_name: backtest_id}
        logger.info(f"A股策略管道初始化: 并发线程数={self.max_workers} (使用线程池，I/O密集型优化)")

    def _load_existing_backtests(self, strategy_names):
        """
        从数据库加载现有的回测结果

        Args:
            strategy_names: 策略名称列表

        Returns:
            dict: {strategy_name: {'backtest_id': int, 'metrics': dict}}
        """
        existing = {}
        for strategy_name in strategy_names:
            try:
                backtest = self.db.get_latest_backtest(strategy_name, asset_type='ashare')
                if backtest:
                    existing[strategy_name] = {
                        'backtest_id': backtest['id'],
                        'metrics': backtest
                    }
                    logger.info(f"  ✓ 找到现有回测: {strategy_name} (ID: {backtest['id']})")
                else:
                    logger.warning(f"  ✗ 未找到回测: {strategy_name}")
            except Exception as e:
                logger.warning(f"  ✗ 查询回测失败 {strategy_name}: {e}")
        return existing

    def run_ashare_backtests(self, version_filter=None):
        """
        运行A股策略回测（使用线程池并发执行）

        Args:
            version_filter: 可选的版本过滤器 ('weekly', 'monthly' 等)
        """
        import time
        overall_start = time.time()

        logger.info("=" * 70)
        if version_filter:
            logger.info(f"开始运行A股策略回测 (版本: {version_filter})...")
        else:
            logger.info("开始运行A股策略回测...")
        logger.info("=" * 70)

        # 加载策略（支持版本过滤）
        loader = StrategyLoader()
        if version_filter:
            strategies = loader.load_ashare_strategies_by_version(version_filter)
            logger.info(f"过滤策略版本: {version_filter}")
        else:
            strategies = loader.load_ashare_strategies()

        if not strategies:
            logger.warning(f"未发现匹配的策略 (version={version_filter})")
            return {}

        total_strategies = len(strategies)
        logger.info(f"✓ 发现 {total_strategies} 个A股策略")
        logger.info(f"✓ 使用 {self.max_workers} 个线程并发执行")
        logger.info(f"✓ 策略列表: {', '.join([s[0] for s in strategies])}")
        logger.info("-" * 70)

        # 使用线程池并发执行回测（I/O密集型任务，线程池更合适）
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有策略到线程池
            future_to_strategy = {
                executor.submit(run_single_strategy_backtest, strategy_info): strategy_info[0]
                for strategy_info in strategies
            }

            logger.info(f"已提交所有 {total_strategies} 个策略到线程池，开始执行...\n")

            # 收集结果
            completed_count = 0
            success_count = 0
            failed_strategies = []

            for future in as_completed(future_to_strategy):
                strategy_name = future_to_strategy[future]
                completed_count += 1

                try:
                    result = future.result()
                    if result and result.get('success'):
                        success_count += 1
                        self.backtest_results[result['display_name']] = {
                            'backtest_id': result['backtest_id'],
                            'metrics': result['metrics']
                        }
                        # 进度提示（每完成一个都显示）
                        logger.info(f"进度: [{completed_count}/{total_strategies}] "
                                  f"成功={success_count} 失败={completed_count - success_count} | "
                                  f"最新: {result['display_name']}")
                    else:
                        failed_strategies.append(strategy_name)
                        logger.warning(f"进度: [{completed_count}/{total_strategies}] "
                                     f"成功={success_count} 失败={completed_count - success_count} | "
                                     f"✗ {strategy_name} 失败")

                except Exception as e:
                    failed_strategies.append(strategy_name)
                    logger.error(f"进度: [{completed_count}/{total_strategies}] "
                               f"成功={success_count} 失败={completed_count - success_count} | "
                               f"✗ {strategy_name} 异常: {e}")

        # 统计总耗时
        overall_elapsed = time.time() - overall_start
        avg_time = overall_elapsed / total_strategies

        logger.info("=" * 70)
        logger.info(f"回测批量执行完成!")
        logger.info(f"总计: {total_strategies} 个策略 | "
                   f"成功: {success_count} 个 | "
                   f"失败: {len(failed_strategies)} 个")
        logger.info(f"总耗时: {overall_elapsed:.2f}秒 ({overall_elapsed/60:.1f}分钟) | "
                   f"平均: {avg_time:.2f}秒/策略")

        if failed_strategies:
            logger.warning(f"失败的策略: {', '.join(failed_strategies)}")

        logger.info("=" * 70)
        return self.backtest_results

    def generate_and_save_signals(self, version_filter=None):
        """
        生成信号并保存到数据库

        Args:
            version_filter: 可选的版本过滤器 ('weekly', 'monthly' 等)
        """
        logger.info("开始生成交易信号...")

        try:
            # 获取当前持仓
            current_positions = self.db.get_positions()

            # 生成信号
            logger.info("  调用信号生成器...")
            all_signals = self.signal_generator.generate_signals(
                current_positions=current_positions,
                version_filter=version_filter
            )

            if not all_signals:
                logger.warning("  没有生成任何信号")
                return

            # 如果指定了版本过滤，则过滤信号
            if version_filter:
                all_signals = self._filter_signals_by_version(all_signals, version_filter)
                if not all_signals:
                    logger.warning(f"  没有找到 {version_filter} 版本的信号")
                    return

            # 保存信号并关联回测
            signal_date = datetime.now().strftime('%Y-%m-%d')
            buy_count = 0
            sell_count = 0

            for strategy_name, signals in all_signals.items():
                logger.info(f"  处理策略: {strategy_name}")

                # 获取该策略的回测ID
                backtest_info = self.backtest_results.get(strategy_name, {})
                backtest_id = backtest_info.get('backtest_id')

                # 保存买入信号
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
                        asset_type='ashare'
                    )

                    # 关联回测
                    if trader_id and backtest_id:
                        self.db.associate_signal_with_backtest(
                            trader_id=trader_id,
                            backtest_id=backtest_id,
                            strategy_name=strategy_name
                        )

                    buy_count += 1

                # 保存卖出信号
                for sell_signal in signals.sell_signals:
                    trader_id = self.db.insert_trader_signal(
                        symbol=sell_signal.symbol,
                        signal_type='sell',
                        strategies=[strategy_name],
                        signal_date=signal_date,
                        price=sell_signal.current_price,
                        asset_type='ashare'
                    )

                    # 关联回测
                    if trader_id and backtest_id:
                        self.db.associate_signal_with_backtest(
                            trader_id=trader_id,
                            backtest_id=backtest_id,
                            strategy_name=strategy_name
                        )

                    sell_count += 1

            logger.success(f"  ✓ 保存信号: {buy_count}个买入, {sell_count}个卖出")

        except Exception as e:
            logger.error(f"  信号生成失败: {e}")
            import traceback
            traceback.print_exc()

    def _filter_signals_by_version(self, signals, version):
        """
        根据策略版本过滤信号

        Args:
            signals: {strategy_name: strategy_signals}
            version: 版本标识 ('weekly', 'monthly' 等)

        Returns:
            dict: 过滤后的信号字典
        """
        loader = StrategyLoader()
        strategies = loader.load_ashare_strategies()

        # 创建策略名称到版本的映射
        name_to_version = {s[0]: s[3] for s in strategies}

        # 过滤信号
        filtered = {}
        for strategy_name, strategy_signals in signals.items():
            if name_to_version.get(strategy_name) == version:
                filtered[strategy_name] = strategy_signals

        logger.info(f"过滤信号: {len(signals)} -> {len(filtered)} (version={version})")
        return filtered

    def _run_signal_only_mode(self, version_filter=None):
        """
        模式: 仅生成信号（使用现有回测结果关联，但不强制要求）

        Args:
            version_filter: 版本过滤 ('weekly', 'monthly' 或 None表示所有)
        """
        if version_filter:
            logger.info(f"【信号生成模式】跳过回测，仅生成{version_filter}策略信号")
        else:
            logger.info("【信号生成模式】跳过回测，仅生成所有策略信号")

        # 加载策略（可按版本过滤）
        loader = StrategyLoader()

        if version_filter:
            strategies = loader.load_ashare_strategies_by_version(version_filter)
            logger.info(f"加载 {version_filter} 策略: {len(strategies)} 个")
        else:
            strategies = loader.load_ashare_strategies()
            logger.info(f"加载所有策略: {len(strategies)} 个")

        strategy_names = [s[0] for s in strategies]

        # 尝试加载现有回测（用于关联，但不强制要求）
        logger.info("检查数据库中的回测结果...")
        self.backtest_results = self._load_existing_backtests(strategy_names)

        if self.backtest_results:
            logger.info(f"找到 {len(self.backtest_results)} 个现有回测，将关联到信号")
        else:
            logger.warning("未找到任何现有回测，信号将不会关联回测结果")

        # 直接生成信号（无论是否有回测，带版本过滤）
        self.generate_and_save_signals(version_filter=version_filter)

    def _run_version_mode(self, version):
        """
        模式2&3: 运行特定版本的回测并生成信号

        Args:
            version: 'weekly' 或 'monthly'
        """
        logger.info(f"【{version.upper()}策略模式】回测 + 信号生成")

        # 步骤1: 运行该版本的回测
        logger.info(f"步骤 1/2: 运行 {version} 策略回测...")
        self.run_ashare_backtests(version_filter=version)

        # 步骤2: 生成该版本的信号
        logger.info(f"步骤 2/2: 生成 {version} 策略信号...")
        self.generate_and_save_signals(version_filter=version)

    def run(self):
        """执行完整A股策略管道"""
        logger.info("="*60)
        logger.info(f"A股策略信号生成管道启动 (mode={self.mode})")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)

        if self.mode == 'signal-weekly':
            # 模式: 仅生成周频策略信号（每日推荐）
            self._run_signal_only_mode(version_filter='weekly')

        elif self.mode == 'signal-all':
            # 模式: 生成所有策略信号
            self._run_signal_only_mode(version_filter=None)

        elif self.mode in ['weekly', 'monthly']:
            # 模式: 运行特定版本的回测并生成信号
            self._run_version_mode(self.mode)

        else:  # mode == 'all'
            # 默认行为: 运行所有回测并生成所有信号
            self.run_ashare_backtests()
            self.generate_and_save_signals()

        logger.info("="*60)
        logger.info("A股策略管道执行完成")
        logger.info(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='A股策略信号生成管道',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python run_ashare_signals.py --signal              仅生成信号(使用现有回测)
  python run_ashare_signals.py --weekly              周频策略: 回测+信号
  python run_ashare_signals.py --monthly             月频策略: 回测+信号
  python run_ashare_signals.py                       所有策略: 回测+信号(默认)

  python run_ashare_signals.py --weekly --force-backtest   强制重新回测
  python run_ashare_signals.py --signal --workers 5         并发优化

  智能选股筛选:
  python run_ashare_signals.py --signal --filter-preset balanced    使用平衡型筛选
  python run_ashare_signals.py --signal --no-filter                禁用智能筛选
  python run_ashare_signals.py --signal --filter-target 800        筛选目标800只

  策略频率:
  python run_ashare_signals.py --signal                          仅生成周频策略信号(每日推荐)
  python run_ashare_signals.py --all-signal                      生成所有策略信号(周频+月频)
  python run_ashare_signals.py --weekly                          周频策略回测+信号
  python run_ashare_signals.py --monthly                         月频策略回测+信号
        """
    )

    # 互斥的模式选择
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--signal',
        action='store_true',
        help='信号生成模式: 仅生成周频策略的交易信号（每日推荐）'
    )
    mode_group.add_argument(
        '--all-signal',
        action='store_true',
        help='全量信号模式: 生成所有策略的交易信号（周频+月频）'
    )
    mode_group.add_argument(
        '--weekly',
        action='store_true',
        help='周频策略模式: 运行周频策略回测并生成信号'
    )
    mode_group.add_argument(
        '--monthly',
        action='store_true',
        help='月频策略模式: 运行月频策略回测并生成信号'
    )

    # 可选参数
    parser.add_argument(
        '--force-backtest',
        action='store_true',
        help='强制重新运行回测（忽略缓存）'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='并发回测的线程数（默认为3，最多15。由于数据加载较慢，建议不超过5）'
    )

    # 智能选股筛选参数
    parser.add_argument(
        '--filter-preset',
        type=str,
        choices=['conservative', 'balanced', 'aggressive'],
        default='balanced',
        help='智能选股预设配置 (默认: balanced，可选: conservative/balanced/aggressive)'
    )

    parser.add_argument(
        '--filter-target',
        type=int,
        default=1000,
        help='筛选目标股票数量 (默认: 1000)'
    )

    parser.add_argument(
        '--no-filter',
        action='store_true',
        help='禁用智能筛选，使用完整股票池'
    )

    args = parser.parse_args()

    # 确定运行模式
    if args.signal:
        mode = 'signal-weekly'  # --signal 默认只运行周频策略（每日推荐）
    elif args.all_signal:
        mode = 'signal-all'  # --all-signal 运行所有策略
    elif args.weekly:
        mode = 'weekly'
    elif args.monthly:
        mode = 'monthly'
    else:
        mode = 'all'  # 默认运行所有策略

    # 准备智能筛选配置
    from core.smart_stock_filter import FilterPresets

    # 获取筛选配置
    if args.no_filter:
        filter_config = None
        enable_filter = False
        logger.info("智能筛选已禁用 (--no-filter)")
    else:
        enable_filter = True
        preset_map = {
            'conservative': FilterPresets.conservative(),
            'balanced': FilterPresets.balanced(),
            'aggressive': FilterPresets.aggressive()
        }
        filter_config = preset_map[args.filter_preset]
        # 覆盖目标数量
        filter_config.target_count = args.filter_target
        logger.info(f"智能筛选已启用: preset={args.filter_preset}, target={args.filter_target}")

    # 创建并运行A股策略管道
    pipeline = AShareSignalPipeline(
        mode=mode,
        force_backtest=args.force_backtest,
        max_workers=args.workers,
        enable_smart_filter=enable_filter,
        filter_config=filter_config
    )
    pipeline.run()


if __name__ == '__main__':
    main()
