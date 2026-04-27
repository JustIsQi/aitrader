"""分项交易成本模型（佣金 + 印花税 + 过户费 + 滑点 + 最低收费）。"""
from __future__ import annotations

from dataclasses import dataclass


class CostModel:
    """成本模型基类。

    输入：
        ``buy_value`` / ``sell_value``: 当日组合层面的买/卖金额（绝对值，元）。
        ``n_buys`` / ``n_sells``: 当日有买/卖发生的标的个数（用于按笔数收最低佣金）。
    输出：
        当日总成本（元）。
    """

    def cost(
        self,
        *,
        buy_value: float,
        sell_value: float,
        n_buys: int = 1,
        n_sells: int = 1,
    ) -> float:
        raise NotImplementedError


@dataclass
class AshareCostModel(CostModel):
    """A 股标准 V2 成本：佣金 + 印花税 + 过户费 + 可选滑点。

    对应 ``AShareCommissionSchemeV2``：
    - ``brokerage_rate``: 佣金 0.02% 双向
    - ``stamp_duty_rate``: 印花税 0.05% 仅卖出
    - ``transfer_fee_rate``: 过户费 0.001% 双向
    - ``min_commission``: 最低佣金（元，按"每只股票每边"判定）
    - ``slippage_bps``: 双向滑点（基点）
    """

    brokerage_rate: float = 0.0002
    stamp_duty_rate: float = 0.0005
    transfer_fee_rate: float = 0.00001
    min_commission: float = 5.0
    slippage_bps: float = 5.0

    def cost(
        self,
        *,
        buy_value: float,
        sell_value: float,
        n_buys: int = 1,
        n_sells: int = 1,
    ) -> float:
        slippage_rate = max(self.slippage_bps, 0.0) / 10000.0
        buy = max(buy_value, 0.0)
        sell = max(sell_value, 0.0)

        avg_buy = buy / max(n_buys, 1) if buy > 0 else 0.0
        avg_sell = sell / max(n_sells, 1) if sell > 0 else 0.0

        # 每只股票按"max(rate*value, min_commission)"再求和
        if buy > 0 and n_buys > 0:
            per_buy_brokerage = max(avg_buy * self.brokerage_rate, self.min_commission)
            buy_brokerage = per_buy_brokerage * n_buys
        else:
            buy_brokerage = 0.0
        if sell > 0 and n_sells > 0:
            per_sell_brokerage = max(avg_sell * self.brokerage_rate, self.min_commission)
            sell_brokerage = per_sell_brokerage * n_sells
        else:
            sell_brokerage = 0.0

        stamp_duty = sell * self.stamp_duty_rate
        transfer_fee = (buy + sell) * self.transfer_fee_rate
        slippage = (buy + sell) * slippage_rate

        return buy_brokerage + sell_brokerage + stamp_duty + transfer_fee + slippage


class ZeroCostModel(CostModel):
    """零成本模型，用于单元测试。"""

    def cost(
        self,
        *,
        buy_value: float,
        sell_value: float,
        n_buys: int = 1,
        n_sells: int = 1,
    ) -> float:  # noqa: D401
        return 0.0
