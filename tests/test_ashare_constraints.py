"""
A股约束功能测试脚本

测试以下功能:
1. T+1结算限制
2. 涨跌停检查
3. 手数调整
4. A股手续费计算
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from loguru import logger

# 导入A股约束模块
from core.ashare_constraints import (
    TPlusOneTracker,
    PriceLimitChecker,
    LotSizeRounder,
    check_buy_order,
    check_sell_order
)

# 导入A股手续费模块
from core.ashare_commission import (
    AShareCommissionSchemeV2,
    calculate_commission_manual
)


def test_t_plus_one_tracker():
    """测试T+1跟踪器"""
    print("\n" + "="*50)
    print("测试 T+1 跟踪器")
    print("="*50)

    tracker = TPlusOneTracker()
    buy_date = pd.Timestamp('2024-01-15')
    current_date = pd.Timestamp('2024-01-15')
    next_date = pd.Timestamp('2024-01-16')

    # 记录买入
    tracker.record_buy('000001.SZ', buy_date)
    print(f"✓ 记录买入: 000001.SZ 于 {buy_date}")

    # 当日不能卖出
    can_sell = tracker.can_sell('000001.SZ', current_date, 100)
    assert can_sell == False, "T+1失败: 当日不应能卖出"
    print(f"✓ 当日检查: 不能卖出 (符合预期)")

    # 次日可以卖出
    can_sell = tracker.can_sell('000001.SZ', next_date, 100)
    assert can_sell == True, "T+1失败: 次日应能卖出"
    print(f"✓ 次日检查: 可以卖出 (符合预期)")

    # 获取持仓天数
    days = tracker.get_holding_days('000001.SZ', next_date)
    assert days == 1, "持仓天数错误"
    print(f"✓ 持仓天数: {days}天 (符合预期)")

    # 移除持仓
    tracker.remove_position('000001.SZ')
    print(f"✓ 移除持仓记录")

    # 历史持仓可以卖出
    can_sell = tracker.can_sell('000001.SZ', next_date, 100)
    assert can_sell == True, "历史持仓应该能卖出"
    print(f"✓ 历史持仓检查: 可以卖出 (符合预期)")

    print("\n✅ T+1跟踪器测试通过!")


def test_price_limit_checker():
    """测试涨跌停检查器"""
    print("\n" + "="*50)
    print("测试涨跌停检查器")
    print("="*50)

    checker = PriceLimitChecker()

    # 普通股票10%涨跌停
    prev_close = 10.0
    limit_up = prev_close * 1.10
    limit_down = prev_close * 0.90

    # 涨停
    is_hit, limit_type = checker.is_limit_hit('000001.SZ', limit_up, prev_close)
    assert is_hit == True, "涨停检查失败"
    print(f"✓ 涨停检测: {limit_up:.2f} 触及涨停 ({limit_type})")

    # 跌停
    is_hit, limit_type = checker.is_limit_hit('000001.SZ', limit_down, prev_close)
    assert is_hit == True, "跌停检查失败"
    print(f"✓ 跌停检测: {limit_down:.2f} 触及跌停 ({limit_type})")

    # 正常价格
    normal_price = 10.5
    is_hit, limit_type = checker.is_limit_hit('000001.SZ', normal_price, prev_close)
    assert is_hit == False, "正常价格不应触发涨跌停"
    print(f"✓ 正常价格: {normal_price:.2f} 未触及涨跌停")

    # 科创板/创业板20%
    star_symbol = '688001.SH'  # 科创板
    limit_up_20 = prev_close * 1.20
    is_hit, limit_type = checker.is_limit_hit(star_symbol, limit_up_20, prev_close)
    assert is_hit == True, "科创板20%涨停检查失败"
    print(f"✓ 科创板涨停检测: {limit_up_20:.2f} 触及20%涨停 ({limit_type})")

    # 获取涨停价
    limit_price = checker.get_limit_price('000001.SZ', prev_close, 'up')
    assert abs(limit_price - limit_up) < 0.01, "涨停价计算错误"
    print(f"✓ 涨停价计算: {limit_price:.2f}")

    print("\n✅ 涨跌停检查器测试通过!")


def test_lot_size_rounder():
    """测试手数调整器"""
    print("\n" + "="*50)
    print("测试手数调整器")
    print("="*50)

    rounder = LotSizeRounder(lot_size=100)

    # 测试整手调整
    test_cases = [
        (155, 100),
        (250, 200),
        (99, 0),
        (100, 100),
        (1000, 1000),
        (1234, 1200),
    ]

    for raw_size, expected in test_cases:
        rounded = rounder.round_to_lot(raw_size)
        assert rounded == expected, f"手数调整失败: {raw_size} -> {rounded}, 预期 {expected}"
        print(f"✓ 调整: {raw_size}股 -> {rounded}股 (符合预期)")

    # 测试按金额调整
    target_value = 10000
    price = 15.5
    shares = rounder.adjust_order_size(target_value, price)
    assert shares is not None and shares % 100 == 0, "金额调整失败"
    actual_value = rounder.get_actual_value(shares, price)
    print(f"✓ 金额调整: 目标{target_value}元 -> {shares}股 -> 实际{actual_value:.2f}元")

    # 不足1手
    target_value = 100
    shares = rounder.adjust_order_size(target_value, price)
    assert shares is None, "不足1手应返回None"
    print(f"✓ 不足1手: 目标{target_value}元 -> {shares} (符合预期)")

    print("\n✅ 手数调整器测试通过!")


def test_commission():
    """测试A股手续费计算"""
    print("\n" + "="*50)
    print("测试A股手续费计算")
    print("="*50)

    # 测试手续费计算
    size = 1000  # 1000股
    price = 10.0  # 10元

    # 买入手续费
    detail = calculate_commission_manual(size, price, is_sell=False, scheme='v2')
    print(f"✓ 买入手续费: {size}股 @ {price}元")
    print(f"  - 成交金额: {detail['value']:.2f}元")
    print(f"  - 佣金: {detail['brokerage']:.2f}元")
    print(f"  - 印花税: {detail['stamp_duty']:.2f}元")
    print(f"  - 过户费: {detail['transfer_fee']:.2f}元")
    print(f"  - 总手续费: {detail['total']:.2f}元")
    print(f"  - 实际费率: {detail['rate']*100:.4f}%")

    # 卖出手续费
    detail = calculate_commission_manual(size, price, is_sell=True, scheme='v2')
    print(f"\n✓ 卖出手续费: {size}股 @ {price}元")
    print(f"  - 成交金额: {detail['value']:.2f}元")
    print(f"  - 佣金: {detail['brokerage']:.2f}元")
    print(f"  - 印花税: {detail['stamp_duty']:.2f}元")
    print(f"  - 过户费: {detail['transfer_fee']:.2f}元")
    print(f"  - 总手续费: {detail['total']:.2f}元")
    print(f"  - 实际费率: {detail['rate']*100:.4f}%")

    # 验证最低佣金
    small_value = 1000  # 1000元
    small_size = int(small_value / price)
    detail = calculate_commission_manual(small_size, price, is_sell=False, scheme='v2')
    assert detail['brokerage'] >= 5.0, "最低佣金应为5元"
    print(f"\n✓ 最低佣金: {detail['brokerage']:.2f}元 (符合预期)")

    print("\n✅ 手续费计算测试通过!")


def test_order_validation():
    """测试订单合规性验证"""
    print("\n" + "="*50)
    print("测试订单合规性验证")
    print("="*50)

    t1_tracker = TPlusOneTracker()
    limit_checker = PriceLimitChecker()
    lot_rounder = LotSizeRounder()

    current_date = pd.Timestamp('2024-01-15')

    # 测试买入订单(符合规则)
    is_valid, msg = check_buy_order(
        '000001.SZ', 100, 10.0, 9.5,
        t1_tracker, limit_checker, lot_rounder, current_date
    )
    assert is_valid, "买入订单验证失败"
    print(f"✓ 买入订单合规: 100股 @ 10.0元")

    # 测试手数不合规
    is_valid, msg = check_buy_order(
        '000001.SZ', 155, 10.0, 9.5,
        t1_tracker, limit_checker, lot_rounder, current_date
    )
    assert not is_valid, "手数不是100倍数应不合规"
    print(f"✓ 手数检查: 155股 不合规 ({msg})")

    # 测试T+1卖出限制
    t1_tracker.record_buy('000001.SZ', current_date)
    is_valid, msg = check_sell_order(
        '000001.SZ', 100, 10.0, 9.5,
        t1_tracker, limit_checker, lot_rounder, current_date
    )
    assert not is_valid, "T+1当日卖出应不合规"
    print(f"✓ T+1检查: 当日卖出 不合规 ({msg})")

    # 测试涨跌停买入限制
    is_valid, msg = check_buy_order(
        '000001.SZ', 100, 11.0, 10.0,
        t1_tracker, limit_checker, lot_rounder, current_date
    )
    assert not is_valid, "涨停买入应不合规"
    print(f"✓ 涨停检查: 涨停价买入 不合规 ({msg})")

    print("\n✅ 订单合规性验证测试通过!")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print(" "*15 + "A股约束功能测试套件")
    print("="*60)

    try:
        test_t_plus_one_tracker()
        test_price_limit_checker()
        test_lot_size_rounder()
        test_commission()
        test_order_validation()

        print("\n" + "="*60)
        print(" "*20 + "🎉 所有测试通过!")
        print("="*60)
        return True

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
