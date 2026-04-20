# A 股策略文件生成模板

根据论文在 `src/aitrader/domain/strategy/<slug>.py` 新建策略模块，然后在 `strategies/` 下补一个 shim 文件即可被现有回测框架调用。

## 1. 放在哪两处

- 真正实现：`src/aitrader/domain/strategy/<slug>.py`
- 入口 shim（可选）：`strategies/stocks_<slug>_selection.py`，只做 `from aitrader.domain.strategy.<slug> import *`

## 2. 实现文件骨架（照搬 agentic_turnover.py 的风格）

```python
# 策略中文名：stocks_<中文名>策略

"""
A 股 <中文名> 策略

论文来源: "<Paper Title>"
ArXiv: <arxiv_id>  作者: <authors>
发布日期: <yyyy-mm-dd>

核心发现:
- <论文关键 finding 1>
- <论文关键 finding 2>

A 股适配理由:
- <为什么在 A 股成立 / 有哪些改动>
- <数据可得性说明：仅日频 OHLCV / 需要换手率 / 需要估值因子 等>

因子实现:
  F1  <name>   <表达式>   权重 xx%
  F2  ...
"""

import sys
from aitrader.domain.backtest.engine import Task, Engine
from aitrader.domain.market.stock_universe import StockUniverse


_COMPOSITE_SIGNAL = (
    'normalize_score(<expr1>) * 0.30 + '
    'normalize_score(<expr2>) * 0.25 + '
    '...'
)


def <slug>_strategy_weekly():
    t = Task()
    t.name = 'A股<中文名>策略-周频'
    t.ashare_mode = True
    t.ashare_commission = 'v2'
    t.start_date = '20190101'
    t.end_date   = '20241231'

    universe = StockUniverse()
    t.symbols = universe.get_all_stocks(
        exclude_st=True,
        exclude_suspend=False,
        exclude_new_ipo_days=None,
        min_data_days=2500,
        exclude_restricted_stocks=True,
    )

    t.select_buy = [
        # 2~4 个偏宽松的硬约束
    ]
    t.buy_at_least_count = 2

    t.select_sell = [
        # 触发任一即卖出
    ]
    t.sell_at_least_count = 1

    t.order_by_signal = _COMPOSITE_SIGNAL
    t.order_by_topK = 20
    t.order_by_DESC = True

    t.period = 'RunWeekly'
    t.weight = 'WeightEqually'
    return t


if __name__ == '__main__':
    task = <slug>_strategy_weekly()
    print(f"策略: {task.name}  股票池: {len(task.symbols)}  TopK: {task.order_by_topK}")
    result = Engine().run(task)
    result.stats()
```

## 3. shim 文件（可选）

```python
"""Compatibility shim"""
import sys; from pathlib import Path as _P
_src = str(_P(__file__).resolve().parent.parent / "src")
if _src not in sys.path: sys.path.insert(0, _src)
from aitrader.domain.strategy.<slug> import *  # noqa
```

## 4. 可用的信号 DSL（节选，详见 `src/aitrader/domain/backtest/indicators.py`）

- 均线：`ma(close,20)`、`ma(turnover_rate,5)`
- 变动率：`roc(close,20)` = 20 日收益率
- 对数：`LOG(...)`
- 标准化：`normalize_score(...)` 截面打分（适合做复合因子）
- 原始字段：`close`、`open`、`high`、`low`、`volume`、`turnover_rate`、`pe`、`pb`、`total_mv`

## 5. 命名约定

- `<slug>`：下划线小写，尽量短（如 `agentic_turnover`、`multi_factor`、`momentum`）
- 文件末尾不要留 TODO 注释——要么实现、要么删掉
