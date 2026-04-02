"""
回测结果提取工具
"""
import pandas as pd
from datetime import datetime
from loguru import logger

from core.backtest_result import BacktestResult


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
        normalized = _ensure_backtest_result(result)

        def get_stat(stat_name, default=0.0, column='策略'):
            value = normalized.statistics.get(stat_name)
            if value is None:
                return default
            if isinstance(value, dict):
                if column in value and not pd.isna(value[column]):
                    return float(value[column])
                if 'strategy' in value and not pd.isna(value['strategy']):
                    return float(value['strategy'])
                for item in value.values():
                    if not pd.isna(item):
                        return float(item)
                return default
            if pd.isna(value):
                return default
            return float(value)

        # 提取基础指标
        metrics = {
            'start_date': task.start_date,
            'end_date': task.end_date,
            'initial_capital': getattr(task, 'initial_capital', 1000000),

            # 收益指标
            'total_return': get_stat('total_return', 0.0) * 100,  # 转为百分比
            'annual_return': get_stat('cagr', 0.0) * 100,  # 使用cagr作为年化收益

            # 风险指标
            'sharpe_ratio': get_stat('daily_sharpe', 0.0),
            'max_drawdown': get_stat('max_drawdown', 0.0) * 100,  # 转为百分比

            # 交易统计
            'total_trades': len(normalized.trades),
            'win_rate': _calculate_win_rate(normalized),
            'profit_factor': _calculate_profit_factor(normalized),

            # 基准比较
            'benchmark_return': get_stat('total_return', 0.0, column='benchmark') * 100,
            'excess_return': (get_stat('total_return', 0.0) - get_stat('total_return', 0.0, column='benchmark')) * 100,
        }

        # 提取权益曲线
        metrics['equity_curve'] = _extract_equity_curve(normalized)

        # 提取交易列表
        metrics['trade_list'] = _extract_trade_list(normalized)

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
            'benchmark_return': 0.0,
            'excess_return': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'total_trades': 0,
            'equity_curve': [],
            'trade_list': [],
        }


def _ensure_backtest_result(result) -> BacktestResult:
    if isinstance(result, BacktestResult):
        return result

    if hasattr(result, 'backtest_result') and isinstance(result.backtest_result, BacktestResult):
        return result.backtest_result

    if hasattr(result, 'perf') or hasattr(result, 'hist_trades'):
        return BacktestResult.from_backtrader_engine(result)

    if isinstance(result, dict):
        return BacktestResult.from_mapping(result)

    raise TypeError(f"Unsupported backtest result type: {type(result)!r}")


def _calculate_win_rate(result: BacktestResult):
    """计算胜率"""
    try:
        if not result.trades:
            return 0.0

        winning_trades = [t for t in result.trades if (t.pnl_comm or t.pnl) > 0]
        return len(winning_trades) / len(result.trades) * 100
    except:
        return 0.0


def _calculate_profit_factor(result: BacktestResult):
    """计算盈亏比"""
    try:
        if not result.trades:
            return 0.0

        total_profit = sum([(t.pnl_comm or t.pnl) for t in result.trades if (t.pnl_comm or t.pnl) > 0])
        total_loss = abs(sum([(t.pnl_comm or t.pnl) for t in result.trades if (t.pnl_comm or t.pnl) < 0]))

        if total_loss == 0:
            return 0.0

        return total_profit / total_loss
    except:
        return 0.0


def _extract_equity_curve(result: BacktestResult):
    """提取权益曲线数据"""
    try:
        return result.equity_curve
    except Exception as e:
        logger.error(f"Failed to extract equity curve: {e}")
        return []


def _extract_trade_list(result: BacktestResult):
    """提取交易列表"""
    try:
        return [trade.to_dict() for trade in result.trades]
    except Exception as e:
        logger.error(f"Failed to extract trade list: {e}")
        return []


def calculate_symbol_backtest(
    symbol: str,
    lookback_days: int = 20,
    end_date: str = None,
    asset_type: str = 'etf'
) -> dict:
    """
    计算单个标的近N天的回测指标

    Args:
        symbol: 标的代码 (如 510300.XSHG)
        lookback_days: 回测天数（默认20天）
        end_date: 结束日期 (YYYYMMDD, 默认为最新日期)
        asset_type: 资产类型 ('etf' or 'ashare')

    Returns:
        dict: 回测指标字典，包含：
            - lookback_days: 实际回测天数
            - start_date: 开始日期
            - end_date: 结束日期
            - total_return: 总收益率
            - max_drawdown: 最大回撤
            - annual_return: 年化收益率
            - volatility: 波动率
            - sharpe_ratio: 夏普比率
    """
    from database.pg_manager import get_db
    from datetime import datetime, timedelta

    db = get_db()

    # 计算日期范围
    if end_date is None:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end_date, '%Y%m%d')

    # 多取30天保证有足够交易日
    start_date = end_date - timedelta(days=lookback_days + 30)

    # 获取历史数据
    if asset_type == 'etf':
        df = db.get_etf_history(
            symbol=symbol,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
    else:
        df = db.get_stock_history(
            symbol=symbol,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )

    if df is None or len(df) < lookback_days:
        logger.warning(f"标的 {symbol} 数据不足，需要至少 {lookback_days} 天，实际 {len(df) if df is not None else 0} 天")
        return None

    # 取最近 lookback_days 个交易日
    df = df.tail(lookback_days).copy()

    # 计算指标
    initial_price = df.iloc[0]['close']
    final_price = df.iloc[-1]['close']
    total_return = (final_price - initial_price) / initial_price

    # 计算最大回撤
    cumulative_returns = (1 + df['close'].pct_change()).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()

    # 计算年化收益率
    days_count = len(df)
    annual_return = (1 + total_return) ** (252 / days_count) - 1

    # 计算波动率
    daily_returns = df['close'].pct_change().dropna()
    volatility = daily_returns.std() * (252 ** 0.5)

    # 计算夏普比率（假设无风险利率为3%）
    risk_free_rate = 0.03
    sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0

    return {
        'lookback_days': days_count,
        'start_date': df.iloc[0]['date'].strftime('%Y-%m-%d'),
        'end_date': df.iloc[-1]['date'].strftime('%Y-%m-%d'),
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'annual_return': annual_return,
        'volatility': volatility,
        'sharpe_ratio': sharpe_ratio
    }
