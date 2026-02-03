# 短线A股选股系统说明

## 概述

短线A股选股系统通过 4 步量化 Pipeline，自动生成每日操作清单。系统从板块资金流分析开始，到个股筛选，再到交易计划生成，全流程自动化。

**核心优势**:
- 自动获取板块数据（无需手动预处理）
- 量化筛选强势板块和个股
- 智能计算仓位、止盈止损
- 支持追涨和低吸两种策略

## 核心逻辑：4 步选股 Pipeline

### 步骤 0: 板块数据准备 (自动)

系统自动检测数据库中是否存在当天板块数据：
- 如不存在，自动从 akshare 获取板块资金流数据
- 计算技术指标（MA5/10, RSI, 放量率等）
- 统计板块涨停家数
- 计算综合得分并写入数据库 `sector_data` 表

**数据源**: akshare `stock_fund_flow_industry`

### 步骤 1: 板块量化筛选

从数据库读取板块数据，进行三维度评分：

#### 1.1 资金面 (权重 50%)
- **主力净流入**: ≥ 300 万
- **成交额放量率**: ≥ 1.5 (相比前5日平均)

#### 1.2 技术面 (权重 30%)
- **MA 多头排列**: Close > MA5 > MA10
- **RSI 健康区间**: 30 ~ 70

#### 1.3 情绪面 (权重 20%)
- **涨停家数**: ≥ 3 只

#### 1.4 综合得分
```
综合得分 = 资金分×0.5 + 技术分×0.3 + 情绪分×0.2
```

筛选出 **Top 5 强势板块** 进入下一步。

### 步骤 2: 个股量化选股

对每个强势板块，分别应用两种策略：

#### 2.1 追涨策略 (Momentum)

**核心逻辑**: 捕捉强势股的上涨动能

**筛选条件**:
- 5 日内创收盘新高
- 涨停或强势突破（涨幅 ≥ 7%）
- 主力净流入 ≥ 500 万
- 量比 ≥ 1.2
- 排除连续涨停 > 3 板

**每个板块最多选 3 只**

#### 2.2 低吸策略 (Mean Reversion)

**核心逻辑**: 捕捉超跌后的反弹机会

**筛选条件**:
- 收盘价偏离 MA5 ≤ 3%
- MACD 金叉
- 板块有资金流入
- RSI 超卖（可选）

**每个板块最多选 2 只**

#### 2.3 风险过滤

两种策略都会进行统一风险过滤：
- ❌ 排除亏损股
- ❌ 排除减持预警股
- ❌ 排除停牌股
- ✅ 流通市值: 20 ~ 300 亿

### 步骤 3: 交易规则量化计算

对选出的股票，生成完整的交易计划：

#### 3.1 仓位分配

根据板块排名分配仓位：

| 板块排名 | 单板块仓位 | 说明 |
|---------|----------|------|
| 1 ~ 2   | 15%      | 最强势板块，重仓 |
| 3 ~ 5   | 10%      | 次强势板块，中仓 |

**限制**:
- 单只股票最多 10% 仓位
- 总仓位最多 80%

#### 3.2 止损策略

两种止损方式并行：

1. **固定止损**: 成本价 -5%
2. **移动止损**: 跌破 MA5（动态）

取两者中较严格的止损价。

#### 3.3 止盈策略 (梯度止盈)

| 涨幅 | 卖出比例 | 说明 |
|-----|---------|------|
| +10% | 30%     | 部分止盈，锁定利润 |
| +20% | 50%     | 大部分止盈 |
| 剩余 | 参考 10 日新高 | 保留趋势仓位 |

#### 3.4 开仓触发条件

次日开盘时，需满足以下条件才建仓：

- **高开幅度**: 2% ~ 5% （太高不追，太低不买）
- **封板率**: ≥ 70%
- **竞价金额**: ≥ 1000 万

### 步骤 4: 保存到数据库

生成的交易计划写入 `daily_operation_list` 表，包含：

- 股票代码、名称
- 所属板块、板块排名
- 策略类型 (追涨/低吸)
- **建议仓位**
- **止损价**
- **止盈价**
- **开仓触发条件** (高开幅度、封板率、竞价金额)
- 综合得分

## 使用方法

### 完整流程（推荐）

```bash
# 自动获取板块数据 + 生成信号
python run_short_term_signals.py 20260120
```

**输出示例**:
```
【步骤0/4】板块数据准备
--------------------------------------------------------------------------------
板块数据不存在，开始获取: 20260120
正在获取行业板块资金流数据...
✓ 获取到 41 个行业板块资金流数据
✓ 成功保存 41 条板块数据

【步骤1/4】板块量化筛选
--------------------------------------------------------------------------------
✓ 筛选出 5 个强势板块: 消费电子, 半导体, 新能源, ...

【步骤2/4】个股量化选股
--------------------------------------------------------------------------------
✓ 追涨策略: 8 只
✓ 低吸策略: 4 只

【步骤3/4】交易规则量化计算
--------------------------------------------------------------------------------
✓ 生成 12 个交易计划

【步骤4/4】保存到数据库
--------------------------------------------------------------------------------
✓ 成功保存 12 条交易计划到数据库

✓✓✓ 每日操作清单生成完成!
```

### 仅获取板块数据

```bash
python run_short_term_signals.py 20260120 --fetch-only
```

适用场景：
- 定时任务提前更新板块数据
- 单独分析板块强弱

### 仅生成信号

```bash
python run_short_term_signals.py 20260120 --signals-only
```

适用场景：
- 板块数据已存在
- 多次调整参数后重新生成信号

### 强制刷新板块数据

```bash
python run_short_term_signals.py 20260120 --force-refresh
```

适用场景：
- 板块数据有误或不完整
- 重新计算技术指标

### 使用今天日期

```bash
# 不指定日期，默认使用今天
python run_short_term_signals.py
```

## 配置文件

配置文件位于 `short_term_config/short_term_config.py`，可调整：

### 板块筛选参数
```python
min_main_net_inflow_1d = 300      # 主力净流入阈值（万元）
min_volume_expansion_ratio = 1.5  # 放量率阈值
require_ma_bullish = True         # 是否要求MA多头
min_rsi = 30                      # RSI下限
max_rsi = 70                      # RSI上限
min_limit_up_count = 3            # 最小涨停家数
top_sectors = 5                   # 选择板块数量
```

### 追涨策略参数
```python
require_5d_high_close = True      # 5日新高
require_limit_up = True           # 要求涨停
min_main_net_inflow = 500         # 主力流入（万元）
min_volume_ratio = 1.2            # 量比
max_stocks_per_sector = 3         # 每板块最大选股数
```

### 低吸策略参数
```python
max_close_ma_deviation = 3        # 收盘价偏离MA5百分比
require_macd_golden_cross = True  # MACD金叉
require_sector_inflow = True      # 板块流入
max_stocks_per_sector = 2         # 每板块最大选股数
```

### 仓位管理参数
```python
max_sector_position = 0.15        # 单板块最大仓位
max_stock_position = 0.10         # 单股票最大仓位
max_total_position = 0.80         # 总仓位上限
```

### 风险控制参数
```python
stop_loss_pct_close = 0.05        # 固定止损 -5%
gradient_10pct_sell_ratio = 0.30  # +10%卖出30%
gradient_20pct_sell_ratio = 0.50  # +20%卖出50%
```

## 数据库表

### `sector_data` 表

板块基础数据，每日更新：

| 字段 | 说明 | 单位 |
|------|------|------|
| date | 日期 | date |
| sector_name | 板块名称 | varchar |
| main_net_inflow_1d | 1日主力净流入 | 万元 |
| volume_expansion_ratio | 成交额放量率 | float |
| limit_up_count | 涨停家数 | int |
| close | 板块指数收盘价 | float |
| ma5 | 5日均线 | float |
| ma10 | 10日均线 | float |
| rsi | RSI指标 | float |
| strength_score | 综合得分 | float |

### `daily_operation_list` 表

每日操作清单，核心输出：

| 字段 | 说明 |
|------|------|
| date | 日期 |
| stock_code | 股票代码 |
| stock_name | 股票名称 |
| sector_name | 所属板块 |
| sector_rank | 板块排名 |
| strategy_type | 策略类型 (chase/dip) |
| position_ratio | 建议仓位 (0-1) |
| stop_loss_price | 止损价 |
| take_profit_price | 止盈价 |
| open_trigger_high_pct | 高开触发条件 |
| open_trigger_seal_ratio | 封板率触发条件 |
| open_trigger_auction_amount | 竞价金额触发条件 |
| strength_score | 综合得分 |
| is_executed | 是否已执行 |

## 系统架构

```
run_short_term_signals.py          # 主入口
├── SectorDataFetcher              # 板块数据获取 (内嵌)
│   ├── fetch_sector_fund_flow()   # 从 akshare 获取
│   ├── calculate_sector_indicators()  # 计算技术指标
│   └── fetch_and_save()           # 保存到数据库
│
├── SectorAnalyzer                 # 板块分析器 (core/sector_analyzer.py)
│   └── calculate_sector_scores()  # 计算板块得分
│
├── StockSelector                  # 选股器 (core/stock_selector.py)
│   ├── select_chase_stocks()      # 追涨选股
│   └── select_dip_stocks()        # 低吸选股
│
└── PositionManager                # 仓位管理器 (core/position_manager.py)
    └── generate_trading_plans()   # 生成交易计划
```

## 注意事项

### 1. 首次使用：填充板块信息

如果是第一次使用系统，需要先填充股票的板块信息：

```bash
python scripts/fill_stock_sectors.py
```

这个脚本会：
- 从 akshare 获取所有行业板块及其成分股
- 更新数据库中 5455 只股票的板块信息
- 约 97% 的股票会被成功分配板块信息

**只需运行一次**，板块信息会持久保存在数据库中。

### 2. 日期格式
统一使用 **YYYYMMDD** 格式，如 `20260120`

### 3. 数据完整性
- 确保数据库中股票历史数据完整（至少 60 天）
- 板块数据依赖 akshare，网络不稳定可能失败
- 如失败，可使用 `--force-refresh` 重试

### 4. 运行时机
建议每个交易日 **收盘后 (15:30 之后)** 运行：
- 15:30 - 运行 `--fetch-only` 更新板块数据
- 16:00 - 运行完整流程生成信号

### 5. Cron 定时任务
```bash
# 每个交易日 15:30 获取板块数据
30 15 * * 1-5 cd /path/to/aitrader && python run_short_term_signals.py $(date +\%Y\%m\%d) --fetch-only

# 每个交易日 16:00 生成交易信号
0 16 * * 1-5 cd /path/to/aitrader && python run_short_term_signals.py $(date +\%Y\%m\%d)
```

### 6. 常见问题

**Q: 提示 "没有成功计算出任何板块数据"？**
A: 需要先运行 `python scripts/fill_stock_sectors.py` 填充板块信息

**Q: 提示 "数据库中无板块数据"？**
A: 先运行 `--fetch-only` 获取板块数据

**Q: 板块数据过旧？**
A: 使用 `--force-refresh` 强制刷新

**Q: 未选出任何股票？**
A: 检查配置参数是否过严，或市场当日无强势板块

**Q: 部分板块技术指标计算失败？**
A: 正常现象，板块内无股票或数据不足时会被跳过

## 性能优化

- 板块数据缓存：自动检测数据库，避免重复获取
- 数据库索引：`sector_data.date`, `daily_operation_list.date`
- 并发计算：因子计算使用多线程（如需要）

## 后续优化方向

1. **回测验证**: 验证策略历史表现
2. **参数自适应**: 根据市场环境自动调整参数
3. **更多策略**: 添加突破策略、事件驱动策略等
4. **实时监控**: 盘中实时监控触发条件
5. **风险归因**: 分析策略盈亏来源

---

**作者**: AITrader
**最后更新**: 2026-01-21
**版本**: 1.0
