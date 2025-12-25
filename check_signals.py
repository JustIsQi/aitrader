#!/usr/bin/env python
"""检查当前买入信号"""

from datetime import datetime, timedelta
import pandas as pd
from datafeed.csv_dataloader import CsvDataLoader
from datafeed.factor_expr import FactorExpr

# 当前日期
today = datetime.now().strftime('%Y%m%d')
one_month_ago = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')

print(f"分析时间范围: {one_month_ago} - {today}")
print("=" * 60)

# ETF列表
etfs = [
    "563300.SH", "159509.SZ", "518880.SH", "513100.SH", "513520.SH",
    "513330.SH", "512100.SH", "162719.SZ", "513030.SH", "513380.SH",
    "513290.SH", "159560.SZ", "513040.SH", "561600.SH", "515880.SH",
    "513090.SH", "159819.SZ", "515790.SH", "515030.SH", "159752.SZ",
    "159761.SZ", "512480.SH", "560800.SH", "513500.SH"
]

# 买入条件（需满足至少2个）
buy_conditions = [
    "roc(close,5)*100<5.5",
    "roc(close,10)*100<10",
    "roc(close,3)*100>-1.5"
]

# 卖出条件（满足1个即卖出）
sell_conditions = [
    "roc(close,10)*100>18.5",
    "roc(close,20)*100>16",
    "roc(close,1)*100<-6.5",
    "roc(close,2)*100<-4",
    "roc(close,3)*100<-8",
    "volume/ma(volume,5)<0.3",
    "volume/ma(volume,20)>4.5",
    "volume/ma(volume,120)>9",
    "ma(volume,5)/ma(volume,120)<0.45",
    "slope(low,25)/ma(low,25)*44+roc(close,13)*0.6+roc(high,8)*0.3+roc(high,5)*0.9+ma(volume,5)/ma(volume,20)<-1"
]

# 排序因子
order_by = "trend_score(close,25)*0.27+roc(close,13)*0.75+roc(close,8)*0.18+roc(high,5)*0.6+ma(volume,5)/ma(volume,20)"

# 加载数据
print("加载数据...")
loader = CsvDataLoader()
dfs = loader.read_dfs(symbols=etfs, start_date=one_month_ago, end_date=today)

# 计算因子
all_conditions = buy_conditions + sell_conditions + [order_by]
factor_expr = FactorExpr()
df_all = factor_expr.calc_formulas(dfs, all_conditions)

# 获取最新一天的数据
latest_date = df_all.index.max()
df_latest = df_all[df_all.index == latest_date].copy()

print(f"\n最新交易日期: {latest_date.date()}")
print("=" * 60)

# 分析每个ETF
buy_candidates = []
sell_signals = []
neutral = []

for symbol in etfs:
    # 获取该symbol在最新日期的行
    symbol_rows = df_latest[df_latest['symbol'] == symbol]
    if symbol_rows.empty:
        continue

    row = symbol_rows.iloc[0]

    # 检查买入条件
    buy_count = 0
    buy_details = []
    for i, cond in enumerate(buy_conditions, 1):
        try:
            val = row.get(cond)
            if pd.notna(val) and val == True:
                buy_count += 1
                buy_details.append(f"  ✓ 条件{i}: {cond}")
        except:
            pass

    # 检查卖出条件
    sell_count = 0
    sell_details = []
    for i, cond in enumerate(sell_conditions, 1):
        try:
            val = row.get(cond)
            if pd.notna(val) and val == True:
                sell_count += 1
                sell_details.append(f"  ✗ 条件{i}: {cond}")
        except:
            pass

    # 获取排序因子值
    try:
        order_val = row.get(order_by)
    except:
        order_val = None

    # 获取收盘价
    close_price = row.get('close', 'N/A')

    # 判断状态
    if sell_count >= 1:
        sell_signals.append({
            'symbol': symbol,
            'sell_count': sell_count,
            'sell_details': sell_details,
            'order_val': order_val,
            'close': close_price
        })
    elif buy_count >= 2:
        buy_candidates.append({
            'symbol': symbol,
            'buy_count': buy_count,
            'buy_details': buy_details,
            'order_val': order_val,
            'close': close_price
        })
    else:
        neutral.append({
            'symbol': symbol,
            'buy_count': buy_count,
            'order_val': order_val,
            'close': close_price
        })

# 输出结果
print("\n【买入建议】满足至少2个买入条件的ETF:\n")
if buy_candidates:
    # 按排序因子排序
    buy_candidates.sort(key=lambda x: x['order_val'] if x['order_val'] is not None else -999, reverse=True)

    for i, item in enumerate(buy_candidates, 1):
        print(f"{i}. {item['symbol']} (收盘价: {item['close']})")
        print(f"   满足买入条件: {item['buy_count']}/3")
        if item['order_val'] is not None:
            print(f"   排序因子值: {item['order_val']:.4f}")
        for detail in item['buy_details']:
            print(detail)
        print()
else:
    print("暂无满足买入条件的ETF\n")

print("\n【卖出信号】满足卖出条件的ETF:\n")
if sell_signals:
    for item in sell_signals:
        print(f"⚠ {item['symbol']} (收盘价: {item['close']})")
        print(f"   满足卖出条件: {item['sell_count']}")
        for detail in item['sell_details']:
            print(detail)
        print()
else:
    print("无卖出信号\n")

print("\n【观察列表】暂不操作的ETF:\n")
if neutral:
    for item in neutral:
        print(f"  {item['symbol']}: 满足买入条件 {item['buy_count']}/3, 收盘价 {item['close']}")
else:
    print("无")

print("\n" + "=" * 60)
print("建议操作:")
if buy_candidates:
    print(f"买入 {buy_candidates[0]['symbol']}（排序因子最高）")
else:
    print("当前无合适买入标的，继续保持空仓")
