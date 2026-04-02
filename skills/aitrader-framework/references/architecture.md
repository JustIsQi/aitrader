# AITrader 架构速览

AITrader 的主链路是：

```text
数据获取 -> PostgreSQL -> DbDataLoader -> FactorExpr -> Engine -> 回测结果
策略函数 -> Task -> StrategyLoader -> 日信号流水线 -> 数据库
```

短线 A股模块是另一条链路：

```text
板块资金流 -> SectorAnalyzer -> StockSelector -> PositionManager -> daily_operation_list
```

## 核心模块映射

- `core/backtrader_engine.py`
  - 定义 `Task`、`DataFeed`、`Engine`
  - 是策略声明式配置和执行器之间的主桥梁
- `datafeed/db_dataloader.py`
  - 从 PostgreSQL 批量读取 ETF / 股票数据
  - 缺数时可触发下载并写回数据库
  - 支持 `adjust_type` 区分前复权和后复权
- `datafeed/factor_expr.py`
  - 负责把诸如 `roc(close,20)`、`ma(close,60)` 的表达式算成因子列
- `database/pg_manager.py`
  - 数据库门面层
  - 负责历史行情、回测结果、信号、持仓等读写
- `core/strategy_loader.py`
  - 自动扫描 `strategies/stocks_*.py`
  - 找出返回 `Task` 且 `ashare_mode=True` 的策略函数
- `run_ashare_signals.py`
  - 批量回测 A股策略
  - 保存回测指标
  - 生成日信号并关联回测结果
- `run_short_term_signals.py`
  - 跑短线 A股“板块 -> 个股 -> 交易计划”流水线
- `short_term_config/short_term_config.py`
  - 短线模块的阈值与风控配置

## 模块职责边界

- 策略文件只负责“返回一个配置好的 `Task`”
- `Engine` 负责把 `Task` 编译成调仓算法链并运行回测
- Loader 和 DB 层负责提供数据，不应在策略内部直接发 SQL
- 信号脚本负责编排批量任务和落库，不应把策略实现塞进脚本本身
- 短线模块与通用回测模块并列存在，适合独立演进

## 变更定位建议

- 改买卖条件、排序和调仓频率：优先改策略函数和 `Task` 字段
- 改历史行情来源、批量查询或自动补数：优先改 `datafeed/` 与 `scripts/get_data.py`
- 改数据库表结构或持久化行为：优先改 `database/models/` 与 `database/pg_manager.py`
- 改 A股批量回测与信号生成：优先改 `run_ashare_signals.py` 和 `signals/`
- 改短线板块打分、个股筛选、仓位和止盈止损：优先改 `core/sector_analyzer.py`、`core/stock_selector.py`、`core/position_manager.py`、`short_term_config/`

## 迁移到别的仓库时的最小保留件

如果目标只是“复用 AITrader 的做法”，最少保留这些概念：

1. 声明式策略对象 `Task`
2. 批量行情加载接口
3. 因子表达式计算层
4. 回测执行器
5. 策略注册或自动发现机制

如果还要复用 A股信号体系，再加：

1. 回测结果模型
2. 策略枚举器
3. 日信号生成入口
