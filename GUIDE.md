# A股模块使用指南

本指南详细介绍如何使用A股智能选股和交易策略模块。

---

## 目录

1. [快速开始](#快速开始)
2. [并发回测优化](#并发回测优化) ⚡ **新增**
3. [A股交易规则](#a股交易规则)
4. [基本配置](#基本配置)
5. [使用示例](#使用示例)
6. [测试验证](#测试验证)
7. [常见问题](#常见问题)
8. [API参考](#api参考)

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
result = e.run(t)
result.stats()
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

## 并发回测优化

### 🚀 性能提升

统一信号生成管道现已支持**多进程并发回测**，可显著提升执行速度。

**系统配置**
- CPU 核心数：**128 核**
- 默认并发数：**8 进程**（自动根据 CPU 核心数设置，最多 8）

**性能对比**

假设有 7 个策略，每个策略回测耗时 5 分钟：

| 并发数 | 预计耗时 | 加速比 | 内存需求 |
|--------|----------|--------|----------|
| 1（顺序执行） | 最慢 | 1x | 最低 |
| **2（默认）** | **推荐** | **约 2x** | **适合 8GB 机器** |
| 3（最大） | 更快 | 约 2-3x | 接近 8GB 安全上限 |

---

### 📋 使用方法

#### 1. 使用默认并发数（推荐）

```bash
python run_ashare_signals.py
```

自动使用 2 个线程并发执行（当前代码默认值）

#### 2. 自定义并发数

```bash
# 使用 3 个线程（当前允许的上限）
python run_ashare_signals.py --workers 3

# 单进程执行（用于调试）
python run_ashare_signals.py --workers 1
```

#### 3. 结合其他参数

```bash
# 强制重新回测 + 3 个并发线程
python run_ashare_signals.py --force-backtest --workers 3

# 查看帮助
python run_ashare_signals.py --help
```

---

### 🔧 技术细节

#### 实现原理

1. **线程池并发**：使用 `ThreadPoolExecutor` 并发运行策略回测
2. **共享连接池**：线程共享数据库连接池，避免 fork 带来的连接问题
3. **内存限制**：当前代码默认 2 个线程，最大限制 3 个
4. **结果收集**：主线程收集所有回测结果并继续生成信号

#### 代码结构

```python
# 单个策略回测函数（在子进程中执行）
def run_single_strategy_backtest(strategy_info):
    # 1. 加载策略
    # 2. 运行回测引擎
    # 3. 提取指标
    # 4. 保存到数据库
    return result

# 并发执行所有策略
with ProcessPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(run_single_strategy_backtest, s) 
               for s in strategies]
    results = [f.result() for f in as_completed(futures)]
```

---

### 📊 日志输出

并发执行时的日志示例：

```
2026-01-06 14:20:00 | INFO | 管道初始化: 并发进程数=8
2026-01-06 14:20:01 | INFO | 发现 7 个A股策略，使用 8 个进程并发执行
2026-01-06 14:20:02 | INFO | [进程 A股动量轮动-激进版] 开始回测...
2026-01-06 14:20:02 | INFO | [进程 A股动量轮动-月频] 开始回测...
2026-01-06 14:20:02 | INFO | [进程 A股多因子智能] 开始回测...
...
2026-01-06 14:25:30 | INFO | [1/7] ✓ A股动量轮动-激进版 完成
2026-01-06 14:25:35 | INFO | [2/7] ✓ A股多因子智能选股-周频 完成
...
2026-01-06 14:26:00 | INFO | 回测完成: 7/7 个策略成功
```

---

### ⚠️ 注意事项

#### 1. 内存使用

每个进程会加载完整的数据到内存，并发数过高可能导致内存不足：

```
单策略内存: ~2GB
8 进程并发: ~16GB
16 进程并发: ~32GB
```

**建议：**
- 内存 32GB：`--workers 8`（推荐）
- 内存 64GB：`--workers 16`
- 内存 128GB+：`--workers 32`

#### 2. 数据库连接

PostgreSQL 默认最大连接数为 100，确保有足够的连接数：

```sql
-- 查看当前连接数
SELECT count(*) FROM pg_stat_activity;

-- 查看最大连接数
SHOW max_connections;

-- 如需增加（重启 PostgreSQL 后生效）
ALTER SYSTEM SET max_connections = 200;
```

#### 3. I/O 瓶颈

如果磁盘 I/O 是瓶颈，过高的并发数反而会降低性能。

**优化建议：**
- 使用 SSD 存储数据库
- 启用数据库缓存
- 适当降低并发数

---

### 🎯 最佳实践

#### 开发阶段
```bash
# 单进程，便于调试
python run_ashare_signals.py --workers 1
```

#### 日常运行
```bash
# 默认并发数，平衡速度和资源
python run_ashare_signals.py
```

#### 大批量回测
```bash
# 当前最大并发线程数为 3
python run_ashare_signals.py --workers 3
```

#### 定时任务
```bash
# 在 crontab 中添加
0 15 * * 1-5 cd /data/home/yy/code/aitrader && python run_ashare_signals.py --workers 2
```

---

### 🔍 常见问题

#### Q1: 应该使用多少并发数？

**A:** 取决于以下因素：

1. **策略数量**
   - ≤ 8 个策略 → 8 进程够用
   - \> 8 个策略 → 可以增至 16-32

2. **内存大小**
   - 32GB → 最多 8-16 进程
   - 64GB → 可用 16-32 进程

3. **目标**
   - 日常运行 → 默认 8 进程
   - 快速测试 → 16 进程
   - 大批量 → 32 进程

**建议：先用默认值，观察系统资源使用情况再调整。**

#### Q2: 为什么 16 进程和 32 进程速度差不多？

**A:** 因为目前只有 7 个策略：
- 8 进程：所有策略同时执行，~5 分钟完成
- 16 进程：仍然只有 7 个任务，额外进程空闲
- 32 进程：同理

**当策略数 > 8 时，更多并发才有意义。**

#### Q3: 出现 "too many clients" 错误？

**A:** PostgreSQL 连接数不足，解决方法：

```bash
# 方法 1: 降低并发数
python run_ashare_signals.py --workers 4

# 方法 2: 增加数据库连接数
psql -c "ALTER SYSTEM SET max_connections = 200;"
sudo systemctl restart postgresql
```

#### Q4: 内存不足怎么办？

**A:** 降低并发数：

```bash
# 从 8 降到 4
python run_ashare_signals.py --workers 4

# 单进程（最省内存）
python run_ashare_signals.py --workers 1
```

#### Q5: 如何查看实时进度？

**A:** 当前版本在日志中显示：

```
[1/7] ✓ A股动量轮动-激进版 完成
[2/7] ✓ A股多因子智能选股-周频 完成
...
```

---

### 📈 监控和优化

#### 实时监控

```bash
# 监控 CPU 使用率
htop

# 监控内存使用
free -h

# 监控进程
ps aux | grep python

# 监控数据库连接
psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='aitrader';"
```

#### 性能分析

添加计时日志查看各策略耗时：

```python
import time
start_time = time.time()
# ... 回测代码 ...
elapsed = time.time() - start_time
logger.info(f"策略 {name} 耗时: {elapsed:.2f}秒")
```

---

### 🔧 故障排查

#### 问题：进程卡死

**原因：** 某个策略回测时间过长或死锁

**解决：**
```bash
# 添加超时控制
timeout 1800 python run_ashare_signals.py  # 30分钟超时
```

#### 问题：内存不足

**原因：** 并发数过高

**解决：**
```bash
# 降低并发数
python run_ashare_signals.py --workers 4
```

#### 问题：数据库连接耗尽

**原因：** 并发进程数 > 可用连接数

**解决：**
1. 降低 `--workers` 数量
2. 增加 PostgreSQL `max_connections`

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

##### 原始数据字段

| 因子 | 说明 | 示例 |
|-----|------|------|
| `pe` | 市盈率 | `pe < 50` |
| `pb` | 市净率 | `pb < 3` |
| `roe` | 净资产收益率 | `roe > 0.08` |
| `turnover_rate` | 换手率 | `turnover_rate > 2` |

##### 基本面因子函数 (19个)

**估值因子** (4个):
| 函数 | 说明 | 示例 |
|-----|------|------|
| `pe_score(pe)` | PE评分(倒数,PE越低分越高) | `pe_score(pe) > 0.05` |
| `pb_score(pb)` | PB评分(倒数,PB越低分越高) | `pb_score(pb) > 0.3` |
| `ps_score(ps)` | PS评分(倒数,PS越低分越高) | `ps_score(ps) > 0.1` |
| `value_score(pe,pb,ps)` | 综合估值评分 | `value_score(pe,pb,ps)` |

**质量因子** (4个):
| 函数 | 说明 | 示例 |
|-----|------|------|
| `roe_score(roe)` | ROE评分 | `roe_score(roe) > 0.12` |
| `roa_score(roa)` | ROA评分 | `roa_score(roa) > 0.05` |
| `profit_margin_score(margin)` | 利润率评分 | `profit_margin_score(profit_margin) > 0.1` |
| `operating_margin_score(margin)` | 营业利润率评分 | `operating_margin_score(operating_margin) > 0.15` |

**市值因子** (4个):
| 函数 | 说明 | 示例 |
|-----|------|------|
| `total_mv_filter(mv,min,max)` | 总市值过滤 | `total_mv_filter(total_mv,50,500)` |
| `circ_mv_filter(mv,min,max)` | 流通市值过滤 | `circ_mv_filter(circ_mv,0,200)` |
| `log_market_cap(mv)` | 对数市值 | `log_market_cap(total_mv)` |
| `market_cap_category(mv)` | 市值分类 | `market_cap_category(total_mv)` |

**综合因子** (3个):
| 函数 | 说明 | 示例 |
|-----|------|------|
| `quality_score(pe,pb,roe)` | 综合质量评分 | `quality_score(pe,pb,roe)` |
| `fundamental_rank_score(**factors)` | 多因子排名评分 | `fundamental_rank_score(pe=pe,roe=roe)` |
| `growth_score(pe,pb,roe)` | 成长评分(GARP) | `growth_score(pe,pb,roe)` |

**工具函数** (2个):
| 函数 | 说明 | 示例 |
|-----|------|------|
| `normalize_score(series,method)` | 标准化因子得分 | `normalize_score(roc,'zscore')` |
| `winsorize(series,limits)` | 去极值处理 | `winsorize(pe,0.05)` |

> **注意**: 所有基本面因子函数同时支持小写和大写调用,例如 `pe_score(pe)` 和 `PE_SCORE(PE)` 都可以。

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

## 股票池管理指南

### 股票池筛选器

StockUniverse 类提供灵活的股票池筛选功能，支持多种筛选条件。

#### 基本使用

```python
from core.stock_universe import StockUniverse

# 创建筛选器实例
universe = StockUniverse()

# 获取所有可交易股票
stocks = universe.get_all_stocks()
print(f"可交易股票: {len(stocks)} 只")
```

---

### 筛选条件说明

#### 1. 基础过滤

```python
# 获取所有股票（包括ST）
all_stocks = universe.get_all_stocks(exclude_st=False)

# 排除ST股票
stocks = universe.get_all_stocks(exclude_st=True)

# 排除ST和停牌
stocks = universe.get_all_stocks(
    exclude_st=True,
    exclude_suspend=True
)

# 排除新上市股票（上市不满60天）
stocks = universe.get_all_stocks(
    exclude_st=True,
    exclude_new_ipo_days=60
)
```

#### 2. 市值筛选

```python
# 大盘股（市值>100亿）
large_caps = universe.get_stock_pool(filters={
    'min_market_cap': 100
})

# 中盘股（50-200亿）
mid_caps = universe.get_stock_pool(filters={
    'min_market_cap': 50,
    'max_market_cap': 200
})

# 小盘股（<50亿）
small_caps = universe.get_stock_pool(filters={
    'max_market_cap': 50
})
```

**市值分类参考**:
- 小盘股: < 50亿
- 中盘股: 50-200亿
- 大盘股: > 200亿

#### 3. 基本面筛选

```python
# 低PE股票（PE<20）
low_pe = universe.get_stock_pool(filters={
    'max_pe': 20
})

# 高ROE股票（ROE>15%）
high_roe = universe.get_stock_pool(filters={
    'min_roe': 0.15
})

# 综合基本面筛选
quality = universe.get_stock_pool(filters={
    'min_market_cap': 50,
    'max_pe': 30,
    'max_pb': 3,
    'min_roe': 0.10
})
```

**支持的基本面参数**:
- `min_pe`, `max_pe`: 市盈率范围
- `min_pb`, `max_pb`: 市净率范围
- `min_roe`, `max_roe`: ROE范围
- `min_roa`: 最小ROA

#### 4. 行业筛选

```python
# 金融行业
financial = universe.get_stock_pool(filters={
    'sectors': ['金融']
})

# 银行+证券
banks = universe.get_stock_pool(filters={
    'industries': ['银行', '证券']
})

# 多板块
multi_sector = universe.get_stock_pool(filters={
    'sectors': ['金融', '科技', '消费']
})
```

---

### 综合筛选示例

#### 示例1: 价值选股策略

```python
universe = StockUniverse()

# 低估值 + 高质量
value_stocks = universe.get_stock_pool(filters={
    'min_market_cap': 50,      # 市值>50亿
    'max_pe': 20,              # PE<20
    'max_pb': 2,               # PB<2
    'min_roe': 0.12,           # ROE>12%
    'exclude_st': True         # 排除ST
})
```

#### 示例2: 大盘蓝筹策略

```python
# 大盘金融股
blue_chips = universe.get_stock_pool(filters={
    'min_market_cap': 200,     # 市值>200亿
    'sectors': ['金融'],       # 金融板块
    'exclude_st': True,
    'exclude_suspend': True
})
```

#### 示例3: GARP策略

```python
# 合理价格成长股
garp_stocks = universe.get_stock_pool(filters={
    'min_market_cap': 50,
    'max_pe': 30,              # 合理估值
    'min_roe': 0.15,           # 高成长性
    'exclude_st': True
})
```

---

### 在策略中使用

#### 示例1: 动态股票池

```python
from core.backtrader_engine import Task, Engine
from core.stock_universe import StockUniverse

t = Task()
t.name = 'A股价值选股'
t.ashare_mode = True

# 动态生成股票池
universe = StockUniverse()
t.symbols = universe.get_stock_pool(filters={
    'min_market_cap': 50,
    'max_pe': 20,
    'min_roe': 0.12,
    'exclude_st': True
})

# 配置策略
t.select_buy = ['roc(close,20) > 0.03']
t.order_by_signal = 'quality_score(pe, pb, roe)'
t.order_by_topK = 20

# 运行回测
e = Engine()
e.run(t)
```

#### 示例2: 多因子策略

```python
t = Task()
t.name = 'A股多因子策略'

# 质量筛选
universe = StockUniverse()
t.symbols = universe.get_stock_pool(filters={
    'min_market_cap': 100,
    'max_pe': 30,
    'min_roe': 0.10
})

# 多因子买入条件
t.select_buy = [
    'roc(close,20) > 0.03',
    'close > ma(close,60)',
    'volume > ma(volume,20)*1.2'
]
t.buy_at_least_count = 2

# 综合评分排序
t.order_by_signal = '''
    quality_score(pe, pb, roe) * 0.4 +
    roc(close,20) * 0.3 +
    trend_score(close,25) * 0.3
'''
t.order_by_topK = 10
```

---

### 统计分析

```python
# 获取股票池统计信息
universe = StockUniverse()
stocks = universe.get_stock_pool(filters={
    'min_market_cap': 100
})

stats = universe.get_universe_stats(stocks[:100])

print(f"股票数量: {stats['total_count']}")
print(f"板块分布: {stats['sectors']}")
print(f"行业分布: {stats['industries']}")
print(f"平均市值: {stats['market_cap']['avg']:.2f}亿")
print(f"平均PE: {stats['fundamental']['avg_pe']:.2f}")
```

---

### 常见问题

#### Q: 如何获取所有A股？
```python
universe = StockUniverse()
all_stocks = universe.get_all_stocks()
```

#### Q: 如何排除ST股票？
```python
stocks = universe.get_all_stocks(exclude_st=True)
# 或
stocks = universe.get_stock_pool(filters={'exclude_st': True})
```

#### Q: 如何筛选大盘股？
```python
large_caps = universe.get_stock_pool(filters={
    'min_market_cap': 100  # 100亿以上
})
```

#### Q: 如何筛选低估值股票？
```python
value_stocks = universe.get_stock_pool(filters={
    'max_pe': 15,
    'max_pb': 2
})
```

#### Q: 如何筛选特定行业？
```python
# 板块筛选
financial = universe.get_stock_pool(filters={
    'sectors': ['金融']
})

# 行业筛选
banks = universe.get_stock_pool(filters={
    'industries': ['银行']
})
```

---

### API参考

#### StockUniverse 类

```python
class StockUniverse:
    def __init__(self, db=None)
        """初始化股票池管理器"""

    def get_all_stocks(self, exclude_st=True, exclude_suspend=True,
                      exclude_new_ipo_days=None) -> List[str]
        """获取所有可交易股票"""

    def filter_by_market_cap(self, symbols, min_mv=None, max_mv=None) -> List[str]
        """按市值筛选"""

    def filter_by_fundamental(self, symbols, min_pe=None, max_pe=None,
                             min_pb=None, max_pb=None,
                             min_roe=None, max_roe=None,
                             min_roa=None) -> List[str]
        """按基本面指标筛选"""

    def filter_by_industry(self, symbols, industries=None, sectors=None) -> List[str]
        """按行业筛选"""

    def filter_by_liquidity(self, symbols, min_amount=None) -> List[str]
        """按流动性筛选"""

    def get_stock_pool(self, date=None, filters=None) -> List[str]
        """综合筛选股票池"""

    def get_universe_stats(self, symbols) -> Dict[str, Any]
        """获取股票池统计信息"""
```

---

### 使用示例

#### 示例1: 基本筛选
```python
from core.stock_universe import StockUniverse

universe = StockUniverse()
stocks = universe.get_all_stocks()
print(f"可交易股票: {len(stocks)} 只")
```

#### 示例2: 质量筛选
```python
quality_stocks = universe.get_stock_pool(filters={
    'min_market_cap': 50,
    'max_pe': 30,
    'min_roe': 0.10,
    'exclude_st': True
})
```

#### 示例3: 在策略中使用
```python
from core.backtrader_engine import Task
from core.stock_universe import StockUniverse

t = Task()
t.name = 'A股价值选股'

# 动态生成股票池
universe = StockUniverse()
t.symbols = universe.get_stock_pool(filters={
    'min_market_cap': 50,
    'max_pe': 20,
    'min_roe': 0.12,
    'exclude_st': True
})

# 配置策略
t.select_buy = ['roc(close,20) > 0.03']
t.order_by_signal = 'quality_score(pe, pb, roe)'
t.order_by_topK = 20
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
result = e.run(t)
result.stats()
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
result = e.run(t)
result.stats()
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
result = e.run(t)
result.stats()
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
result = e.run(task)
result.stats()
result.plot()
```

**2026-03 更新**:
- `Engine.run(task)` 推荐视为返回标准 `BacktestResult`
- 推荐通过 `result.stats()` / `result.plot()` 使用结果对象
- `task.end_date` 现在会被真实用于回测区间
- 为兼容旧脚本，`engine.stats()` / `engine.plot()` 仍可继续使用，但不建议新代码再直接依赖 `engine.perf`、`engine.hist_trades`

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
- `initial_capital` / 默认初始资金由引擎管理
- `select_buy` (List[str]): 买入条件列表
- `select_sell` (List[str]): 卖出条件列表
- `period` (str): 调仓频率 'RunDaily', 'RunWeekly', 'RunMonthly'
- `weight` (str): 权重方案 'WeightEqually'

---

#### 3. portfolio_bt_engine.PortfolioTask

ETF 组合回测任务配置对象。

```python
from core.portfolio_bt_engine import PortfolioTask, PortfolioBacktestEngine

task = PortfolioTask(
    name='ETF组合策略',
    symbols=['510300.SH', '518880.SH', '511260.SH'],
    start_date='20220101',
    end_date='20241231',
    select_buy=['roc(close,20) > 0'],
    target_annual_vol=0.12,
    max_total_weight=0.95,
    risk_off_drawdown_trigger=-0.10,
    risk_off_drawdown_exit=-0.05,
    risk_off_multiplier=0.35,
)

result = PortfolioBacktestEngine(task).run()
print(result['annual_return'], result['max_drawdown'])
```

**常用新增字段（2026-03）**:
- `target_annual_vol`: 启用目标波动率缩放
- `max_total_weight`: 风险资产总权重上限
- `enable_cash_refill`: 未使用权重自动回填现金
- `risk_multiplier_min` / `risk_multiplier_max`: 风险倍率裁剪
- `risk_off_drawdown_trigger` / `risk_off_drawdown_exit`: 组合回撤进入/退出阈值
- `risk_off_vol_trigger` / `risk_off_vol_exit`: 波动率进入/退出阈值
- `risk_off_daily_loss_trigger` / `risk_off_daily_loss_exit`: 单日亏损进入/退出阈值
- `risk_off_multiplier`: 进入 risk-off 后保留的风险资产倍率

**说明**:
- 命令行入口没有破坏性变化
- 这些字段主要面向 Python API、自定义 ETF 组合策略和风险平价策略扩展

---

### A股约束模块

#### 4. ashare_constraints.TPlusOneTracker

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

#### 5. ashare_constraints.PriceLimitChecker

涨跌停检查器。

```python
from core.ashare_constraints import PriceLimitChecker

checker = PriceLimitChecker()
is_hit, limit_type = checker.is_limit_hit(symbol, order_price, prev_close)
limit_up = checker.get_limit_price(symbol, prev_close, 'up')
limit_down = checker.get_limit_price(symbol, prev_close, 'down')
```

---

#### 6. ashare_constraints.LotSizeRounder

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

#### 7. ashare_commission.AShareCommissionSchemeV2

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

#### 8. ashare_commission.calculate_commission_manual

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

---

# A股策略使用指南

本指南介绍如何使用已实现的A股智能选股策略。

---

## 目录

1. [策略快速开始](#策略快速开始)
2. [策略对比](#策略对比)
3. [策略详情](#策略详情)
4. [自定义策略](#自定义策略)
5. [批量回测](#批量回测)

---

## 策略快速开始

### 1. 多因子智能选股策略

多因子策略综合技术面和基本面因子,适合稳健投资者。

```python
from strategies.stocks_多因子智能选股策略 import multi_factor_strategy_weekly
from core.backtrader_engine import Engine

# 创建策略
task = multi_factor_strategy_weekly()

# 运行回测
engine = Engine()
result = engine.run(task)

# 查看结果
result.stats()
# 如需画图：
# result.plot()
```

**策略特点**:
- 技术因子(40%) + 质量因子(30%) + 估值因子(20%) + 流动性因子(10%)
- 至少满足7个条件中的3个
- 持仓20只股票,周频调仓
- 剔除ST、停牌、新股

### 2. 动量轮动选股策略

动量策略追求高收益,适合趋势行情和激进投资者。

```python
from strategies.stocks_动量轮动选股策略 import momentum_strategy_weekly
from core.backtrader_engine import Engine

# 创建策略
task = momentum_strategy_weekly()

# 运行回测
engine = Engine()
result = engine.run(task)

# 查看结果
result.stats()
# 如需画图：
# result.plot()
```

**策略特点**:
- 纯动量驱动,6个强势条件全部满足
- 持仓15只股票,周频调仓
- 多层止损机制
- 避免涨停追高

---

## 策略对比

| 策略 | 风险水平 | 持仓数量 | 调仓频率 | 适用场景 | 买入条件 |
|-----|---------|---------|---------|---------|---------|
| 多因子-周频 | 中等 | 20只 | 每周 | 震荡市、慢牛 | 至少满足3/7个 |
| 多因子-月频 | 中等 | 30只 | 每月 | 长期投资 | 至少满足3/7个 |
| 多因子-保守版 | 低 | 15只 | 每周 | 稳健投资 | 至少满足5/7个 |
| 动量-周频 | 高 | 15只 | 每周 | 趋势牛市 | 全部满足(6/6) |
| 动量-月频 | 中高 | 20只 | 每月 | 趋势牛市 | 至少满足4/6个 |
| 动量-激进版 | 极高 | 10只 | 每周 | 强势牛市 | 全部满足(7/7) |

### 预期收益特征

| 策略类型 | 目标年化 | 最大回撤 | 夏普比率 | 适合市场 |
|---------|---------|---------|---------|---------|
| 多因子-周频 | 15-25% | < 20% | > 1.0 | 震荡市、慢牛 |
| 多因子-月频 | 12-20% | < 18% | > 1.2 | 长期投资 |
| 多因子-保守版 | 10-18% | < 15% | > 1.3 | 稳健投资 |
| 动量-周频 | 20-35% | < 30% | > 0.8 | 趋势牛市 |
| 动量-月频 | 15-30% | < 25% | > 0.9 | 趋势牛市 |
| 动量-激进版 | 25-45% | < 40% | > 0.6 | 强势牛市 |

---

## 策略详情

### 多因子智能选股策略

#### 策略版本

**文件**: `strategies/stocks_多因子智能选股策略.py`

```python
# 导入策略
from strategies.stocks_多因子智能选股策略 import (
    multi_factor_strategy_weekly,      # 周频版本
    multi_factor_strategy_monthly,     # 月频版本
    multi_factor_strategy_conservative # 保守版本
)
```

#### 选股条件

**周频买入条件（至少满足3个）**:
```python
roc(close,20) > 0.03              # 正动量 > 3%
trend_score(close,25) > 0         # 趋势向上
volume > ma(volume,20)*1.2        # 放量确认
close > ma(close,60)              # 长期趋势向上
pe > 0 and pe < 80                # 合理估值区间
roe > 0.08                        # ROE > 8%
turnover_rate > 2                 # 换手率 > 2%
```

**卖出条件（满足任一）**:
```python
roc(close,20) < -0.05             # 动量转负
close < ma(close,20)*0.95         # 跌破20日均线5%
turnover_rate < 0.5               # 流动性枯竭
```

#### 综合评分公式

```python
# 技术因子 (40%)
roc(close,20)*0.25 +
trend_score(close,25)*0.15 +

# 质量因子 (30%)
normalize_score(roe)*0.15 +
normalize_score(profit_to_revenue)*0.10 +
normalize_score(operating_profit_to_revenue)*0.05 +

# 估值因子 (20%)
normalize_score(pe_score(pe))*0.10 +
normalize_score(pb_score(pb))*0.10 +

# 流动性因子 (10%)
LOG(turnover_rate + 1)*0.10
```

#### 组合管理

| 版本 | 持仓数量 | 调仓频率 | 选股要求 | 风险等级 |
|-----|---------|---------|---------|---------|
| 周频 | 20只 | 每周 | 至少3/7 | 中等 |
| 月频 | 30只 | 每月 | 至少3/7 | 中等 |
| 保守版 | 15只 | 每周 | 至少5/7 | 低 |

### 动量轮动选股策略

#### 策略版本

**文件**: `strategies/stocks_动量轮动选股策略.py`

```python
# 导入策略
from strategies.stocks_动量轮动选股策略 import (
    momentum_strategy_weekly,      # 周频版本
    momentum_strategy_monthly,     # 月频版本
    momentum_strategy_aggressive   # 激进版本
)
```

#### 选股条件

**周频买入条件（全部满足）**:
```python
roc(close,20) > 0.08              # 强动量 > 8%
roc(close,5) > -0.03              # 短期未大幅回调
volume > ma(volume,20)            # 量能支撑
close > ma(close,20)              # 上升趋势
turnover_rate > 1.5               # 流动性充足
close < ref(close,1)*1.095        # 未涨停
```

**卖出条件（满足任一）**:
```python
roc(close,20) < 0                 # 动量转负
close/ref(close,1) < 0.92         # 单日大跌-8%
close < ma(close,20)*0.95         # 跌破均线
volume < ma(volume,20)*0.3        # 缩量
roc(close,5) < -0.10              # 短期暴跌
```

#### 组合管理

| 版本 | 持仓数量 | 调仓频率 | 选股要求 | 风险等级 |
|-----|---------|---------|---------|---------|
| 周频 | 15只 | 每周 | 6/6全部满足 | 高 |
| 月频 | 20只 | 每月 | 至少4/6 | 中高 |
| 激进版 | 10只 | 每周 | 7/7全部满足 | 极高 |

---

## 自定义策略

### 修改持仓数量

```python
from strategies.stocks_多因子智能选股策略 import multi_factor_strategy_weekly

def my_custom_strategy():
    t = multi_factor_strategy_weekly()
    t.name = '我的自定义策略'
    t.order_by_topK = 30  # 改为持仓30只
    return t

# 运行自定义策略
from core.backtrader_engine import Engine
engine = Engine()
result = engine.run(my_custom_strategy())
```

### 修改选股条件

```python
from strategies.stocks_多因子智能选股策略 import multi_factor_strategy_weekly

def my_custom_strategy():
    t = multi_factor_strategy_weekly()
    t.name = '高ROE策略'

    # 更严格的条件
    t.select_buy = [
        'roc(close,20) > 0.05',      # 提高动量要求
        'roe > 0.15',                 # 提高ROE要求到15%
        'pe < 30',                    # 降低估值要求
        'close > ma(close,120)'       # 更长期趋势
    ]
    t.buy_at_least_count = 3

    return t
```

### 修改股票池

```python
from strategies.stocks_多因子智能选股策略 import multi_factor_strategy_weekly
from core.stock_universe import StockUniverse

def my_custom_strategy():
    universe = StockUniverse()

    # 只选择大市值股票
    symbols = universe.filter_by_market_cap(
        symbols=universe.get_all_stocks(),
        min_mv=200  # 市值>200亿
    )

    # 只选择特定行业
    symbols = universe.filter_by_industry(
        symbols=symbols,
        industries=['金融', '消费', '医疗']
    )

    t = multi_factor_strategy_weekly()
    t.symbols = symbols
    t.name = '大市值行业龙头策略'

    return t
```

### 修改因子权重

```python
from strategies.stocks_多因子智能选股策略 import multi_factor_strategy_weekly

def my_value_strategy():
    """价值偏好策略"""
    t = multi_factor_strategy_weekly()
    t.name = '价值偏好策略'

    # 调整因子权重,提高估值因子权重
    t.order_by_signal = '''
        # 技术因子 (20%) - 降低
        roc(close,20)*0.15 +
        trend_score(close,25)*0.05 +

        # 质量因子 (30%) - 保持
        normalize_score(roe)*0.15 +
        normalize_score(profit_to_revenue)*0.10 +
        normalize_score(operating_profit_to_revenue)*0.05 +

        # 估值因子 (50%) - 大幅提高
        normalize_score(pe_score(pe))*0.25 +
        normalize_score(pb_score(pb))*0.25
    '''

    return t
```

### 修改调仓周期

```python
from strategies.stocks_多因子智能选股策略 import multi_factor_strategy_weekly

def my_quarterly_strategy():
    """季度调仓策略"""
    t = multi_factor_strategy_weekly()
    t.name = '季度调仓策略'
    t.period = 'RunMonthly'  # 改为月频
    t.order_by_topK = 40     # 增加持仓数量

    # 修改回测日期范围
    t.start_date = '20200101'
    t.end_date = '20241231'

    return t
```

---

## 批量回测

### 使用回测脚本

**文件**: `scripts/run_stock_backtests.py`

```bash
# 运行所有策略
python scripts/run_stock_backtests.py --all

# 运行所有多因子策略
python scripts/run_stock_backtests.py --multi-factor-all

# 运行所有动量策略
python scripts/run_stock_backtests.py --momentum-all

# 运行指定策略
python scripts/run_stock_backtests.py --strategy multi_factor --period weekly

# 显示图表
python scripts/run_stock_backtests.py --all --plot
```

### 在Python中批量运行

```python
from core.backtrader_engine import Engine
from strategies.stocks_多因子智能选股策略 import (
    multi_factor_strategy_weekly,
    multi_factor_strategy_monthly
)
from strategies.stocks_动量轮动选股策略 import (
    momentum_strategy_weekly,
    momentum_strategy_monthly
)

# 定义策略列表
strategies = [
    ('多因子-周频', multi_factor_strategy_weekly),
    ('多因子-月频', multi_factor_strategy_monthly),
    ('动量-周频', momentum_strategy_weekly),
    ('动量-月频', momentum_strategy_monthly),
]

# 批量运行
results = {}
for name, strategy_func in strategies:
    print(f"\n运行策略: {name}")
    task = strategy_func()
    engine = Engine()
    result = engine.run(task)
    result.stats()
    results[name] = result

# 对比结果
print("\n策略对比:")
for name, result in results.items():
    print(f"{name}: {result}")
```

---

## 策略选择建议

### 根据市场环境选择

| 市场环境 | 推荐策略 | 理由 |
|---------|---------|------|
| 震荡市 | 多因子-周频 | 综合因子,稳健收益 |
| 慢牛 | 多因子-月频 | 降低交易成本,长期持有 |
| 快速上涨 | 动量-周频 | 捕捉上涨趋势 |
| 强势牛市 | 动量-激进版 | 追求最大化收益 |
| 不确定 | 多因子-保守版 | 风险控制优先 |

### 根据风险偏好选择

| 风险偏好 | 推荐策略 | 预期年化 | 最大回撤 |
|---------|---------|---------|---------|
| 保守 | 多因子-保守版 | 10-18% | < 15% |
| 稳健 | 多因子-周频 | 15-25% | < 20% |
| 平衡 | 多因子-月频 | 12-20% | < 18% |
| 激进 | 动量-周频 | 20-35% | < 30% |
| 极进 | 动量-激进版 | 25-45% | < 40% |

---

## 注意事项

1. **数据依赖**: 策略需要完整的基本面数据,请确保已运行`scripts/unified_update.py`
2. **计算性能**: 全市场回测可能需要较长时间,建议先用小股票池测试
3. **过拟合风险**: 历史表现不代表未来,实盘前需充分验证
4. **交易成本**: A股手续费较高,高频策略需考虑交易成本影响
5. **市场适应性**: 不同策略适合不同市场环境,需根据实际情况调整

---

## 下一步

- 查看完整实施计划: [PLAN.md](PLAN.md#phase-4-策略实现)
- 了解A股交易规则: [A股交易规则](#a股交易规则)
- 查看API参考: [API参考](#api参考)
- 阅读测试用例: [tests/test_stock_universe.py](tests/test_stock_universe.py)

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
  - ✅ 基本面因子库(factor_fundamental.py) - 19个因子函数
  - ✅ 因子表达式引擎注册(factor_expr.py)
  - ✅ 定时任务配置(setup_fundamental_cron.sh)
  - ✅ 支持PE、PB、ROE等估值和质量因子
  - ✅ 全市场5700+只A股覆盖
  - ✅ 1年历史数据保留
  - ✅ 基本面因子与技术因子无缝集成

- **v3.0** (2026-01-05): Phase 3股票池管理系统完成
  - ✅ 股票池筛选器(core/stock_universe.py) - StockUniverse类
  - ✅ 统一数据更新脚本(scripts/unified_update.py)
  - ✅ 定时任务配置(crontab自动更新)
  - ✅ 支持市值、基本面、行业等多维度筛选
  - ✅ 股票池统计分析功能
  - ✅ 完整测试覆盖

- **v4.0** (2026-01-06): Phase 4策略实现完成
  - ✅ 多因子智能选股策略(strategies/stocks_多因子智能选股策略.py)
  - ✅ 动量轮动选股策略(strategies/stocks_动量轮动选股策略.py)
  - ✅ 策略回测脚本(scripts/run_stock_backtests.py)
  - ✅ 6个策略版本(周频/月频/保守版/激进版)
  - ✅ 完整策略使用指南(本文档"策略使用指南"章节)
  - ✅ 支持动态因子权重、行业中性化、流动性过滤
  - ✅ 完整的自定义策略示例

- **v4.1** (2026-01-06): 并发回测优化 ⚡
  - ✅ 多进程并发执行策略回测（run_ashare_signals.py）
  - ✅ 自动检测 CPU 核心数，智能设置并发数
  - ✅ 命令行参数支持：`--workers N`
  - ✅ **性能提升 7 倍**（7 个策略从 35 分钟降至 5 分钟）
  - ✅ 进程隔离，独立数据库连接
  - ✅ 实时进度追踪和结果收集
  - ✅ 完整的并发回测使用指南（本文档"并发回测优化"章节）
  - ✅ 修复 `stock_metadata.list_date` 缺失问题（scripts/update_stock_list_date.py）
  - ✅ 更新 5384 只股票的上市日期数据

---

## 联系支持

如有问题或建议,请查阅:
- 实施计划: [PLAN.md](PLAN.md)
- 项目详情: [README.md](README.md)
- 测试文件: [tests/test_ashare_constraints.py](tests/test_ashare_constraints.py)
- 并发回测: 参考本文档"并发回测优化"章节
