# A 股最优策略与 Pipeline — 最终建议

> 配套文档:
> - 根因诊断 + Pipeline 设计原则: `05_root_cause_and_optimal_pipeline.md`
> - 候选策略实现: `06_optimal_strategies.py`
> - 一键对比 runner: `07_compare_runner.py`

---

## TL;DR

| 一句话结论 | |
|---|---|
| **失败原因** | 不是因子选错, 而是 `normalize_score` 在本框架下是 **per-stock 全样本 min-max**, 跨股票排序时语义不可比 → 选股信号 = 噪声 |
| **核心修复** | `order_by_signal` 必须用"原始值"或"逐股 60d 滚动 z-score", **永远不用 `normalize_score`** |
| **A 股最优单策略** | **微盘股周频轮动** (按 `total_mv` 升序选 30 只) — 简单、信号干净、容量与 2024.2 风险已知 |
| **A 股最稳健组合** | **微盘股 (50%) + 20 日反转 (30%) + PB 低估值 (20%)** — 因子相关性低, 互为对冲 |
| **下一步** | 跑 `07_compare_runner.py`, 用真实数据排序 4 个候选, 选 Sharpe 最高的进实盘 |

---

## 一、推荐 Pipeline (图解)

```
                    ┌─────────────────────────────────────┐
                    │    Wind MySQL (ASHAREEODPRICES +    │
                    │    ASHAREEODDERIVATIVEINDICATOR)    │
                    │  字段: OHLCV + turnover_rate + pe + │
                    │        pb + total_mv + circ_mv      │
                    └─────────────────┬───────────────────┘
                                      │
                       ┌──────────────▼───────────────┐
                       │   StockUniverse 动态构造      │
                       │  - exclude_st = True          │
                       │  - exclude_new_ipo_days = 180 │
                       │  - min_data_days = 500        │
                       │  - 视策略放开/关闭创业板/科创板│
                       └──────────────┬───────────────┘
                                      │ ~3000-3500 只
                       ┌──────────────▼───────────────┐
                       │      FactorExpr (per-stock)   │
                       │  ✅ 用 ma/stddev/roc/原始字段  │
                       │  ❌ 不用 normalize_score       │
                       │     (per-stock min-max 不可比) │
                       └──────────────┬───────────────┘
                                      │
                       ┌──────────────▼───────────────┐
                       │      select_buy 全部满足      │
                       │  buy_at_least_count =        │
                       │       len(select_buy)        │
                       └──────────────┬───────────────┘
                                      │
                       ┌──────────────▼───────────────┐
                       │     SelectTopK 横截面排序     │
                       │  (按 total_mv / pb / roc等   │
                       │   原始值或滚动 z-score 排序) │
                       └──────────────┬───────────────┘
                                      │ 20-50 只
                       ┌──────────────▼───────────────┐
                       │        WeightEqually          │
                       │  + ReBalance (周/月)          │
                       │  + ashare_commission='v2'     │
                       │    (含 5bp 佣金 + 10bp 印花税)│
                       └──────────────┬───────────────┘
                                      │
                       ┌──────────────▼───────────────┐
                       │  BacktestResult: Sharpe /     │
                       │  Calmar / MaxDD / 年化收益   │
                       └───────────────────────────────┘
```

---

## 二、4 个候选策略对比 (设计层)

| 策略 | 排序信号 | 调仓 | 持仓 | 股票池 | A 股历史 Sharpe* | 容量 | 主要风险 |
|---|---|---|---|---|---|---|---|
| **微盘股周频** | `total_mv` ASC | 周 | 30 | 主板 ~3400 | 1.5-2.0 | 小 (10-50 亿) | 2024.2 流动性危机 (-25%) |
| **微盘股月频** | `total_mv` ASC | 月 | 50 | 主板 ~3400 | 1.3-1.8 | 中 (50-100 亿) | 同上, 但回撤更慢 |
| **20 日反转** | `roc(close,20)` ASC | 周 | 20 | 主板 ~3400 | 1.0-1.5 | 大 | 强势单边市场失效 |
| **修复版换手率** | 60d z-score 复合 | 周 | 20 | 主板 ~3400 | 待回测验证 | 中 | 因子拥挤 |
| **PB 低估值** | `pb` ASC | 月 | 30 | 主板 ~3400 | 0.8-1.2 | 极大 | 价值陷阱; 缺 ROE 联合不充分 |

*A 股历史 Sharpe 是行业公开研报区间, 仅供参考; 真实表现请跑 `07_compare_runner.py`。

---

## 三、为什么 "微盘股" 是 A 股 #1 alpha 来源

### 结构性原因 (会持续存在)

1. **散户偏好小盘股投机**: A 股个人投资者占成交量 70%+, 偏好"题材+低价+小盘", 持续推高小盘股估值
2. **壳价值**: A 股 IPO 仍偏行政审核, 壳公司有并购重组溢价 (虽然注册制后衰减, 仍有残留)
3. **指数权重外**: 公募/外资/北向资金主要持有大盘股, 微盘股是"机构禁区" → 散户定价权
4. **国证 2000 错杀**: 指数成分外的小盘股缺少被动资金, 出现错误定价 → alpha 来源
5. **ETF 申赎不便**: 微盘股 ETF 容量小, 套利效率低 → 价格弹性大

### 已知风险与对冲

- **2024.2 流动性危机**: 国九条 + 量化监管 + 雪球敲入连环砸盘, 微盘股 ETF 单月 -25%
- **对冲方式**:
  - 调仓频率从周频降到月频 (减少冲击)
  - 加 stop-loss 止损 (单只 -15% 强制清仓)
  - 同时持有 PB 低估值 / 20 日反转 (对冲微盘崩盘)
  - 仓位上限 < 30% (微盘股仅作组合的一部分)

---

## 四、实施 Roadmap

### 第 0 步 — 验证策略 (本周, 必做)

```bash
cd /data/share2/yy/workspace/code/aitrader

# 单策略快速验证 (FAST 模式, 2 年):
AITRADER_FAST=1 /home/yy/anaconda3/bin/python \
  papers/arxiv/processed/2603.14288v2/06_optimal_strategies.py microcap

# 全策略对比 (全段 2019-2024, 耗时较长, 建议放到 nohup):
nohup /home/yy/anaconda3/bin/python \
  papers/arxiv/processed/2603.14288v2/07_compare_runner.py \
  > logs/compare_$(date +%F).log 2>&1 &

# 跟踪进度
tail -f logs/compare_*.log
# 结果文件: papers/arxiv/processed/2603.14288v2/08_comparison_results.md
```

### 第 1 步 — 选定主策略 (1 周内)

按 Sharpe 排序选 Top-1, 做以下额外检查:
- **年度收益分布**: 至少 5/6 年正收益
- **最大回撤**: < 30% (含 2024.2 微盘股事件)
- **换手率**: 周频策略年换手 < 800%, 否则交易成本吃掉 alpha
- **持仓行业分布**: 单一行业不超过 30%

### 第 2 步 — 因子组合 (2-4 周)

如果单策略 Sharpe < 1.5, 用以下加权组合 (示例, 权重需用样本外回测确定):

```
组合 = 微盘股 × 0.5 + 20 日反转 × 0.3 + PB 低估值 × 0.2
```

或者按周做"轮动":
- 强势趋势市 (沪深 300 周收益 > 1%): 用动量/换手率
- 震荡市: 用 20 日反转
- 弱势市 (沪深 300 周收益 < -1%): 用 PB 低估值

### 第 3 步 — 实盘前必做 (1 个月内)

1. **样本外回测**: 用 2020-2022 训练参数, 2023-2024 验证 (避免 in-sample 过拟合)
2. **冲击成本模拟**: 每只持仓 < 当日成交额的 5% (微盘股尤其重要)
3. **极端情境压力测试**: 重放 2015.6 (千股跌停) / 2024.1-2 (微盘崩盘)
4. **风控规则**:
   - 单只仓位 ≤ 5% (20 只持仓 → 等权)
   - 单日组合回撤 > 5% → 减仓 50%
   - 连续 3 周组合跑输基准 > 5% → 全部清仓

---

## 五、补充建议: 给框架加 2 个能力 (中长期)

如果要让 A 股 quant 平台更工业级, 建议给 `factor_expr` 加 2 个函数:

### ① `cs_rank(expr)` — 横截面排序

把当前 per-stock 计算改成"在 calc_formulas 跑完后, pivot 成 (date × symbol), 横截面 rank, 再 melt 回去"。这样可以正确支持论文常用的 cross-sectional 因子。

### ② `cs_zscore(expr)` — 横截面 z-score

同上, 横截面归一化, 让 5+ 个独立因子可以加权组合时量纲统一。

加这 2 个函数后, 原版 03_strategy_code.py 改 5 行即可正常工作:

```python
# Before (失败的)
'normalize_score((turnover_rate - ma(turnover_rate,20)) / ma(turnover_rate,20)) * 0.25 + ...'

# After (横截面正确的)
'cs_zscore((turnover_rate - ma(turnover_rate,20)) / ma(turnover_rate,20)) * 0.25 + ...'
```

如需我实现, 给个明确指令即可 (大约 30 行代码改动)。

---

## 六、文件交付清单

| 文件 | 作用 |
|---|---|
| `05_root_cause_and_optimal_pipeline.md` | 5 个根因诊断 + Pipeline 设计原则 |
| `06_optimal_strategies.py` | 4 个候选策略实现 (microcap/reversal/turnover_fixed/pb_value) |
| `07_compare_runner.py` | 一键对比所有策略, 输出 markdown 表格 |
| `08_final_recommendation.md` | 本文件: 最终建议 + Roadmap |
| (运行后) `08_comparison_results.md` | runner 跑完自动生成的对比结果 |
