"""
双动量ETF策略 - ETF Dual Momentum Strategy

策略逻辑(参考Gary Antonacci的Dual Momentum):
1. 绝对动量: 筛选出正收益ETF (roc(close,12) > 0)
2. 相对动量: 在正收益ETF中选择表现最好的
3. 若无正收益ETF, 持有防御资产(债券ETF)

优势:
- 结合绝对和相对动量
- 天然具有风险控制(负收益时切换防御资产)
- 实施简单,逻辑清晰

作者: AITrader
日期: 2026-02-14
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

from core.portfolio_bt_engine import PortfolioBacktestEngine, PortfolioTask


@dataclass
class DualMomentumConfig:
    """双动量策略配置"""
    # 绝对动量计算周期
    absolute_momentum_period: int = 12  # 月 (约60交易日)

    # 相对动量计算周期
    relative_momentum_period: int = 6  # 月

    # 绝对动量阈值 (收益率必须大于此值)
    absolute_threshold: float = 0.0  # 0表示只要正收益即可

    # 持仓数量
    top_n: int = 3  # 选择前N名

    # 防御资产 (当无正收益ETF时持有)
    defensive_assets: List[str] = None

    # 防御资产最小持有比例
    defensive_min_weight: float = 0.0

    # 再平衡频率
    rebalance_frequency: str = 'monthly'  # monthly, quarterly

    def __post_init__(self):
        if self.defensive_assets is None:
            # 默认防御资产: 债券ETF和黄金ETF
            self.defensive_assets = ['511010.SH', '518880.SH']  # 十年国债、黄金


class DualMomentumETFEngine(PortfolioBacktestEngine):
    """
    双动量ETF策略引擎

    继承自PortfolioBacktestEngine
    """

    def __init__(self, task: PortfolioTask, config: DualMomentumConfig = None):
        super().__init__(task)
        self.config = config or DualMomentumConfig()

    def run(self) -> Dict:
        """
        运行双动量策略回测

        Returns:
            回测结果字典
        """
        logger.info(f"开始双动量ETF策略回测: {self.task.name}")
        logger.info(f"配置: 绝对动量周期={self.config.absolute_momentum_period}月, "
                   f"持仓数量={self.config.top_n}")

        # 获取交易日列表
        trading_days = self._get_trading_days()
        logger.info(f"交易日数量: {len(trading_days)}")

        # 逐日模拟
        last_rebalance_date = None
        rebalance_count = 0
        current_holdings = {}  # {symbol: weight}

        for i, date in enumerate(trading_days):
            if i % 50 == 0:
                logger.info(f"处理进度: {i}/{len(trading_days)} ({i/len(trading_days)*100:.1f}%)")

            # 判断是否需要再平衡
            should_rebalance = self._should_rebalance_by_frequency(date, last_rebalance_date)

            if should_rebalance:
                # 1. 计算双动量信号
                selected_symbols = self._calculate_dual_momentum(date)

                if selected_symbols:
                    # 2. 生成目标组合 (等权或按动量加权)
                    target_portfolio = self._generate_target_portfolio(selected_symbols, date)

                    # 3. 执行再平衡
                    prices = self._get_prices(date)
                    trades = self._execute_rebalance(date, target_portfolio, prices)

                    for trade in trades:
                        self.tracker.add_transaction(
                            date=date,
                            symbol=trade['symbol'],
                            action=trade['action'],
                            shares=trade['shares'],
                            price=trade['price'],
                            amount=trade['amount']
                        )

                    current_holdings = target_portfolio
                    rebalance_count += 1
                    last_rebalance_date = date

                    selected_str = ', '.join([f'{s}({w:.1%})' for s, w in selected_symbols[:3]])
                    logger.debug(f"{date}: 持仓 {selected_str}")
                else:
                    # 无符合条件的标的,清空或持有防御资产
                    if self.config.defensive_min_weight > 0:
                        # 持有防御资产
                        target_portfolio = self._get_defensive_portfolio()
                        prices = self._get_prices(date)
                        trades = self._execute_rebalance(date, target_portfolio, prices)

                        for trade in trades:
                            self.tracker.add_transaction(
                                date=date,
                                symbol=trade['symbol'],
                                action=trade['action'],
                                shares=trade['shares'],
                                price=trade['price'],
                                amount=trade['amount']
                            )

                        current_holdings = target_portfolio
                        rebalance_count += 1
                        last_rebalance_date = date
                    else:
                        # 清空持仓
                        prices = self._get_prices(date)
                        trades = self._close_all_positions(date, prices)
                        current_holdings = {}

            # 更新每日状态
            prices = self._get_prices(date)
            self.tracker.update_daily_state(date, prices, [])

        logger.info(f"回测完成,共再平衡 {rebalance_count} 次")

        # 计算最终指标
        metrics = self._calculate_final_metrics()

        # 保存到数据库
        if self.task.name:
            self._save_results(metrics)

        return metrics

    def _should_rebalance_by_frequency(self, date: str, last_rebalance: str) -> bool:
        """根据频率判断是否需要再平衡"""
        if last_rebalance is None:
            return True

        freq = self.config.rebalance_frequency
        current = pd.to_datetime(date)
        last = pd.to_datetime(last_rebalance)

        if freq == 'monthly':
            # 每月第一个交易日
            return current.month != last.month or current.year != last.year
        elif freq == 'quarterly':
            # 每季度第一个月
            return (current.month != last.month and
                   ((current.month - 1) % 3 == 0))
        else:
            return True

    def _calculate_dual_momentum(self, date: str) -> List[tuple]:
        """
        计算双动量信号

        Returns:
            [(symbol, score), ...] 按得分排序
        """
        scores = {}

        # 计算周期(转换为交易日)
        # A股平均每月约20个交易日（全年约242-244天）
        A_SHARE_TRADING_DAYS_PER_MONTH = 20
        abs_period = int(self.config.absolute_momentum_period * A_SHARE_TRADING_DAYS_PER_MONTH)
        rel_period = int(self.config.relative_momentum_period * A_SHARE_TRADING_DAYS_PER_MONTH)

        for symbol in self.task.symbols:
            df = self.price_data.get(symbol)
            if df is None or df.empty or 'close' not in df.columns:
                continue

            close = df['close']

            # 1. 绝对动量检查
            if len(close) > abs_period:
                abs_return = close.iloc[-1] / close.iloc[-abs_period - 1] - 1
            else:
                abs_return = -999  # 无效值

            # 必须满足绝对动量阈值
            if abs_return < self.config.absolute_threshold:
                continue

            # 2. 相对动量计算
            if len(close) > rel_period:
                rel_return = close.iloc[-1] / close.iloc[-rel_period - 1] - 1
            else:
                rel_return = abs_return  # 使用绝对动量作为后备

            # 3. 综合得分 (绝对动量 + 相对动量)
            # 可以调整权重,这里简单相加
            score = abs_return + rel_return

            scores[symbol] = {
                'absolute_momentum': abs_return,
                'relative_momentum': rel_return,
                'score': score
            }

        # 按综合得分排序
        ranked = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)

        # 返回前N名及其得分
        return [(s, scores[s]) for s, _ in ranked[:self.config.top_n]]

    def _generate_target_portfolio(self, selected_symbols: List[tuple],
                                date: str) -> Dict[str, float]:
        """
        生成目标组合权重

        Args:
            selected_symbols: [(symbol, score_dict), ...]
            date: 当前日期

        Returns:
            {symbol: weight}
        """
        if not selected_symbols:
            return {}

        # 策略1: 等权配置
        n = len(selected_symbols)
        equal_weight = {s[0]: 1.0/n for s in selected_symbols}

        # 策略2: 按动量强度加权 (可选)
        # 这里使用等权,更稳健
        return equal_weight

    def _get_defensive_portfolio(self) -> Dict[str, float]:
        """获取防御资产组合"""
        defensive = self.config.defensive_assets
        if not defensive:
            return {}

        # 过滤掉不在标的池中的防御资产
        valid_defensive = [s for s in defensive if s in self.task.symbols]

        if not valid_defensive:
            return {}

        n = len(valid_defensive)
        weight = 1.0 / n
        return {s: weight for s in valid_defensive}


# 便捷函数
def run_dual_momentum_etf(
        symbols: List[str],
        start_date: str = '20220101',
        end_date: str = None,
        absolute_momentum_period: int = 12,
        relative_momentum_period: int = 6,
        top_n: int = 3,
        defensive_assets: List[str] = None,
        rebalance_frequency: str = 'monthly',
        benchmark: str = '510300.SH',
        initial_capital: float = 1000000,
        commission_rate: float = 0.0003
) -> Dict:
    """
    快速运行双动量ETF回测

    Args:
        symbols: ETF池 (风险资产)
        start_date: 开始日期
        end_date: 结束日期 (None则使用当前日期)
        absolute_momentum_period: 绝对动量周期(月)
        relative_momentum_period: 相对动量周期(月)
        top_n: 持仓数量
        defensive_assets: 防御资产列表
        rebalance_frequency: 再平衡频率
        benchmark: 基准
        initial_capital: 初始资金
        commission_rate: 手续费率

    Returns:
        回测结果字典
    """
    from core.portfolio_bt_engine import PortfolioTask

    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    # 合并风险资产和防御资产
    all_symbols = list(set(symbols + (defensive_assets or [])))

    task = PortfolioTask(
        name='双动量ETF策略',
        symbols=all_symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        commission_rate=commission_rate,
        benchmark=benchmark
    )

    config = DualMomentumConfig(
        absolute_momentum_period=absolute_momentum_period,
        relative_momentum_period=relative_momentum_period,
        top_n=top_n,
        defensive_assets=defensive_assets,
        rebalance_frequency=rebalance_frequency
    )

    engine = DualMomentumETFEngine(task, config)
    return engine.run()


# 默认ETF池配置
DEFAULT_RISK_ASSETS = [
    # A股宽基
    '510300.SH',  # 沪深300ETF
    '510500.SH',  # 中证500ETF
    '159915.SZ',  # 创业板ETF
    '512100.SH',  # 中证1000ETF
    '588000.SH',  # 科创50ETF
    # 行业主题
    '512010.SH',  # 医药ETF
    '159928.SZ',  # 消费ETF
    '512100.SH',  # 中证1000ETF
    # 海外
    '513100.SH',  # 纳指100ETF
    '513520.SH',  # 日经225ETF
    '513330.SH',  # 德国DAX ETF
]

DEFAULT_DEFENSIVE_ASSETS = [
    '511010.SH',  # 十年国债ETF
    '518880.SH',  # 黄金ETF
]


if __name__ == '__main__':
    """测试代码"""
    logger.info('双动量ETF策略测试')

    # 测试: 近3年回测
    result = run_dual_momentum_etf(
        symbols=DEFAULT_RISK_ASSETS[:8],  # 使用前8个作为测试
        start_date='20220101',
        top_n=3,
        defensive_assets=DEFAULT_DEFENSIVE_ASSETS,
        rebalance_frequency='monthly'
    )

    # 打印结果
    print("\n" + "="*60)
    print(f"策略名称: {result['strategy_name']}")
    print(f"回测期间: {result['start_date']} ~ {result['end_date']}")
    print("="*60)
    print(f"总收益: {result['total_return']*100:.2f}%")
    print(f"年化收益: {result['annual_return']*100:.2f}%")
    print(f"夏普比率: {result['sharpe_ratio']:.2f}")
    print(f"Sortino比率: {result['sortino_ratio']:.2f}")
    print(f"Calmar比率: {result['calmar_ratio']:.2f}")
    print(f"最大回撤: {result['max_drawdown']*100:.2f}%")
    print("="*60)

    # 打印月度收益
    if result['monthly_returns']:
        print("\n月度收益(最后6个月):")
        for month, ret in list(result['monthly_returns'].items())[-6:]:
            print(f"  {month}: {ret*100:+.2f}%")
