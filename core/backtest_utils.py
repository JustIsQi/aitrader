"""
回测结果提取工具
"""
import pandas as pd
from datetime import datetime
from loguru import logger


def extract_backtest_metrics(result, task):
    """
    从回测结果中提取关键指标

    Args:
        result: Engine.run() 返回的结果对象
        task: Task 配置对象

    Returns:
        dict: 包含所有回测指标的字典
    """
    try:
        # 获取性能统计
        perf_stats = result.perf.stats

        # 提取基础指标
        metrics = {
            'start_date': task.start_date,
            'end_date': task.end_date,
            'initial_capital': task.initial_cash if hasattr(task, 'initial_cash') else 1000000,

            # 收益指标
            'total_return': perf_stats.get('total_return', 0.0) * 100,  # 转为百分比
            'annual_return': perf_stats.get('yearly_return', 0.0) * 100,

            # 风险指标
            'sharpe_ratio': perf_stats.get('yearly_sharpe', 0.0),
            'max_drawdown': perf_stats.get('max_drawdown', 0.0) * 100,  # 转为百分比

            # 交易统计
            'total_trades': len(result.hist_trades) if hasattr(result, 'hist_trades') else 0,
            'win_rate': _calculate_win_rate(result),
            'profit_factor': _calculate_profit_factor(result),

            # 基准比较
            'benchmark_return': perf_stats.get('benchmark_return', 0.0) * 100,
        }

        # 提取权益曲线
        metrics['equity_curve'] = _extract_equity_curve(result)

        # 提取交易列表
        metrics['trade_list'] = _extract_trade_list(result)

        return metrics

    except Exception as e:
        logger.error(f"Failed to extract backtest metrics: {e}")
        # 返回默认值
        return {
            'start_date': task.start_date,
            'end_date': task.end_date,
            'total_return': 0.0,
            'annual_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'equity_curve': [],
            'trade_list': [],
        }


def _calculate_win_rate(result):
    """计算胜率"""
    try:
        if not hasattr(result, 'hist_trades') or len(result.hist_trades) == 0:
            return 0.0

        winning_trades = [t for t in result.hist_trades if t.get('pnl', 0) > 0]
        return len(winning_trades) / len(result.hist_trades) * 100
    except:
        return 0.0


def _calculate_profit_factor(result):
    """计算盈亏比"""
    try:
        if not hasattr(result, 'hist_trades') or len(result.hist_trades) == 0:
            return 0.0

        total_profit = sum([t.get('pnl', 0) for t in result.hist_trades if t.get('pnl', 0) > 0])
        total_loss = abs(sum([t.get('pnl', 0) for t in result.hist_trades if t.get('pnl', 0) < 0]))

        if total_loss == 0:
            return 0.0

        return total_profit / total_loss
    except:
        return 0.0


def _extract_equity_curve(result):
    """提取权益曲线数据"""
    try:
        if hasattr(result, 'perf') and hasattr(result.perf, 'prices'):
            # 转换为列表格式: [{date: '2020-01-01', value: 100000}, ...]
            equity_df = result.perf.prices.reset_index()
            equity_df.columns = ['date', 'value']

            # 转换日期为字符串格式
            equity_df['date'] = pd.to_datetime(equity_df['date']).dt.strftime('%Y-%m-%d')

            return equity_df.to_dict('records')
        return []
    except Exception as e:
        logger.error(f"Failed to extract equity curve: {e}")
        return []


def _extract_trade_list(result):
    """提取交易列表"""
    try:
        if hasattr(result, 'hist_trades'):
            # 转换交易记录为字典列表
            trades = []
            for trade in result.hist_trades:
                trade_dict = {
                    'date': str(trade.get('date', '')),
                    'symbol': trade.get('symbol', ''),
                    'type': trade.get('type', ''),  # 'buy' or 'sell'
                    'price': float(trade.get('price', 0)),
                    'quantity': int(trade.get('quantity', 0)),
                    'pnl': float(trade.get('pnl', 0)),
                }
                trades.append(trade_dict)
            return trades
        return []
    except Exception as e:
        logger.error(f"Failed to extract trade list: {e}")
        return []
