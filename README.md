# AITrader

AITrader 现在专注于 A 股研究、回测与信号生成。
日频历史行情直接从 Wind MySQL 表 `ASHAREEODPRICES` 读取；
PE/PB/PS、换手率、市值等字段从 `ASHAREEODDERIVATIVEINDICATOR` join。

## 运行环境

安装依赖：

```bash
pip install -r requirements.txt
pip install -e .
```

通过 `MYSQL_URL` 或下面这组分量变量配置 Wind MySQL 价格源；这些配置只用于历史价格读取：

```bash
MYSQL_HOST=...
MYSQL_PORT=3306
MYSQL_USER=...
MYSQL_PASSWORD=...
MYSQL_DATABASE=winddb
```

应用层状态库使用 `DATABASE_URL`，不设置时回落到本地 SQLite：

```bash
DATABASE_URL=sqlite:///aitrader.db
```

请勿把真实数据库凭据提交到仓库。

## 主要工作流

### A 股信号生成

推荐入口：

```bash
python -m aitrader.app.cli.ashare_signals
aitrader-ashare-signals
```

常用参数：

```bash
python -m aitrader.app.cli.ashare_signals --workers 2
python -m aitrader.app.cli.ashare_signals --force-backtest
python -m aitrader.app.cli.ashare_signals --weekly
python -m aitrader.app.cli.ashare_signals --monthly
```

### 短线工作流

```bash
python -m aitrader.app.cli.short_term_signals
aitrader-short-term
python -m aitrader.app.cli.short_term_signals 20260120
python -m aitrader.app.cli.short_term_signals 20260120 --fetch-only
python -m aitrader.app.cli.short_term_signals 20260120 --signals-only
```

### 回测

```bash
python -m aitrader.app.cli.stock_backtests
aitrader-stock-backtests
```

### ArXiv → A 股策略 Pipeline（统一入口）

把"拉取近 N 天 arxiv q-fin 论文 → LLM 判断 A 股适用性 → LLM 生成 select_fn →
跑近 1 年 H1/H2 回测 → 跨论文汇总"一条命令跑完：

```bash
python -m aitrader.app.cli.arxiv_pipeline                           # 默认 14d / 全 5 步
aitrader-arxiv --since 30d --max-papers 5                           # 自定义窗口
aitrader-arxiv --paper 2604.99999 --rerun                           # 单篇重跑
aitrader-arxiv --steps fetch,aggregate --no-llm                     # 只跑非 LLM 步骤
aitrader-arxiv --rerun-legacy --steps generate,backtest,aggregate   # 老论文换成 LLM 生成版
aitrader-arxiv --dry-run                                            # 仅打印计划
```

LLM 配置见 `.env.example`（不设时回落 `model.py` 中的小蝶 AI gpt-5.4）。

每篇论文产物落到
`papers/arxiv/processed/<arxiv_id>/`：`00_meta.json` / `01_paper.md` /
`02_applicability.md` / `03_strategy_code.py` / `select_fn.py` /
`04_backtest_summary.md` + 标准 csv/json/png；跨论文比较位于
`papers/arxiv/processed/_aggregate/cross_paper_comparison.md` 与
`pipeline_status.json`。

## 回测性能优化

当前已落地的提速措施：

- 批量回测改走 `ParallelBacktestRunner`，父进程在 fork worker 之前预热原始行情和基准缓存。
- 热数据加载使用 `DbDataLoader.read_dfs(..., copy_result=False)`，让 fork 出来的 worker 复用继承的缓存状态，免去额外 dataframe 拷贝。
- `FactorExpr` 现在按股票并行计算因子，在 Linux 下能更充分地占满 CPU 核心。
- `factor_extends.py` 中的 `trend_score` 和 RSRS 相关辅助函数已向量化，减少 Python 循环开销。

## 验证命令

语法检查：

```bash
/home/yy/anaconda3/bin/python -m py_compile \
  src/aitrader/domain/backtest/engine.py \
  src/aitrader/domain/backtest/bt_engine.py \
  src/aitrader/domain/backtest/parallel.py \
  src/aitrader/app/use_cases/stock_backtests.py \
  src/aitrader/infrastructure/db/factor_cache.py \
  src/aitrader/infrastructure/market_data/factor_expr.py \
  src/aitrader/infrastructure/market_data/loaders.py \
  src/aitrader/infrastructure/market_data/factor_extends.py
```

不依赖数据库的因子流水线 smoke 测试：

```bash
/home/yy/anaconda3/bin/python - <<'PY'
import numpy as np
import pandas as pd
from aitrader.infrastructure.market_data.factor_expr import FactorExpr

np.random.seed(0)
dates = pd.date_range('2024-01-01', periods=40, freq='D')

def make_df(symbol, base):
    close = base + np.cumsum(np.random.randn(len(dates)))
    return pd.DataFrame({
        'date': dates,
        'symbol': symbol,
        'open': close,
        'high': close,
        'low': close,
        'close': close,
        'volume': np.full(len(dates), 1000),
    })

dfs = {
    '000001.SZ': make_df('000001.SZ', 10),
    '000002.SZ': make_df('000002.SZ', 20),
}

result = FactorExpr().calc_formulas(
    dfs,
    ['trend_score(close,5)', 'MACD(close,12,26,9)'],
    parallel=True,
)
print(result.shape)
print('smoke ok')
PY
```

配置好 MySQL 后的真实回测命令：

```bash
MYSQL_HOST=... MYSQL_PORT=3306 MYSQL_USER=... MYSQL_PASSWORD=... MYSQL_DATABASE=... \
/home/yy/anaconda3/bin/python -m aitrader.app.cli.stock_backtests --multi-factor-all
```

## 架构

```text
A 股策略 -> Task -> Engine -> DbDataLoader -> MySQLAshareReader -> Wind MySQL
                            -> FactorExpr / FactorCache -> 信号
```

## 源码布局

核心应用代码正在迁移到 `src/aitrader/`：

- `src/aitrader/app`：CLI 入口、用例、应用层服务
- `src/aitrader/domain`：策略、回测、组合相关的领域层落地区
- `src/aitrader/infrastructure`：数据库、行情数据、配置
- `src/aitrader/shared`：共享辅助工具

关键模块：

- `src/aitrader/infrastructure/market_data/mysql_reader.py`：读取 Wind MySQL 的 A 股日频行情和衍生指标。
- `src/aitrader/infrastructure/market_data/loaders.py`：保留原有 `{symbol: DataFrame}` 加载契约，供引擎和因子代码使用。
- `src/aitrader/domain/backtest/engine.py`：执行策略 `Task` 对象。
- `src/aitrader/domain/strategy/loader.py`：发现并加载 `strategies/stocks_*.py`。
- `src/aitrader/app/cli/ashare_signals.py`：运行 A 股回测和信号生成。
- `src/aitrader/app/cli/short_term_signals.py`：运行 A 股短线选股工作流。
- `src/aitrader/infrastructure/db/db_manager.py`：信号、回测、持仓、参考数据、短线操作清单等的中性应用持久化门面。

## 数据契约

`DbDataLoader.read_dfs(symbols, start_date, end_date)` 按 Wind 风格的股票代码返回每只股票一份 DataFrame。
每份 frame 至少包含以下列：

- `date`
- `symbol`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `vwap`
- `real_open`
- `real_close`
- `real_low`

兼容性列也保留，包括 `amount`、`change_pct`、`turnover_rate`、`pe`、`pe_ttm`、`pb`、
`ps`、`ps_ttm`、`total_mv`、`circ_mv`。

| 加载器列名 | Wind 来源 |
| --- | --- |
| `date` | `TRADE_DT` |
| `symbol` | `S_INFO_WINDCODE` |
| `real_open` | `S_DQ_OPEN` |
| `real_close` | `S_DQ_CLOSE` |
| `real_low` | `S_DQ_LOW` |
| `open` | `S_DQ_ADJOPEN` |
| `close` | `S_DQ_ADJCLOSE` |
| `high` | `S_DQ_ADJHIGH` |
| `low` | `S_DQ_ADJLOW` |
| `vwap` | `S_DQ_AVGPRICE` |
| `volume` | `S_DQ_VOLUME` |
| `amount` | `S_DQ_AMOUNT` |
| `change_pct` | `S_DQ_PCTCHANGE` |
| `turnover_rate` | `ASHAREEODDERIVATIVEINDICATOR.S_DQ_TURN` |
| `free_turnover_rate` | `ASHAREEODDERIVATIVEINDICATOR.S_DQ_FREETURNOVER` |
| `pe` | `ASHAREEODDERIVATIVEINDICATOR.S_VAL_PE` |
| `pe_ttm` | `ASHAREEODDERIVATIVEINDICATOR.S_VAL_PE_TTM` |
| `pb` | `ASHAREEODDERIVATIVEINDICATOR.S_VAL_PB_NEW` |
| `ps` | `ASHAREEODDERIVATIVEINDICATOR.S_VAL_PS` |
| `ps_ttm` | `ASHAREEODDERIVATIVEINDICATOR.S_VAL_PS_TTM` |
| `total_mv` | `ASHAREEODDERIVATIVEINDICATOR.S_VAL_MV` |
| `circ_mv` | `ASHAREEODDERIVATIVEINDICATOR.S_DQ_MV` |

历史价格只从 Wind MySQL 读取，不依赖本地缓存。

## 本地持久化

信号、回测、持仓、股票元数据以及短线操作清单，统一通过
`src/aitrader/infrastructure/db/db_manager.py` 走 `DATABASE_URL`。
价格读取与应用层持久化保持解耦。

## 已移除的范围

ETF 信号生成、ETF 组合回测、ETF 下载器，以及本地 PostgreSQL 行情缓存均已移除。
MySQL 缺数据按上游数据源问题处理，不再做本地兜底。
