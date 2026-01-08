# A股智能选股与交易策略实施计划

> **当前进度**: Phase 1 已完成 ✅
> **更新时间**: 2025-12-29

---

## 📋 项目概述

基于现有ETF轮动系统,新增A股智能选股和交易策略功能,包括:
1. **多因子智能选股策略** - 基于基本面+技术面的Smart Beta模型
2. **动量轮动策略** - 基于价格动量的股票轮动
3. **严格模拟A股交易规则** - T+1、涨跌停、100股/手、真实手续费
4. **全市场股票池** - 动态筛选全市场5700+只A股
5. **基本面数据支持** - PE、PB、ROE、市值等因子

---

## 🎯 实施进度总览

| 阶段 | 任务 | 预计时间 | 实际时间 | 状态 |
|-----|------|---------|---------|------|
| **Phase 1** | 基础设施建设 | 5-7天 | 1天 | ✅ **已完成** |
| **Phase 2** | 基本面数据系统 | 3-5天 | 1天 | ✅ **已完成** |
| **Phase 3** | 股票池管理 | 2-3天 | 2天 | ✅ **已完成** |
| **Phase 4** | 策略实现 | 5-7天 | 1天 | ✅ **已完成** |
| **Phase 5** | 回测与验证 | 3-5天 | - | ⏳ 待开始 |
| **Phase 6** | 信号生成集成 | 2-3天 | - | ⏳ 待开始 |
| **Phase 7** | 测试与优化 | 3-5天 | - | ⏳ 待开始 |

---

## ✅ Phase 1: 基础设施建设 (已完成)

### 完成时间
2024-12-29

### 完成内容

#### 1. A股交易约束模块 ✨
**文件**: `core/ashare_constraints.py`

实现了三个核心类:

##### `TPlusOneTracker` - T+1结算跟踪器
- ✅ 记录股票买入日期
- ✅ 检查是否可以卖出(T+1限制)
- ✅ 获取持仓天数
- ✅ 移除持仓记录

##### `PriceLimitChecker` - 涨跌停检查器
- ✅ 普通股票 ±10%
- ✅ ST股票 ±5%
- ✅ 科创板/创业板 ±20%
- ✅ 北交所 ±30%
- ✅ 新股前5日无限制

##### `LotSizeRounder` - 手数调整器
- ✅ 调整到100股整数倍
- ✅ 按目标金额计算股数
- ✅ 不足1手检测

---

#### 2. A股手续费方案 💰
**文件**: `core/ashare_commission.py`

实现了四种手续费方案:

##### `AShareCommissionScheme` - V1方案(2015-2023)
- 佣金: 0.025%
- 印花税: 0.1% (仅卖出)
- 过户费: 0.001%
- 最低佣金: 5元

##### `AShareCommissionSchemeV2` - V2方案(2023年后) ⭐
- 佣金: 0.02%
- 印花税: 0.05% (仅卖出)
- 过户费: 0.001%
- 最低佣金: 5元

##### `ZeroCommission` - 零佣金(测试用)
- 不收取任何手续费

##### `FixedCommission` - 固定费率
- 简化的固定费率方案

---

#### 3. 策略模板集成 🔧
**文件**: `core/backtrader_strategy.py`

##### 修改内容:
- ✅ 添加A股模式参数 (`ashare_mode`, `lot_size`, `enable_t1`, `enable_limit_check`, `enable_lot_rounding`)
- ✅ 在`__init__`中初始化T+1 tracker、涨跌停检查器、手数调整器
- ✅ 在`notify_order`中记录买入日期(T+1)
- ✅ 在`rebalance`中集成所有A股约束:
  - T+1检查(卖出前)
  - 手数调整(买卖)
  - 涨跌停检查(买卖)

---

#### 4. 回测引擎支持 🚀
**文件**: `core/backtrader_engine.py`

##### 修改内容:
- ✅ Task类添加A股模式参数 (`ashare_mode`, `ashare_commission`)
- ✅ AlgoStrategy支持A股模式参数传递
- ✅ Engine.run()方法:
  - 检测`ashare_mode`
  - 自动应用A股手续费方案
  - 传递参数到策略

---

#### 5. 测试与验证 ✅
**文件**: `tests/test_ashare_constraints.py`

##### 测试覆盖:
- ✅ T+1跟踪器: 6个测试用例全部通过
- ✅ 涨跌停检查器: 5个测试用例全部通过
- ✅ 手数调整器: 8个测试用例全部通过
- ✅ 手续费计算: 3个测试用例全部通过
- ✅ 订单合规性验证: 4个测试用例全部通过

**测试结果**: 🎉 所有26个测试用例通过!

---

### 关键特性

✅ **向后兼容** - ETF策略不受影响
✅ **可选启用** - 通过`ashare_mode`参数控制,默认关闭
✅ **日志完善** - 所有关键操作都有日志记录
✅ **测试覆盖** - 26个单元测试全部通过
✅ **文档齐全** - 使用指南、示例、总结

---

### 新增/修改文件

#### 新建文件 (4个)
1. `core/ashare_constraints.py` - A股交易约束模块 (378行)
2. `core/ashare_commission.py` - A股手续费方案 (230行)
3. `tests/test_ashare_constraints.py` - 单元测试 (280行)
4. `examples/ashare_strategy_example.py` - 使用示例 (120行)

#### 修改文件 (2个)
1. `core/backtrader_strategy.py` - 策略模板基类
   - 添加A股模式参数定义
   - 修改`__init__`方法
   - 修改`notify_order`方法
   - 重写`rebalance`方法

2. `core/backtrader_engine.py` - 回测引擎
   - Task类添加A股参数
   - AlgoStrategy构造函数修改
   - `run()`方法重构

---

### 如何使用

#### 启用A股模式非常简单:

```python
from core.backtrader_engine import Task, Engine

# 创建策略
t = Task()
t.name = 'A股动量选股'
t.symbols = ['000001.SZ', '600000.SH']
t.start_date = '20200101'

# 策略逻辑
t.select_buy = ['roc(close,20) > 0.05']
t.order_by_topK = 1
t.period = 'RunWeekly'

# ========== 启用A股模式 ==========
t.ashare_mode = True              # 启用A股交易约束
t.ashare_commission = 'v2'        # 手续费方案

# 运行回测
e = Engine()
e.run(t)
e.stats()
```

---

### A股约束规则总结

| 约束类型 | 规则 | 实现状态 |
|---------|------|---------|
| **T+1结算** | 当日买入次日才能卖出 | ✅ 完整实现 |
| **涨跌停** | 普通股±10%, ST股±5%, 科创板±20% | ✅ 完整实现 |
| **手数限制** | 必须是100股的整数倍 | ✅ 完整实现 |
| **手续费** | V2方案: 买入0.05%, 卖出0.1% | ✅ 完整实现 |

---

---

---

## ✅ Phase 2: 基本面数据系统 (已完成)

### 完成时间
2025-12-29

### 完成内容

#### 1. 数据库表扩展 ✨
**文件**: `database/db_manager.py`

**新增表**:
- ✅ `stock_metadata` - 股票元数据(名称、行业、ST状态)
- ✅ `stock_fundamental_daily` - 每日基本面数据(保留1年历史)
- ✅ `factor_cache` - 因子计算缓存

**新增方法**:
- ✅ `create_stock_metadata_table()` - 创建元数据表
- ✅ `create_stock_fundamental_table()` - 创建基本面数据表
- ✅ `upsert_stock_metadata()` - 更新股票元数据
- ✅ `upsert_fundamental_daily()` - 更新单日基本面数据
- ✅ `batch_upsert_fundamental()` - 批量更新基本面
- ✅ `get_stock_metadata()` - 查询股票元数据
- ✅ `get_fundamental_daily()` - 查询历史基本面数据
- ✅ `get_latest_fundamental()` - 获取最新基本面数据
- ✅ `cleanup_old_fundamental()` - 清理超过1年的旧数据
- ✅ `cache_factor()` / `get_cached_factor()` - 因子缓存

---

#### 2. 基本面数据获取脚本 📥
**文件**: `scripts/fetch_fundamental_data.py`

**功能**:
- ✅ 获取全市场A股列表(5700+只)
- ✅ 拉取PE、PB、ROE等财务指标
- ✅ 识别ST、停牌、新股状态
- ✅ 批量写入DuckDB数据库
- ✅ 断点续传与错误重试
- ✅ 进度显示与日志记录

**数据源**:
- `ak.stock_zh_a_spot_em()` - 实时行情数据
- `ak.stock_zh_a_hist()` - 历史行情与估值指标
- `ak.stock_individual_info_em()` - 个股详细信息

**使用方式**:
```bash
# 更新全市场
python scripts/fetch_fundamental_data.py

# 更新指定股票
python scripts/fetch_fundamental_data.py --symbols 000001.SZ,600000.SH

# 增量更新
python scripts/fetch_fundamental_data.py --days 7
```

---

#### 3. 基本面因子库 📊
**文件**: `datafeed/factor_fundamental.py`

**实现的因子**:

##### 估值因子
- ✅ `pe_score()` - PE评分(倒数)
- ✅ `pb_score()` - PB评分(倒数)
- ✅ `ps_score()` - PS评分(倒数)

##### 质量因子
- ✅ `roe_score()` - ROE评分
- ✅ `roa_score()` - ROA评分
- ✅ `profit_margin_score()` - 利润率评分

##### 市值因子
- ✅ `market_cap_filter()` - 市值过滤
- ✅ `log_market_cap()` - 对数市值

##### 综合因子
- ✅ `quality_score(pe, pb, roe)` - 综合质量评分
- ✅ `value_score(pe, pb, ps)` - 价值评分

**特点**:
- 所有函数返回`pd.Series`,与`factor_expr.py`兼容
- 支持向量化计算
- 自动处理NaN值

---

#### 4. 定时任务配置 ⏰
**文件**: `scripts/setup_fundamental_cron.sh`

**配置**:
- ✅ 每个交易日18:00自动更新基本面数据
- ✅ 日志记录到`logs/fundamental_update.log`
- ✅ 日志轮转配置(保留4周)
- ✅ 支持手动清理超过1年的历史数据

**安装方式**:
```bash
cd /data/home/yy/code/aitrader/scripts
chmod +x setup_fundamental_cron.sh
./setup_fundamental_cron.sh
```

---

#### 5. 因子表达式引擎注册 🔧
**文件**: `datafeed/factor_expr.py`

**修改内容**:
- ✅ 导入`factor_fundamental`模块
- ✅ 注册所有基本面因子到表达式上下文
- ✅ 支持19个基本面因子函数

**注册的因子**:

##### 估值因子 (4个)
- `pe_score()` - PE评分(倒数)
- `pb_score()` - PB评分(倒数)
- `ps_score()` - PS评分(倒数)
- `value_score()` - 综合估值评分

##### 质量因子 (4个)
- `roe_score()` - ROE评分
- `roa_score()` - ROA评分
- `profit_margin_score()` - 利润率评分
- `operating_margin_score()` - 营业利润率评分

##### 市值因子 (4个)
- `total_mv_filter()` - 总市值过滤
- `circ_mv_filter()` - 流通市值过滤
- `log_market_cap()` - 对数市值
- `market_cap_category()` - 市值分类

##### 综合因子 (3个)
- `quality_score()` - 综合质量评分
- `fundamental_rank_score()` - 多因子排名评分
- `growth_score()` - 成长评分

##### 工具函数 (2个)
- `normalize_score()` - 标准化因子得分
- `winsorize()` - 去极值处理

---

#### 6. 集成测试 ✅
**文件**: `tests/test_fundamental_factors_simple.py`

**测试覆盖**:
- ✅ 因子注册验证 (19个因子全部注册)
- ✅ PE评分计算测试
- ✅ 综合质量评分测试
- ✅ 技术因子+基本面因子组合测试
- ✅ 策略条件筛选测试

**测试结果**: 🎉 所有测试通过!

---

### 关键特性

✅ **全市场覆盖** - 支持5700+只A股
✅ **历史数据** - 保留1年历史基本面数据
✅ **多数据源** - 集成AkShare多个API
✅ **自动更新** - 定时任务每日更新
✅ **因子缓存** - 提升计算性能
✅ **容错机制** - 断点续传、错误重试
✅ **向后兼容** - 不影响现有ETF策略

---

### 新增/修改文件

#### 新建文件 (4个)
1. `scripts/fetch_fundamental_data.py` - 基本面数据获取脚本 (420行)
2. `datafeed/factor_fundamental.py` - 基本面因子库 (426行)
3. `scripts/setup_fundamental_cron.sh` - 定时任务配置脚本 (60行)
4. `tests/test_fundamental_factors_simple.py` - 集成测试 (180行)

#### 修改文件 (2个)
1. `database/db_manager.py`
   - 新增`stock_metadata`表(股票元数据)
   - 新增`stock_fundamental_daily`表(每日基本面数据,保留1年历史)
   - 新增`factor_cache`表(因子缓存)
   - 新增元数据与基本面数据CRUD方法
   - 新增历史数据清理方法

2. `datafeed/factor_expr.py`
   - 导入`factor_fundamental`模块
   - 注册19个基本面因子函数到表达式上下文
   - 支持大小写两种调用方式

---

### 使用示例

#### 示例1: 价值选股策略

```python
from core.backtrader_engine import Task, Engine

t = Task()
t.name = 'A股价值选股'
t.symbols = ['000001.SZ', '600000.SH', '600036.SH', '600519.SH']
t.start_date = '20200101'
t.ashare_mode = True

# 低估值+高质量筛选
t.select_buy = [
    'pe < 20',                    # 低PE
    'pb < 2',                     # 低PB
    'roe > 0.12',                 # 高ROE
    'total_mv > 100'              # 大市值
]
t.buy_at_least_count = 3

# 按质量评分排序
t.order_by_signal = 'quality_score(pe, pb, roe)'
t.order_by_topK = 2

e = Engine()
e.run(t)
```

#### 示例2: GARP策略(Growth at Reasonable Price)

```python
t = Task()
t.name = 'GARP策略'
t.ashare_mode = True

# 合理价格+成长性
t.select_buy = [
    'pe > 10 and pe < 30',        # 合理PE区间
    'roe > 0.12',                 # 高ROE
    'roc(close,20) > 0.03'        # 价格动量
]
t.buy_at_least_count = 2

# 综合评分
t.order_by_signal = '''
    quality_score(pe, pb, roe) * 0.5 +
    roc(close,20) * 0.3 +
    value_score(pe, pb, ps) * 0.2
'''
```

---

### 测试验证

#### 单元测试
**文件**: `tests/test_fundamental_data.py` (新建)

```bash
# 运行测试
python tests/test_fundamental_data.py
```

**测试覆盖**:
- ✅ 数据库表创建
- ✅ 元数据CRUD操作
- ✅ 基本面因子计算
- ✅ 因子缓存读写
- ✅ 数据获取脚本

---

### 数据统计

**全市场覆盖情况** (预计):
- 总股票数: ~5700只
- 有PE数据: ~4500只 (78%)
- 有PB数据: ~4500只 (78%)
- 有ROE数据: ~4200只 (74%)
- ST股票: ~150只 (2.6%)

**更新性能**:
- 全市场更新时间: ~30-60分钟
- 单只股票更新: ~1-2秒
- 批量写入(100只): ~10秒

---

### 注意事项

1. **数据延迟**: AkShare财务数据有1-2天延迟
2. **数据缺失**: 部分股票可能缺少某些指标,需在策略中处理NaN
3. **网络限制**: 频繁请求可能被限流,建议设置请求间隔
4. **存储空间**:
   - `stock_metadata`表: ~5MB
   - `stock_fundamental_daily`表(1年数据): ~500-800MB
   - 定期清理旧数据可控制存储空间
5. **更新时间**: 全市场5700+只股票约需30-60分钟

---

### 数据不冲突说明

**与auto_update_etf_data.py的关系**:

| 脚本 | 数据类型 | 目标表 | 用途 |
|-----|---------|--------|------|
| auto_update_etf_data.py | 行情数据(OHLCV) | stock_history | 技术分析 |
| fetch_fundamental_data.py | 基本面数据(PE/PB/ROE) | stock_fundamental_daily | 基本面分析 |

**结论**: 两个脚本互补,一个提供价格数据(技术面),一个提供财务数据(基本面),可以独立运行,不会冲突。

---

---

---

## 📊 第一部分:现有策略分析结论

### 策略适用性评估

18个现有ETF策略的A股适用性:

| 策略类型 | 数量 | A股适用性 | 适配难度 |
|---------|------|----------|---------|
| **动量轮动策略** | 8 | ✅ 高 (70%) | 中等 |
| **趋势跟踪策略** | 4 | ✅ 高 (85%) | 中等 |
| **择时策略** | 2 | ❌ 仅ETF | 不适用 |
| **风险平价策略** | 1 | ❌ 固定权重 | 不适用 |
| **基础模板** | 3 | ✅ 完全适用 | 简单 |

### 可复用的核心组件

- ✅ **Task配置系统** - `core/backtrader_engine.py` 可直接用于股票
- ✅ **因子引擎** - `datafeed/factor_extends.py` 的ROC/trend_score/RSRS等指标
- ✅ **回测引擎** - Engine类只需增加A股约束
- ✅ **信号系统** - `signals/multi_strategy_signals.py` 可扩展到股票

### 需要新增的功能

- ❌ **T+1交易规则** - 当日买入次日才能卖出
- ❌ **涨跌停限制** - ±10% (ST股票±5%)
- ❌ **手数限制** - 必须是100股的整数倍
- ❌ **真实手续费** - 佣金0.02%+印花税0.03%(卖出)+最低5元
- ❌ **基本面因子** - PE、PB、ROE、市值、行业等
- ❌ **股票池管理** - 剔除ST、停牌、新股等

---

## 🎯 第二部分:新策略设计

### 策略1: 多因子智能选股策略

**文件**: `strategies/stocks_多因子智能选股策略.py`

#### 策略逻辑

```python
# 因子权重配置
因子配置 = {
    '技术因子(40%)': {
        'roc(close,20)': 0.25,      # 20日动量
        'trend_score(close,25)': 0.15  # 趋势强度
    },
    '质量因子(30%)': {
        'roe': 0.15,                # ROE越高越好
        'roa': 0.10,                # ROA越高越好
        'profit_to_revenue': 0.05   # 利润率
    },
    '估值因子(20%)': {
        '1/pe': 0.10,               # PE越低越好(倒数)
        '1/pb': 0.10                # PB越低越好(倒数)
    },
    '流动性因子(10%)': {
        'turnover_rate': 0.05,      # 换手率
        'volume_ratio': 0.05        # 量比
    }
}

# 买入条件(必须满足至少3个)
买入条件 = [
    'roc(close,20) > 0.03',         # 正动量 > 3%
    'volume > ma(volume,20)*1.2',   # 放量确认
    'turnover_rate > 2',            # 最低流动性
    'close > ma(close,60)',         # 长期趋势向上
    'roe > 0.08',                   # ROE > 8%
    'pe < 50'                       # PE < 50(避免高估值)
]

# 卖出条件(满足任一)
卖出条件 = [
    'roc(close,20) < -0.05',        # 动量转负
    'close < ma(close,20)*0.95',    # 跌破20日均线
    '持仓收益率 < -0.08'            # 止损-8%
]

# 组合管理
持仓数量 = 20
权重方式 = '等权重'
调仓频率 = '周频'
```

#### 预期收益特征

- **目标年化**: 15-25%
- **最大回撤**: < 20%
- **夏普比率**: > 1.0
- **适合市场**: 震荡市、慢牛

---

### 策略2: A股动量轮动策略

**文件**: `strategies/stocks_动量轮动选股策略.py`

#### 策略逻辑

```python
# 纯动量排序
排序因子 = 'roc(close,20)'

# 强势筛选(必须全部满足)
买入条件 = [
    'roc(close,20) > 0.08',         # 强动量 > 8%
    'roc(close,5) > -0.03',         # 短期未大幅回调
    'volume > ma(volume,20)',       # 量能支撑
    'close > ma(close,20)',         # 上升趋势
    'turnover_rate > 1.5',          # 流动性充足
    'close < ref(close,1)*1.095'    # 未涨停(留出追涨空间)
]

# 止损/止盈
卖出条件 = [
    'roc(close,20) < 0',            # 动量转负
    'close/ref(close,1) < 0.92',    # 日跌停-8%止损
    'volume < ma(volume,20)*0.3',   # 缩量
    '持仓收益率 > 0.20'             # 止盈+20%
]

# 组合管理
持仓数量 = 15
跳过前N个 = 2                      # 跳过最强势2只(避免极端追高)
调仓频率 = '周频'
```

#### 预期收益特征

- **目标年化**: 20-35%
- **最大回撤**: < 30%
- **夏普比率**: > 0.8
- **适合市场**: 趋势牛市、行业轮动
- **换手率**: 较高(周频调仓)

---

## 🔧 第三部分:A股交易规则实现

### 3.1 T+1结算机制

**文件**: `core/ashare_constraints.py` (新建)

```python
class TPlusOneTracker:
    """T+1交易限制跟踪"""

    def __init__(self):
        self.buy_dates = {}  # {symbol: buy_date}

    def can_sell(self, symbol, current_date, position_size):
        """检查是否可卖出"""
        if symbol not in self.buy_dates:
            return True  # 历史持仓可卖

        days_held = (current_date - self.buy_dates[symbol]).days
        return days_held >= 1

    def record_buy(self, symbol, date):
        """记录买入日期"""
        self.buy_dates[symbol] = date

    def remove_position(self, symbol):
        """移除持仓记录"""
        self.buy_dates.pop(symbol, None)
```

**集成位置**: `core/backtrader_strategy.py:133` rebalance方法

---

### 3.2 涨跌停限制

```python
class PriceLimitChecker:
    """涨跌停检查器"""

    LIMIT_REGULAR = 0.10   # 普通股±10%
    LIMIT_ST = 0.05        # ST股±5%

    def is_limit_hit(self, symbol, order_price, prev_close):
        """检查订单价格是否触及涨跌停"""
        change_pct = abs(order_price - prev_close) / prev_close

        limit = self.LIMIT_ST if self._is_st_stock(symbol) else self.LIMIT_REGULAR

        return change_pct >= limit
```

**集成位置**: `core/backtrader_strategy.py:155` buy/sell前检查

---

### 3.3 手数限制(100股/手)

```python
def round_to_lot(size, lot_size=100):
    """调整到整手"""
    return int(math.floor(size / lot_size) * lot_size)

def adjust_order_size(target_value, price, lot_size=100):
    """计算目标金额对应的整手数量"""
    raw_shares = target_value / price
    rounded_shares = round_to_lot(raw_shares, lot_size)

    # 至少1手
    if rounded_shares < lot_size:
        return None  # 资金不足

    return rounded_shares
```

**集成位置**: `core/backtrader_strategy.py:152` size_diff计算后

---

### 3.4 真实手续费结构

**文件**: `core/ashare_commission.py` (新建)

```python
class AShareCommissionScheme(bt.CommInfoBase):
    """A股真实手续费"""

    params = (
        ('brokerage_rate', 0.0002),   # 佣金0.02%
        ('stamp_duty_rate', 0.0003),  # 印花税0.03%(仅卖出)
        ('transfer_fee_rate', 0.00001), # 过户费0.001%(仅上海)
        ('min_commission', 5.0),      # 最低5元
    )

    def _getcommission(self, size, price):
        """计算总手续费"""
        value = abs(size) * price

        # 佣金
        brokerage = max(value * self.p.brokerage_rate, self.p.min_commission)

        # 印花税(仅卖出)
        stamp_duty = value * self.p.stamp_duty_rate if size < 0 else 0

        # 过户费(仅上海,暂忽略)

        return brokerage + stamp_duty
```

**集成位置**: `core/backtrader_engine.py` _init_cerebro方法

---

## 📈 第四部分:基本面数据系统

### 4.1 数据源选择

**主数据源**: AkShare

```python
import akshare as ak

# 股票列表
stock_list = ak.stock_zh_a_spot_em()

# 基本面数据
financial_data = {
    '估值指标': ak.stock_zh_a_hist(),  # PE、PB等
    '财务数据': ak.stock_financial_report(),  # ROE、ROA等
    '市值数据': ak.stock_zh_a_hist(),  # 总市值、流通市值
}
```

---

### 4.2 数据库设计

**新表**: `stock_metadata`

```sql
CREATE TABLE stock_metadata (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    sector VARCHAR(50),              -- 行业
    industry VARCHAR(50),            -- 二级行业
    list_date DATE,                  -- 上市日期

    -- 基本面字段(每日更新)
    pe_ratio DOUBLE,                 -- 市盈率
    pb_ratio DOUBLE,                 -- 市净率
    ps_ratio DOUBLE,                 -- 市销率
    roe DOUBLE,                      -- 净资产收益率
    roa DOUBLE,                      -- 总资产收益率
    profit_margin DOUBLE,            -- 利润率

    -- 市值字段
    total_mv DOUBLE,                 -- 总市值(亿)
    circ_mv DOUBLE,                  -- 流通市值(亿)

    -- 状态标记
    is_st BOOLEAN DEFAULT FALSE,     -- 是否ST
    is_suspend BOOLEAN DEFAULT FALSE, -- 是否停牌
    is_new_ipo BOOLEAN DEFAULT FALSE, -- 是否新股(上市<60天)

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### 4.3 数据更新脚本

**文件**: `scripts/fetch_fundamental_data.py` (新建)

```python
def update_stock_metadata():
    """更新股票元数据和基本面数据"""

    # 1. 获取股票列表
    stock_list = ak.stock_zh_a_spot_em()

    # 2. 获取ST股票列表
    st_stocks = fetch_st_stocks()

    # 3. 遍历更新
    for stock in stock_list:
        symbol = format_symbol(stock['代码'])

        # 获取基本面数据
        fundamental = fetch_fundamental(symbol)

        # 更新数据库
        db.upsert_stock_metadata(
            symbol=symbol,
            name=stock['名称'],
            pe=fundamental['pe'],
            pb=fundamental['pb'],
            roe=fundamental['roe'],
            is_st=(symbol in st_stocks),
            ...
        )
```

**定时任务**: 每日22:00运行(行情数据更新后)

---

### 4.4 基本面因子实现

**文件**: `datafeed/factor_fundamental.py` (新建)

```python
def pe_score(pe_series):
    """PE评分(倒数,PE越低分越高)"""
    return 1 / (pe_series + 1e-6)

def pb_score(pb_series):
    """PB评分(倒数)"""
    return 1 / (pb_series + 1e-6)

def roe_score(roe_series):
    """ROE评分(直接值,越高越好)"""
    return roe_series

def market_cap_filter(mv_series, min_mv=50):
    """市值过滤(>=50亿)"""
    return mv_series >= min_mv

def composite_quality_score(pe, pb, roe, market_cap):
    """综合质量评分"""
    return (
        pe_score(pe) * 0.3 +
        pb_score(pb) * 0.3 +
        roe_score(roe) * 0.3 +
        np.log(market_cap) * 0.1  # 对数市值
    )
```

---

## 🗂️ 第五部分:股票池管理

### 5.1 股票池筛选器

**文件**: `core/stock_universe.py` (新建)

```python
class StockUniverse:
    """A股股票池管理"""

    def filter_universe(self, date, filters=None):
        """动态筛选股票池"""

        default_filters = {
            'min_market_cap': 50e8,        # 最小市值50亿
            'min_turnover': 1.0,            # 最低换手率1%
            'exclude_st': True,             # 剔除ST
            'exclude_suspend': True,        # 剔除停牌
            'exclude_new_ipo_days': 180,    # 剔除次新股(上市<180天)
            'max_pe': None,                 # PE上限(可选)
            'sectors': None,                # 行业限制(可选)
        }

        if filters:
            default_filters.update(filters)

        # 查询数据库
        query = f"""
            SELECT symbol FROM stock_metadata
            WHERE total_mv >= {default_filters['min_market_cap']}
            AND turnover_rate >= {default_filters['min_turnover']}
        """

        if default_filters['exclude_st']:
            query += " AND is_st = FALSE"

        if default_filters['exclude_suspend']:
            query += " AND is_suspend = FALSE"

        # 执行查询并返回symbol列表
        symbols = db.conn.sql(query).df()['symbol'].tolist()

        return symbols
```

---

### 5.2 股票池快照

**新表**: `stock_universe_snapshot`

```sql
CREATE TABLE stock_universe_snapshot (
    id INTEGER PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    filter_criteria TEXT,  -- JSON格式的筛选条件
    created_at TIMESTAMP
);
```

**用途**:
- 回溯历史股票池
- 策略性能归因分析
- 避免未来函数

---

## 🏗️ 第六部分:实施架构

### 文件结构

```
/data/home/yy/code/aitrader/
├── core/
│   ├── backtrader_engine.py          # ✏️ 修改: 添加A股模式
│   ├── backtrader_strategy.py        # ✏️ 修改: 集成T+1、涨跌停检查
│   ├── ashare_constraints.py          # 🆕 新建: T+1、涨跌停、手数
│   ├── ashare_commission.py           # 🆕 新建: A股手续费
│   └── stock_universe.py              # 🆕 新建: 股票池管理
│
├── datafeed/
│   ├── factor_extends.py              # ✏️ 修改: 保持现有
│   ├── factor_fundamental.py          # 🆕 新建: 基本面因子
│   └── factor_expr.py                 # ✏️ 修改: 注册基本面因子
│
├── strategies/
│   ├── stocks_多因子智能选股策略.py    # 🆕 新建
│   ├── stocks_动量轮动选股策略.py      # 🆕 新建
│   └── [18个现有ETF策略...]
│
├── database/
│   └── db_manager.py                  # ✏️ 修改: 添加stock_metadata等表
│
├── scripts/
│   ├── fetch_fundamental_data.py      # 🆕 新建: 基本面数据更新
│   ├── update_stock_universe.py       # 🆕 新建: 股票池更新
│   └── run_stock_backtest.py          # 🆕 新建: 股票策略回测入口
│
└── signals/
    └── multi_strategy_signals.py      # ✏️ 修改: 支持股票信号生成
```

---

## 📝 第七部分:详细实施步骤

### Phase 1: 基础设施建设 (预计5-7天)

#### Step 1.1: 创建A股约束模块
**文件**: `core/ashare_constraints.py`

```python
# 实现3个类:
- TPlusOneTracker      # T+1跟踪
- PriceLimitChecker    # 涨跌停检查
- LotSizeRounder       # 手数调整
```

#### Step 1.2: 创建手续费模块
**文件**: `core/ashare_commission.py`

```python
# 实现1个类:
- AShareCommissionScheme  # 继承bt.CommInfoBase
```

#### Step 1.3: 修改策略模板
**文件**: `core/backtrader_strategy.py`

**修改点**:
- 第13行: `__init__`方法中添加T+1 tracker初始化
- 第133行: `rebalance`方法中集成手数调整
- 第155行: buy前检查涨跌停
- 第159行: sell前检查T+1

#### Step 1.4: 修改回测引擎
**文件**: `core/backtrader_engine.py`

**修改点**:
- `_init_cerebro`方法: 添加`ashare_mode`参数
- 如果`ashare_mode=True`,使用`AShareCommissionScheme`

---

### Phase 2: 基本面数据系统 (预计3-5天)

#### Step 2.1: 数据库表创建
**文件**: `database/db_manager.py`

**新增方法**:
```python
def create_stock_metadata_table(self):
    """创建stock_metadata表"""

def upsert_stock_metadata(self, symbol, **kwargs):
    """更新股票元数据"""

def get_stock_metadata(self, symbol):
    """查询股票元数据"""
```

#### Step 2.2: 基本面数据更新脚本
**文件**: `scripts/fetch_fundamental_data.py`

**功能**:
- 使用akshare获取数据
- 批量更新数据库
- 错误处理和日志
- 进度显示

#### Step 2.3: 基本面因子库
**文件**: `datafeed/factor_fundamental.py`

**实现因子**:
- `pe_score()`, `pb_score()`, `roe_score()`
- `market_cap_filter()`, `quality_score()`
- 所有函数返回pd.Series,兼容factor_expr

#### Step 2.4: 因子表达式引擎注册
**文件**: `datafeed/factor_expr.py`

**修改点**:
- 导入`factor_fundamental`模块
- 将基本面函数注册到context

---

### Phase 3: 股票池管理 (✅ 已完成)

#### 完成时间
2026-01-05 (全部完成)

---

### ✅ 已完成内容

#### 1. 统一数据更新脚本 ✨
**文件**: `scripts/unified_update.py` (333行)

**核心类**: `UnifiedUpdater`

**主要功能**:
- 三阶段数据更新流程:
  - 阶段1: ETF数据更新
  - 阶段2: 基本面数据更新
  - 阶段3: 股票交易数据更新
- 智能代码表检查: 自动检测代码表是否为空
- 自动初始化: 空表时自动调用 `CodeInitializer`
- 灵活的命令行参数: 支持选择特定阶段
- 完整的统计报告: 成功/失败/耗时统计

**使用方式**:
```bash
# 完整更新所有数据
python scripts/unified_update.py

# 仅更新ETF
python scripts/unified_update.py --stage etf

# 仅更新基本面
python scripts/unified_update.py --stage fundamental

# 仅更新股票
python scripts/unified_update.py --stage stock

# 组合更新
python scripts/unified_update.py --stage etf --stage stock

# 跳过代码检查
python scripts/unified_update.py --skip-code-check
```

**技术特性**:
- 自动检测代码表状态
- 分阶段执行，每阶段间隔2秒
- 详细的进度日志
- 统一的异常处理机制

---

#### 2. 定时任务配置 ⏰
**配置方式**: 系统级 crontab

**定时任务**:
```bash
# 每个交易日 16:00 更新ETF数据
0 16 * * 1-5 cd /data/home/yy/code/aitrader && \
  /root/miniconda3/bin/python scripts/unified_update.py --stage etf \
  >> logs/etf_update.log 2>&1

# 每个交易日 16:30 更新基本面数据
30 16 * * 1-5 cd /data/home/yy/code/aitrader && \
  /root/miniconda3/bin/python scripts/unified_update.py --stage fundamental \
  >> logs/fundamental_update.log 2>&1

# 每个交易日 17:00 更新股票交易数据
0 17 * * 1-5 cd /data/home/yy/code/aitrader && \
  /root/miniconda3/bin/python scripts/unified_update.py --stage stock \
  >> logs/stock_update.log 2>&1
```

**执行时间**:
- ETF数据: 每周一至五 16:00
- 基本面数据: 每周一至五 16:30
- 股票交易数据: 每周一至五 17:00

**日志文件**:
- `logs/etf_update.log` - ETF更新日志
- `logs/fundamental_update.log` - 基本面更新日志
- `logs/stock_update.log` - 股票更新日志

---

### ❌ 待完成内容

#### Step 3.1: 股票池筛选器 ✅ (已完成)
**文件**: `core/stock_universe.py` (350行)

**实现类**: `StockUniverse`

**核心方法**:
```python
class StockUniverse:
    def get_all_stocks() -> List[str]
        # 获取所有可交易股票（排除ST、停牌、退市）

    def filter_by_market_cap(symbols, min_mv, max_mv) -> List[str]
        # 按市值筛选

    def filter_by_fundamental(symbols, **kwargs) -> List[str]
        # 按基本面指标筛选（PE、PB、ROE等）

    def filter_by_industry(symbols, industries, sectors) -> List[str]
        # 按行业筛选

    def filter_by_liquidity(symbols, min_amount) -> List[str]
        # 按流动性筛选

    def get_stock_pool(date, filters) -> List[str]
        # 综合筛选股票池

    def get_universe_stats(symbols) -> Dict
        # 获取股票池统计信息
```

**支持的筛选条件**:
- ✅ 市值筛选: `min_market_cap`, `max_market_cap`
- ✅ 基本面筛选: `min_pe`, `max_pe`, `min_pb`, `max_pb`, `min_roe`, `max_roe`, `min_roa`
- ✅ 行业筛选: `industries`, `sectors`
- ✅ 基础过滤: `exclude_st`, `exclude_suspend`, `exclude_new_ipo`
- ✅ 流动性筛选: `min_liquidity`

**测试文件**: `tests/test_stock_universe.py` (250行)
- ✅ 7个测试场景，覆盖所有核心功能

#### Step 3.2: 统一数据更新脚本 ✅ (已完成)
**文件**: `scripts/unified_update.py`

**功能**:
- ✅ 三阶段数据更新流程 (ETF → 基本面 → 股票)
- ✅ 智能代码表检查和自动初始化
- ✅ 灵活的命令行参数支持
- ✅ 完整的错误处理和统计报告

#### Step 3.3: 定时任务配置 ✅ (已完成)
**配置**: 系统级 crontab

**已配置任务**:
- ✅ 每个交易日 16:00 更新ETF数据
- ✅ 每个交易日 16:30 更新基本面数据
- ✅ 每个交易日 17:00 更新股票交易数据

**日志文件**:
- `logs/etf_update.log`
- `logs/fundamental_update.log`
- `logs/stock_update.log`

---

### Phase 4: 策略实现 (✅ 已完成)

#### 完成时间
2026-01-06

#### 完成内容

##### 1. 多因子智能选股策略 ✨
**文件**: `strategies/stocks_多因子智能选股策略.py`

**策略版本**:
- 周频版本: `multi_factor_strategy_weekly()`
- 月频版本: `multi_factor_strategy_monthly()`
- 保守版本: `multi_factor_strategy_conservative()`

**策略特点**:
- 动态因子权重（技术40% + 质量30% + 估值20% + 流动性10%）
- 综合选股条件（至少满足3/7个条件）
- 行业中性化
- 新股过滤（排除上市252天内）
- 流动性过滤（换手率>2%）

**选股条件**:
```python
买入条件（至少满足3个）:
- roc(close,20) > 0.03          # 正动量
- trend_score(close,25) > 0      # 趋势向上
- volume > ma(volume,20)*1.2     # 放量
- close > ma(close,60)           # 长期趋势
- pe > 0 and pe < 80             # 合理估值
- roe > 0.08                     # 盈利能力
- turnover_rate > 2              # 流动性

卖出条件（满足任一）:
- roc(close,20) < -0.05          # 动量转负
- close < ma(close,20)*0.95      # 跌破均线
- turnover_rate < 0.5            # 流动性枯竭
```

**组合管理**:
- 周频: 持仓20只股票
- 月频: 持仓30只股票
- 保守版: 持仓15只股票
- 等权重配置

##### 2. 动量轮动选股策略 ✨
**文件**: `strategies/stocks_动量轮动选股策略.py`

**策略版本**:
- 周频版本: `momentum_strategy_weekly()`
- 月频版本: `momentum_strategy_monthly()`
- 激进版本: `momentum_strategy_aggressive()`

**策略特点**:
- 纯动量驱动（激进型）
- 强势筛选（6个条件全部满足）
- 多层止损机制
- 避免涨停追高

**选股条件**:
```python
周频买入条件（全部满足）:
- roc(close,20) > 0.08           # 强动量>8%
- roc(close,5) > -0.03           # 短期未大幅回调
- volume > ma(volume,20)         # 量能支撑
- close > ma(close,20)           # 上升趋势
- turnover_rate > 1.5            # 流动性充足
- close < ref(close,1)*1.095     # 未涨停

卖出条件（满足任一）:
- roc(close,20) < 0              # 动量转负
- close/ref(close,1) < 0.92      # 大跌-8%止损
- close < ma(close,20)*0.95      # 跌破均线
- volume < ma(volume,20)*0.3     # 缩量
- roc(close,5) < -0.10           # 短期暴跌
```

**组合管理**:
- 周频: 持仓15只股票
- 月频: 持仓20只股票
- 激进版: 持仓10只股票
- 等权重配置

##### 3. 策略回测脚本 ✨
**文件**: `scripts/run_stock_backtests.py`

**功能**:
- 单个策略运行
- 批量运行所有策略
- 策略对比报告
- 命令行参数支持

**使用方式**:
```bash
# 运行所有策略
python scripts/run_stock_backtests.py --all

# 运行指定策略
python scripts/run_stock_backtests.py --strategy multi_factor --period weekly --plot

# 运行所有多因子策略
python scripts/run_stock_backtests.py --multi-factor-all

# 运行所有动量策略
python scripts/run_stock_backtests.py --momentum-all
```

---

### Phase 5: 回测与验证 (预计3-5天)

#### Step 5.1: 股票策略回测入口
**文件**: `scripts/run_stock_backtest.py`

**功能**:
```python
# 命令行接口
python run_stock_backtest.py \
    --strategy stocks_多因子智能选股策略 \
    --start 20200101 \
    --end 20231231 \
    --ashare-mode \
    --plot
```

#### Step 5.2: 回测验证脚本
**文件**: `scripts/validate_stock_backtests.py`

**验证项**:
- ✅ T+1规则: 持仓天数>=1
- ✅ 手数规则: 所有持仓是100的倍数
- ✅ 涨跌停: 无涨停买入/跌停卖出
- ✅ 手续费: 与真实计算一致
- ✅ 收益指标: 年化、夏普、回撤合理范围

#### Step 5.3: 性能分析报告
**文件**: `scripts/analyze_strategy_performance.py`

**生成报告**:
- 策略收益曲线
- 回撤分析
- 持仓统计
- 交易次数/换手率
- 行业分布

---

### Phase 6: 信号生成集成 (预计2-3天)

#### Step 6.1: 修改信号生成器
**文件**: `signals/multi_strategy_signals.py`

**修改点**:
- 支持`ashare_mode`参数
- 股票池动态加载
- 信号保存到`trader`表

#### Step 6.2: Web API扩展
**文件**: `web/routers/trading.py`

**新增端点**:
```python
@router.get("/stock-signals/{date}")
async def get_stock_signals(date: str):
    """获取指定日期的股票信号"""

@router.get("/stock-universe/{date}")
async def get_stock_universe(date: str):
    """获取指定日期的股票池"""
```

---

### Phase 7: 测试与优化 (预计3-5天)

#### Step 7.1: 单元测试
**文件**: `tests/test_ashare_constraints.py` (新建)

**测试用例**:
```python
def test_t_plus_one_settlement()
def test_price_limit_checker()
def test_lot_rounding()
def test_commission_calculation()
```

#### Step 7.2: 集成测试
**文件**: `tests/test_stock_strategies.py` (新建)

**测试用例**:
```python
def test_multi_factor_strategy_initialization()
def test_momentum_strategy_backtest()
def test_stock_universe_filtering()
```

#### Step 7.3: 性能优化
- 因子计算缓存
- 股票池预筛选
- 数据库索引优化
- 并行计算支持

---

## 🎯 第八部分:关键文件清单

### 必须修改的文件 (5个)

1. **`core/backtrader_engine.py`**
   - 重要性: ⭐⭐⭐⭐⭐
   - 修改内容: 添加ashare_mode参数,集成手续费方案

2. **`core/backtrader_strategy.py`**
   - 重要性: ⭐⭐⭐⭐⭐
   - 修改内容: T+1检查,涨跌停检查,手数调整

3. **`database/db_manager.py`**
   - 重要性: ⭐⭐⭐⭐⭐
   - 修改内容: 新增stock_metadata等表

4. **`datafeed/factor_expr.py`**
   - 重要性: ⭐⭐⭐⭐
   - 修改内容: 注册基本面因子

5. **`signals/multi_strategy_signals.py`**
   - 重要性: ⭐⭐⭐⭐
   - 修改内容: 支持股票信号生成

### 必须新建的文件 (10个)

1. **`core/ashare_constraints.py`** - A股交易约束
2. **`core/ashare_commission.py`** - A股手续费
3. **`core/stock_universe.py`** - 股票池管理
4. **`datafeed/factor_fundamental.py`** - 基本面因子
5. **`strategies/stocks_多因子智能选股策略.py`** - 多因子策略
6. **`strategies/stocks_动量轮动选股策略.py`** - 动量策略
7. **`scripts/fetch_fundamental_data.py`** - 基本面数据更新
8. **`scripts/update_stock_universe.py`** - 股票池更新
9. **`scripts/run_stock_backtest.py`** - 回测入口
10. **`tests/test_ashare_constraints.py`** - 单元测试

---

## 📊 第九部分:预期成果

### 策略表现预期

| 策略 | 年化收益 | 最大回撤 | 夏普比率 | 适用场景 |
|-----|---------|---------|---------|---------|
| **多因子智能选股** | 15-25% | < 20% | > 1.0 | 震荡市、慢牛 |
| **动量轮动** | 20-35% | < 30% | > 0.8 | 趋势市 |
| **现有ETF轮动** | 10-20% | < 15% | > 1.2 | 全市场 |

### 系统能力提升

- ✅ 支持5700+只A股策略
- ✅ 严格模拟A股交易规则
- ✅ 基本面+技术面双因子驱动
- ✅ 动态股票池管理
- ✅ 完整的回测与信号生成流程

### 下一步扩展(可选)

- 📋 机器学习选股模型
- 📋 行业轮动策略
- 📋 事件驱动策略(财报、并购等)
- 📋 组合优化(Markowitz、Black-Litterman)
- 📋 实盘交易接口对接

---

## ✅ 第十部分:验收标准

### 功能验收

- [ ] T+1规则: 所有买入次日才能卖出
- [ ] 涨跌停: 无涨停买入、跌停卖出
- [ ] 手数限制: 所有持仓是100的倍数
- [ ] 手续费: 与真实A股手续费误差<1%
- [ ] 股票池: 动态筛选全市场A股
- [ ] 基本面数据: PE、PB、ROE等因子可用
- [ ] 多因子策略: 可正常运行回测
- [ ] 动量策略: 可正常运行回测
- [ ] 信号生成: 每日自动生成股票信号
- [ ] Web界面: 可查看股票策略信号

### 性能验收

- [ ] 回测速度: 10年数据< 5分钟
- [ ] 数据更新: 基本面数据< 10分钟
- [ ] 股票池筛选: < 30秒
- [ ] 信号生成: < 2分钟

### 质量验收

- [ ] 单元测试覆盖率> 70%
- [ ] 所有测试通过
- [ ] 代码注释完整
- [ ] 日志记录完善
- [ ] 错误处理健全

---

## 📅 第十一部分:时间估算

| 阶段 | 任务 | 预计时间 |
|-----|------|---------|
| **Phase 1** | 基础设施建设 | 5-7天 |
| **Phase 2** | 基本面数据系统 | 3-5天 |
| **Phase 3** | 股票池管理 | 2-3天 |
| **Phase 4** | 策略实现 | 5-7天 |
| **Phase 5** | 回测与验证 | 3-5天 |
| **Phase 6** | 信号生成集成 | 2-3天 |
| **Phase 7** | 测试与优化 | 3-5天 |
| **总计** | | **23-35天** |

---

## 🎬 总结

本实施计划在现有ETF轮动系统基础上,新增A股智能选股和交易功能,包括:

### 核心特性
1. ✅ **2个新策略**: 多因子智能选股 + 动量轮动
2. ✅ **严格A股规则**: T+1、涨跌停、手数、真实手续费
3. ✅ **全市场覆盖**: 5700+只A股动态筛选
4. ✅ **基本面数据**: PE、PB、ROE等因子支持

### 技术架构
- 最小化对现有代码的修改
- 模块化设计,易于扩展
- 完整的测试与验证流程

### 实施优先级
**高优先级**: Phase 1 → Phase 4 (基础设施+策略实现)
**中优先级**: Phase 2 → Phase 3 (基本面数据+股票池)
**低优先级**: Phase 6 → Phase 7 (信号集成+优化)

**建议**: 先实现Phase 1和Phase 4,验证核心功能,再逐步完善其他模块。

---

## 📝 附录: Phase 1 交付物清单

### 核心代码文件
1. ✅ `core/ashare_constraints.py` (378行)
   - TPlusOneTracker类
   - PriceLimitChecker类
   - LotSizeRounder类
   - 订单验证工具函数

2. ✅ `core/ashare_commission.py` (230行)
   - AShareCommissionScheme类
   - AShareCommissionSchemeV2类
   - ZeroCommission类
   - FixedCommission类
   - setup_ashare_commission()工具函数

3. ✅ `core/backtrader_strategy.py` (修改)
   - 添加A股模式参数支持
   - rebalance方法集成A股约束

4. ✅ `core/backtrader_engine.py` (修改)
   - Task类添加ashare_mode参数
   - Engine.run()支持A股手续费

### 测试文件
5. ✅ `tests/test_ashare_constraints.py` (280行)
   - 26个单元测试用例
   - 100%测试通过率

### 示例与文档
6. ✅ `examples/ashare_strategy_example.py` (120行)
   - 3个完整策略示例
   - ETF策略对比示例

7. ✅ `PHASE1_COMPLETED.md`
   - 详细完成总结
   - 使用说明
   - 注意事项

8. ✅ `docs/A股模式快速指南.md`
   - 快速开始指南
   - 参数说明
   - 常见问题

### 测试结果
```
✅ T+1跟踪器: 6/6 通过
✅ 涨跌停检查器: 5/5 通过
✅ 手数调整器: 8/8 通过
✅ 手续费计算: 3/3 通过
✅ 订单验证: 4/4 通过
─────────────────────
总计: 26/26 通过 ✅
```

### 代码统计
- 新增代码: ~1000行
- 修改代码: ~200行
- 测试代码: ~280行
- 文档: ~1500行
- **总工作量**: ~3000行

---

## 🎯 下一步工作计划

### Phase 2: 基本面数据系统
**预计工作量**: 3-5天

#### 需要完成的任务:
1. 数据库表设计
   - stock_metadata表结构
   - factor_cache表
   - stock_universe_snapshot表

2. 数据获取脚本
   - AkShare数据源集成
   - 基本面数据更新
   - 错误处理与重试

3. 基本面因子库
   - PE/PB因子
   - ROE/ROA因子
   - 市值因子
   - 质量因子

4. 定时任务
   - 每日数据更新
   - 数据质量检查

### Phase 3: 股票池管理
**预计工作量**: 2-3天

#### 需要完成的任务:
1. 股票池筛选器
   - 动态筛选逻辑
   - 多条件组合
   - 历史快照

2. 数据更新脚本
   - 每日股票池更新
   - 统计报告生成

3. 定时任务配置
   - Cron脚本配置
   - 日志记录

---

## 💡 经验总结

### Phase 1 成功要素
1. **模块化设计** - 每个约束独立成类,职责清晰
2. **向后兼容** - 不影响现有ETF策略
3. **测试驱动** - 先写测试,确保功能正确
4. **文档完善** - 示例、指南、总结齐全

### 遇到的挑战
1. **Backtrader参数传递** - 通过修改StrategyTemplate解决
2. **T+1状态管理** - 使用字典跟踪买入日期
3. **涨跌停判断** - 需要获取前收盘价数据

### 解决方案
1. **参数化设计** - 所有约束都可通过参数控制
2. **日志记录** - 便于调试和问题排查
3. **灵活配置** - 支持多种手续费方案

---

**Phase 1 完成日期**: 2024-12-29
**下一阶段**: Phase 2 - 基本面数据系统
**文档版本**: v1.0
