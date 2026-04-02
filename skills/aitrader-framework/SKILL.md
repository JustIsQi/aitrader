---
name: aitrader-framework
description: Use when working with AITrader or reusing its Python quant trading patterns in another repository. Covers Task/Engine backtests, ETF and A-share strategy definitions, PostgreSQL plus AKShare data loading, strategy auto-discovery, and daily signal or short-term stock-selection pipelines.
---

# AITrader Framework

这个 skill 用于两类场景：

1. 当前仓库本身就是 AITrader，需要直接修改策略、数据层、回测或信号流水线。
2. 当前仓库不是 AITrader，但需要复用它的量化交易架构和工作流。

## 先判定模式

优先用 `rg --files` 检查这些标记文件：

- `core/backtrader_engine.py`
- `database/pg_manager.py`
- `run_ashare_signals.py`
- `run_short_term_signals.py`
- `strategies/stocks_*.py`

命中 2 个及以上时，按 `embedded` 模式处理；否则按 `porting` 模式处理。

## Embedded 模式

- 沿用现有 `Task -> DataFeed -> Engine -> signal pipeline` 结构，不要另起一套配置协议。
- 策略函数保持“返回 `Task`”的风格；不要在策略文件里混入执行逻辑。
- 数据读取默认走 PostgreSQL；只有确认缺数时才补下载逻辑。
- 需要看哪一部分时再加载对应参考：
  - 架构和模块分工：`references/architecture.md`
  - 策略约定、字段、因子表达式：`references/strategy-patterns.md`
  - 初始化、运行命令、运维约束：`references/workflows.md`
  - A股规则与手续费：`references/ashare-rules.md`

## Porting 模式

- 只迁移最小必需切片，不要复制整个 AITrader 仓库。
- 先在目标仓库建立 5 个等价抽象，再写业务：
  1. 任务模型 `Task`
  2. 历史行情加载器
  3. 因子或表达式求值器
  4. 回测执行器
  5. 策略注册或发现机制
- 如果还要迁移 A股信号生成，再补 3 个部件：
  1. 回测结果持久化
  2. 策略枚举器
  3. 日信号生成入口
- 若目标仓库不使用 PostgreSQL，可以替换存储层，但要保留这 3 个能力：
  - 批量读 bars
  - 保存回测结果
  - 保存信号或操作清单

## Hard Rules

- 标的格式保持 `000001.SZ` / `600000.SH` / `510300.SH`
- 日期输入优先 `YYYYMMDD`
- 选股条件、排序因子、调仓频率优先写进 `Task`，不要把条件散落到执行器内部
- A股场景显式设置 `ashare_mode` 和 `ashare_commission`
- 需要调整复权时，统一传递 `adjust_type`，不要让 loader、pipeline、strategy 的默认值互相打架
- 涉及并发回测时，优先共享连接池的线程池方案；只有确认 CPU 才是瓶颈时再考虑进程池

## 常见任务

- 新增或修改 ETF / A股策略
- 把 AITrader 的 `Task/Engine` 架构移植到别的仓库
- 给策略补因子表达式、排序逻辑、风控和调仓频率
- 排查 PostgreSQL 数据缺失、批量查询或信号流水线问题
- 构建短线 A股“板块 -> 个股 -> 仓位/止盈止损 -> 落库”流程

## 交付要求

- 回答或实施前，先说明采用 `embedded` 还是 `porting`
- `porting` 任务要明确：
  - 迁移了哪些最小模块
  - 哪些 AITrader 细节被保留
  - 哪些细节为了适配目标仓库被简化
