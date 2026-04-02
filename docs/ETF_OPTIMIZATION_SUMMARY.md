# ETF模块优化总结

## 本次优化概览（2026-02-23）

针对选股逻辑、调仓规则、风控机制的全面审查与优化，共涉及8个文件。

---

## 后续补充（2026-03-23）

本轮又补了三类底层能力，使用上需要注意：

1. **CLI 无破坏性变化**
   - `run_etf_portfolio_backtest.py`、`run_ashare_signals.py` 的命令行用法保持不变

2. **ETF 组合回测新增组合级风险控制字段**
   - 已落到 `core/portfolio_bt_engine.py`
   - 适用于 `PortfolioTask` 和基于它的 ETF 组合策略
   - 新增能力包括：
     - `target_annual_vol`
     - `max_total_weight`
     - `enable_cash_refill`
     - `risk_multiplier_min` / `risk_multiplier_max`
     - `risk_off_drawdown_trigger` / `risk_off_drawdown_exit`
     - `risk_off_vol_trigger` / `risk_off_vol_exit`
     - `risk_off_daily_loss_trigger` / `risk_off_daily_loss_exit`
     - `risk_off_multiplier`

3. **风险平价策略已接入新的组合级风控**
   - 文件：`strategies/etf_risk_parity.py`
   - 新增逻辑：
     - 目标波动率缩放
     - risk-off 进入/退出
     - 现金回填
     - 先卖后买的再平衡顺序

4. **组合日结果模型已标准化**
   - 新文件：`core/portfolio_daily_result.py`
   - `portfolio_tracker` / `portfolio_metrics` 已可输出更结构化的 `daily_df` / `equity_curve`

如果你是通过 Python API 自定义 ETF 组合任务，建议优先使用新的 `PortfolioTask` 风控字段；如果你只是走 CLI，通常不需要修改现有调用方式。

---

## P0 Bug修复

### 1. `enable_rsi_oversold` 配置不一致
- **文件**: `short_term_config/short_term_config.py`
- **问题**: Python默认值 `False`，JSON为 `true`，直接实例化时行为不符预期
- **修复**: Python默认值改为 `True`，与生产JSON一致

### 2. 止损历史数据校验不足
- **文件**: `core/position_manager.py`
- **问题**: 仅检查 `len(df) < 2`，MA5需要至少5条数据，不足时静默失效
- **修复**: 数据不足时输出具体条数警告，MA5不足时明确提示退化为百分比止损

### 3. 配置校验逻辑补全
- **文件**: `short_term_config/short_term_config.py`
- **修复**: `validate()` 补充 `sector_rank_3_5_position > max_stock_position` 的检查

---

## P1 风控增强

### 1. ATR自适应止损（替代固定3%止损）
- **文件**: `core/position_manager.py`
- **问题**: 固定-3%止损，低波动品种止损过宽，高波动品种止损过窄
- **改动**:
  - `StopLossConfig` 新增 `use_atr_stop/atr_multiplier(2.0)/atr_period(14)/max_loss_pct(-10%)`
  - 止损 = `max(百分比止损, MA5止损, ATR×2止损)`，取最不激进的
  - 10%为绝对底线（`max_loss_pct`）
  - 新增 `_calculate_atr()` 方法，查询窗口从20天扩大到30天以支持ATR

### 2. ATR止盈（震荡市适配）
- **文件**: `core/position_manager.py`
- **问题**: `max(10日高点, +10%)` 在震荡市中止盈目标可能永远无法触及
- **改动**:
  - `TakeProfitConfig` 新增 `use_atr_tp/atr_tp_multiplier(3.0)`
  - 止盈 = `min(原始逻辑, ATR×3止盈)`，取更保守的
  - `enable_gradient` 默认改为 `True`（梯度止盈默认开启）

### 3. 组合级风险预算
- **文件**: `core/position_manager.py`
- **改动**:
  - 新增 `PortfolioRiskConfig`（最大回撤15%，10%开始减仓至50%）
  - 新增 `get_position_scale_factor(current_value, peak_value)` 方法
  - `generate_trading_plans()` 新增可选参数，触发组合风控时暂停开仓

### 4. 多策略轮动防抖动
- **文件**: `strategies/etf_multi_strategy_rotation.py`
- **问题**: 市场环境判断可逐日翻转，导致频繁换手
- **改动**:
  - `MarketRegimeDetector` 新增 `_regime_history` 缓存，连续3次确认才切换环境
  - `_should_rebalance_dynamic()` 新增最小5日再平衡间隔

---

## P2 选股质量提升

### 1. 动量因子 `trend_score` 加界限
- **文件**: `core/multi_factor_etf_filter.py`
- **问题**: `trend_score * 50` 无上界，可主导整个动量评分
- **修复**: `np.clip(trend_score, -0.2, 0.2) * 50`，最大贡献±10，与ROC项量级一致

### 2. Sharpe估计改进
- **文件**: `core/multi_factor_etf_filter.py`
- **问题**: 未减去无风险利率，未年化
- **修复**: 年化收益/年化波动，扣除2.5%无风险利率，结果限制在[-3, 3]

### 3. ETF相关性过滤
- **文件**: `core/multi_factor_etf_filter.py`
- **改动**:
  - `MultiFactorConfig` 新增 `max_correlation: float = 0.85`
  - 新增 `_apply_correlation_filter()` 方法，在评分排名后、截取top_count前执行
  - 逐一选入ETF，与已选集合中任一相关系数 > 0.85 则跳过

### 4. 双动量交易日修正
- **文件**: `strategies/etf_dual_momentum.py`
- **问题**: 硬编码每月21个交易日，A股实际约20天
- **修复**: 定义常量 `A_SHARE_TRADING_DAYS_PER_MONTH = 20`

### 5. 风险平价波动率自适应
- **文件**: `strategies/etf_risk_parity.py`
- **问题**: 固定60日滚动窗口，极端行情后反应迟钝
- **修复**: EWMA×0.7 + 滚动×0.3 混合波动率，对近期波动赋予更高权重
- `RiskParityConfig` 新增 `use_ewm_volatility: bool = True`

---

## P3 代码质量

### 涨停阈值可配置化
- **文件**: `core/stock_selector.py`、`short_term_config/short_term_config.py`
- **改动**: 硬编码 `9.5%` 改为 `ChaseStrategyConfig.limit_up_threshold`（默认9.5%，创业板/科创板可调至19.5%）

---

## 配置文件变更（`short_term_config.json`）

新增字段：

```json
"chase": {
  "limit_up_threshold": 9.5
},
"stop_loss": {
  "use_atr_stop": true,
  "atr_multiplier": 2.0,
  "atr_period": 14,
  "max_loss_pct": -0.10
},
"take_profit": {
  "enable_gradient": true,
  "use_atr_tp": true,
  "atr_tp_multiplier": 3.0
}
```

---

## 涉及文件清单

| 文件 | 改动类型 |
|------|---------|
| `core/position_manager.py` | ATR止损/止盈、组合风控、数据校验 |
| `core/multi_factor_etf_filter.py` | trend_score界限、Sharpe改进、相关性过滤 |
| `core/stock_selector.py` | 涨停阈值可配置 |
| `short_term_config/short_term_config.py` | 配置默认值对齐、校验补全、新字段 |
| `short_term_config/short_term_config.json` | 同步新增字段 |
| `strategies/etf_multi_strategy_rotation.py` | 防抖动机制、最小再平衡间隔 |
| `strategies/etf_dual_momentum.py` | 交易日常量修正 |
| `strategies/etf_risk_parity.py` | EWMA自适应波动率 |

---

## 注意事项

1. `generate_trading_plans()` 新增可选参数 `current_value/peak_value`，不传则组合风控不生效（向后兼容）
2. ATR止损/止盈需要 `StockHistoryQfq` 表有 `high/low` 列
3. ETF相关性过滤会减少最终筛选数量，池子较小时可适当调高 `max_correlation` 阈值（如0.92）
4. 风险平价 `use_ewm_volatility` 默认开启，如需复现旧结果可设为 `False`
