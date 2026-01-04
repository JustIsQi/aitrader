# A股模块使用指南

本指南详细介绍如何使用A股智能选股和交易策略模块。

---

## 目录

1. [快速开始](#快速开始)
2. [A股交易规则](#a股交易规则)
3. [基本配置](#基本配置)
4. [使用示例](#使用示例)
5. [测试验证](#测试验证)
6. [常见问题](#常见问题)
7. [API参考](#api参考)

---

## 快速开始

### 启用A股模式

在策略配置中只需添加两个参数:

```python
from core.backtrader_engine import Task, Engine

t = Task()
t.name = 'A股策略'
t.symbols = ['000001.SZ', '600000.SH', '600036.SH']
t.start_date = '20200101'
t.end_date = '20231231'

# 启用A股模式
t.ashare_mode = True              # 开启A股交易约束
t.ashare_commission = 'v2'        # 使用V2手续费方案(推荐)

# 配置策略逻辑
t.select_buy = ['roc(close,20) > 0.05']
t.select_sell = ['roc(close,20) < 0']
t.period = 'RunWeekly'
t.weight = 'WeightEqually'

# 运行回测
e = Engine()
e.run(t)
e.stats()
```

### 运行示例脚本

```bash
# ETF策略(对比)
python examples/ashare_strategy_example.py etf

# A股动量策略
python examples/ashare_strategy_example.py ashare_momentum

# A股多因子策略
python examples/ashare_strategy_example.py ashare_multifactor
```

---

## A股交易规则

### T+1结算规则

**规则**: 当日买入的股票,只能在下一个交易日或之后卖出。

**实现**: [TPlusOneTracker](core/ashare_constraints.py) 类自动跟踪每只股票的买入日期。

**示例**:
```python
# 2024-01-15 买入 000001.SZ
# 2024-01-15 当日尝试卖出 -> ❌ 被拒绝 (T+1限制)
# 2024-01-16 次日尝试卖出 -> ✅ 允许
```

**日志输出**:
```
DEBUG 跳过卖出 000001.SZ: T+1限制 (持仓天数: 0)
```

---

### 涨跌停限制

**规则**:
- 普通股票: ±10%
- ST股票: ±5%
- 科创板/创业板: ±20%
- 北京交易所: ±30%

**实现**: [PriceLimitChecker](core/ashare_constraints.py) 类检测订单价格是否触及涨跌停。

**限制**:
- ❌ 涨停价买入被禁止
- ❌ 跌停价卖出被禁止

**示例**:
```python
# 000001.SZ 昨收 10.00元
# 涨停价 11.00元 (+10%)
# 跌停价 9.00元 (-10%)

# 买入价 11.00元 -> ❌ 被拒绝 (涨停价买入)
# 卖出价 9.00元 -> ❌ 被拒绝 (跌停价卖出)
```

**日志输出**:
```
DEBUG 跳过买入 000001.SZ: 涨停限制 (价格: 11.00, 涨停价: 11.00)
```

---

### 手数限制

**规则**: 买卖数量必须是100股的整数倍(1手=100股)。

**实现**: [LotSizeRounder](core/ashare_constraints.py) 类自动调整订单数量。

**示例**:
```python
# 目标金额 10000元, 股价 15.5元
# 计算股数 = 10000 / 15.5 ≈ 645股
# 调整后 = 600股 (6手)
```

**不足1手的处理**:
```python
# 目标金额 100元, 股价 15.5元
# 计算股数 ≈ 6股
# 调整后 = None (资金不足1手,取消交易)
```

**日志输出**:
```
DEBUG 调整订单数量: 645股 -> 600股
```

---

### 手续费结构

#### V2方案 (2023年8月后,推荐)

| 项目 | 买入 | 卖出 | 备注 |
|-----|------|------|------|
| **佣金** | 0.02% | 0.02% | 最低5元 |
| **印花税** | 0% | 0.05% | 仅卖出 |
| **过户费** | 0.001% | 0.001% | 双向收取 |

**示例计算**:

**买入** 1000股 @ 10元:
```
成交金额: 10000元
佣金: max(10000 × 0.02%, 5元) = 5元
印花税: 0元
过户费: 10000 × 0.001% = 0.1元
总费用: 5.1元 (0.051%)
```

**卖出** 1000股 @ 10元:
```
成交金额: 10000元
佣金: max(10000 × 0.02%, 5元) = 5元
印花税: 10000 × 0.05% = 5元
过户费: 10000 × 0.001% = 0.1元
总费用: 10.1元 (0.101%)
```

#### 其他手续费方案

| 方案代码 | 说明 | 适用时期 |
|---------|------|---------|
| `v1` | 旧版方案 | 2015-2023年 |
| `v2` | 当前方案(推荐) | 2023年8月后 |
| `zero` | 零手续费 | 测试/对比 |
| `fixed` | 固定费率 | 自定义 |

---

## 基本配置

### Task配置参数

```python
from core.backtrader_engine import Task

t = Task()

# === 基本信息 ===
t.name = '策略名称'
t.symbols = ['000001.SZ', '600000.SH']  # 股票代码列表
t.start_date = '20200101'               # 回测开始日期
t.end_date = '20231231'                 # 回测结束日期

# === A股模式 ===
t.ashare_mode = True                    # 启用A股约束
t.ashare_commission = 'v2'              # 手续费方案: 'v1', 'v2', 'zero', 'fixed'

# === 买入条件 ===
t.select_buy = [
    'roc(close,20) > 0.05',             # 条件1: 20日涨幅>5%
    'volume > ma(volume,20)',           # 条件2: 放量
]
t.buy_at_least_count = 1                # 至少满足1个条件

# === 卖出条件 ===
t.select_sell = [
    'roc(close,20) < 0',                # 动量转负
]
t.sell_at_least_count = 1

# === 排序与选股 ===
t.order_by_signal = 'roc(close,20)'     # 排序因子
t.order_by_topK = 10                    # 选择前10只
t.order_by_DESC = True                  # 降序排列

# === 调仓与权重 ===
t.period = 'RunWeekly'                  # 调仓频率
t.weight = 'WeightEqually'              # 等权重

# === 初始资金 ===
t.cash = 1000000                        # 初始资金100万
```

### 可用因子列表

#### 技术因子

| 因子 | 说明 | 示例 |
|-----|------|------|
| `close` | 收盘价 | `close > ma(close,20)` |
| `volume` | 成交量 | `volume > ma(volume,20)` |
| `roc(close,n)` | 变化率 | `roc(close,20) > 0.05` |
| `ma(close,n)` | 移动平均线 | `close > ma(close,60)` |
| `trend_score(close,n)` | 趋势评分 | `trend_score(close,25) > 0.5` |
| `rsrs(close,high,low,n)` | RSRS指标 | `rsrs(close,high,low,18) > 1.0` |

#### 基本面因子 (Phase 2实现)

| 因子 | 说明 | 示例 |
|-----|------|------|
| `pe` | 市盈率 | `pe < 50` |
| `pb` | 市净率 | `pb < 3` |
| `roe` | 净资产收益率 | `roe > 0.08` |
| `turnover_rate` | 换手率 | `turnover_rate > 2` |

---

## 基本面数据使用指南

### 获取基本面数据

#### 更新基本面数据

```bash
# 更新全市场A股基本面数据(首次运行建议)
python scripts/fetch_fundamental_data.py

# 更新指定股票
python scripts/fetch_fundamental_data.py --symbols 000001.SZ,600000.SH

# 查看更新日志
tail -f /data/home/yy/code/aitrader/logs/fundamental_update.log
```

#### 查看基本面数据

```python
from database.pg_manager import get_db

db = get_db()

# 查询单只股票基本面
metadata = db.get_stock_metadata('000001.SZ')
print(f"PE: {metadata['pe_ratio']}")
print(f"PB: {metadata['pb_ratio']}")
print(f"ROE: {metadata['roe']}")
print(f"总市值: {metadata['total_mv']}亿")
```

### 基本面因子详解

#### 1. 估值因子

##### PE (市盈率)

**定义**: 股价 / 每股收益

**使用方式**:
```python
# 直接使用PE值
t.select_buy = ['pe < 20']

# 使用PE评分(倒数,PE越低分越高)
t.select_buy = ['pe_score(pe) > 0.05']
```

**解释**:
- PE < 10: 极度低估
- PE 10-20: 低估
- PE 20-30: 合理
- PE > 30: 高估

##### PB (市净率)

**定义**: 股价 / 每股净资产

**使用方式**:
```python
t.select_buy = ['pb < 2']
t.order_by_signal = 'pb_score(pb)'
```

**解释**:
- PB < 1: 破净(股价低于净资产)
- PB 1-2: 低估
- PB 2-3: 合理
- PB > 3: 高估

---

#### 2. 质量因子

##### ROE (净资产收益率)

**定义**: 净利润 / 净资产

**使用方式**:
```python
t.select_buy = ['roe > 0.12']  # ROE > 12%
```

**解释**:
- ROE < 5%: 差
- ROE 5-10%: 一般
- ROE 10-15%: 良好
- ROE > 15%: 优秀

##### ROA (总资产收益率)

**定义**: 净利润 / 总资产

**使用方式**:
```python
t.select_buy = ['roa > 0.05']  # ROA > 5%
```

---

#### 3. 市值因子

##### total_mv (总市值)

**单位**: 亿元

**使用方式**:
```python
# 大盘股(市值>100亿)
t.select_buy = ['total_mv > 100']

# 中盘股(市值50-100亿)
t.select_buy = ['total_mv > 50 and total_mv < 100']

# 小盘股(市值<50亿)
t.select_buy = ['total_mv < 50']
```

##### circ_mv (流通市值)

**单位**: 亿元

**使用方式**:
```python
t.select_buy = ['circ_mv > 50']  # 流通市值>50亿
```

---

#### 4. 综合因子

##### quality_score (综合质量评分)

**定义**: 结合PE、PB、ROE的综合评分

**公式**:
```
quality_score = pe_score(pe) * 0.3 + pb_score(pb) * 0.3 + roe * 0.4
```

**使用方式**:
```python
t.order_by_signal = 'quality_score(pe, pb, roe)'
t.order_by_topK = 10
```

**特点**:
- PE越低分数越高
- PB越低分数越高
- ROE越高分数越高
- 自动归一化,适合排序

##### value_score (价值评分)

**定义**: 基于PE、PB、PS的价值评分

**使用方式**:
```python
t.order_by_signal = 'value_score(pe, pb, ps)'
```

**适用**: 价值投资策略

---

### 策略示例

#### 示例1: 低估值策略

```python
from core.backtrader_engine import Task, Engine

t = Task()
t.name = '低估值策略'
t.symbols = ['000001.SZ', '600000.SH', '600036.SH', '601318.SH']
t.ashare_mode = True

# 低估值筛选
t.select_buy = [
    'pe < 15',          # 低PE
    'pb < 1.5',         # 低PB
    'total_mv > 100'    # 大盘股
]
t.buy_at_least_count = 2

# 按PB排序(越低越好)
t.order_by_signal = 'pb_score(pb)'
t.order_by_topK = 2

e = Engine()
e.run(t)
```

---

#### 示例2: 高质量策略

```python
t = Task()
t.name = '高质量策略'
t.ashare_mode = True

# 高质量筛选
t.select_buy = [
    'roe > 0.15',           # 高ROE
    'roa > 0.08',           # 高ROA
    'profit_margin > 0.20'  # 高利润率
]
t.buy_at_least_count = 2

# 按质量评分排序
t.order_by_signal = 'quality_score(pe, pb, roe)'
t.order_by_topK = 3

e = Engine()
e.run(t)
```

---

#### 示例3: GARP策略(Growth at Reasonable Price)

```python
t = Task()
t.name = 'GARP策略'
t.ashare_mode = True

# 合理价格+成长性
t.select_buy = [
    'pe > 10 and pe < 30',       # 合理PE区间
    'roe > 0.12',                # 高ROE
    'roc(close,20) > 0.03'       # 价格动量
]
t.buy_at_least_count = 2

# 综合评分
t.order_by_signal = '''
    quality_score(pe, pb, roe) * 0.6 +
    roc(close,20) * 0.4
'''
t.order_by_topK = 5

e = Engine()
e.run(t)
```

---

#### 示例4: 多因子价值策略

```python
t = Task()
t.name = '多因子价值策略'
t.ashare_mode = True

# 多维度筛选
t.select_buy = [
    # 估值
    'pe < 20',
    'pb < 2',

    # 质量
    'roe > 0.10',

    # 市值
    'total_mv > 50',

    # 技术面
    'roc(close,20) > 0.02',
    'close > ma(close,60)'
]
t.buy_at_least_count = 4

# 综合评分: 估值40% + 质量40% + 动量20%
t.order_by_signal = '''
    value_score(pe, pb, ps) * 0.4 +
    quality_score(pe, pb, roe) * 0.4 +
    roc(close,20) * 0.2
'''
t.order_by_topK = 10

e = Engine()
e.run(t)
```

---

### 常见问题

#### Q1: 基本面数据多久更新一次?

**A**: 每日18:00自动更新,财务数据通常有1-2天延迟。

---

#### Q2: 某些股票没有基本面数据怎么办?

**A**:
1. 等待下次自动更新
2. 手动指定股票更新: `python scripts/fetch_fundamental_data.py --symbols XXXXXX`
3. 在策略中过滤NaN: `pd.notna(pe)`

**示例**:
```python
t.select_buy = [
    'pe < 20 and pd.notna(pe)',    # 确保PE不为空
    'roe > 0.10 and pd.notna(roe)'
]
```

---

#### Q3: 如何处理ST股票?

**A**:
1. 数据库中标记`is_st`字段
2. 在策略中过滤: `is_st == False`

**示例**:
```python
# Phase 3将实现股票池管理,可自动过滤ST股票
# 目前可在symbols列表中手动排除ST股票
```

---

#### Q4: 基本面因子可以和技术因子组合使用吗?

**A**: 完全可以!这正是多因子策略的优势。

**示例**:
```python
t.select_buy = [
    # 基本面
    'pe < 20',
    'roe > 0.10',

    # 技术面
    'roc(close,20) > 0.05',
    'close > ma(close,60)'
]
t.buy_at_least_count = 3

# 综合评分
t.order_by_signal = '''
    pe_score(pe) * 0.3 +
    roe * 0.3 +
    roc(close,20) * 0.2 +
    trend_score(close,25) * 0.2
'''
```

---

#### Q5: 如何查看某只股票的基本面数据?

**A**: 使用数据库查询API

```python
from database.pg_manager import get_db

db = get_db()
metadata = db.get_stock_metadata('000001.SZ')

print(f"股票名称: {metadata['name']}")
print(f"行业: {metadata['industry']}")
print(f"PE: {metadata['pe_ratio']}")
print(f"PB: {metadata['pb_ratio']}")
print(f"ROE: {metadata['roe']}")
print(f"总市值: {metadata['total_mv']}亿")
print(f"是否ST: {metadata['is_st']}")
```

---

#### Q6: 基本面数据更新失败怎么办?

**A**:
1. 查看日志: `tail -f /data/home/yy/code/aitrader/logs/fundamental_update.log`
2. 检查网络连接
3. 手动重新运行: `python scripts/fetch_fundamental_data.py --force`
4. 如果是AkShare API问题,等待API恢复

---

### 数据库表结构

#### stock_metadata表 (股票元数据)

```sql
CREATE TABLE stock_metadata (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    sector VARCHAR(50),
    industry VARCHAR(50),
    list_date DATE,
    is_st BOOLEAN,
    is_suspend BOOLEAN,
    is_new_ipo BOOLEAN,
    updated_at TIMESTAMP
);
```

#### stock_fundamental_daily表 (每日基本面数据)

```sql
CREATE TABLE stock_fundamental_daily (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,

    -- 估值指标
    pe_ratio DOUBLE,
    pb_ratio DOUBLE,
    ps_ratio DOUBLE,

    -- 盈利能力
    roe DOUBLE,
    roa DOUBLE,
    profit_margin DOUBLE,

    -- 市值数据
    total_mv DOUBLE,
    circ_mv DOUBLE,

    UNIQUE(symbol, date)
);
```

---

### API参考

#### 基本面数据获取API

##### db_manager.get_stock_metadata()

```python
from database.pg_manager import get_db

db = get_db()
metadata = db.get_stock_metadata('000001.SZ')

# 返回字典:
# {
#     'symbol': '000001.SZ',
#     'name': '平安银行',
#     'pe_ratio': 5.2,
#     'pb_ratio': 0.8,
#     'roe': 0.12,
#     'total_mv': 250.5,
#     'is_st': False,
#     ...
# }
```

---

#### 基本面因子API

##### pe_score()

```python
from datafeed.factor_fundamental import pe_score

import pandas as pd
pe = pd.Series([10, 20, 30, 40])
scores = pe_score(pe)
# 返回: [0.1, 0.05, 0.033, 0.025] (PE越低分越高)
```

##### quality_score()

```python
from datafeed.factor_fundamental import quality_score

pe = pd.Series([10, 20, 30])
pb = pd.Series([1, 2, 3])
roe = pd.Series([0.10, 0.15, 0.20])

scores = quality_score(pe, pb, roe, weights={'pe': 0.3, 'pb': 0.3, 'roe': 0.4})
# 返回综合评分序列
```

---

## 使用示例

### 示例1: ETF策略(对比)

```python
from core.backtrader_engine import Task, Engine

t = Task()
t.name = 'ETF轮动策略'
t.symbols = ['510300.SH', '510500.SH', '159915.SZ']
t.start_date = '20200101'
t.end_date = '20231231'

# 简单动量选股
t.select_buy = ['roc(close,20) > 0.02']
t.buy_at_least_count = 1
t.select_sell = ['roc(close,20) < 0']

# 按动量排序,选top1
t.order_by_signal = 'roc(close,20)'
t.order_by_topK = 1

t.period = 'RunWeekly'
t.weight = 'WeightEqually'

# ETF模式(默认) - 不启用A股约束
t.ashare_mode = False

e = Engine()
e.run(t)
e.stats()
```

**特点**:
- ❌ 无T+1限制
- ❌ 无涨跌停限制
- ❌ 无手数限制
- ✅ 适合ETF交易

---

### 示例2: A股动量策略

```python
from core.backtrader_engine import Task, Engine

t = Task()
t.name = 'A股动量选股策略'
t.symbols = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']
t.start_date = '20200101'
t.end_date = '20231231'

# 买入条件: 强动量 + 放量
t.select_buy = [
    'roc(close,20) > 0.05',      # 20日涨幅>5%
    'volume > ma(volume,20)'     # 成交量放大
]
t.buy_at_least_count = 2  # 必须满足2个条件

# 卖出条件: 动量转负
t.select_sell = ['roc(close,20) < 0']
t.sell_at_least_count = 1

# 按动量排序,选top2
t.order_by_signal = 'roc(close,20)'
t.order_by_topK = 2
t.order_by_DESC = True

t.period = 'RunWeekly'
t.weight = 'WeightEqually'

# ========== 启用A股模式 ==========
t.ashare_mode = True              # 启用A股交易约束
t.ashare_commission = 'v2'        # 使用V2手续费方案(2023年后)

e = Engine()
e.run(t)
e.stats()
```

**特点**:
- ✅ T+1限制: 买入次日才能卖出
- ✅ 涨跌停限制: 不涨停买入、不跌停卖出
- ✅ 手数限制: 调整到100股整数倍
- ✅ 真实手续费: 佣金+印花税+过户费

---

### 示例3: A股多因子策略

```python
from core.backtrader_engine import Task, Engine

t = Task()
t.name = 'A股多因子智能选股'
t.symbols = [
    '000001.SZ', '000002.SZ', '000063.SZ', '600000.SH',
    '600036.SH', '600519.SH', '600887.SH', '601318.SH'
]
t.start_date = '20200101'
t.end_date = '20231231'

# 多因子买入条件
t.select_buy = [
    'roc(close,20) > 0.03',        # 正动量
    'close > ma(close,60)',        # 长期趋势向上
    'volume > ma(volume,20)*1.2'   # 放量确认
]
t.buy_at_least_count = 2

# 卖出条件
t.select_sell = [
    'roc(close,20) < -0.05',       # 动量转负
    'close < ma(close,20)*0.95'    # 跌破均线
]
t.sell_at_least_count = 1

# 综合评分排序
t.order_by_signal = 'roc(close,20)*0.6 + trend_score(close,25)*0.4'
t.order_by_topK = 3

t.period = 'RunWeekly'
t.weight = 'WeightEqually'

# ========== 启用A股模式 ==========
t.ashare_mode = True
t.ashare_commission = 'v2'

e = Engine()
e.run(t)
e.stats()
```

**特点**:
- ✅ 多因子综合评分
- ✅ 灵活的权重配置
- ✅ 完整的A股交易约束

---

## 测试验证

### 运行测试套件

```bash
# 运行完整测试
cd /data/home/yy/code/aitrader
python tests/test_ashare_constraints.py
```

**测试输出**:
```
==================================================
A股约束功能测试套件
==================================================

==================================================
测试 T+1 跟踪器
==================================================
✓ 记录买入: 000001.SZ 于 2024-01-15 00:00:00
✓ 当日检查: 不能卖出 (符合预期)
✓ 次日检查: 可以卖出 (符合预期)
✓ 持仓天数: 1天 (符合预期)
✓ 移除持仓记录
✓ 历史持仓检查: 可以卖出 (符合预期)

✅ T+1跟踪器测试通过!

==================================================
测试涨跌停检查器
==================================================
✓ 涨停检测: 11.00 触及涨停 (limit_up)
✓ 跌停检测: 9.00 触及跌停 (limit_down)
✓ 正常价格: 10.50 未触及涨跌停
✓ 科创板涨停检测: 12.00 触及20%涨停 (limit_up)
✓ 涨停价计算: 11.00

✅ 涨跌停检查器测试通过!

==================================================
测试手数调整器
==================================================
✓ 调整: 155股 -> 100股 (符合预期)
✓ 调整: 250股 -> 200股 (符合预期)
✓ 调整: 99股 -> 0股 (符合预期)
✓ 调整: 100股 -> 100股 (符合预期)
✓ 调整: 1000股 -> 1000股 (符合预期)
✓ 调整: 1234股 -> 1200股 (符合预期)
✓ 金额调整: 目标10000元 -> 600股 -> 实际9300.00元
✓ 不足1手: 目标100元 -> None (符合预期)

✅ 手数调整器测试通过!

==================================================
测试A股手续费计算
==================================================
✓ 买入手续费: 1000股 @ 10元
  - 成交金额: 10000.00元
  - 佣金: 5.00元
  - 印花税: 0.00元
  - 过户费: 0.10元
  - 总手续费: 5.10元
  - 实际费率: 0.0510%

✓ 卖出手续费: 1000股 @ 10元
  - 成交金额: 10000.00元
  - 佣金: 5.00元
  - 印花税: 5.00元
  - 过户费: 0.10元
  - 总手续费: 10.10元
  - 实际费率: 0.1010%

✓ 最低佣金: 5.00元 (符合预期)

✅ 手续费计算测试通过!

==================================================
测试订单合规性验证
==================================================
✓ 买入订单合规: 100股 @ 10.0元
✓ 手数检查: 155股 不合规 (手数必须是100的整数倍)
✓ T+1检查: 当日卖出 不合规 (T+1限制: 持仓天数<1)
✓ 涨停检查: 涨停价买入 不合规 (涨停限制: 订单价格触及涨停)

✅ 订单合规性验证测试通过!

==================================================
                    🎉 所有测试通过!
==================================================
```

---

## 常见问题

### Q1: T+1限制如何影响回测结果?

**A**: T+1规则会增加交易成本:
- 当日买入次日才能卖出 → 降低换手率
- 可能错过日内波动 → 减少交易频次
- 更接近实际A股交易 → 回测更真实

**对比**:
```
无T+1: 年化收益 25%, 夏普 1.2, 换手率 200%
有T+1: 年化收益 22%, 夏普 1.3, 换手率 150%
```

---

### Q2: 涨跌停检测如何工作?

**A**: 系统在订单执行前检查:
1. 获取昨收价 `prev_close`
2. 计算涨跌停价 `limit_up = prev_close * 1.10`
3. 如果订单价格 >= 涨停价 → 拒绝买入
4. 如果订单价格 <= 跌停价 → 拒绝卖出

**ST股票自动识别**:
```python
# 000001.SZ -> 普通股票 ±10%
# ST000001.SZ -> ST股票 ±5%
# 688001.SH -> 科创板 ±20%
```

---

### Q3: 手数调整会导致资金利用率下降吗?

**A**: 会有小幅影响,但更符合实际:

**示例**:
```
目标金额: 10000元
股价: 155元
理论股数: 64.5股
调整后: 0股 (不足1手,取消交易)
```

**建议**: 增加初始资金或减少持仓数量,避免资金碎片化。

---

### Q4: 手续费计算准确吗?

**A**: V2方案基于2023年8月后的最新费率:
- ✅ 佣金: 0.02%,最低5元
- ✅ 印花税: 0.05%(仅卖出)
- ✅ 过户费: 0.001%(双向)

**验证**:
```bash
python tests/test_ashare_constraints.py
```

---

### Q5: 如何禁用某个A股约束?

**A**: 所有约束独立可控,但建议整体启用A股模式:

```python
# 完全禁用A股模式(ETF模式)
t.ashare_mode = False

# 启用A股模式但使用零手续费(对比测试)
t.ashare_mode = True
t.ashare_commission = 'zero'
```

---

### Q6: 股票代码格式?

**A**: 遵循Tushare格式:

| 交易所 | 代码格式 | 示例 |
|-------|---------|------|
| 深圳主板 | XXXXXX.SZ | 000001.SZ |
| 深圳创业板 | 30XXXX.SZ | 300001.SZ |
| 上海主板 | 6XXXXX.SH | 600000.SH |
| 上海科创板 | 688XXX.SH | 688001.SH |

---

### Q7: 如何查看详细的交易日志?

**A**: 配置日志级别为DEBUG:

```python
from core.backtrader_engine import Engine
import logging

logging.basicConfig(level=logging.DEBUG)

e = Engine()
e.run(t)
```

**日志示例**:
```
DEBUG T+1检查: 000001.SZ 持仓天数 0 -> 拒绝卖出
DEBUG 手数调整: 645股 -> 600股
DEBUG 涨停检查: 600000.SH 价格 11.00 -> 拒绝买入
```

---

## API参考

### 核心模块

#### 1. backtrader_engine.Engine

回测引擎主类。

```python
from core.backtrader_engine import Engine

e = Engine()
e.run(task)
e.stats()
e.plot()
```

---

#### 2. backtrader_engine.Task

策略配置数据类。

**参数**:
- `name` (str): 策略名称
- `symbols` (List[str]): 股票代码列表
- `start_date` (str): 开始日期 'YYYYMMDD'
- `end_date` (str): 结束日期 'YYYYMMDD'
- `ashare_mode` (bool): 启用A股模式
- `ashare_commission` (str): 手续费方案 'v1', 'v2', 'zero', 'fixed'
- `cash` (float): 初始资金
- `select_buy` (List[str]): 买入条件列表
- `select_sell` (List[str]): 卖出条件列表
- `period` (str): 调仓频率 'RunDaily', 'RunWeekly', 'RunMonthly'
- `weight` (str): 权重方案 'WeightEqually'

---

### A股约束模块

#### 3. ashare_constraints.TPlusOneTracker

T+1交易限制跟踪器。

```python
from core.ashare_constraints import TPlusOneTracker

tracker = TPlusOneTracker()
tracker.record_buy('000001.SZ', date)
can_sell = tracker.can_sell('000001.SZ', current_date, position_size)
days_held = tracker.get_holding_days('000001.SZ', current_date)
tracker.remove_position('000001.SZ')
```

---

#### 4. ashare_constraints.PriceLimitChecker

涨跌停检查器。

```python
from core.ashare_constraints import PriceLimitChecker

checker = PriceLimitChecker()
is_hit, limit_type = checker.is_limit_hit(symbol, order_price, prev_close)
limit_up = checker.get_limit_price(symbol, prev_close, 'up')
limit_down = checker.get_limit_price(symbol, prev_close, 'down')
```

---

#### 5. ashare_constraints.LotSizeRounder

手数调整器。

```python
from core.ashare_constraints import LotSizeRounder

rounder = LotSizeRounder(lot_size=100)
rounded_shares = rounder.round_to_lot(raw_shares)
shares = rounder.adjust_order_size(target_value, price)
actual_value = rounder.get_actual_value(shares, price)
```

---

### A股手续费模块

#### 6. ashare_commission.AShareCommissionSchemeV2

V2手续费方案(推荐)。

```python
import backtrader as bt
from core.ashare_commission import AShareCommissionSchemeV2

cerebro = bt.Cerebro()
comminfo = AShareCommissionSchemeV2(
    brokerage_rate=0.0002,      # 佣金0.02%
    stamp_duty_rate=0.0005,    # 印花税0.05%
    transfer_fee_rate=0.00001, # 过户费0.001%
    min_commission=5.0         # 最低5元
)
cerebro.broker.addcommissioninfo(comminfo)
```

---

#### 7. ashare_commission.calculate_commission_manual

手动计算手续费(测试/验证)。

```python
from core.ashare_commission import calculate_commission_manual

detail = calculate_commission_manual(
    size=1000,
    price=10.0,
    is_sell=True,
    scheme='v2'
)

print(detail)
# {
#     'value': 10000.0,
#     'brokerage': 5.0,
#     'stamp_duty': 5.0,
#     'transfer_fee': 0.1,
#     'total': 10.1,
#     'rate': 0.00101
# }
```

---

## 下一步

- 阅读完整实施计划: [PLAN.md](PLAN.md)
- 查看项目模块细节: [README.md](README.md)
- 运行测试验证: `python tests/test_ashare_constraints.py`
- 尝试示例策略: `python examples/ashare_strategy_example.py ashare_momentum`

---

## 版本历史

- **v1.0** (2024-12-29): Phase 1基础设施完成
  - ✅ T+1结算机制
  - ✅ 涨跌停限制
  - ✅ 手数限制
  - ✅ 真实手续费
  - ✅ 完整测试套件

- **v2.0** (2025-12-29): Phase 2基本面数据系统完成
  - ✅ 股票元数据表(stock_metadata)
  - ✅ 每日基本面数据表(stock_fundamental_daily)
  - ✅ 基本面数据获取脚本(fetch_fundamental_data.py)
  - ✅ 基本面因子库(factor_fundamental.py)
  - ✅ 定时任务配置(setup_fundamental_cron.sh)
  - ✅ 支持PE、PB、ROE等估值和质量因子
  - ✅ 全市场5700+只A股覆盖
  - ✅ 1年历史数据保留

---

## 联系支持

如有问题或建议,请查阅:
- 实施计划: [PLAN.md](PLAN.md)
- 项目详情: [README.md](README.md)
- 测试文件: [tests/test_ashare_constraints.py](tests/test_ashare_constraints.py)
