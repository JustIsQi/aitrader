"""
示例：结合 DuckDB 进行交易信号分析

这个脚本展示了如何：
1. 从数据库读取数据
2. 根据策略生成交易信号
3. 分析买卖建议
"""
from db_manager import get_db
from datafeed.db_dataloader import DbDataLoader
from backtrader_engine import Task, DataFeed
from datetime import datetime
import pandas as pd

# ========== 配置参数 ==========
INITIAL_CAPITAL = 5000
MAX_POSITIONS = 5
CASH_PER_POSITION = INITIAL_CAPITAL / MAX_POSITIONS

ETF_LIST = [
    "563300.SH", "159509.SZ", "518880.SH", "513100.SH", "513520.SH",
    "588000.SH", "513330.SH", "512100.SH", "162719.SZ", "513030.SH",
    "513380.SH", "513290.SH", "159560.SZ", "588100.SH", "513040.SH",
    "561600.SH", "515880.SH", "513090.SH", "159819.SZ", "515790.SH",
    "515030.SH", "159752.SZ", "159761.SZ", "512480.SH", "560800.SH",
    "513500.SH"
]

BUY_CONDITIONS = [
    "roc(close,5)*100<5.5",
    "roc(close,10)*100<10",
    "roc(close,3)*100>-1.5"
]

SELL_CONDITIONS = [
    "roc(close,10)*100>18.5",
    "roc(close,20)*100>16",
    "roc(close,1)*100<-6.5",
]

ORDER_SIGNAL = "trend_score(close,25)*0.27+roc(close,13)*0.75+roc(close,8)*0.18+roc(high,5)*0.6+ma(volume,5)/ma(volume,20)"


def check_signals_with_db():
    """检查交易信号并分析买卖建议"""
    print("="*80)
    print("基于 DuckDB 的交易信号分析")
    print("="*80)

    # 初始化数据库
    db = get_db('/data/home/yy/data/duckdb/trading.db')

    # 创建任务配置
    t = Task()
    t.name = '全球大类资产轮动'
    t.symbols = ETF_LIST
    t.start_date = '20200101'
    t.end_date = datetime.now().strftime('%Y%m%d')
    t.select_buy = BUY_CONDITIONS
    t.select_sell = SELL_CONDITIONS
    t.buy_at_least_count = 2
    t.sell_at_least_count = 1
    t.order_by_signal = ORDER_SIGNAL

    # 加载数据（优先从 DuckDB）
    print("\n⏳ 从 DuckDB 加载数据...")
    datafeed = DataFeed(t)

    # 获取当前持仓
    print("\n📊 当前持仓情况:")
    current_positions = db.get_positions()

    if current_positions.empty:
        print("  当前无持仓")
        holding_symbols = set()
    else:
        holding_symbols = set(current_positions['symbol'].tolist())
        for _, row in current_positions.iterrows():
            print(f"  {row['symbol']}: {row['quantity']:.0f}股, "
                  f"成本 {row['avg_cost']:.3f}, "
                  f"市值 {row['market_value']:.2f}")

    # 检查卖出信号
    print("\n" + "="*80)
    print("📉 检查卖出信号")
    print("="*80)

    df_close = datafeed.get_factor_df('close')
    sell_candidates = set()

    for condition in SELL_CONDITIONS:
        df_condition = datafeed.get_factor_df(condition)
        df_condition = df_condition.replace({True: 1, False: 0})
        latest_values = df_condition.iloc[-1]
        symbols_sell = latest_values[latest_values == 1].index.tolist()

        if symbols_sell:
            # 只关注已持仓的标的
            symbols_to_sell = [s for s in symbols_sell if s in holding_symbols]
            if symbols_to_sell:
                print(f"\n条件: {condition}")
                print(f"  触发卖出的持仓: {', '.join(symbols_to_sell)}")
                sell_candidates.update(symbols_to_sell)

                for symbol in symbols_to_sell:
                    sell_price = df_close.iloc[-1][symbol]
                    position = current_positions[current_positions['symbol'] == symbol].iloc[0]
                    print(f"    {symbol}: {sell_price:.3f}元 (持仓 {position['quantity']:.0f}股, 成本 {position['avg_cost']:.3f})")

    # 检查买入信号
    print("\n" + "="*80)
    print("📈 检查买入信号")
    print("="*80)

    buy_signals = {}
    for condition in BUY_CONDITIONS:
        df_condition = datafeed.get_factor_df(condition)
        df_condition = df_condition.replace({True: 1, False: 0})
        buy_signals[condition] = df_condition

    buy_summary = {}
    for symbol in ETF_LIST:
        if symbol in holding_symbols - sell_candidates:  # 跳过已持有且不卖的
            continue

        satisfied_count = 0
        for condition, df in buy_signals.items():
            if symbol in df.columns:
                satisfied_count += df.iloc[-1][symbol]

        if satisfied_count >= 2:
            buy_summary[symbol] = satisfied_count

    if buy_summary:
        # 按评分排序
        df_order = datafeed.get_factor_df(ORDER_SIGNAL)
        latest_order = df_order.iloc[-1]

        order_summary = {}
        for symbol in buy_summary.keys():
            if symbol in latest_order.index and pd.notna(latest_order[symbol]):
                order_summary[symbol] = latest_order[symbol]

        order_summary = dict(sorted(order_summary.items(), key=lambda x: x[1], reverse=True))

        # 计算可买入数量（考虑已持仓 + 新买入 <= MAX_POSITIONS）
        current_holdings = len(holding_symbols - sell_candidates)
        available_slots = MAX_POSITIONS - current_holdings

        if available_slots > 0:
            print(f"\n🎯 建议买入 (前 {available_slots} 个):")
            buy_candidates = list(order_summary.items())[:available_slots]

            for idx, (symbol, score) in enumerate(buy_candidates, 1):
                latest_price = df_close.iloc[-1][symbol]
                quantity = int(CASH_PER_POSITION / latest_price)

                print(f"\n【{idx}】 {symbol}")
                print(f"    最新价格: {latest_price:.3f}元")
                print(f"    综合评分: {score:.4f}")
                print(f"    建议买入: {quantity}股")
                print(f"    投入金额: {quantity * latest_price:.2f}元")
        else:
            print("\n⚠️  持仓已满，无法买入新标的")
    else:
        print("\n⚠️  当前没有满足买入条件的标的")

    print("\n" + "="*80)
    print(f"分析完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)


if __name__ == '__main__':
    check_signals_with_db()
