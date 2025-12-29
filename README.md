# AITrader - 量化交易系统

## 目录

- [项目概述](#项目概述)
- [目录结构](#目录结构)
- [DuckDB 数据库集成](#duckdb-数据库集成)
- [快速开始](#快速开始)
- [核心模块](#核心模块)
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
├── database/               # 数据库管理 (DuckDB)
│   ├── db_manager.py          # DuckDB 数据库管理器
│   ├── factor_cache.py        # 因子缓存
│   └── import_to_duckdb.py    # 数据导入工具
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
│   └── setup_duckdb.sh         # DuckDB 初始化
├── tests/                  # 测试模块
├── data/                   # 数据存储
│   └── akshare_data/          # AKShare 数据
└── logs/                   # 日志文件
```

### 核心特性

- **DuckDB 数据库**: 高性能 OLAP 数据库，查询速度提升 10-20 倍
- **双引擎支持**: 基于 `bt` 和 `backtrader` 两种回测框架
- **灵活的因子系统**: 支持自定义因子表达式和 Alpha158 因子库
- **多种选股策略**: 条件筛选、TopK 排序、多因子组合
- **交易记录管理**: 完整的持仓、交易历史跟踪
- **风险管理**: 止损、止盈、风险平价配置

---

## DuckDB 数据库集成

### 为什么选择 DuckDB？

- ✅ **高性能**: 列式存储，分析查询速度比 CSV 快 10-20 倍
- ✅ **零侵入**: 对现有代码透明，自动回退到 CSV
- ✅ **易用性**: Python 原生支持，SQL 兼容
- ✅ **持久化**: 磁盘存储，重启不丢失数据
- ✅ **双保险**: CSV + DuckDB 双存储保障

### 数据库架构

```
/data/home/yy/data/duckdb/trading.db
├── etf_history      -- ETF 历史行情数据
├── etf_codes        -- ETF 代码清单
├── stock_history    -- 股票历史行情数据
├── stock_codes      -- 股票代码清单
├── transactions     -- 交易记录
└── positions        -- 当前持仓
```

### 表结构

#### etf_history（ETF 历史行情）
```sql
CREATE SEQUENCE seq_etf_history START 1;

CREATE TABLE etf_history (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_etf_history'),
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    amount DOUBLE,
    amplitude DOUBLE,              -- 振幅
    change_pct DOUBLE,             -- 涨跌幅（百分比）
    change_amount DOUBLE,          -- 涨跌额（绝对值）
    turnover_rate DOUBLE,          -- 换手率
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);

-- 索引
CREATE INDEX idx_etf_history_symbol_date ON etf_history(symbol, date DESC);
CREATE INDEX idx_etf_history_date ON etf_history(date DESC);
```

#### stock_history（股票历史行情）
```sql
CREATE SEQUENCE seq_stock_history START 1;

CREATE TABLE stock_history (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_stock_history'),
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    amount DOUBLE,
    amplitude DOUBLE,              -- 振幅
    change_pct DOUBLE,             -- 涨跌幅（百分比）
    change_amount DOUBLE,          -- 涨跌额（绝对值）
    turnover_rate DOUBLE,          -- 换手率
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);

-- 索引
CREATE INDEX idx_stock_history_symbol_date ON stock_history(symbol, date DESC);
CREATE INDEX idx_stock_history_date ON stock_history(date DESC);
```

**字段说明**:
- `id`: 主键，自增
- `symbol`: ETF/股票代码（如 '510300.SH'）
- `date`: 交易日期
- `open/high/low/close`: 开盘价/最高价/最低价/收盘价
- `volume`: 成交量
- `amount`: 成交额
- `amplitude`: 振幅
- `change_pct`: 涨跌幅（百分比）
- `change_amount`: 涨跌额（绝对值）
- `turnover_rate`: 换手率
- `created_at`: 记录创建时间

#### transactions（交易记录）
```sql
CREATE SEQUENCE seq_transactions START 1;

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_transactions'),
    symbol VARCHAR(20) NOT NULL,
    buy_sell VARCHAR(10) NOT NULL,
    quantity DOUBLE NOT NULL,
    price DOUBLE NOT NULL,
    trade_date DATE NOT NULL,
    strategy_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_transactions_symbol_date ON transactions(symbol, trade_date DESC);
```

**字段说明**:
- `symbol`: 交易标的代码
- `buy_sell`: 交易类型（'buy' 或 'sell'）
- `quantity`: 交易数量
- `price`: 交易价格
- `trade_date`: 交易日期
- `strategy_name`: 策略名称（可选）

#### positions（持仓管理）
```sql
CREATE TABLE positions (
    symbol VARCHAR(20) PRIMARY KEY,
    quantity DOUBLE NOT NULL,
    avg_cost DOUBLE NOT NULL,
    current_price DOUBLE,
    market_value DOUBLE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**字段说明**:
- `symbol`: 持仓标的代码（主键）
- `quantity`: 持仓数量
- `avg_cost`: 平均成本
- `current_price`: 当前价格（可选）
- `market_value`: 市值（可选）
- `updated_at`: 更新时间

#### etf_codes（ETF 代码清单）
```sql
CREATE TABLE etf_codes (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR,
    list_date DATE,
    fund_type VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**字段说明**:
- `id`: 主键，自增
- `symbol`: ETF 代码（唯一，如 '510300.SH'）
- `name`: ETF 名称（可选）
- `list_date`: 上市日期（可选）
- `fund_type`: 基金类型（可选）
- `created_at`: 记录创建时间
- `updated_at`: 记录更新时间

**用途**:
- 维护所有策略中使用的 ETF 代码清单
- 通过 `scripts/sync_strategy_codes.py` 自动从策略文件中提取并同步
- 用于批量更新数据时遍历所有需要更新的 ETF

#### stock_codes（股票代码清单）
```sql
CREATE TABLE stock_codes (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR,
    list_date DATE,
    industry VARCHAR,
    market VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**字段说明**:
- `id`: 主键，自增
- `symbol`: 股票代码（唯一，如 '000001.SZ'）
- `name`: 股票名称（可选）
- `list_date`: 上市日期（可选）
- `industry`: 所属行业（可选）
- `market`: 交易市场（可选，如 '主板', '创业板'）
- `created_at`: 记录创建时间
- `updated_at`: 记录更新时间

**用途**:
- 维护所有策略中使用的股票代码清单
- 通过 `scripts/sync_strategy_codes.py` 自动从策略文件中提取并同步
- 用于批量更新数据时遍历所有需要更新的股票

### 配置选项

**auto_update_etf_data.py:**
```python
ENABLE_DUCKDB = True  # 是否写入 DuckDB
DUCKDB_PATH = '/data/home/yy/data/duckdb/trading.db'
```

**datafeed/csv_dataloader.py:**
```python
ENABLE_DUCKDB = True  # 是否从 DuckDB 读取
DUCKDB_PATH = '/data/home/yy/data/duckdb/trading.db'
```

---

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- backtrader - 回测框架
- duckdb - 数据库
- pandas - 数据处理
- ffn - 金融分析
- loguru - 日志

### 初始化数据库

**方式一：一键启动**
```bash
./setup_duckdb.sh
```

**方式二：手动步骤**
```bash
# 1. 创建数据库目录
mkdir -p /data/home/yy/data/duckdb

# 2. 导入历史数据
python import_to_duckdb.py

# 3. 测试数据库
python test_duckdb.py
```

### 日常使用

#### 更新数据

```bash
# 自动更新（同时更新 CSV 和 DuckDB）
python auto_update_etf_data.py
```

#### 测试数据库

```bash
python test_duckdb.py
```

#### 查看数据库统计

```python
from database.db_manager import get_db

db = get_db()
stats = db.get_statistics()
print(f"ETF 数量: {stats['total_symbols']}")
print(f"总记录数: {stats['total_records']}")
print(f"数据范围: {stats['earliest_date']} ~ {stats['latest_date']}")
```

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

# 自动优先使用 DuckDB，失败则回退到 CSV
loader = CsvDataLoader()
dfs = loader.read_dfs(['510300.SH', '513100.SH'])
```

**特性**:
- ✅ 优先从 DuckDB 读取（高性能）
- ✅ DuckDB 失败自动回退到 CSV
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
python run_multi_strategy_signals.py

# 指定分析日期
python run_multi_strategy_signals.py --date 20251225

# 输出到文件
python run_multi_strategy_signals.py --output report.txt

# 设置最大持仓数和初始资金
python run_multi_strategy_signals.py --max-positions 10 --initial-capital 10000

# 显示详细执行信息
python run_multi_strategy_signals.py --verbose
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
- 使用 DuckDB 作为数据源，CSV 作为后备
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
3. **数据库**: 使用 DuckDB 存储历史数据和持仓信息
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

### db_manager.DuckDBManager

数据库管理器类，提供完整的 CRUD 操作。

#### 初始化

```python
from db_manager import get_db

# 获取单例
db = get_db('/data/home/yy/data/duckdb/trading.db')
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

数据加载器类，支持从 CSV 或 DuckDB 读取数据。

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

| 操作 | CSV 文件 | DuckDB | 提升 |
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
| [db_manager.py](db_manager.py) | DuckDB 数据库管理器 |
| [datafeed/csv_dataloader.py](datafeed/csv_dataloader.py) | 数据加载器（支持 DuckDB） |
| [datafeed/factor_expr.py](datafeed/factor_expr.py) | 因子计算引擎 |
| [get_data.py](get_data.py) | Akshare 数据下载 |
| [auto_update_etf_data.py](auto_update_etf_data.py) | 自动更新脚本 |
| [import_to_duckdb.py](import_to_duckdb.py) | 历史数据导入脚本 |

### 工具脚本

| 文件 | 说明 |
|------|------|
| [test_duckdb.py](test_duckdb.py) | 测试数据库功能 |
| [trading_with_duckdb.py](trading_with_duckdb.py) | 交易决策示例 |
| [daily_signal.py](daily_signal.py) | 每日信号生成 |
| [setup_duckdb.sh](setup_duckdb.sh) | 一键启动脚本 |

---

## Web 部署指南

### 概述

AITrader 提供了 FastAPI Web 应用，支持:
- 📊 **Dashboard**: 可视化查看交易信号、持仓、盈亏
- 📅 **历史信号**: 按日期分组展示历史推荐策略，支持展开/收缩
- 🔔 **自动信号生成**: Cron 定时任务每日分析
- 💾 **交易记录管理**: 完整的交易历史跟踪
- 🔍 **API 接口**: RESTful API 支持集成

### DuckDB 并发访问说明

**重要**: DuckDB 采用单写入者模式，系统已优化为:

- **Web 服务**: 使用只读连接查询数据，写操作有重试机制
- **定时任务**: 每日 18:00 自动运行，支持自动重试（最多3次，间隔2秒）
- **手动操作**: 如需手动生成信号，建议直接运行，会自动重试；如多次失败可先停止 web 服务

### 前置条件

```bash
# 安装依赖
pip install -r requirements.txt

# 主要依赖包括:
# - fastapi, uvicorn (Web 服务)
# - duckdb (数据库)
# - pandas, numpy (数据处理)
```

### 快速启动

#### 开发模式

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

Dashboard 主页 (`/`) 左侧显示最近5个交易日的推荐策略：

1. **按日期分组**: 自动获取最近5个有信号的交易日，每个日期为一个独立的栏目
2. **可展开/收缩**: 点击日期标题可以展开或收起该日期下的所有信号
3. **信号数量显示**: 每个日期标题显示该日期的信号总数
4. **颜色标识**: 买入信号为绿色，卖出信号为红色
5. **简洁设计**: 适合快速查看最近的策略推荐

#### 使用方法

1. 访问 http://localhost:8000
2. 左侧显示最近5个交易日的信号
3. 点击日期标题展开/收缩该日期的信号列表
4. 查看信号详情（标的、类型、价格、策略、评分）

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

#### 生产模式（systemd）

1. **创建服务文件**:
```bash
sudo cp aitrader-web.service.example /etc/systemd/system/aitrader-web.service
```

2. **启动服务**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable aitrader-web  # 开机自启
sudo systemctl start aitrader-web  # 立即启动
```

3. **查看状态**:
```bash
sudo systemctl status aitrader-web
sudo journalctl -u aitrader-web -f  # 查看日志
```

### 设置定时任务

#### 自动配置

```bash
cd /data/home/yy/code/aitrader/scripts
chmod +x setup_signal_cron.sh
./setup_signal_cron.sh
```

#### 手动配置

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每个交易日 18:00 生成信号并保存到数据库）
0 18 * * 1-5 cd /data/home/yy/code/aitrader && python run_multi_strategy_signals.py --save-to-db >> /data/home/yy/code/aitrader/logs/signal_generation.log 2>&1
```

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
- **Web 服务**: `journalctl -u aitrader-web`

#### 常用命令

```bash
# 查看定时任务
crontab -l

# 查看定时任务日志
tail -f /data/home/yy/code/aitrader/logs/signal_generation.log

# 查看 Web 服务状态
sudo systemctl status aitrader-web

# 重启 Web 服务
sudo systemctl restart aitrader-web

# 备份数据库
cp /data/home/yy/data/duckdb/trading.db /data/home/yy/data/duckdb/trading.db.backup.$(date +%Y%m%d)
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

# 查看服务日志
sudo journalctl -u aitrader-web -n 50

# 手动测试
cd /data/home/yy/code/aitrader
python -m uvicorn web.main:app --host 0.0.0.0 --port 8000
```

#### 问题: 数据库连接失败

```bash
# 验证数据库文件
ls -la /data/home/yy/data/duckdb/trading.db

# 测试连接
python -c "from database.db_manager import get_db; db = get_db(); print(db.get_statistics())"

# Web 服务运行时手动生成信号
python run_multi_strategy_signals.py --save-to-db  # 会自动重试
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
│         │   DuckDB 数据库    │                        │
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

### Q: DuckDB 读取失败，回退到 CSV？

**A**: 正常情况。DuckDB 中没有该标的的数据时会自动回退到 CSV。

解决方法：
```bash
python import_to_duckdb.py  # 导入缺失的数据
```

### Q: 数据库文件损坏？

**A**: 使用 CSV 备份恢复。

```bash
# 删除旧数据库
rm /data/home/yy/data/duckdb/trading.db

# 重新导入
python import_to_duckdb.py
```

### Q: 查询速度慢？

**A**: 检查是否启用了 DuckDB。

```python
from datafeed.csv_dataloader import CsvDataLoader

loader = CsvDataLoader()
print(loader.use_duckdb)  # 应该为 True
```

---

## 版本信息

- **项目名称**: AITrader v3.5
- **更新日期**: 2025-12-26
- **Python 版本**: 3.x
- **主要依赖**: backtrader, bt, duckdb, pandas, numpy, ffn

---

## 许可证

MIT License
