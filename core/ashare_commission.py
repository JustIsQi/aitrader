"""
A股手续费方案

实现A股真实的交易费用结构:
1. 佣金: 0.02% (双向), 最低5元
2. 印花税: 0.03% (仅卖出)
3. 过户费: 0.001% (仅上海市场)
"""

import backtrader as bt
from loguru import logger


class AShareCommissionScheme(bt.CommInfoBase):
    """
    A股真实手续费方案

    费用结构:
    - 佣金(Brokerage): 万分之2.5(0.025%), 双向收取, 最低5元
    - 印花税(Stamp Duty): 千分之1(0.1%), 仅卖出收取
    - 过户费(Transfer Fee): 万分之0.1(0.001%), 仅上海市场双向收取

    注: 2015年后A股印花税调整为0.1%(卖出)
    2023年进一步降低,但这里使用较保守的费率
    """

    params = (
        ('brokerage_rate', 0.00025),    # 佣金0.025% (万2.5)
        ('stamp_duty_rate', 0.001),     # 印花税0.1% (千1, 仅卖出)
        ('transfer_fee_rate', 0.00001), # 过户费0.001% (万0.1, 仅上海)
        ('min_commission', 5.0),        # 最低佣金5元
    )

    def _getcommission(self, size: float, price: float) -> float:
        """
        计算总手续费

        Args:
            size: 成交数量(股数,正数为买入,负数为卖出)
            price: 成交价格

        Returns:
            float: 总手续费
        """
        # 计算成交金额
        value = abs(size) * price

        # 1. 佣金(双向)
        brokerage = value * self.p.brokerage_rate
        brokerage = max(brokerage, self.p.min_commission)

        # 2. 印花税(仅卖出)
        stamp_duty = 0.0
        if size < 0:  # 卖出
            stamp_duty = value * self.p.stamp_duty_rate

        # 3. 过户费(仅上海市场,这里简化为双向收取)
        # 实际应用中可以根据股票代码判断是否为上海市场
        transfer_fee = value * self.p.transfer_fee_rate

        # 总手续费
        total_commission = brokerage + stamp_duty + transfer_fee

        logger.debug(f"手续费计算: 金额={value:.2f}, 佣金={brokerage:.2f}, "
                    f"印花税={stamp_duty:.2f}, 过户费={transfer_fee:.2f}, "
                    f"总计={total_commission:.2f}")

        return total_commission


class AShareCommissionSchemeV2(bt.CommInfoBase):
    """
    A股手续费方案 V2 (2023年后新费率)

    费用结构(2023年8月降费后):
    - 佣金: 0.02% (万2), 双向, 最低5元
    - 印花税: 0.05% (万5), 仅卖出 (2023年8月28日从0.1%降至0.05%)
    - 过户费: 0.001% (万0.1), 仅上海, 双向
    """

    params = (
        ('brokerage_rate', 0.0002),     # 佣金0.02% (万2)
        ('stamp_duty_rate', 0.0005),    # 印花税0.05% (万5, 仅卖出)
        ('transfer_fee_rate', 0.00001), # 过户费0.001% (万0.1, 仅上海)
        ('min_commission', 5.0),        # 最低佣金5元
    )

    def _getcommission(self, size: float, price: float) -> float:
        """
        计算总手续费(2023年后新费率)

        Args:
            size: 成交数量
            price: 成交价格

        Returns:
            float: 总手续费
        """
        value = abs(size) * price

        # 佣金
        brokerage = max(value * self.p.brokerage_rate, self.p.min_commission)

        # 印花税(仅卖出)
        stamp_duty = value * self.p.stamp_duty_rate if size < 0 else 0.0

        # 过户费(上海市场)
        transfer_fee = value * self.p.transfer_fee_rate

        total = brokerage + stamp_duty + transfer_fee

        return total


class ZeroCommission(bt.CommInfoBase):
    """
    零佣金方案(用于测试)

    不收取任何手续费
    """

    params = ()

    def _getcommission(self, size: float, price: float) -> float:
        """零手续费"""
        return 0.0


class FixedCommission(bt.CommInfoBase):
    """
    固定费率佣金方案

    简化的固定费率,适用于快速测试
    """

    params = (
        ('commission_rate', 0.0003),  # 固定费率0.03%
    )

    def _getcommission(self, size: float, price: float) -> float:
        """
        计算固定费率手续费

        Args:
            size: 成交数量
            price: 成交价格

        Returns:
            float: 手续费
        """
        value = abs(size) * price
        return value * self.p.commission_rate


def setup_ashare_commission(cerebro: bt.Cerebro, scheme_version: str = 'v2',
                          commission_rate: float = None) -> None:
    """
    为Cerebro回测引擎设置A股手续费方案

    Args:
        cerebro: Backtrader Cerebro实例
        scheme_version: 手续费方案版本 ('v1', 'v2', 'zero', 'fixed')
        commission_rate: 自定义固定费率(仅当scheme_version='fixed'时使用)

    Examples:
        >>> cerebro = bt.Cerebro()
        >>> setup_ashare_commission(cerebro, scheme_version='v2')
        >>> # 或使用自定义固定费率
        >>> setup_ashare_commission(cerebro, scheme_version='fixed', commission_rate=0.0003)
    """
    if scheme_version == 'v1':
        comm_scheme = AShareCommissionScheme()
        logger.info("使用A股手续费方案V1 (印花税0.1%)")
    elif scheme_version == 'v2':
        comm_scheme = AShareCommissionSchemeV2()
        logger.info("使用A股手续费方案V2 (印花税0.05%)")
    elif scheme_version == 'zero':
        comm_scheme = ZeroCommission()
        logger.info("使用零佣金方案(测试用)")
    elif scheme_version == 'fixed':
        if commission_rate is None:
            commission_rate = 0.0003
        comm_scheme = FixedCommission(commission_rate=commission_rate)
        logger.info(f"使用固定费率方案 ({commission_rate*100:.3f}%)")
    else:
        raise ValueError(f"未知的手续费方案版本: {scheme_version}")

    cerebro.broker.setcommission(commission=comm_scheme)
    logger.info("A股手续费方案已设置")


# 便捷函数
def calculate_commission_manual(size: float, price: float, is_sell: bool = False,
                               scheme: str = 'v2', is_shanghai: bool = True) -> dict:
    """
    手动计算手续费(不依赖Backtrader)

    Args:
        size: 成交数量(股)
        price: 成交价格(元)
        is_sell: 是否为卖出
        scheme: 手续费方案 ('v1', 'v2')
        is_shanghai: 是否为上海市场

    Returns:
        dict: 手续费明细
            {
                'value': 成交金额,
                'brokerage': 佣金,
                'stamp_duty': 印花税,
                'transfer_fee': 过户费,
                'total': 总手续费,
                'rate': 实际费率
            }
    """
    value = abs(size) * price

    if scheme == 'v1':
        brokerage_rate = 0.00025
        stamp_duty_rate = 0.001
        transfer_fee_rate = 0.00001
    elif scheme == 'v2':
        brokerage_rate = 0.0002
        stamp_duty_rate = 0.0005
        transfer_fee_rate = 0.00001
    else:
        raise ValueError(f"未知的手续费方案: {scheme}")

    # 佣金
    brokerage = max(value * brokerage_rate, 5.0)

    # 印花税(仅卖出)
    stamp_duty = value * stamp_duty_rate if is_sell else 0.0

    # 过户费(仅上海)
    transfer_fee = value * transfer_fee_rate if is_shanghai else 0.0

    total = brokerage + stamp_duty + transfer_fee
    actual_rate = total / value

    return {
        'value': value,
        'brokerage': brokerage,
        'stamp_duty': stamp_duty,
        'transfer_fee': transfer_fee,
        'total': total,
        'rate': actual_rate
    }
