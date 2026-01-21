"""
示例：ETF组合策略

演示如何使用组合回测引擎构建ETF组合策略
"""
from core.portfolio_bt_engine import PortfolioBacktestEngine, PortfolioTask, run_portfolio_backtest


def etf_momentum_portfolio():
    """
    ETF动量组合策略

    策略逻辑：
    1. 买入条件：满足至少2个
       - 20日收益率 > 5%（动量）
       - 5日均线上穿20日均线（趋势）
       - 成交量放大（流动性）
    2. 卖出条件：满足任一
       - 20日收益率 < -5%（动量转负）
       - 跌破20日均线5%（趋势破坏）
    3. 组合构建：等权配置所有符合条件的标的
    4. 再平衡：信号变化时触发
    """
    task = PortfolioTask(
        name='ETF动量组合策略',
        symbols=[
            '510300.SH',  # 沪深300ETF
            '510500.SH',  # 中证500ETF
            '159915.SZ',  # 创业板ETF
            '512100.SH',  # 中证1000ETF
            '588000.SH',  # 科创50ETF
            '513100.SH',  # 纳指100ETF
            '518880.SH',  # 黄金ETF
            '159985.SZ',  # 豆粕ETF
            '513520.SH',  # 日经225ETF
            '513330.SH',  # 德国DAX ETF
        ],
        start_date='20200101',
        end_date='20251215',
        initial_capital=1000000,
        commission_rate=0.0003,

        # 买入条件：满足至少2个
        select_buy=[
            'roc(close,20) > 0.05',      # 20日收益率 > 5%
            'ma(close,5) > ma(close,20)', # 5日均线上穿20日均线
            'volume > ma(volume,20)',     # 成交量放大
        ],
        buy_at_least_count=2,

        # 卖出条件：满足任一
        select_sell=[
            'roc(close,20) < -0.05',      # 20日收益率 < -5%
            'close < ma(close,20)*0.95',  # 跌破20日均线5%
        ],
        sell_at_least_count=1,

        weight_type='equal',
        rebalance_on_signal_change=True
    )

    engine = PortfolioBacktestEngine(task)
    result = engine.run()

    # 打印结果
    print("\n" + "="*60)
    print(f"策略名称: {result['strategy_name']}")
    print(f"回测期间: {result['start_date']} ~ {result['end_date']}")
    print(f"初始资金: {result['initial_capital']:,.0f} 元")
    print(f"最终资金: {result['final_value']:,.0f} 元")
    print("="*60)
    print(f"总收益: {result['total_return']*100:.2f}%")
    print(f"年化收益: {result['annual_return']*100:.2f}%")
    print(f"夏普比率: {result['sharpe_ratio']:.2f}")
    print(f"Sortino比率: {result['sortino_ratio']:.2f}")
    print(f"Calmar比率: {result['calmar_ratio']:.2f}")
    print(f"最大回撤: {result['max_drawdown']*100:.2f}%")
    print(f"95% VaR: {result['var_95']*100:.2f}%")
    print(f"95% CVaR: {result['cvar_95']*100:.2f}%")
    print("="*60)
    print(f"平均换手率: {result['avg_turnover_rate']*100:.2f}%")
    print(f"总交易次数: {result['total_trades']}")
    print(f"日胜率: {result['win_rates']['daily']:.2f}%")
    print(f"周胜率: {result['win_rates']['weekly']:.2f}%")
    print(f"月胜率: {result['win_rates']['monthly']:.2f}%")
    print("="*60)

    # 打印月度收益
    if result['monthly_returns']:
        print("\n月度收益:")
        for month, ret in result['monthly_returns'].items():
            print(f"  {month}: {ret*100:+.2f}%")

    # 打印最后持仓
    if result['final_holdings']:
        print("\n最后持仓:")
        for holding in result['final_holdings']:
            print(f"  {holding['symbol']}: {holding['shares']}股, "
                  f"市值 {holding['market_value']:,.0f}元, "
                  f"权重 {holding['weight']*100:.2f}%")

    return result


def etf_trend_following_portfolio():
    """
    ETF趋势跟踪组合策略

    策略逻辑：
    1. 买入条件：趋势向上
       - 收盘价 > 60日均线（长期趋势）
       - 20日收益率 > 0（中期动量）
    2. 卖出条件：趋势向下
       - 收盘价 < 60日均线
    3. 组合构建：等权配置
    """
    return run_portfolio_backtest(
        name='ETF趋势跟踪组合',
        symbols=[
            '510300.SH',  # 沪深300
            '510500.SH',  # 中证500
            '159915.SZ',  # 创业板
            '512100.SH',  # 中证1000
            '588000.SH',  # 科创50
        ],
        start_date='20200101',
        end_date='20251215',
        select_buy=[
            'close > ma(close,60)',     # 长期趋势向上
            'roc(close,20) > 0',         # 中期动量
        ],
        buy_at_least_count=2,
        select_sell=[
            'close < ma(close,60)',     # 跌破长期均线
        ],
        sell_at_least_count=1,
        initial_capital=1000000
    )


def etf_global_asset_allocation():
    """
    全球资产配置组合策略

    配置多个大类资产ETF，实现全球化配置
    """
    return run_portfolio_backtest(
        name='全球资产配置组合',
        symbols=[
            '510300.SH',  # A股：沪深300
            '159915.SZ',  # A股：创业板
            '513100.SH',  # 美国：纳指100
            '513520.SH',  # 日本：日经225
            '513330.SH',  # 欧洲：德国DAX
            '518880.SH',  # 商品：黄金
            '511880.SH',  # 现金：银华日利
        ],
        start_date='20200101',
        end_date='20251215',
        select_buy=[
            'roc(close,20) > 0.03',      # 动量 > 3%
            'close > ma(close,20)',       # 上升趋势
        ],
        buy_at_least_count=1,
        select_sell=[
            'roc(close,20) < -0.03',     # 动量 < -3%
        ],
        sell_at_least_count=1,
        initial_capital=1000000
    )


if __name__ == '__main__':
    # 运行动量组合策略
    print("运行ETF动量组合策略...")
    result1 = etf_momentum_portfolio()

    print("\n" + "="*60)
    print("\n运行ETF趋势跟踪组合策略...")
    result2 = etf_trend_following_portfolio()

    print("\n" + "="*60)
    print("\n运行全球资产配置组合策略...")
    result3 = etf_global_asset_allocation()

    print("\n" + "="*60)
    print("所有策略回测完成！")
