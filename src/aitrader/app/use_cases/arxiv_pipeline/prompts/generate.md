你是 A 股量化策略工程师。基于下面这篇 arxiv 论文 + A 股适用性判断，写出一份**完整、可直接被 importlib 加载执行**的 A 股策略代码。

## 论文标题
{paper_title}

## ArXiv ID
{paper_id}

## 论文 Markdown 全文（已截断到 ~30k 字符）
{paper_md}

## A 股适用性判断（上一步 LLM 输出）
{applicability_md}

## 框架背景

仓库已有一个统一研究 runner：`aitrader.research.runner.run_research`。它接受一个 `StrategySpec`，自动完成：

- 动态选池（`UniverseSpec(top_n, refresh_freq)`）
- 价格面板加载（`PanelLoader`）
- 调仓日历（`rebalance_dates_for(panels.close_adj.index, freq, warmup_days)`）
- 向量化模拟（next-open execution / T+1 / 涨跌停 / 现金利率 / 分项交易成本）
- 性能指标 + 基线对比 + Train/Holdout 切分 + 可选 Grid Ablation

你只需要写：

1. `select_fn.py` — 真正算信号、出权重的函数。
2. `03_strategy_code.py` — 入口文件，声明 `StrategySpec` + 在 `__main__` 调 `run_research`。

## select_fn.py 强制约束

```python
from __future__ import annotations
import numpy as np
import pandas as pd
from aitrader.research.runner.specs import SelectFnContext, SelectionResult
# 可选：from aitrader.research.signals.network import (eigenvector_centrality, pca_leading_factor, complexity_gap)


def select_<slug>(context: SelectFnContext, params: dict) -> SelectionResult:
    panels = context.panels                # PricePanels：close_adj/open_adj/high_adj/low_adj/volume/amount/...
    universe = context.universe            # DynamicLiquidUniverse；universe.universe_for_trading(dt) 拿当时的池子
    rebalance_dates = context.rebalance_dates

    # 1) 在每个 rebalance_date 上算信号；信号必须只用 prior 日及之前的数据，禁止 look-ahead
    # 2) 输出 target_weights：DataFrame，index = panels.close_adj.index, columns = panels.close_adj.columns
    #    rebalance_date 那天写入权重（缺省/不持有为 0），其它行 NaN（runner 会 forward fill）
    # 3) 单只权重 ≤ params 中给的 max_single_weight；总和 ≤ 1（若小于 1 表示有现金）
    # 4) 把每个 rebalance_date 的关键中间量（如分位数、阈值、Top 股票）追加到 signal_rows，最后构造成 signal_df

    target = pd.DataFrame(np.nan, index=panels.close_adj.index, columns=panels.close_adj.columns)
    signal_rows: list[dict] = []
    # ... 算法主体 ...
    return SelectionResult(target_weights=target, signal_df=pd.DataFrame(signal_rows))
```

**严禁**导入除以下白名单之外的模块：

- 标准库：`__future__`、`logging`、`math`、`typing`、`dataclasses`
- 第三方：`numpy as np`、`pandas as pd`
- 项目内：`aitrader.research.runner.specs`、`aitrader.research.signals.network`、`aitrader.research.signals.industry`、`aitrader.research.signals.rebalance`

**严禁**使用：`os`、`sys`、`subprocess`、`open(..., "w")`、`exec`、`eval`、`__import__`、`importlib`、网络访问。

## 03_strategy_code.py 强制约束

照搬 few-shot 范例的结构（下面给一份现成的）：

```python
from __future__ import annotations
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aitrader.research.baselines.baseline_spec import BaselineSpec
from aitrader.research.baselines import (
    buy_and_hold_weights,
    momentum_topk_weights,
    equal_weight_universe_weights,
)
from aitrader.research.data.dynamic_universe import UniverseSpec
from aitrader.research.runner import (
    RebalanceSpec,
    StrategySpec,
    TrainHoldoutWindow,
    run_research,
)

from select_fn import select_<slug>  # type: ignore


PAPER_ID = "{paper_id}"
PAPER_TITLE = "<title>"
STRATEGY_NAME = "<中文策略名>"
OUTPUT_DIR = Path(__file__).parent

DEFAULT_PARAMS = {{
    # 你定义的所有 select_fn 参数
}}


def build_spec() -> StrategySpec:
    return StrategySpec(
        paper_id=PAPER_ID,
        paper_title=PAPER_TITLE,
        strategy_name=STRATEGY_NAME,
        methodology="<一句话方法论>",
        universe_spec=UniverseSpec(
            top_n=120, min_data_days=750, min_close=3.0,
            snapshot_window_days=45, refresh_freq="Q",
        ),
        rebalance=RebalanceSpec(freq="W", warmup_days=60, max_single_weight=0.20),
        select_fn=select_<slug>,
        select_params=dict(DEFAULT_PARAMS),
        notes=["<论文要点 1>", "<A 股适配点 1>"],
        param_grid={{
            # 1-3 个最关键的 ablation 维度，组合 ≤ 12
        }},
        train_holdout=TrainHoldoutWindow(),
    )


def main() -> None:
    spec = build_spec()
    baselines = [
        BaselineSpec(name="buy_and_hold_top30", builder=buy_and_hold_weights, kwargs={{"top_n": 30}}),
        BaselineSpec(name="momentum_top15_60d", builder=momentum_topk_weights, kwargs={{"lookback_days": 60, "top_k": 15}}),
        BaselineSpec(name="equal_weight_universe", builder=equal_weight_universe_weights),
    ]
    run_research(spec, output_dir=OUTPUT_DIR, baselines=baselines)


if __name__ == "__main__":
    main()
```

## few-shot 范例（参考结构和写法即可，不要照抄）

### 范例 1 — 偏度分散度择时（select_fn.py）
```python
{example_skew_select_fn}
```

### 范例 2 — 网络中心性选股（select_fn.py）
```python
{example_centrality_select_fn}
```

## 输出要求

输出**两个**用 ` ```python ` 围起来的代码块，**严格按这个顺序**：

1. 第一个代码块 = `select_fn.py` 的完整内容
2. 第二个代码块 = `03_strategy_code.py` 的完整内容

代码块之间不要写额外解释；如果一定要解释，只在两个代码块之前用一两句话。除两个 ```python``` 代码块外不要输出其它围栏。

## 选 slug 的规则

- 用下划线小写，从论文核心方法里取 1-2 个英文单词，例如 `skew_dispersion`、`centrality`、`complexity_gap`、`reversal_lstm`。
- `select_fn` 的函数名必须叫 `select_<slug>`。
- 03_strategy_code.py 里 `from select_fn import select_<slug>` 的 slug 要和函数名完全一致。
