# 策略模式与字段约定

## `Task` 的核心字段

- `name`
  - 策略显示名
- `symbols`
  - 标的列表，格式如 `000001.SZ`、`600000.SH`、`510300.SH`
- `start_date` / `end_date`
  - 回测区间，建议用 `YYYYMMDD`
- `select_buy`
  - 买入条件表达式列表
- `buy_at_least_count`
  - 至少满足多少个买入条件；小于等于 0 时，等价于“全部满足”
- `select_sell`
  - 卖出条件表达式列表
- `sell_at_least_count`
  - 至少满足多少个卖出条件；默认常见语义是“满足一个就卖”
- `order_by_signal`
  - 排序因子表达式
- `order_by_topK`
  - 选前 K 个
- `order_by_dropN`
  - 排序后丢弃前 N 个
- `order_by_DESC`
  - 是否降序
- `weight`
  - 常见值是 `WeightEqually` 或 `WeightFix`
- `weight_fixed`
  - 固定权重字典
- `period`
  - 常见值是 `RunDaily`、`RunWeekly`、`RunEveryNPeriods`
- `period_days`
  - `RunEveryNPeriods` 时使用
- `ashare_mode`
  - 是否启用 A股交易约束
- `ashare_commission`
  - 手续费方案，通常用 `v2`
- `adjust_type`
  - `qfq` 前复权或 `hfq` 后复权

## 推荐的策略函数形态

策略函数应该只做一件事：返回一个配置好的 `Task`。

```python
from core.backtrader_engine import Task

def momentum_strategy_weekly():
    t = Task()
    t.name = "A股动量周频"
    t.symbols = ["000001.SZ", "600000.SH", "600036.SH"]
    t.start_date = "20200101"
    t.end_date = "20231231"
    t.select_buy = ["roc(close,20) > 0.05", "volume > ma(volume,20)"]
    t.buy_at_least_count = 2
    t.select_sell = ["roc(close,20) < 0"]
    t.order_by_signal = "roc(close,20)"
    t.order_by_topK = 2
    t.period = "RunWeekly"
    t.weight = "WeightEqually"
    t.ashare_mode = True
    t.ashare_commission = "v2"
    return t
```

## 因子表达式风格

AITrader 倾向在配置里直接写表达式，而不是为每个条件单独写 Python 逻辑。常见写法：

- `roc(close,20) > 0.05`
- `close > ma(close,60)`
- `volume > ma(volume,20) * 1.2`
- `roc(close,20) * 0.6 + trend_score(close,25) * 0.4`

只有当表达式体系无法覆盖时，才考虑扩展因子函数。

## A股策略发现约定

`run_ashare_signals.py` 依赖 `core/strategy_loader.py` 自动发现策略，默认约束是：

- 文件名匹配 `strategies/stocks_*.py`
- 函数名通常以这些前缀开头：
  - `multi_factor_`
  - `momentum_`
  - `value_`
  - `quality_`
  - `low_vol_`
- 函数调用后必须返回 `Task`
- `Task.ashare_mode` 必须为 `True`

如果改了这些约定，要一起改 `StrategyLoader`，否则信号脚本会漏策略。

## ETF 与 A股的区分

- ETF 轮动策略通常不启用 `ashare_mode`
- A股个股策略通常启用 `ashare_mode=True`
- 如果目标策略包含 T+1、涨跌停、100 股整数手这些约束，按 A股处理

## 迁移到别的仓库时建议保留的约定

- 保留“策略函数返回 `Task`”这一层，方便策略可枚举、可测试、可批量运行
- 保留声明式条件和排序字段，避免执行器和策略强耦合
- 保留策略发现约定，或改成明确的注册表，但不要一半自动发现、一半手写脚本
