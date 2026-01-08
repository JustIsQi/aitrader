# AITrader - 量化交易系统

## 目录

- [项目概述](#项目概述)
- [目录结构](#目录结构)
- [PostgreSQL 数据库集成](#postgresql-数据库集成)
- [快速开始](#快速开始)
- [核心模块](#核心模块)
- [A股智能选股模块](#a股智能选股模块)
- [多策略信号系统](#多策略信号系统)
- [策略配置](#策略配置)
- [API 参考](#api-参考)
- [性能对比](#性能对比)
- [Web 部署指南](#web-部署指南)
- [故障排除](#故障排除)
- [版本信息](#版本信息)

---

## 项目概述

AITrader 是一个基于 Python 的完整量化交易系统，采用模块化设计，支持从数据获取、因子计算、策略实现到回测验证的全流程。

### 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      AITrader v3.5                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 数据获取模块  │  │ 因子计算模块  │  │ 策略回测模块  │      │
│  │ scripts/     │  │ alpha/       │  │ core/        │      │
│  │ database/    │  │ datafeed/    │  │ strategies/  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ 信号生成模块  │  │ 优化模块      │                         │
│  │ signals/     │  │ optimization/ │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

### 目录结构

```
aitrader/
├── core/                   # 核心引擎模块 (backtrader 封装)
│   ├── backtrader_engine.py    # Backtrader 引擎封装
│   ├── bt_engine.py            # Cerebro 引擎
│   ├── backtrader_strategy.py  # 基础策略类
│   ├── backtrader_algos.py     # 交易算法
│   └── backtrader_inds.py      # 技术指标
├── database/               # 数据库管理 (PostgreSQL)
│   ├── pg_manager.py          # PostgreSQL 数据库管理器
│   ├── models/                # ORM 模型定义
│   │   ├── base.py            # 数据库连接配置
│   │   └── models.py          # 所有数据表模型
│   └── factor_cache.py        # 因子缓存
├── signals/                # 信号生成与报告
│   ├── multi_strategy_signals.py   # 多策略信号生成器
│   ├── signal_reporter.py          # 报告生成器
│   ├── strategy_parser.py          # 策略解析器
│   └── daily_signal.py             # 每日信号生成
├── strategies/             # 交易策略库
│   ├── 上证50双均线策略.py
│   ├── 创业板择时策略.py
│   ├── 沪深300ETF的RSRS择时.py
│   └── ... (共17个策略文件)
├── datafeed/               # 数据加载与处理
│   ├── csv_dataloader.py      # CSV 数据加载器
│   ├── factor_extends.py      # 因子扩展
│   └── factor_expr.py         # 因子表达式
├── alpha/                  # Alpha 因子计算
│   ├── factor_engine.py        # 因子引擎
│   ├── stock_engine.py         # 股票引擎
│   └── load_bar_df.py          # K线数据加载
├── optimization/           # 策略优化 (遗传算法)
│   ├── deap_engine.py          # DEAP 遗传算法引擎
│   └── init_pset.py            # 参数集初始化
├── scripts/                # 工具脚本
│   ├── auto_update_etf_data.py # 自动更新 ETF 数据
│   ├── get_data.py             # 数据下载
│   ├── init_postgres_db.py     # PostgreSQL 数据库初始化
│   └── sync_strategy_codes.py  # 同步策略代码
├── tests/                  # 测试模块
├── data/                   # 数据存储
│   └── akshare_data/          # AKShare 数据
└── logs/                   # 日志文件
```

### 核心特性

- **PostgreSQL 数据库**: 企业级数据库，支持高并发和ACID事务
- **双引擎支持**: 基于 `bt` 和 `backtrader` 两种回测框架
- **灵活的因子系统**: 支持自定义因子表达式和 Alpha158 因子库
- **多种选股策略**: 条件筛选、TopK 排序、多因子组合
- **交易记录管理**: 完整的持仓、交易历史跟踪
- **风险管理**: 止损、止盈、风险平价配置

---

## 数据管理

本项目使用 PostgreSQL 数据库存储所有历史数据、交易记录和信号。

**完整的数据架构、更新流程和维护指南请参阅 [数据管理指南](DATA.md)**。

---

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- backtrader - 回测框架
- pandas - 数据处理
- numpy - 数值计算
- ffn - 金融分析
- loguru - 日志
- fastapi - Web 框架

> **提示**: 数据库初始化和配置请参阅 [数据管理指南](DATA.md)

---

## 核心模块

### 1. 数据获取模块

**文件**: [scripts/get_data.py](scripts/get_data.py)

```python
from scripts.get_data import fetch_etf_history

# 获取 ETF 历史数据
df = fetch_etf_history('510300')
```

**特性**:
- 支持 ETF、股票数据获取
- 自动代理配置
- 增量更新机制

### 2. 数据加载器

**文件**: [datafeed/csv_dataloader.py](datafeed/csv_dataloader.py)

```python
from datafeed.csv_dataloader import CsvDataLoader

# 自动优先使用 PostgreSQL，失败则回退到 CSV
loader = CsvDataLoader()
dfs = loader.read_dfs(['510300.SH', '513100.SH'])
```

**特性**:
- ✅ 优先从 PostgreSQL 读取（高性能）
- ✅ PostgreSQL 失败自动回退到 CSV
- ✅ 对上层代码完全透明

### 3. 数据库管理器

**文件**: [db_manager.py](db_manager.py)

```python
from db_manager import get_db

db = get_db()

# 查询历史数据
df = db.get_etf_history('510300.SH', start_date='2024-01-01')

# 记录交易
db.insert_transaction(
    symbol='510300.SH',
    buy_sell='buy',
    quantity=100,
    price=4.5,
    trade_date='2024-12-26',
    strategy_name='趋势策略'
)

# 更新持仓
db.update_position('510300.SH', quantity=100, avg_cost=4.5, current_price=4.6)

# 获取当前持仓
positions = db.get_positions()
```

### 4. 选股模块

**核心类**: `Task` ([backtrader_engine.py:24-48](backtrader_engine.py))

```python
@dataclass
class Task:
    name: str = '策略'
    symbols: List[str] = field(default_factory=list)
    start_date: str = '20100101'
    end_date: str = datetime.now().strftime('%Y%m%d')

    # 选股相关
    select_buy: List[str] = field(default_factory=list)    # 买入条件
    buy_at_least_count: int = 0                           # 满足几个条件才买入
    select_sell: List[str] = field(default_factory=list)  # 卖出条件
    sell_at_least_count: int = 1                          # 满足几个条件才卖出

    # 排序相关
    order_by_signal: str = ''      # 排序因子
    order_by_topK: int = 1         # 选取前 K 个
    order_by_dropN: int = 0        # 丢弃前 N 个
    order_by_DESC: bool = True     # 是否降序

    # 权重相关
    weight: str = 'WeighEqually'   # 权重分配方式
    period: str = 'RunDaily'       # 调仓频率
```

### 5. 支持的因子类型

#### 基础指标

| 因子名称 | 表达式 | 说明 |
|---------|-------|------|
| 开盘价 | `open` | 当日开盘价 |
| 收盘价 | `close` | 当日收盘价 |
| 成交量 | `volume` | 当日成交量 |
| 动量 | `roc(close,20)` | 20 日变化率 |
| 斜率 | `slope(close,25)` | 25 日线性回归斜率 |

#### 技术指标

| 因子名称 | 表达式 | 说明 |
|---------|-------|------|
| RSRS | `RSRS(high,low,18)` | 18 日 RSRS 指标 |
| RSRS 标准分 | `RSRS_zscore(high,low,18,600)` | 标准化 RSRS |
| 均线金叉 | `ma(close,5)>ma(close,20)` | 5 日均线 > 20 日均线 |
| 布林带 | `bbands_up(close,20,2)` | 布林带上轨 |
| ATR | `ta_atr(high,low,close,14)` | 14 日 ATR |

---

## A股智能选股模块

### 简介

基于现有的ETF轮动系统,新增A股智能选股和交易策略功能,严格模拟A股市场交易规则。

### 核心特性

- ✅ **T+1交易规则**: 当日买入次日才能卖出
- ✅ **涨跌停限制**: 普通股±10%, ST股±5%, 科创板±20%
- ✅ **手数限制**: 自动调整到100股整数倍
- ✅ **真实手续费**: 佣金0.02% + 印花税0.05%(卖出) + 过户费0.001%
- ✅ **向后兼容**: 不影响现有ETF策略,可独立启用

### 快速使用

#### 启用A股模式

只需在策略配置中添加两个参数:

```python
from core.backtrader_engine import Task, Engine

t = Task()
t.name = 'A股策略'
t.symbols = ['000001.SZ', '600000.SH', '600036.SH']
t.start_date = '20200101'
t.end_date = '20231231'

# 启用A股模式
t.ashare_mode = True              # 开启A股交易约束
t.ashare_commission = 'v2'        # 使用V2手续费方案(2023年后,推荐)

# 配置策略逻辑
t.select_buy = ['roc(close,20) > 0.05', 'volume > ma(volume,20)']
t.buy_at_least_count = 2
t.select_sell = ['roc(close,20) < 0']
t.period = 'RunWeekly'
t.weight = 'WeightEqually'

# 运行回测
e = Engine()
e.run(t)
e.stats()
```

#### 运行示例脚本

```bash
# A股动量策略
python examples/ashare_strategy_example.py ashare_momentum

# A股多因子策略
python examples/ashare_strategy_example.py ashare_multifactor
```

### A股交易规则详解

#### 1. T+1结算规则

**规则**: 当日买入的股票,只能在下一个交易日或之后卖出。

**实现**: 系统自动跟踪每只股票的买入日期,并在卖出时检查持仓天数。

**示例**:
```
2024-01-15 买入 000001.SZ
2024-01-15 当日尝试卖出 -> ❌ 被拒绝 (T+1限制)
2024-01-16 次日尝试卖出 -> ✅ 允许
```

#### 2. 涨跌停限制

**规则**:
- 普通股票: ±10%
- ST股票: ±5%
- 科创板/创业板: ±20%
- 北京交易所: ±30%

**限制**:
- ❌ 涨停价买入被禁止
- ❌ 跌停价卖出被禁止

#### 3. 手数限制

**规则**: 买卖数量必须是100股的整数倍(1手=100股)。

系统自动调整订单数量到最近的100股倍数。

**示例**:
```
目标金额: 10000元, 股价: 155元
计算股数: 64股
调整后: 0股 (不足1手,取消交易)
```

#### 4. 手续费结构

**V2方案 (2023年8月后,推荐)**:

| 项目 | 买入 | 卖出 | 备注 |
|-----|------|------|------|
| 佣金 | 0.02% | 0.02% | 最低5元 |
| 印花税 | 0% | 0.05% | 仅卖出 |
| 过户费 | 0.001% | 0.001% | 双向收取 |

**示例计算**:

买入1000股 @ 10元:
```
成交金额: 10000元
佣金: max(10000 × 0.02%, 5元) = 5元
印花税: 0元
过户费: 10000 × 0.001% = 0.1元
总费用: 5.1元 (0.051%)
```

### 核心模块

#### 1. A股约束模块

**文件**: [core/ashare_constraints.py](core/ashare_constraints.py)

提供三个核心类:

- **TPlusOneTracker**: T+1交易限制跟踪
- **PriceLimitChecker**: 涨跌停检测
- **LotSizeRounder**: 手数调整

#### 2. A股手续费模块

**文件**: [core/ashare_commission.py](core/ashare_commission.py)

提供四种手续费方案:

- **V1**: 2015-2023年费率
- **V2**: 2023年8月后费率(推荐)
- **Zero**: 零手续费(测试/对比)
- **Fixed**: 固定费率(自定义)

#### 3. 策略模板集成

**文件**: [core/backtrader_strategy.py](core/backtrader_strategy.py)

策略模板已完全集成A股约束,在`rebalance`方法中自动应用所有规则。

### 测试验证

运行完整测试套件:

```bash
python tests/test_ashare_constraints.py
```

测试覆盖:
- ✅ T+1结算: 26个测试用例
- ✅ 涨跌停检测
- ✅ 手数调整
- ✅ 手续费计算
- ✅ 订单合规性验证

所有测试通过 ✅

### 对比: A股模式 vs ETF模式

| 特性 | ETF模式 | A股模式 |
|-----|---------|---------|
| T+1限制 | ❌ 无 | ✅ 有 |
| 涨跌停限制 | ❌ 无 | ✅ 有 |
| 手数限制 | ❌ 无 | ✅ 100股/手 |
| 手续费 | 简化费率 | 真实费率 |
| 适用标的 | ETF | A股股票 |

### 详细文档

- **完整实施计划**: [PLAN.md](PLAN.md)
- **使用指南**: [GUIDE.md](GUIDE.md) - 包含完整的A股策略使用指南
- **测试文件**: [tests/test_ashare_constraints.py](tests/test_ashare_constraints.py)
- **示例脚本**: [examples/ashare_strategy_example.py](examples/ashare_strategy_example.py)

---

## A股策略库

### 策略列表

系统已实现6个A股智能选股策略，涵盖多因子和动量两大类：

#### 多因子智能选股策略

**文件**: [strategies/stocks_多因子智能选股策略.py](strategies/stocks_多因子智能选股策略.py)

| 策略版本 | 函数名 | 持仓数 | 风险等级 | 适用场景 |
|---------|-------|-------|---------|---------|
| 周频版本 | `multi_factor_strategy_weekly()` | 20只 | 中等 | 震荡市、慢牛 |
| 月频版本 | `multi_factor_strategy_monthly()` | 30只 | 中等 | 长期投资 |
| 保守版本 | `multi_factor_strategy_conservative()` | 15只 | 低 | 稳健投资 |

**策略特点**:
- 综合技术面(40%) + 质量因子(30%) + 估值因子(20%) + 流动性因子(10%)
- 至少满足7个条件中的3个
- 动态因子权重
- 新股过滤、流动性过滤

**快速使用**:
```python
from strategies.stocks_多因子智能选股策略 import multi_factor_strategy_weekly
from core.backtrader_engine import Engine

task = multi_factor_strategy_weekly()
engine = Engine()
result = engine.run(task)
result.stats()
```

#### 动量轮动选股策略

**文件**: [strategies/stocks_动量轮动选股策略.py](strategies/stocks_动量轮动选股策略.py)

| 策略版本 | 函数名 | 持仓数 | 风险等级 | 适用场景 |
|---------|-------|-------|---------|---------|
| 周频版本 | `momentum_strategy_weekly()` | 15只 | 高 | 趋势牛市 |
| 月频版本 | `momentum_strategy_monthly()` | 20只 | 中高 | 趋势牛市 |
| 激进版本 | `momentum_strategy_aggressive()` | 10只 | 极高 | 强势牛市 |

**策略特点**:
- 纯动量驱动，追求高收益
- 强势筛选（6个条件全部满足）
- 多层止损机制
- 避免涨停追高

**快速使用**:
```python
from strategies.stocks_动量轮动选股策略 import momentum_strategy_weekly
from core.backtrader_engine import Engine

task = momentum_strategy_weekly()
engine = Engine()
result = engine.run(task)
result.stats()
```

### 批量回测

使用回测脚本批量运行所有策略：

```bash
# 运行所有策略
python scripts/run_stock_backtests.py --all

# 运行所有多因子策略
python scripts/run_stock_backtests.py --multi-factor-all

# 运行所有动量策略
python scripts/run_stock_backtests.py --momentum-all

# 运行指定策略
python scripts/run_stock_backtests.py --strategy multi_factor --period weekly
```

### 策略对比

| 策略 | 风险 | 年化收益 | 最大回撤 | 适合市场 |
|-----|------|---------|---------|---------|
| 多因子-周频 | 中等 | 15-25% | < 20% | 震荡市、慢牛 |
| 多因子-月频 | 中等 | 12-20% | < 18% | 长期投资 |
| 多因子-保守版 | 低 | 10-18% | < 15% | 稳健投资 |
| 动量-周频 | 高 | 20-35% | < 30% | 趋势牛市 |
| 动量-月频 | 中高 | 15-30% | < 25% | 趋势牛市 |
| 动量-激进版 | 极高 | 25-45% | < 40% | 强势牛市 |

### 自定义策略

所有策略都支持自定义修改：

```python
from strategies.stocks_多因子智能选股策略 import multi_factor_strategy_weekly

def my_custom_strategy():
    t = multi_factor_strategy_weekly()
    t.name = '我的自定义策略'

    # 修改持仓数量
    t.order_by_topK = 30

    # 修改选股条件
    t.select_buy = [
        'roc(close,20) > 0.05',
        'roe > 0.15',
        'pe < 30'
    ]
    t.buy_at_least_count = 2

    # 修改因子权重
    t.order_by_signal = '''
        roc(close,20)*0.5 +
        trend_score(close,25)*0.3 +
        roe_score(roe)*0.2
    '''

    return t
```

### 详细文档

完整的A股策略使用指南请参阅：
- **A股策略使用指南**: [GUIDE.md - A股策略使用指南](GUIDE.md#a股策略使用指南)
- **实施计划**: [PLAN.md - Phase 4](PLAN.md#phase-4-策略实现)

---

## 基本面数据系统

支持全市场 A 股基本面数据获取、存储和因子计算功能，提供 PE、PB、市值等估值因子。

**核心特性**:
- ✅ **最新快照**: 每日更新全市场 5700+ 只 A 股的实时估值数据
- ✅ **快速更新**: 约 10-15 秒完成全市场数据更新
- ✅ **估值因子**: 支持 PE、PB、市值等常用估值指标
- ⚠️ **数据限制**: 只提供最新快照，不包含历史估值数据（受限于免费数据源）

**数据更新**:
```bash
# 更新基本面数据
python scripts/unified_update.py --stage fundamental
```

**策略使用**:
```python
# 价值选股策略示例
t.select_buy = [
    'pe < 20',          # PE < 20
    'pb < 2',           # PB < 2
    'total_mv > 100'    # 市值 > 100亿
]
t.order_by_signal = 'pe_score(pe) + pb_score(pb)'  # 低估值优先
```

**详细使用方法请参阅 [数据管理指南 - 基本面数据系统](DATA.md#6-基本面数据系统)**。

---

## 多策略信号系统

### 简介

多策略交易信号集成系统集成了 `strategies/` 目录下所有策略文件，每个策略独立生成买卖信号，结合当前持仓情况，输出综合命令行报告。

### 功能特性

- ✅ **自动解析策略文件**: 支持基于 bt 和 backtrader 两种引擎的策略
- ✅ **因子缓存优化**: 批量计算因子，避免重复计算，提升性能
- ✅ **独立信号生成**: 每个策略独立运行，互不干扰
- ✅ **持仓感知**: 自动读取当前持仓，生成针对性建议
- ✅ **跨策略汇总**: 统计多个策略对同一标的的推荐情况
- ✅ **操作建议**: 基于策略共识和仓位限制给出可执行建议

### 快速开始

#### 基本使用

```bash
# 运行所有策略，输出到终端
python run_etf_signals.py

# 指定分析日期
python run_etf_signals.py --date 20251225

# 输出到文件
python run_etf_signals.py --output report.txt

# 设置最大持仓数和初始资金
python run_etf_signals.py --max-positions 10 --initial-capital 10000

# 显示详细执行信息
python run_etf_signals.py --verbose
```

#### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--date` | 分析日期 (YYYYMMDD) | 最新可用日期 |
| `--max-positions` | 最大持仓数 | 5 |
| `--initial-capital` | 初始资金 | 5000 |
| `--output` | 输出文件路径 | 终端输出 |
| `--verbose` | 显示详细日志 | 关闭 |

### 输出示例

```
====================================================================================================
多策略交易信号分析报告
====================================================================================================
报告生成时间: 2025-12-26 19:49:10
分析策略数量: 17

====================================================================================================
当前持仓情况
====================================================================================================
当前无持仓

====================================================================================================
各策略信号详情
====================================================================================================

----------------------------------------------------------------------------------------------------
策略: 创业板布林带策略
分析标的数量: 1
----------------------------------------------------------------------------------------------------

买入信号 (1个):
排名   代码             价格        评分        建议数量
----------------------------------------------------------------------------------------------------
    1 510050.SH          3.917       1.0000        255

====================================================================================================
操作建议汇总
====================================================================================================

【建议买入】 (可用仓位: 5)
  1. 510050.SH - 1个策略推荐, 平均评分1.0000
     策略: 创业板布林带
     建议: 买入255股 @ 3.917元, 投入998.83元
```

### 工作原理

#### 1. 策略解析
系统使用 Python AST (抽象语法树) 解析策略文件，提取以下信息:
- 策略类型 (bt 或 backtrader)
- 买卖条件 (select_buy, select_sell)
- 排序因子 (order_by_signal)
- 标的列表 (symbols)
- 其他参数 (topK, dropN, 等)

#### 2. 因子计算
- 收集所有策略的因子表达式
- 去重后批量计算
- 使用 PostgreSQL 作为数据源，CSV 作为后备
- 缓存结果供所有策略复用

#### 3. 信号生成
对每个策略独立执行:
- **卖出检查**: 评估卖出条件 (OR 逻辑)，仅针对持仓标的
- **买入检查**: 评估买入条件 (AND 逻辑)，按 buy_at_least_count 过滤
- **排名筛选**: 按 order_by_signal 评分，应用 topK 和 dropN 限制
- **持仓建议**: 既无买入也无卖出的持仓标的

#### 4. 报告生成
- 当前持仓摘要
- 各策略信号详情
- 跨策略信号汇总 (统计推荐数量)
- 操作建议 (基于共识和仓位限制)

### 已集成策略列表

#### bt 引擎策略 (10个)
1. 多标的动量轮动
2. 多标的轮动
3. 大小盘轮动策略
4. 年化收益评分的轮动策略
5. 年化收益评分的轮动策略-超级轮动
6. 优质资产动量轮动
7. 创业板择时策略
8. 上证50双均线策略
9. 创业板布林带策略
10. 沪深300ETF的RSRS择时

#### backtrader 引擎策略 (7个)
1. backtrader_原生_轮动
2. backtrader-多标的轮动454% 回撤6.9%
3. backtrader-多资产轮动-趋势评分
4. backtrader-多资产轮动-趋势评分-optuna多参数优化
5. backtrader-创业板择时策略
6. backtrader-大小盘轮动策略
7. backtrader_风险平价

### 性能优化

- **因子去重**: 相同因子表达式只计算一次
- **批量加载**: CsvDataLoader 一次性加载所有标的数据
- **缓存机制**: FactorCache 缓存所有计算结果
- **预计性能**: 17策略 × 30标的 × 10因子 < 30秒

### 依赖项

```
- core/backtrader_engine.py  # Task 类定义
- database/db_manager.py      # 数据库操作
- datafeed/csv_dataloader.py # 数据加载
- datafeed/factor_expr.py    # 因子计算
- strategies/*.py            # 策略文件
```

### 扩展性

系统设计支持以下扩展:

1. **添加新策略**: 在 `strategies/` 目录下创建新策略文件，系统自动识别
2. **自定义报告格式**: 修改 `signals/signal_reporter.py` 中的格式化函数
3. **添加新因子**: 在 `datafeed/` 目录下扩展因子库
4. **Web 界面**: 基于现有模块开发 Flask/Django 接口
5. **实时推送**: 集成 WebSocket 或消息队列

### 注意事项

1. **数据依赖**: 首次运行会自动下载缺失的标的数据
2. **网络要求**: 需要连接 akshare 数据源
3. **数据库**: 使用 PostgreSQL 存储历史数据和持仓信息
4. **风险提示**: 策略信号仅供参考，实际投资需谨慎

### 故障排查

#### 问题: 没有生成任何策略信号
**解决方案**:
- 检查策略文件格式是否正确
- 确认标的数据已下载
- 使用 `--verbose` 查看详细日志

#### 问题: 某些标的无法解析
**解决方案**:
- 检查标的代码格式 (如 510300.SH)
- 确认网络连接正常
- 手动运行单策略测试

#### 问题: 因子计算失败
**解决方案**:
- 检查因子表达式语法
- 确认数据完整性
- 查看日志中的错误信息

---

## 统一信号管道与回测集成

### 简介

统一信号管道 (`run_ashare_signals.py`) 是一个集成了回测分析和信号生成的自动化系统，支持智能选股和多策略频率分离。

### 核心特性

- ✅ **智能选股筛选**: 多层级筛选（基础→市值→流动性），将5298只股票减少到1000只，性能提升80%
- ✅ **频率分离**: 周频策略用于每日推荐，月频策略用于长期投资
- ✅ **回测与信号分离**: 支持只生成信号或回测+信号两种模式
- ✅ **数据库存储**: 回测结果持久化存储在 PostgreSQL
- ✅ **信号关联**: 交易信号与对应策略的回测报告自动关联

### 快速开始

#### 命令行参数

```bash
# ========== 信号生成模式 ==========

# 每日推荐（仅周频策略，2个）
python run_ashare_signals.py --signal

# 全量信号（所有策略，7个：周频2 + 月频2 + 其他3）
python run_ashare_signals.py --all-signal

# ========== 回测+信号模式 ==========

# 周频策略回测+信号（2个策略）
python run_ashare_signals.py --weekly

# 月频策略回测+信号（2个策略）
python run_ashare_signals.py --monthly

# 所有策略回测+信号（默认，7个策略）
python run_ashare_signals.py

# ========== 智能选股筛选 ==========

# 使用保守型筛选（500只，大市值+高流动性）
python run_ashare_signals.py --signal --filter-preset conservative

# 使用激进型筛选（1500只，较低市值要求）
python run_ashare_signals.py --signal --filter-preset aggressive

# 自定义目标数量
python run_ashare_signals.py --signal --filter-target 800

# 禁用智能筛选（使用完整股票池5298只）
python run_ashare_signals.py --signal --no-filter

# ========== 组合使用 ==========

# 周频回测+保守型筛选
python run_ashare_signals.py --weekly --filter-preset conservative

# 月频回测+激进型筛选
python run_ashare_signals.py --monthly --filter-preset aggressive

# 强制重新运行回测（忽略缓存）
python run_ashare_signals.py --weekly --force-backtest

# 并发优化（默认3个线程，最多15个）
python run_ashare_signals.py --signal --workers 5
```

#### 命令对比

| 命令 | 策略数量 | 回测 | 信号 | 适用场景 | 耗时 |
|------|---------|------|------|---------|------|
| `--signal` | 2个（周频） | ❌ | ✅ | 每日推荐 | ~1分钟 |
| `--all-signal` | 7个（全部） | ❌ | ✅ | 完整信号 | ~2-3分钟 |
| `--weekly` | 2个（周频） | ✅ | ✅ | 周一更新 | ~2-3分钟 |
| `--monthly` | 2个（月频） | ✅ | ✅ | 每月1号更新 | ~3-4分钟 |
| 无参数 | 7个（全部） | ✅ | ✅ | 完整运行 | ~5-12分钟 |

### 智能选股模块

#### 筛选流程

**文件**: [core/smart_stock_filter.py](core/smart_stock_filter.py)

三层筛选架构：

1. **第0层：基础过滤**
   - 排除ST股票
   - 排除停牌股票
   - 排除新上市股票（默认60天内）
   - 数据完整性检查（至少180天历史数据）

2. **第1层：市值筛选**
   - Conservative: 市值 > 100亿
   - **Balanced（默认）**: 市值 > 50亿
   - Aggressive: 市值 > 30亿

3. **第2层：流动性筛选**
   - Conservative: 换手率 > 2%, 日均成交额 > 1亿
   - **Balanced（默认）**: 换手率 > 1.5%, 日均成交额 > 5000万
   - Aggressive: 换手率 > 1%, 日均成交额 > 3000万

#### 性能提升

| 指标 | 无筛选 | 智能筛选 | 提升 |
|------|--------|---------|------|
| 股票池大小 | 5298只 | 1000只 | 减少81% |
| 因子计算时间 | 100% | 20-30% | 提升70-80% |
| 总执行时间 | 100% | 40-60% | 提升40-60% |
| 内存占用 | 100% | 30-40% | 降低60-70% |

### 策略列表

系统已实现7个A股智能选股策略：

#### 多因子智能选股策略（3个）

**文件**: [strategies/stocks_多因子智能选股策略.py](strategies/stocks_多因子智能选股策略.py)

| 策略版本 | 函数名 | 版本标识 | 持仓数 | 风险等级 |
|---------|-------|---------|-------|---------|
| 周频版本 | `multi_factor_strategy_weekly()` | weekly | 20只 | 中等 |
| 月频版本 | `multi_factor_strategy_monthly()` | monthly | 30只 | 中等 |
| 保守版本 | `multi_factor_strategy_conservative()` | conservative | 15只 | 低 |

#### 动量轮动选股策略（4个）

**文件**: [strategies/stocks_动量轮动选股策略.py](strategies/stocks_动量轮动选股策略.py)

| 策略版本 | 函数名 | 版本标识 | 持仓数 | 风险等级 |
|---------|-------|---------|-------|---------|
| 周频版本 | `momentum_strategy_weekly()` | weekly | 15只 | 高 |
| 月频版本 | `momentum_strategy_monthly()` | monthly | 20只 | 中高 |
| 激进版本 | `momentum_strategy_aggressive()` | aggressive | 10只 | 极高 |
| 跳过版本 | `momentum_strategy_with_skip()` | default | 17只 | 中高 |

### 推荐使用流程

#### 每日推荐流程（周一至周五）

```bash
# 每天运行周频策略信号（每日推荐）
python run_ashare_signals.py --signal

# 输出示例:
# ✓ 智能选股已启用: preset=balanced, target=1000
# ✓ 第0层(基础过滤): 5298 只股票
# ✓ 第1层(市值筛选): 2697 只股票
# ✓ 第2层(流动性筛选): 1729 只股票
# ✓ 最终限制: 1000 只股票
# ✓ 筛选完成! 最终: 1000 只股票, 减少 81.1%, 耗时 4.42秒
# ✓ 2 个策略, 1000 个标的, 52 个因子
```

#### 周一更新流程（推荐）

```bash
# 每周一运行周频策略的完整回测和信号生成
python run_ashare_signals.py --weekly

# 流程:
# 步骤 1/2: 运行 weekly 策略回测...
#   - A股动量轮动-周频
#   - A股多因子智能选股-周频
# 步骤 2/2: 生成 weekly 策略信号...
```

#### 月初更新流程

```bash
# 每月1号运行月频策略的完整回测和信号生成
python run_ashare_signals.py --monthly

# 流程:
# 步骤 1/2: 运行 monthly 策略回测...
#   - A股动量轮动-月频
#   - A股多因子智能选股-月频
# 步骤 2/2: 生成 monthly 策略信号...
```

### 回测指标

每个策略回测后存储以下关键指标：

| 指标 | 说明 |
|------|------|
| Total Return | 总收益率 (%) |
| Annual Return | 年化收益率 (%) |
| Sharpe Ratio | 夏普比率 |
| Max Drawdown | 最大回撤 (%) |
| Win Rate | 胜率 (%) |
| Profit Factor | 盈亏比 |
| Total Trades | 总交易次数 |
| Benchmark Return | 基准收益率 (%) |
| Equity Curve | 权益曲线数据 |
| Trade List | 交易明细 |

### Web 界面展示

#### ETF 信号模块
- 显示所有 ETF 交易信号（带 .SH/.SZ 后缀）
- 按日期分组，可展开/收起
- 绿色 = 买入，红色 = 卖出

#### A股信号模块
- 显示所有 A股信号（6位数字代码）
- **每个信号关联对应的回测报告**
- 回测报告可展开查看核心指标（4个关键指标）
- "View Full Report" 按钮打开详细回测信息模态框
  - 完整的性能指标
  - 权益曲线可视化
  - 最近20笔交易明细

### 数据库表结构

#### strategy_backtests
存储策略回测结果，包含所有性能指标和详细数据。

#### signal_backtest_associations
关联交易信号 (trader 表) 与回测结果 (strategy_backtests 表)。

### 定时任务配置

```bash
# 查看当前定时任务
crontab -l

# 统一管道任务（每个工作日 20:00 执行）
0 20 * * 1-5 cd /data/home/yy/code/aitrader && /root/miniconda3/bin/python run_ashare_signals.py >> logs/ashare_pipeline.log 2>&1
```

### 日志文件

- **统一管道日志**: `logs/ashare_pipeline.log`

### API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/signals/etf/latest` | 获取最新 ETF 信号 |
| `GET /api/signals/ashare/latest` | 获取最新 A股 信号（带回测信息） |
| `GET /api/signals/ashare/backtest/{id}` | 获取完整回测报告 |

### 工作流程

1. **回测阶段**
   - 遍历所有6个A股策略
   - 运行完整回测
   - 提取性能指标
   - 存储到 `strategy_backtests` 表

2. **信号生成阶段**
   - 调用多策略信号生成器
   - 获取当前持仓
   - 生成买卖信号
   - 存储到 `trader` 表

3. **关联阶段**
   - 将每个信号与对应策略的回测关联
   - 存储关联关系到 `signal_backtest_associations` 表

4. **Web展示阶段**
   - Dashboard 从数据库读取 ETF 和 A-share 信号
   - A-share 信号自动加载关联的回测信息
   - 用户可查看回测概要和详细报告

### 故障排查

#### 问题: 回测失败
**解决方案**:
- 检查数据完整性（确保历史数据存在）
- 查看日志 `logs/ashare_pipeline.log`
- 单独运行策略测试

#### 问题: 信号与回测未关联
**解决方案**:
- 检查数据库表 `signal_backtest_associations`
- 确认回测ID和信号ID都存在
- 查看 PostgreSQL 日志

---

## 策略配置

### 示例 1: 动量轮动策略

```python
from backtrader_engine import Task, Engine

# 创建策略任务
t = Task()
t.name = '动量轮动策略'
t.symbols = ['510300.SH', '510500.SH', '159915.SZ']
t.start_date = '20200101'
t.end_date = '20231231'

# 配置选股参数
t.order_by_signal = 'roc(close,20)'  # 按动量排序
t.order_by_topK = 2                   # 选择前 2 个

# 配置权重和频率
t.weight = 'WeighEqually'             # 等权重
t.period = 'RunWeekly'                # 每周调仓

# 运行回测
e = Engine()
e.run(t)
e.stats()
e.plot()
```

### 示例 2: 多条件筛选策略

```python
t = Task()
t.name = '多条件策略'

# 买入条件（至少满足 2 个）
t.select_buy = [
    "roc(close,5)*100<5.5",
    "roc(close,10)*100<10",
    "roc(close,3)*100>-1.5"
]
t.buy_at_least_count = 2

# 卖出条件（满足 1 个即卖出）
t.select_sell = [
    "roc(close,10)*100>18.5",
    "roc(close,20)*100>16",
    "roc(close,1)*100<-6.5"
]
t.sell_at_least_count = 1

# 排序规则
t.order_by_signal = "trend_score(close,25)*0.27+roc(close,13)*0.75"
t.order_by_topK = 5
```

### 示例 3: 使用数据库记录交易

```python
from db_manager import get_db
from datetime import datetime

db = get_db()

# 1. 检查当前持仓
positions = db.get_positions()
print(positions)

# 2. 执行买入
db.insert_transaction(
    symbol='510300.SH',
    buy_sell='buy',
    quantity=100,
    price=4.5,
    trade_date='2024-12-26',
    strategy_name='动量策略'
)

# 3. 更新持仓
db.update_position(
    symbol='510300.SH',
    quantity=100,
    avg_cost=4.5,
    current_price=4.6
)

# 4. 查询交易历史
transactions = db.get_transactions(
    symbol='510300.SH',
    start_date='2024-01-01'
)
print(transactions)
```

---

## API 参考

### db_manager.PostgreSQLManager

数据库管理器类，提供完整的 CRUD 操作。

#### 初始化

```python
from db_manager import get_db

# 获取单例
db = get_db('PostgreSQL数据库')
```

#### 主要方法

##### get_etf_history()

获取 ETF 历史数据。

```python
df = db.get_etf_history(
    symbol='510300.SH',
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

**参数**:
- `symbol` (str): ETF 代码
- `start_date` (str, optional): 开始日期 (YYYY-MM-DD)
- `end_date` (str, optional): 结束日期 (YYYY-MM-DD)

**返回**: DataFrame

##### insert_transaction()

记录交易。

```python
db.insert_transaction(
    symbol='510300.SH',
    buy_sell='buy',  # 'buy' 或 'sell'
    quantity=100,
    price=4.5,
    trade_date='2024-12-26',
    strategy_name='策略名称'
)
```

##### update_position()

更新持仓信息。

```python
db.update_position(
    symbol='510300.SH',
    quantity=100,
    avg_cost=4.5,
    current_price=4.6
)
```

##### get_positions()

获取当前所有持仓。

```python
positions = db.get_positions()
```

##### get_transactions()

查询交易记录。

```python
transactions = db.get_transactions(
    symbol='510300.SH',      # 可选
    start_date='2024-01-01', # 可选
    end_date='2024-12-31'    # 可选
)
```

##### get_statistics()

获取数据库统计信息。

```python
stats = db.get_statistics()
# {
#     'total_symbols': 27,
#     'total_records': 40716,
#     'earliest_date': '2012-05-28',
#     'latest_date': '2025-12-26'
# }
```

---

### 数据加载器 API

#### CsvDataLoader

数据加载器类，支持从 CSV 或 PostgreSQL 读取数据。

```python
from datafeed.csv_dataloader import CsvDataLoader

# 初始化（自动选择数据源）
loader = CsvDataLoader()

# 读取多个标的数据
dfs = loader.read_dfs(
    symbols=['510300.SH', '513100.SH'],
    start_date='20200101',
    end_date='20231231'
)

# 读取合并数据
df = loader.read_df(
    symbols=['510300.SH', '513100.SH'],
    start_date='20200101'
)
```

---

## 性能对比

| 操作 | CSV 文件 | PostgreSQL | 提升 |
|------|---------|--------|------|
| 读取单个 ETF | ~50ms | ~10ms | 5x |
| 读取多个 ETF | ~500ms | ~50ms | 10x |
| 日期范围查询 | ~200ms | ~20ms | 10x |
| 聚合统计 | ~1000ms | ~50ms | 20x |

---

## 核心文件索引

### 引擎文件

| 文件 | 说明 |
|------|------|
| [bt_engine.py](bt_engine.py) | 基于 bt 库的回测引擎 |
| [backtrader_engine.py](backtrader_engine.py) | 基于 backtrader 的回测引擎 |
| [backtrader_strategy.py](backtrader_strategy.py) | Backtrader 策略模板 |
| [backtrader_algos.py](backtrader_algos.py) | 自定义算法实现 |

### 数据相关

| 文件 | 说明 |
|------|------|
| [db_manager.py](db_manager.py) | PostgreSQL 数据库管理器 |
| [datafeed/csv_dataloader.py](datafeed/csv_dataloader.py) | 数据加载器（支持 PostgreSQL） |
| [datafeed/factor_expr.py](datafeed/factor_expr.py) | 因子计算引擎 |
| [get_data.py](get_data.py) | Akshare 数据下载 |
| [auto_update_etf_data.py](auto_update_etf_data.py) | 自动更新脚本 |
| [import_to_postgresql.py](import_to_postgresql.py) | 历史数据导入脚本 |

### 工具脚本

| 文件 | 说明 |
|------|------|
| [test_postgresql.py](test_postgresql.py) | 测试数据库功能 |
| [trading_with_postgresql.py](trading_with_postgresql.py) | 交易决策示例 |
| [daily_signal.py](daily_signal.py) | 每日信号生成 |
| [setup_postgresql.sh](setup_postgresql.sh) | 一键启动脚本 |

---

## Web 部署指南

### 概述

AITrader 提供了 FastAPI Web 应用，支持:
- 📊 **Dashboard**: 可视化查看交易信号、持仓、盈亏
- 📅 **历史信号**: 按日期分组展示历史推荐策略，支持展开/收缩
- 🔔 **自动信号生成**: Cron 定时任务每日分析
- 💾 **交易记录管理**: 完整的交易历史跟踪
- 🔍 **API 接口**: RESTful API 支持集成

### PostgreSQL 并发访问说明

**重要**: PostgreSQL 支持高并发访问，系统已优化为:

- **Web 服务**: 使用连接池，支持多并发请求
- **定时任务**: 每日 18:00 自动运行，支持自动重试（最多3次，间隔2秒）
- **手动操作**: 如需手动生成信号，建议直接运行，会自动重试

### 前置条件

```bash
# 安装依赖
pip install -r requirements.txt

# 主要依赖包括:
# - fastapi, uvicorn (Web 服务)
# - postgresql (数据库)
# - pandas, numpy (数据处理)
```

### 快速启动

#### 生产模式（推荐）

使用提供的控制脚本管理 Web 服务：

```bash
cd /data/home/yy/code/aitrader

# 启动服务器（后台运行）
./web_server.sh start

# 查看运行状态
./web_server.sh status

# 停止服务器
./web_server.sh stop

# 重启服务器
./web_server.sh restart
```

**特性**:
- ✅ 后台运行，不阻塞终端
- ✅ 自动日志记录到 `logs/web_server.log`
- ✅ PID 文件管理，防止重复启动
- ✅ 优雅停止，支持强制结束
- ✅ 状态查询，显示访问地址和日志路径

**输出示例**:
```
$ ./web_server.sh start
Starting web server...
Web server started (PID: 3976686)
Logs: /data/home/yy/code/aitrader/logs/web_server.log
Access: http://0.0.0.0:8000

$ ./web_server.sh status
Web server is running (PID: 3976686)
Access: http://0.0.0.0:8000
Logs: /data/home/yy/code/aitrader/logs/web_server.log
```

#### 开发模式

如需实时重载功能（开发调试）：

```bash
cd /data/home/yy/code/aitrader
python -m uvicorn web.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000 查看 Dashboard

**主要页面：**
- `/` - Dashboard 主页（最近5个交易日的信号，按日期分组）
- `/history` - 历史信号页面（按日期分组展示，支持日期筛选）
- `/trading` - 交易管理页面

### Dashboard 主页功能

#### 特性说明

Dashboard 主页 (`/`) 采用**分层布局**显示交易信号：

**左侧信号区（分为两个独立模块）：**

1. **ETF 交易信号模块**（上方）
   - 显示所有 ETF 信号（带 .SH/.SZ 后缀的标的）
   - 按日期分组，可独立展开/收起模块
   - 每个日期组也可展开/收起
   - 绿色 = 买入，红色 = 卖出

2. **A 股信号模块**（下方）
   - 显示所有 A 股信号（6位数字代码）
   - **每个信号卡片包含对应的回测报告**
   - 回测报告默认折叠，点击展开查看4个核心指标：
     - Total Return (总收益率)
     - Annual Return (年化收益率)
     - Sharpe Ratio (夏普比率)
     - Max Drawdown (最大回撤)
   - "View Full Report" 按钮打开完整回测详情模态框
     - 所有性能指标
     - 权益曲线数据
     - 最近20笔交易明细

**右侧交易管理区：**
- 交易记录表单
- 当前持仓列表
- 盈亏汇总

#### 使用方法

1. 访问 http://localhost:8000
2. 点击 ETF/A-share 模块标题展开/收起整个模块
3. 点击日期标题展开/收起该日期的信号列表
4. 对于 A-share 信号：
   - 点击回测报告标题展开/收起核心指标
   - 点击 "View Full Report" 查看完整回测详情
   - 在模态框中查看交易明细和完整指标

### 历史信号页面功能

#### 特性说明

历史信号页面 (`/history`) 提供了按日期分组展示历史推荐策略的功能：

1. **按日期分组**: 所有历史信号按照信号日期分组，每个日期为一个独立的栏目
2. **可展开/收缩**: 点击日期标题可以展开或收起该日期下的所有信号
3. **动态加载**: 通过 AJAX 从后端 API 获取数据
4. **日期范围筛选**:
   - 预设选项：最近 7/14/30/60/90/180/365 天或全部时间
   - 自定义日期范围：手动选择开始和结束日期
5. **响应式设计**: 适配桌面和移动设备

#### 使用方法

1. 访问 http://localhost:8000/history
2. 使用日期范围下拉菜单选择预设时间段（如最近 30 天）
3. 或手动输入开始和结束日期进行精确筛选
4. 点击 "Load" 按钮加载选定日期范围的信号
5. 点击日期标题展开/收缩该日期的信号列表

#### 信号卡片信息

每个信号卡片显示：
- 标的代码和信号类型（买入/卖出）
- 价格、评分、数量
- 推荐策略标签
- 创建时间

#### 颜色标识

- 🟢 **绿色**: 买入信号
- 🔴 **红色**: 卖出信号

### 设置定时任务

详见 [数据管理指南 - 定时任务配置](DATA.md#3-定时任务配置)。

### API 接口

#### 核心端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Dashboard 主页 |
| `/health` | GET | 健康检查 |
| `/history` | GET | 历史信号页面（按日期分组展示） |
| `/api/signals/latest` | GET | 获取最新信号 |
| `/api/signals/history/grouped` | GET | 获取历史信号（按日期分组） |
| `/api/trading/positions` | GET | 获取当前持仓 |
| `/api/trading/transactions` | GET | 获取交易历史 |
| `/api/trading/record` | POST | 添加交易记录 |
| `/api/analytics/profit-loss` | GET | 盈亏分析 |

#### 使用示例

```bash
# 获取最新信号
curl http://localhost:8000/api/signals/latest?limit=10

# 获取历史信号（按日期分组）
curl "http://localhost:8000/api/signals/history/grouped?start_date=2025-01-01&end_date=2025-12-27"

# 获取持仓
curl http://localhost:8000/api/trading/positions

# 添加交易记录
curl -X POST http://localhost:8000/api/trading/record \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "513100.SH",
    "buy_sell": "buy",
    "quantity": 100,
    "price": 1.38,
    "trade_date": "2025-12-27",
    "strategy_name": "多标的动量轮动"
  }'

# 盈亏分析
curl http://localhost:8000/api/analytics/profit-loss
```

### 配置 Nginx 反向代理（可选）

如果需要使用域名和 HTTPS:

1. **安装 Nginx**:
```bash
sudo apt-get install nginx
```

2. **创建配置**:
```bash
sudo nano /etc/nginx/sites-available/aitrader
```

3. **添加配置**:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # 修改为你的域名

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

4. **启用站点**:
```bash
sudo ln -s /etc/nginx/sites-available/aitrader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 监控和维护

#### 日志文件

- **Cron 定时任务**: `/data/home/yy/code/aitrader/logs/signal_generation.log`
- **Web 服务**: 终端输出（开发模式）或配置的日志文件

#### 常用命令

```bash
# 查看定时任务
crontab -l

# 查看定时任务日志
tail -f /data/home/yy/code/aitrader/logs/signal_generation.log

# 备份数据库
cp PostgreSQL数据库 PostgreSQL数据库.backup.$(date +%Y%m%d)
```

### 故障排除

#### 问题: Cron 任务未运行

```bash
# 检查 cron 服务
sudo systemctl status cron

# 验证 cron 任务
crontab -l

# 检查日志文件权限
ls -la /data/home/yy/code/aitrader/logs/
```

#### 问题: Web 服务无法启动

```bash
# 检查端口占用
sudo lsof -i :8000

# 手动测试
cd /data/home/yy/code/aitrader
python -m uvicorn web.main:app --host 0.0.0.0 --port 8000
```

#### 问题: 数据库连接失败

```bash
# 验证数据库文件
ls -la PostgreSQL数据库

# 测试连接
python -c "from database.pg_manager import get_db; db = get_db(); print(db.get_statistics())"

# Web 服务运行时手动生成信号
python run_etf_signals.py --save-to-db  # 会自动重试
```

### 安全建议

1. **认证**: 添加 API 认证机制（如 JWT）
2. **HTTPS**: 生产环境使用 SSL 证书
3. **防火墙**: 仅开放必要端口（80/443）
4. **备份**: 定期备份数据库文件

### 系统架构

```
┌──────────────────────────────────────────────────────┐
│                    AITrader 系统                       │
├──────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐         ┌──────────────┐           │
│  │  FastAPI     │         │   Cron Job   │           │
│  │  Web 服务    │         │  定时任务    │           │
│  │  (端口8000)  │         │  (每日18:00) │           │
│  └──────┬───────┘         └──────┬───────┘           │
│         │                         │                    │
│         └──────────┬──────────────┘                    │
│                    ▼                                   │
│         ┌────────────────────┐                        │
│         │   PostgreSQL 数据库    │                        │
│         │  (trading.db)      │                        │
│         └────────────────────┘                        │
│                                                         │
│  功能:                                                 │
│  - Web 查询: 只读连接                                 │
│  - Cron 写入: 读写连接 + 重试机制                     │
│  - 交易记录: 通过 Web API 添加                        │
└──────────────────────────────────────────────────────┘
```

---

## 故障排除

### Q: PostgreSQL 读取失败，回退到 CSV？

**A**: 正常情况。PostgreSQL 中没有该标的的数据时会自动回退到 CSV。

解决方法：
```bash
python import_to_postgresql.py  # 导入缺失的数据
```

### Q: 数据库文件损坏？

**A**: 使用 CSV 备份恢复。

```bash
# 删除旧数据库
rm PostgreSQL数据库

# 重新导入
python import_to_postgresql.py
```

### Q: 查询速度慢？

**A**: 检查是否启用了 PostgreSQL。

```python
from datafeed.csv_dataloader import CsvDataLoader

loader = CsvDataLoader()
print(loader.use_postgresql)  # 应该为 True
```

---

## 版本信息

- **项目名称**: AITrader v3.5
- **更新日期**: 2025-12-26
- **Python 版本**: 3.x
- **主要依赖**: backtrader, bt, postgresql, pandas, numpy, ffn

---

## 许可证

MIT License
