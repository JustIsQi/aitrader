"""
简单测试基本面因子集成
"""

import pandas as pd
import numpy as np
from datafeed.factor_expr import FactorExpr


def test_basic_registration():
    """测试基本面因子是否注册"""
    print("=" * 60)
    print("测试基本面因子注册")
    print("=" * 60)

    fe = FactorExpr()

    # 检查几个关键因子
    factors_to_check = [
        'pe_score', 'PE_SCORE',
        'quality_score', 'QUALITY_SCORE',
        'value_score', 'VALUE_SCORE',
        'total_mv_filter', 'TOTAL_MV_FILTER'
    ]

    print("\n检查因子注册:")
    all_found = True
    for factor in factors_to_check:
        if factor in fe.context:
            print(f"   ✅ {factor}")
        else:
            print(f"   ❌ {factor}")
            all_found = False

    return all_found


def test_basic_usage():
    """测试基本用法"""
    print("\n" + "=" * 60)
    print("测试基本用法")
    print("=" * 60)

    # 创建测试数据
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=5),
        'open': [10, 11, 12, 13, 14],
        'high': [11, 12, 13, 14, 15],
        'low': [9, 10, 11, 12, 13],
        'close': [10, 11, 12, 13, 14],
        'volume': [1000, 1100, 1200, 1300, 1400],
    })

    df.set_index('date', inplace=True)

    fe = FactorExpr()

    # 手动添加基本面数据列到context (模拟真实使用场景)
    fe.context['PE'] = pd.Series([10, 20, 30, 40, 50], index=df.index)
    fe.context['PB'] = pd.Series([1, 2, 3, 4, 5], index=df.index)
    fe.context['ROE'] = pd.Series([0.05, 0.10, 0.15, 0.20, 0.25], index=df.index)

    # 测试1: PE评分
    print("\n1. 测试PE评分:")
    try:
        result = fe.calc_formula(df, 'pe_score(pe)')
        print(f"   表达式: pe_score(pe)")
        print(f"   结果: {result.tolist()}")
        print("   ✅ 成功")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False

    # 测试2: 综合质量评分
    print("\n2. 测试综合质量评分:")
    try:
        result = fe.calc_formula(df, 'quality_score(pe, pb, roe)')
        print(f"   表达式: quality_score(pe, pb, roe)")
        print(f"   结果: {result.tolist()}")
        print("   ✅ 成功")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False

    # 测试3: 技术因子 + 基本面因子组合
    print("\n3. 测试组合因子:")
    try:
        result = fe.calc_formula(df, 'roc(close, 20) * 0.5 + quality_score(pe, pb, roe) * 0.5')
        print(f"   表达式: roc(close, 20) * 0.5 + quality_score(pe, pb, roe) * 0.5")
        print(f"   结果: {result.tolist()}")
        print("   ✅ 成功")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False

    return True


def test_strategy_conditions():
    """测试策略条件"""
    print("\n" + "=" * 60)
    print("测试策略条件")
    print("=" * 60)

    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10),
        'open': range(10, 20),
        'high': range(11, 21),
        'low': range(9, 19),
        'close': range(10, 20),
        'volume': range(1000, 2000, 100),
    })

    df.set_index('date', inplace=True)

    fe = FactorExpr()

    # 添加基本面数据
    fe.context['PE'] = pd.Series([15, 18, 20, 22, 25, 28, 30, 32, 35, 38], index=df.index)
    fe.context['PB'] = pd.Series([1.5, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0, 3.2, 3.5, 3.8], index=df.index)
    fe.context['ROE'] = pd.Series([0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19], index=df.index)

    # 测试买入条件
    print("\n测试买入条件:")
    conditions = [
        ('pe < 30', '低PE筛选'),
        ('roe > 0.12', '高ROE筛选'),
        ('pb < 3.0', '低PB筛选')
    ]

    for expr, desc in conditions:
        try:
            result = fe.calc_formula(df, expr)
            count = result.sum()
            print(f"   ✅ {desc} ({expr}): {count} 只股票满足")
        except Exception as e:
            print(f"   ❌ {desc} ({expr}): {e}")
            return False

    return True


if __name__ == '__main__':
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "基本面因子集成测试" + " " * 27 + "║")
    print("╚" + "═" * 58 + "╝")

    success = True

    if not test_basic_registration():
        success = False

    if not test_basic_usage():
        success = False

    if not test_strategy_conditions():
        success = False

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    if success:
        print("\n✅ 所有测试通过!")
        print("\n📋 已注册的基本面因子:")
        print("   - pe_score, pb_score, ps_score")
        print("   - roe_score, roa_score, profit_margin_score")
        print("   - quality_score, value_score, growth_score")
        print("   - total_mv_filter, log_market_cap")
        print("   - fundamental_rank_score")
        print("   - normalize_score, winsorize")
        print("\n💡 使用方法:")
        print("   在策略中添加基本面数据列后,可以直接使用:")
        print("   t.select_buy = ['pe < 20', 'roe > 0.12']")
        print("   t.order_by_signal = 'quality_score(pe, pb, roe)'")
    else:
        print("\n❌ 部分测试失败")
        exit(1)

    print("\n" + "=" * 60 + "\n")
