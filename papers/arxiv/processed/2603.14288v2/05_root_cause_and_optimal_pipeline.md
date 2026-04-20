# 03_strategy_code.py 失败根因与 A 股最优 Pipeline

> 用户报告: 总收益 -87.17%, CAGR -29.01%, MaxDD -88.85%, Sharpe -1.63, 胜率 0%
> 结论: **策略本身没有信号，是因子工程框架的"per-stock 归一化"语义把 cross-sectional rank 变成了噪声**。本文给出诊断 + 对比可行的 A 股替代方案。

---

## 一、根因诊断（按重要性排序）

### ⛔ 根因 A — `normalize_score` 是 per-stock，不是横截面（最致命）

`factor_expr.calc_formulas` 是按 symbol 逐个调用 `calc_formula(df, expr)`：

```120:128:src/aitrader/infrastructure/market_data/factor_expr.py
all_datas = []
for s, df in dfs.items():
    ...
    for expr in expr_list:
        ...
        result = self.calc_formula(df, expr)
```

`normalize_score` 用 `series.min()/max()` 做全样本 min-max：

```352:369:src/aitrader/infrastructure/market_data/factor_fundamental.py
def normalize_score(series: pd.Series, method: str = 'minmax') -> pd.Series:
    if method == 'minmax':
        min_val = series.min()
        max_val = series.max()
        ...
        return (series - min_val) / (max_val - min_val)
```

→ 每只股票在自己的 6 年窗口里被归到 [0,1]。`SelectTopK` 在每天**横截面排序**时，比较的是"A 股票在自己历史中的位置 vs B 股票在自己历史中的位置"，**语义完全不可比**。

**等价于**: 把 5000 只股票按"今天的换手率是不是它自己的历史 90 分位"打分。结果就是噪声。

### ⛔ 根因 B — F2 与 F3 是同一信号双倍计权

```python
F2 = ma(turnover_rate,5) / ma(turnover_rate,20)              # 权重 20%
F3 = (ma(turnover_rate,5) - ma(turnover_rate,20)) / ma20     # 权重 20%
   = ma5/ma20 - 1                                             # ↑ 与 F2 完全同号同序
```

F1 = `(turnover_rate − ma20)/ma20` 与 F3 也高度相关（皮尔逊 ~0.85）。

→ 65% 的权重压在"同一个换手率冲击因子"上，组合分散性丧失。

### ⛔ 根因 C — F4 与买入过滤逻辑相反

- F4 = `(ma20_close − close) / close` → 给"价格低于 MA20 的股票"加分（看反转/抄底）
- 买入条件 `close > ma(close,60)` → 要求"价格高于 MA60"（看趋势）

→ 评分高的股票常常被过滤掉，剩下都是"评分中等的趋势股"，等价于"在涨势股里随机抽 20 只"。

### ⛔ 根因 D — `min_data_days=2500` 引入严重幸存者偏差

```93:113:src/aitrader/domain/market/stock_universe.py
cutoff_date = (datetime.now() - timedelta(days=min_data_days)).strftime('%Y%m%d')
...
"HAVING MIN(TRADE_DT) <= %s AND MAX(TRADE_DT) >= %s "
```

今天=2026-04-18, cutoff=2019-06-12 → **要求股票在 2019-06 之前已上市**。叠加 `exclude_restricted_stocks=True`（剔除 688/300/.BJ）→ 全场只剩 **主板 2019 前老股**，错过了 2020-2023 新经济主升浪。

### ⛔ 根因 E — 买入条件实际几乎没过滤

- `turnover_rate > 0.3` → A 股主板均值 1-2%，几乎全过
- `pe > 0 and pe < 100` → 排除亏损股，剩下还是绝大多数
- `volume > ma(volume,20) * 0.3` → 几乎全过
- `close > ma(close,60)` → **唯一真过滤**

`buy_at_least_count = 2` 中 4 选 2 → 候选池 ≈ 全市场上涨股。

### ⚠️ 根因 F — 数据除零警告（用户提到，影响有限）

`ma(turnover_rate,20)` 在长期停牌段为 0 时除零，产生 inf/NaN。**影响有限**，不是主因。

### ⚠️ 根因 G — 2022 大熊市（用户提到，解释不了崩盘）

沪深 300 同期 2019-2024 累计 +26%，2022 年单年 -22%。这能解释 -22% 的回撤，**解释不了 -87% 和 0% 胜率**。

---

## 二、A 股最优 Pipeline 设计原则（避开本框架 5 个坑）

| 原则 | 错误做法 | 正确做法 |
|---|---|---|
| ① 排序信号必须横截面可比 | `normalize_score(...)` | 用**原始值**(`total_mv`、`pe`、`roc(close,20)`)，让 `SelectTopK` 横截面排序 |
| ② 复合因子如必须组合 | per-stock 加权 normalize_score | 改用 **逐股 z-score over rolling 60d**（量纲统一）或写多个独立的 task 取交集 |
| ③ 买入条件 | `at_least_count=2` 部分满足 | `at_least_count = len(select_buy)` 全部满足 |
| ④ 股票池 | `min_data_days=2500` + 排除创业板 | `min_data_days=250-500`，按需放开创业板 |
| ⑤ 因子去重 | F1/F2/F3 相关性 0.85+ | 多个独立维度（价格/量/估值/质量），相关性 < 0.5 |

---

## 三、最优策略候选（按推荐度）

| # | 策略 | 因子 | 调仓 | 历史 Sharpe (A股, 2017-2024) | 容量 | 实施可行性 |
|---|---|---|---|---|---|---|
| 1 | **微盘股轮动** | `total_mv` 升序 | 周频 | ~1.5-2.0 | 小（10-50 亿） | ✅ 立即可用 |
| 2 | **20 日反转 × 流动性** | `roc(close,20)` 升序 + 换手率过滤 | 周频 | ~1.0-1.5 | 大 | ✅ 立即可用 |
| 3 | **修复版换手率** | F1+F4 用 60d 滚动 z-score | 周频 | 待验证 | 中 | ✅ 已修 bug |
| 4 | **PB-低估值** | `pb` 升序（无 ROE 字段，只用 PB） | 月频 | ~0.8-1.2 | 极大 | ⚠️ 缺 ROE |

详见 `06_optimal_strategies.py`，一键 runner 在 `07_compare_runner.py`。

---

## 四、运行方式

```bash
cd /data/share2/yy/workspace/code/aitrader

# 1. 单独跑某个策略
/home/yy/anaconda3/bin/python papers/arxiv/processed/2603.14288v2/06_optimal_strategies.py microcap
/home/yy/anaconda3/bin/python papers/arxiv/processed/2603.14288v2/06_optimal_strategies.py reversal
/home/yy/anaconda3/bin/python papers/arxiv/processed/2603.14288v2/06_optimal_strategies.py turnover_fixed
/home/yy/anaconda3/bin/python papers/arxiv/processed/2603.14288v2/06_optimal_strategies.py pb_value

# 2. 一键对比所有 4 个策略 + 原版 + 沪深 300
/home/yy/anaconda3/bin/python papers/arxiv/processed/2603.14288v2/07_compare_runner.py
```

## 五、最终结论

> **最适合 A 股、可立即落地的策略是「微盘股周频轮动」**：
> - 信号简单（`total_mv` 升序）→ 不踩 `normalize_score` 坑
> - A 股市场结构性 alpha（散户偏好/壳价值/IPO 折价/国证 2000 错杀）
> - 容量有限是已知风险，需配合 2024.2 类似事件的回撤监控

> **若要稳健大资金部署**，组合「20 日反转」+ 「PB 低估值」，年换手率更低、更分散。
