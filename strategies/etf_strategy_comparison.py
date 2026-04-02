"""
ETF策略比较器 - ETF Strategy Comparison

功能:
1. 并行回测多个策略
2. 生成对比报告(收益、夏普、最大回撤、卡玛比率等)
3. 策略排名和可视化
4. 参数敏感性分析

作者: AITrader
日期: 2026-02-14
"""

from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np
from loguru import logger
from concurrent.futures import ProcessPoolExecutor, as_completed
import time


@dataclass
class StrategyResult:
    """策略回测结果"""
    name: str
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    var_95: float
    cvar_95: float
    win_rate_daily: float
    win_rate_weekly: float
    win_rate_monthly: float
    avg_turnover_rate: float
    total_trades: int
    equity_curve: List[float]
    monthly_returns: Dict[str, float]

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'name': self.name,
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'max_drawdown': self.max_drawdown,
            'var_95': self.var_95,
            'cvar_95': self.cvar_95,
            'win_rate_daily': self.win_rate_daily,
            'win_rate_weekly': self.win_rate_weekly,
            'win_rate_monthly': self.win_rate_monthly,
            'avg_turnover_rate': self.avg_turnover_rate,
            'total_trades': self.total_trades,
        }


class ETFStrategyComparator:
    """
    ETF策略比较器

    功能:
    1. 注册多个策略
    2. 并行回测
    3. 生成对比报告
    """

    def __init__(self,
                 symbols: List[str],
                 start_date: str,
                 end_date: str = None,
                 initial_capital: float = 1000000,
                 benchmark: str = '510300.SH'):
        """
        初始化策略比较器

        Args:
            symbols: ETF池
            start_date: 回测开始日期
            end_date: 回测结束日期 (None则当前日期)
            initial_capital: 初始资金
            benchmark: 基准
        """
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime('%Y%m%d')
        self.initial_capital = initial_capital
        self.benchmark = benchmark

        # 策略列表
        self.strategies: Dict[str, Callable] = {}

        # 注册默认策略
        self._register_default_strategies()

    def _register_default_strategies(self):
        """注册默认策略"""
        # 1. 原始简单动量策略
        from strategies.etf_portfolio_backtest import etf_momentum_portfolio
        self.strategies['simple_momentum'] = lambda: etf_momentum_portfolio()

        # 2. 多策略轮动
        from strategies.etf_multi_strategy_rotation import run_multi_strategy_etf
        self.strategies['multi_strategy'] = lambda: run_multi_strategy_etf(
            symbols=self.symbols,
            start_date=self.start_date,
            end_date=self.end_date,
            initial_capital=self.initial_capital
        )

        # 3. 风险平价
        from strategies.etf_risk_parity import run_risk_parity_etf
        self.strategies['risk_parity'] = lambda: run_risk_parity_etf(
            symbols=self.symbols,
            start_date=self.start_date,
            end_date=self.end_date,
            initial_capital=self.initial_capital
        )

        # 4. 双动量
        from strategies.etf_dual_momentum import run_dual_momentum_etf
        self.strategies['dual_momentum'] = lambda: run_dual_momentum_etf(
            symbols=self.symbols,
            start_date=self.start_date,
            end_date=self.end_date,
            initial_capital=self.initial_capital
        )

    def add_strategy(self, name: str, strategy_func: Callable):
        """添加自定义策略"""
        self.strategies[name] = strategy_func
        logger.info(f"添加策略: {name}")

    def run_comparison(self,
                      strategy_names: List[str] = None,
                      parallel: bool = True) -> Dict[str, StrategyResult]:
        """
        运行策略对比回测

        Args:
            strategy_names: 要测试的策略列表 (None则测试全部)
            parallel: 是否并行运行

        Returns:
            {strategy_name: StrategyResult}
        """
        if strategy_names is None:
            strategy_names = list(self.strategies.keys())

        logger.info("=" * 60)
        logger.info(f"开始策略对比回测: {len(strategy_names)} 个策略")
        logger.info(f"回测期间: {self.start_date} ~ {self.end_date}")
        logger.info(f"ETF池: {len(self.symbols)} 个标的")
        logger.info("=" * 60)

        results = {}
        start_time = time.time()

        if parallel and len(strategy_names) > 1:
            # 并行运行
            with ProcessPoolExecutor(max_workers=min(4, len(strategy_names))) as executor:
                futures = {}
                for name in strategy_names:
                    if name in self.strategies:
                        future = executor.submit(self._run_single_strategy, name)
                        futures[future] = name

                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        result = future.result(timeout=300)
                        results[name] = result
                        logger.info(f"✓ {name}: 年化收益={result.annual_return*100:.2f}%, "
                                   f"夏普={result.sharpe_ratio:.2f}")
                    except Exception as e:
                        logger.error(f"✗ {name} 回测失败: {e}")
        else:
            # 串行运行
            for name in strategy_names:
                if name in self.strategies:
                    try:
                        result = self._run_single_strategy(name)
                        results[name] = result
                        logger.info(f"✓ {name}: 年化收益={result.annual_return*100:.2f}%, "
                                   f"夏普={result.sharpe_ratio:.2f}")
                    except Exception as e:
                        logger.error(f"✗ {name} 回测失败: {e}")

        elapsed = time.time() - start_time
        logger.success(f"策略对比完成! 耗时 {elapsed:.2f}秒")
        logger.info("=" * 60)

        return results

    def _run_single_strategy(self, name: str) -> StrategyResult:
        """运行单个策略"""
        logger.info(f"运行策略: {name}...")

        strategy_func = self.strategies.get(name)
        if strategy_func is None:
            raise ValueError(f"策略不存在: {name}")

        # 运行策略
        result_dict = strategy_func()

        # 转换为StrategyResult
        return self._dict_to_result(result_dict, name)

    def _dict_to_result(self, result_dict: Dict, name: str) -> StrategyResult:
        """将回测结果字典转换为StrategyResult"""
        return StrategyResult(
            name=name,
            total_return=result_dict.get('total_return', 0),
            annual_return=result_dict.get('annual_return', 0),
            sharpe_ratio=result_dict.get('sharpe_ratio', 0),
            sortino_ratio=result_dict.get('sortino_ratio', 0),
            calmar_ratio=result_dict.get('calmar_ratio', 0),
            max_drawdown=result_dict.get('max_drawdown', 0),
            var_95=result_dict.get('var_95', 0),
            cvar_95=result_dict.get('cvar_95', 0),
            win_rate_daily=result_dict.get('win_rates', {}).get('daily', 0),
            win_rate_weekly=result_dict.get('win_rates', {}).get('weekly', 0),
            win_rate_monthly=result_dict.get('win_rates', {}).get('monthly', 0),
            avg_turnover_rate=result_dict.get('avg_turnover_rate', 0),
            total_trades=result_dict.get('total_trades', 0),
            equity_curve=result_dict.get('equity_curve', []),
            monthly_returns=result_dict.get('monthly_returns', {})
        )

    def generate_report(self, results: Dict[str, StrategyResult]) -> str:
        """
        生成对比报告

        Returns:
            报告文本
        """
        lines = []
        lines.append("=" * 80)
        lines.append("ETF策略对比报告")
        lines.append("=" * 80)
        lines.append(f"回测期间: {self.start_date} ~ {self.end_date}")
        lines.append(f"初始资金: {self.initial_capital:,.0f} 元")
        lines.append(f"基准: {self.benchmark}")
        lines.append("")

        # 1. 总览表
        lines.append("-" * 80)
        lines.append("策略总览")
        lines.append("-" * 80)
        lines.append(f"{'策略名称':<20} {'年化收益':<12} {'夏普比率':<12} {'最大回撤':<12} {'卡玛比率':<12}")
        lines.append("-" * 80)

        # 按夏普比率排序
        ranked = sorted(results.items(), key=lambda x: x[1].sharpe_ratio, reverse=True)

        for i, (name, result) in enumerate(ranked, 1):
            lines.append(
                f"{i}. {name:<18} {result.annual_return*100:>8.2f}%   "
                f"{result.sharpe_ratio:>8.2f}    "
                f"{result.max_drawdown*100:>8.2f}%    "
                f"{result.calmar_ratio:>8.2f}"
            )

        lines.append("")

        # 2. 详细指标表
        lines.append("-" * 80)
        lines.append("详细指标")
        lines.append("-" * 80)

        metrics = [
            ('总收益率', 'total_return', '%'),
            ('年化收益率', 'annual_return', '%'),
            ('夏普比率', 'sharpe_ratio', ''),
            ('Sortino比率', 'sortino_ratio', ''),
            ('Calmar比率', 'calmar_ratio', ''),
            ('最大回撤', 'max_drawdown', '%'),
            ('95% VaR', 'var_95', '%'),
            ('95% CVaR', 'cvar_95', '%'),
            ('日胜率', 'win_rate_daily', '%'),
            ('周胜率', 'win_rate_weekly', '%'),
            ('月胜率', 'win_rate_monthly', '%'),
            ('平均换手率', 'avg_turnover_rate', '%'),
            ('交易次数', 'total_trades', ''),
        ]

        # 表头
        header = ['指标'] + [r[0][:8] for r in ranked]
        lines.append(f"{'指标':<20}" + "".join(f"{h:>16}" for h in header))
        lines.append("-" * 80)

        for metric_name, metric_key, suffix in metrics:
            row = [metric_name]
            for _, result in ranked:
                value = getattr(result, metric_key, 0)
                if suffix == '%':
                    row.append(f"{value*100:>12.2f}%")
                else:
                    row.append(f"{value:>16.2f}")
            lines.append(f"{row[0]:<20}" + "".join(row[1:]))

        lines.append("")

        # 3. 综合评分
        lines.append("-" * 80)
        lines.append("综合评分排名")
        lines.append("-" * 80)

        # 计算综合得分 (年化收益 + 夏普比率 - 最大回撤惩罚)
        for name, result in ranked:
            score = (
                result.annual_return * 100 * 0.4 +  # 40%收益权重
                result.sharpe_ratio * 20 * 0.4 +  # 40%夏普权重
                result.max_drawdown * 100 * -0.2  # 20%回撤惩罚
            )
            lines.append(f"{name}: {score:.2f}")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def save_report(self, report: str, filename: str = None):
        """保存报告到文件"""
        if filename is None:
            filename = f"etf_strategy_comparison_{self.end_date}.txt"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"报告已保存: {filename}")

    def plot_comparison(self, results: Dict[str, StrategyResult],
                       save_path: str = None):
        """
        绘制策略对比图

        Args:
            results: 策略结果
            save_path: 保存路径 (None则显示)
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib import rcParams

            # 设置中文字体
            rcParams['font.family'] = 'SimHei'
            rcParams['axes.unicode_minus'] = False

            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            fig.suptitle('ETF策略对比', fontsize=16, fontweight='bold')

            names = list(results.keys())

            # 1. 年化收益率对比
            ax = axes[0, 0]
            returns = [results[n].annual_return * 100 for n in names]
            colors = ['green' if r > 0 else 'red' for r in returns]
            ax.bar(names, returns, color=colors, alpha=0.7)
            ax.set_title('年化收益率对比')
            ax.set_ylabel('收益率 (%)')
            ax.axhline(y=0, color='black', linestyle='--', linewidth=0.8)
            ax.tick_params(axis='x', rotation=45)

            # 2. 夏普比率对比
            ax = axes[0, 1]
            sharpe = [results[n].sharpe_ratio for n in names]
            ax.bar(names, sharpe, color='steelblue', alpha=0.7)
            ax.set_title('夏普比率对比')
            ax.set_ylabel('夏普比率')
            ax.axhline(y=1, color='red', linestyle='--', linewidth=0.8, label='基准线=1')
            ax.legend()
            ax.tick_params(axis='x', rotation=45)

            # 3. 最大回撤对比
            ax = axes[1, 0]
            drawdowns = [results[n].max_drawdown * 100 for n in names]
            ax.bar(names, drawdowns, color='darkred', alpha=0.7)
            ax.set_title('最大回撤对比')
            ax.set_ylabel('回撤 (%)')
            ax.tick_params(axis='x', rotation=45)

            # 4. 净值曲线
            ax = axes[1, 1]
            for name in names:
                equity = results[name].equity_curve
                if equity:
                    # 归一化为初始值1
                    normalized = np.array(equity) / 1000000
                    ax.plot(normalized, label=name, linewidth=2)
            ax.set_title('净值曲线对比')
            ax.set_ylabel('净值 (初始=1)')
            ax.set_xlabel('交易日')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)

            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                logger.info(f"图表已保存: {save_path}")
            else:
                plt.show()

        except ImportError:
            logger.warning("matplotlib未安装,无法绘图")
        except Exception as e:
            logger.error(f"绘图失败: {e}")

    def find_best_strategy(self, results: Dict[str, StrategyResult],
                          metric: str = 'sharpe_ratio') -> Tuple[str, StrategyResult]:
        """
        找出最优策略

        Args:
            results: 策略结果
            metric: 评价指标 (sharpe_ratio, annual_return, calmar_ratio等)

        Returns:
            (strategy_name, result)
        """
        best_name = max(results.keys(), key=lambda n: getattr(results[n], metric, -999))
        return best_name, results[best_name]


# 便捷函数
def compare_etf_strategies(
        symbols: List[str] = None,
        start_date: str = '20220101',
        end_date: str = None,
        initial_capital: float = 1000000,
        benchmark: str = '510300.SH',
        strategy_names: List[str] = None,
        save_report: bool = True,
        plot_results: bool = True
) -> Dict[str, StrategyResult]:
    """
    快速对比ETF策略

    Args:
        symbols: ETF池 (None则使用默认池)
        start_date: 回测开始日期
        end_date: 回测结束日期
        initial_capital: 初始资金
        benchmark: 基准
        strategy_names: 要测试的策略 (None则全部)
        save_report: 是否保存报告
        plot_results: 是否绘图

    Returns:
        策略结果字典
    """
    if symbols is None:
        # 默认ETF池
        symbols = [
            '510300.SH',  # 沪深300ETF
            '510500.SH',  # 中证500ETF
            '159915.SZ',  # 创业板ETF
            '512100.SH',  # 中证1000ETF
            '588000.SH',  # 科创50ETF
            '513100.SH',  # 纳指100ETF
            '518880.SH',  # 黄金ETF
        ]

    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    # 创建比较器
    comparator = ETFStrategyComparator(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        benchmark=benchmark
    )

    # 运行对比
    results = comparator.run_comparison(strategy_names=strategy_names)

    if results:
        # 生成报告
        report = comparator.generate_report(results)
        print(report)

        if save_report:
            comparator.save_report(report)

        if plot_results:
            comparator.plot_comparison(results)

        # 找出最优策略
        best_name, best_result = comparator.find_best_strategy(results)
        logger.success(f"最优策略(按夏普): {best_name}, 夏普={best_result.sharpe_ratio:.2f}")

    return results


if __name__ == '__main__':
    """测试代码"""
    logger.info('ETF策略对比测试')

    # 测试: 近3年对比
    results = compare_etf_strategies(
        symbols=[
            '510300.SH',  # 沪深300ETF
            '510500.SH',  # 中证500ETF
            '159915.SZ',  # 创业板ETF
            '513100.SH',  # 纳指100ETF
            '518880.SH',  # 黄金ETF
        ],
        start_date='20220101',
        strategy_names=['simple_momentum', 'dual_momentum'],  # 先测试这两个
        plot_results=False  # 测试时不绘图
    )
