# aitrader 与 aitrader_037 对比

## 1. 结论先行

`aitrader` 更像一个面向执行和持续运行的量化工程项目。它把“股票池筛选 -> 策略发现 -> 回测 -> 信号生成 -> 数据库存储”串成了完整流水线，A 股和 ETF 也分别做了更明确的模块拆分。

`aitrader_037` 更像一个研究型/原型型项目。它有一套可复用的 `Task + Algo + Backtrader` 组合式回测框架，但更多价值在于独立策略脚本、Notebook、GUI/Streamlit 分析页和 AI 实验模块，统一的生产化筛选与落库闭环明显弱于 `aitrader`。

如果只看“数据筛选、策略、回测”三件事：

| 维度 | aitrader | aitrader_037 |
|---|---|---|
| 数据筛选 | 有独立筛选层，且分 A 股、ETF、短线选股三条线 | 以策略内表达式筛选和 GUI 侧分析筛选为主，缺少统一预筛选主线 |
| 策略组织 | `Task`/`PortfolioTask` 统一描述，`StrategyLoader` 自动发现 | 一部分是 `Task` 驱动，一部分是独立 `bt.Strategy` 脚本 |
| 回测架构 | A 股公式型回测 + ETF 组合回测双主线，支持持久化 | 以 Backtrader 单引擎为核心，结果更多停留在脚本内存和图表层 |
| 工程化程度 | 高 | 中，偏研究原型 |
| 更适合 | 定时跑信号、沉淀回测记录、继续扩展生产流程 | 快速试策略、做多种风格实验、GUI 展示与交互分析 |

## 2. 数据筛选差异

### 2.1 aitrader 的数据筛选是独立模块，不只是策略条件

`aitrader` 的筛选不是简单把条件写进策略里，而是拆成了独立可复用的筛选层：

- A 股预筛选主线在 `core/smart_stock_filter.py`
- A 股基础股票池与基本面/流动性过滤在 `core/stock_universe.py`
- ETF 预筛选主线在 `core/smart_etf_filter.py`
- 短线个股筛选在 `core/stock_selector.py`
- 短线仓位与止盈止损计划在 `core/position_manager.py`

其中最核心的是 `SmartStockFilter.filter_stocks()`，它把股票池筛成三层：

1. 基础过滤：ST、停牌、数据不足、新股、受限板块
2. 市值过滤：`min_market_cap`
3. 流动性过滤：`turnover_rate`、`amount`

ETF 侧 `SmartETFFilter.filter_etfs()` 也有独立层次：

1. 数据可用性过滤
2. 流动性过滤
3. 可选技术指标过滤
4. 按目标数量截断

这说明 `aitrader` 的筛选是“先缩池，再做策略判断”，目的不是只为了回测，更是为了降低后续信号计算和数据库写入成本。

### 2.2 aitrader_037 的筛选更偏“策略内部表达式”或“分析页查询”

`aitrader_037` 当前能直接从核心代码确认的筛选主线，在 `core/backtrader_engine.py` 和 `core/backtrader_algos.py`：

- `Task.symbols` 定义初始标的池
- `select_buy` / `select_sell` 定义布尔筛选条件
- `buy_at_least_count` / `sell_at_least_count` 定义命中阈值
- `order_by_signal` 定义排序因子
- `order_by_topK` / `order_by_dropN` 定义最终入选数量

执行上是：

1. `DataFeed` 先加载标的数据并计算因子
2. `Engine._parse_rules()` 把条件组合成按日期对齐的布尔矩阵
3. `SelectWhere` 取命中条件的候选池
4. `SelectTopK` 再对候选池排序并取前 `K`

这条链是有效的，但它和 `aitrader` 的差别在于：

- 它更像“策略内部的选标逻辑”
- 不太像“全局统一预筛选层”
- 很多股票池本身是手工给定或在脚本里写死的

`README.md` 还描述了 SQLite/`performance` 表上的 GUI 筛选与排名能力，但在当前核对范围内，这条链更多是分析展示侧能力，不是和 `aitrader/run_ashare_signals.py` 对等的一体化执行入口。

### 2.3 两者在筛选目标上的本质区别

`aitrader` 的筛选目标更偏“可执行交易候选集”：

- 先缩小股票池
- 再跑多策略信号
- 最后生成 `BuySignal` / `SellSignal`
- 并把结果与回测记录关联到数据库

`aitrader_037` 的筛选目标更偏“回测时选出本期应持有资产”：

- 先给定资产池
- 再用表达式和排序做当期选标
- 结果直接进入回测调仓

所以在“数据筛选”这件事上，`aitrader` 明显更重视独立筛选层、参数预设和执行闭环，`aitrader_037` 更重视策略自由度。

## 3. 策略差异

### 3.1 aitrader 的策略是统一配置语言加自动发现

`aitrader` 的核心抽象是 `core/backtrader_engine.py` 里的 `Task` 和 `core/portfolio_bt_engine.py` 里的 `PortfolioTask`。一个策略主要由这些字段描述：

- `symbols`
- `select_buy` / `select_sell`
- `buy_at_least_count` / `sell_at_least_count`
- `order_by_signal`
- `order_by_topK`
- `period`
- `weight`
- A 股特有的 `ashare_mode` / `ashare_commission`

策略加载不靠手工注册，而是由 `core/strategy_loader.py` 自动扫描 `strategies/stocks_*.py`。这让 `run_ashare_signals.py` 可以统一发现并批量回测 A 股策略。

当前可直接确认的 A 股主策略有两类：

- `strategies/stocks_multi_factor_selection.py`
- `strategies/stocks_momentum_rotation_selection.py`

前者偏多因子综合打分，后者偏强动量轮动。ETF 侧则进一步分化成：

- `strategies/etf_portfolio_backtest.py` 这类公式型组合策略
- `strategies/etf_dual_momentum.py`
- `strategies/etf_risk_parity.py`
- `strategies/etf_portfolio_optimized.py`
- `strategies/etf_multi_strategy_rotation.py`

也就是说，`aitrader` 在策略层已经形成了“统一描述 + 自动发现 + 多资产主线分层”的结构。

### 3.2 aitrader_037 的策略更像“统一骨架 + 多种实验实现并存”

`aitrader_037` 也有统一骨架：

- `core/backtrader_engine.py` 负责 `Task -> DataFeed -> AlgoStrategy`
- `core/backtrader_algos.py` 提供调仓周期、筛选、排序、权重、再平衡积木
- `core/backtrader_strategy.py` 提供策略模板和交易记录能力

但它并没有像 `aitrader` 那样，把主要策略都收束到统一发现和统一调度入口上。当前能看到两种并存风格：

1. 配置式策略
   - 典型是 `策略集/backtrader-多标的轮动454% 回撤6.9%.py`
   - 直接构造 `Task`，再交给 `Engine.run()`

2. 自定义 `bt.Strategy` 策略
   - `策略集/大类资产配置.py`
   - `策略集/大类资产-择时.py`
   - `策略集/大类资产_机器学习.py`
   - `策略集/大类资产-机器学习-优化.py`

第二类脚本里，动量、均线、波动率、相关性、LightGBM 预测、风险平价、止损止盈等逻辑常常直接写在策略类内部。这种方式很灵活，但统一维护成本也更高。

### 3.3 风控和约束的内建程度不同

`aitrader` 把不少风控做成了基础设施：

- `core/ashare_constraints.py` 支持 T+1、涨跌停、整手交易
- `core/ashare_commission.py` 支持更接近真实 A 股费用结构
- `core/position_manager.py` 支持仓位上限、ATR 止损、梯度止盈、开盘触发条件

`aitrader_037` 的风控更多内嵌在具体策略脚本里：

- 某些策略有回撤阈值
- 某些策略有波动率阈值
- 某些策略有止损、移动止盈

这使得 `aitrader_037` 的策略更自由，但“通用风险约束”复用度不如 `aitrader`。

## 4. 回测差异

### 4.1 aitrader 是双主线回测架构

`aitrader` 至少有两条明确的回测主线：

1. A 股公式型回测
   - 入口是 `core/backtrader_engine.py` 的 `Engine.run()`
   - 外层调度是 `run_ashare_signals.py`

2. ETF 组合回测
   - 入口是 `core/portfolio_bt_engine.py` 的 `PortfolioBacktestEngine.run()`
   - 外层调度是 `run_etf_portfolio_backtest.py`

A 股主线会：

- 自动发现策略
- 并发跑回测
- 提取收益、回撤、夏普、交易明细
- 再生成信号
- 最后把回测和信号写入数据库

ETF 组合主线则更偏组合级模拟：

- 逐交易日取价
- 当日按公式生成入选标的
- 判断是否需要再平衡
- 执行买卖并记录每日状态
- 期末计算 `Sortino`、`Calmar`、`VaR`、`CVaR`、月胜率等更丰富的组合指标

### 4.2 aitrader_037 以单套 Backtrader 引擎为核心

`aitrader_037` 的回测核心在 `core/backtrader_engine.py`：

- `_prepare_run()` 负责加载数据并注册到 `Cerebro`
- `DataFeed` 负责计算策略需要的因子
- `_get_algos()` 组装算法链
- `Engine.run()` 执行回测并产出 `perf`、`hist_trades`、`signals`、`weights`

统计上它已经具备：

- `PyFolio`
- `SharpeRatio`
- `DrawDown`
- `Returns`
- `TimeReturn`
- `ffn.calc_stats()`

所以它不是“不能回测”，而是“回测能力比较集中，外围工程化较少”。很多高级分析和风险控制，放在具体脚本里各自实现，而不是像 `aitrader` 那样在统一的回测与信号流水线上沉淀。

### 4.3 回测结果持久化和可追踪性差别很大

`aitrader` 更重视结果沉淀：

- `run_ashare_signals.py` 会调用 `save_backtest_result`
- `signals/multi_strategy_signals.py` 会生成可落库的 `BuySignal` / `SellSignal`
- 文档和模型里还能看到 `signal_backtest_associations`

这意味着它天然支持：

- 某次信号来自哪个策略
- 对应哪一次回测
- 回测指标是什么

`aitrader_037` 当前可直接确认的主链中，没有看到与之等价的统一持久化机制。结果更多停留在：

- 脚本运行过程
- 图表显示
- `perf` 统计对象
- 控制台输出

因此它更适合研究，不太像一个已经打通“策略结果资产化”的系统。

### 4.4 两边都存在需要注意的实现细节

`aitrader`：

- `core/backtrader_engine.py` 的 `Engine.run()` 会把 `task.end_date` 强制改成当前日期，策略里预设的结束日期不会真正生效
- `run_ashare_signals.py` 把 `Engine.run(task)` 的返回值直接交给 `extract_backtest_metrics()`，而静态看 `Engine.run()` 返回的是 `self.results`，`extract_backtest_metrics()` 则读取 `perf` 和 `hist_trades`，这块接口对齐需要继续核实

`aitrader_037`：

- `Engine._prepare_run()` 走的是 `CsvDataLoader`
- `README.md` 强调的 SQLite/GUI 分析主线，与当前回测主链并不是完全同一套数据访问路径

这意味着 `aitrader_037` 的“分析展示链”和“策略回测链”之间耦合度比 README 看起来更松。

## 5. 最终判断

如果目标是“搭一个能持续跑、能落库、能做策略比较和信号分发的量化系统”，`aitrader` 明显更合适。

如果目标是“快速试很多想法，保留脚本、Notebook、自定义 `bt.Strategy`、机器学习和 AI 实验的自由度”，`aitrader_037` 更顺手。

可以把两者的差异概括成一句话：

- `aitrader` 强在工程化执行链
- `aitrader_037` 强在研究型策略实验空间

## 6. 关键证据文件

### aitrader

- `run_ashare_signals.py`
- `core/smart_stock_filter.py`
- `core/stock_universe.py`
- `signals/multi_strategy_signals.py`
- `core/backtrader_engine.py`
- `core/portfolio_bt_engine.py`
- `core/portfolio_metrics.py`
- `core/ashare_constraints.py`
- `core/ashare_commission.py`
- `core/position_manager.py`
- `strategies/stocks_multi_factor_selection.py`
- `strategies/stocks_momentum_rotation_selection.py`
- `strategies/etf_dual_momentum.py`
- `strategies/etf_risk_parity.py`
- `strategies/etf_multi_strategy_rotation.py`

### aitrader_037

- `README.md`
- `core/backtrader_engine.py`
- `core/backtrader_algos.py`
- `core/backtrader_strategy.py`
- `gui/streamlit_app.py`
- `agents/IndicatorAgent.py`
- `agents/main_agent.py`
- `策略集/backtrader-多标的轮动454% 回撤6.9%.py`
- `策略集/大类资产配置.py`
- `策略集/大类资产-择时.py`
- `策略集/大类资产_机器学习.py`
- `策略集/大类资产-机器学习-优化.py`
