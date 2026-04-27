# ArXiv Quant - A 股研究框架

- 处理日期：2026-04-22（本轮 2026-04-23 框架升级）
- 数据来源：`Wind MySQL 直读`
- 研究窗口：`2019-01-01` 至 `2024-12-31`
- 框架代码沉到 `src/aitrader/research/`，本目录仅保留每篇论文的 `select_fn` 与配置

## 1. 目录结构

```text
papers/arxiv/processed/
├── README.md                     # 本文件
├── _aggregate/
│   └── cross_paper_comparison.md # 跨论文汇总（自动生成）
├── _cache/                       # PanelLoader parquet 缓存
├── common/
│   └── ashare_research_utils.py  # 向后兼容薄层 → aitrader.research.*
├── 2604.07870/                   # 偏度分散度月频择时
│   ├── 01_applicability_judgment.md
│   ├── 02_parsed_content.md
│   ├── 03_strategy_code.py       # 入口（瘦身后约 60 行：声明 spec + run_research）
│   ├── 04_backtest_summary.md    # 自动生成的回测摘要
│   ├── select_fn.py              # 策略信号函数
│   ├── equity_curve.csv
│   ├── daily_returns.csv
│   ├── holdings.csv
│   ├── invested_exposure.csv
│   ├── rebalance_log.csv
│   ├── signals.csv
│   ├── ablation_train.csv
│   ├── ablation_holdout.csv
│   ├── baseline_*_equity_curve.csv
│   ├── equity_drawdown.png
│   ├── meta.json                 # 给 aggregator 用
│   ├── performance.json
│   ├── performance_train.json
│   ├── performance_holdout.json
│   └── baselines_metrics.json
├── 2604.12197/                   # 网络中心性选股
└── 2604.19107/                   # 复杂度缺口风控
```

## 2. 入选论文（与原始 arXiv ID 一一对应）

| 论文ID | 标题 | A股映射 |
|---|---|---|
| `2604.07870` | Skewness Dispersion and Stock Market Returns | 偏度分散度月频择时 |
| `2604.12197` | Emergence of Statistical Financial Factors by a Diffusion Process | 收益相关网络中心性选股 |
| `2604.19107` | Structural Dynamics of G5 Stock Markets ... Complexity Gap Approach | 复杂度缺口风控开关 |

## 3. 复现单篇

```bash
cd papers/arxiv/processed/2604.12197
PYTHONPATH=/data/datavol/yy/code/aitrader/src python 03_strategy_code.py
```

每篇会产出上节"目录结构"里列出的全部 csv / json / png / md 产物。所有论文的
工程化部分（动态选池、向量化回测、绩效统计、基线、ablation）由
`aitrader.research.runner.run_research` 统一负责，每篇论文文件只需声明：

- `select_fn`：把价格面板 + 调仓日 → `SelectionResult(target_weights, signal_df)`；
- `param_grid`：要做的 grid ablation 维度（每篇 ≤ 36 组合）；
- `train_holdout`：默认 train=2019-2021、holdout=2022-2024；
- `param_grid_filter`：可选的参数组合过滤函数（例如保证 `risk_on_q < risk_off_q`）。

## 4. 跨论文汇总

跑完所有论文之后：

```bash
PYTHONPATH=/data/datavol/yy/code/aitrader/src \
  python -c "from aitrader.research.runner import aggregate_processed; \
             aggregate_processed('papers/arxiv/processed')"
```

会自动扫描每个论文目录里的 `meta.json` / `performance.json` /
`performance_train.json` / `performance_holdout.json` / `baselines_metrics.json`，
重新生成 `_aggregate/cross_paper_comparison.md`。

## 5. 框架修复点对照（本轮 20 项原问题 → 落点）

| # | 问题 | 修复落点 |
|---|---|---|
| 1 | look-ahead 股票池 | `research/data/dynamic_universe.py` 按 as_of 滚动选池 |
| 2 | T+1 时序泄漏 | `research/engine/vectorized_simulator.py` 统一 `target.shift(1)` |
| 3 | 复杂度缺口 O(T²) | `papers/.../2604.19107/select_fn.py` 只在 rebalance 点算 |
| 4 | 特征向量物理含义混淆 | `research/signals/network.py` 拆 `eigenvector_centrality(perron)` 与 `pca_leading_factor` |
| 5 | 隐性过拟合 | `research/runner/{splitter, grid_ablation}.py` train+holdout |
| 6 | 二元开关丢信号 | `research/engine/position_policies.py` 提供 tiered / signal_weighted |
| 7 | 池子口径不一致 | `DynamicLiquidUniverse.union_symbols()` 统一池子 |
| 8 | 行业 / 风格中性化缺失 | `research/signals/industry.py` + 论文 12197 配置项 |
| 9 | 开关与多头耦合 | 论文 19107 拆 risk_position × holding_basket |
| 10 | 偏度截面只有 30 只 | 论文 07870 信号池（500）/ 持仓池（30）解耦 |
| 11 | 空仓零收益 | `cash_rate_annual` 进 simulator |
| 12 | 交易成本粗糙 | `research/engine/cost_model.py:AshareCostModel` 拆佣金 / 印花税 / 过户 / 滑点，按笔数计最低佣金 |
| 13 | 涨跌停 / 停牌过滤 | `research/data/tradability_mask.py` + simulator 在调仓日回退 |
| 14 | 风险 / 绩效指标不全 | `research/metrics/performance.py:PerformanceReport` 含 alpha/beta/IR/Sortino/VaR/CVaR/Calmar/分年 |
| 15 | 基准没进代码 | `research/baselines/{buy_and_hold, momentum_topk, equal_weight_universe}` |
| 16 | 三脚本重复 | 统一 runner，`03_strategy_code.py` 瘦身 |
| 17 | 缓存只在内存 | `PanelLoader` 持久化 parquet 到 `_cache/` |
| 18 | 产物太单薄 | 自动生成 csv / md / png / json 全套 |
| 19 | 没 logging / 测试 | `research.<paper>` logger + `tests/research/` 29 个用例 |
| 20 | ddof / off-by-one | `_safe_std(ddof=1)`、Sharpe 扣无风险利率、`tradability` NaN 防御 |

## 6. 备注

- 旧入口（`pick_liquid_symbols` / `read_price_history` / `simulate_equal_weight_strategy` 等）已被
  `papers/arxiv/processed/common/ashare_research_utils.py` 收敛成 `DeprecationWarning` 薄层，
  仅做向后兼容，请尽快迁移到 `aitrader.research.*`。
- 因为修复了 T+1、加了涨跌停、加了现金利率、改了分项成本，三篇论文的
  数值会与上一轮的"粗回测"明显不同，旧 README 里的总收益数字不再有效，
  请以 `cross_paper_comparison.md` 与每篇论文目录下的 `04_backtest_summary.md` 为准。
- 本轮股票池仍是高流动性主板样本，但已改为按 as_of 季度刷新，幸存者偏差已显著减弱。
