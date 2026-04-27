# 回测摘要：复杂度缺口风控（rebalance 点计算 + 风控/多头解耦）

- 论文ID: `2604.19107`
- 论文标题: Structural Dynamics of G5 Stock Markets During Exogenous Shocks: A Random Matrix Theory-Based Complexity Gap Approach
- 方法映射: 60 日相关矩阵复杂度缺口（仅 rebalance 点计算）→ 多档风控仓位 → 60 日动量 Top-15

## 核心指标（Holdout / 全期）

| 指标 | 数值 |
|---|---:|
| 总收益 | +23.50% |
| 复合年化收益 | +14.71% |
| 波动率 | +6.56% |
| 夏普比率 | 1.886 |
| Sortino | 1.276 |
| Calmar | 9.795 |
| 最大回撤 | -1.50% |
| 最大回撤起 | 2026-04-20 |
| 最大回撤止 | 2026-04-21 |
| 回撤恢复天数 | 1 |
| VaR(95) | +0.01% |
| CVaR(95) | -0.00% |
| alpha (年化) | +11.72% |
| beta | 0.057 |
| 信息比率 | 0.037 |
| 跟踪误差 | +20.87% |
| 胜率 (vs 基准) | +37.77% |
| 年化换手 | 0.849 |
| 平均持仓周期(日) | 296.842 |
| 交易次数 | 5 |
| 平均持仓数 | 14.471 |
| 最大持仓数 | 16 |
| 持仓天数占比 | +4.52% |
| 2024 年收益 | +0.48% |
| 2025 年收益 | +1.93% |
| 2026 年收益 | +20.59% |

## vs 基线

| 策略 | 总收益 | 年化 | 夏普 | Sortino | 最大回撤 | Calmar |
|---|---:|---:|---:|---:|---:|---:|
| 策略 | +23.50% | +14.71% | 1.89 | 1.28 | -1.50% | 9.80 |
| buy_and_hold_top30 | +1.65% | +1.07% | 0.08 | 0.10 | -23.16% | 0.05 |
| momentum_top15_60d | -20.32% | -13.72% | -0.29 | -0.35 | -38.51% | -0.36 |
| equal_weight_universe | +18.48% | +11.65% | 0.55 | 0.64 | -20.65% | 0.56 |

## Train(2019-2021) vs Holdout(2022-2024)

| 策略 | 总收益 | 年化 | 夏普 | Sortino | 最大回撤 | Calmar |
|---|---:|---:|---:|---:|---:|---:|
| 全期 | +23.50% | +14.71% | 1.89 | 1.28 | -1.50% | 9.80 |
| Train(2019-2021) | +2.07% | +1.95% | NA | NA | +0.00% | NA |
| Holdout(2022-2024) | +21.00% | +50.25% | 3.46 | 4.17 | -1.50% | 33.47 |

## Grid Ablation Top-5（按 train sharpe 排序）

| score | train_total_return | train_cagr | train_sharpe | train_max_drawdown | train_calmar | gap_window | risk_off_q | risk_on_q |
|---|---|---|---|---|---|---|---|---|
| -1000000000.00 | 0.0207 | 0.0195 | NA | 0.0000 | NA | 60.0000 | 0.2000 | 0.5500 |
| -1000000000.00 | 0.0207 | 0.0195 | NA | 0.0000 | NA | 60.0000 | 0.2000 | 0.7000 |
| -1000000000.00 | 0.0207 | 0.0195 | NA | 0.0000 | NA | 60.0000 | 0.3500 | 0.5500 |
| -1000000000.00 | 0.0207 | 0.0195 | NA | 0.0000 | NA | 60.0000 | 0.3500 | 0.7000 |
| -1000000000.00 | 0.0207 | 0.0195 | NA | 0.0000 | NA | 120.00 | 0.2000 | 0.5500 |

## 结论

- 论文结论：复杂度缺口在外生冲击期会塌缩，预示组合波动。
- 本次实现：风控开关与多头篮子解耦；缺口仅在调仓日算，复杂度从 O(T²) 降到 O(T)。
- 已修复：look-ahead 选池 / O(T²) 计算 / 二元开关 / T+1 / 涨跌停 / 现金利率。

## 产物清单

- `equity_curve.csv`
- `daily_returns.csv`
- `holdings.csv`
- `invested_exposure.csv`
- `rebalance_log.csv`
- `equity_drawdown.png`
- `signals.csv`
- `ablation_train.csv`
- `ablation_holdout.csv`
- `baseline_buy_and_hold_top30_equity_curve.csv`
- `baseline_momentum_top15_60d_equity_curve.csv`
- `baseline_equal_weight_universe_equity_curve.csv`

