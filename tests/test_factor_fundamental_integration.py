"""
测试基本面因子集成到因子表达式引擎

验证factor_fundamental.py中的因子能否通过FactorExpr正确调用
"""

import pandas as pd
import numpy as np
from datafeed.factor_expr import FactorExpr


def test_fundamental_factor_registration():
    """测试基本面因子是否成功注册到表达式引擎"""

    print("=" * 60)
    print("测试基本面因子注册")
    print("=" * 60)

    # 创建因子表达式引擎
    fe = FactorExpr()

    # 检查基本面因子是否在context中
    fundamental_factors = [
        'pe_score', 'PE_SCORE',
        'pb_score', 'PB_SCORE',
        'roe_score', 'ROE_SCORE',
        'quality_score', 'QUALITY_SCORE',
        'value_score', 'VALUE_SCORE',
        'total_mv_filter', 'TOTAL_MV_FILTER',
        'log_market_cap', 'LOG_MARKET_CAP',
        'fundamental_rank_score', 'FUNDAMENTAL_RANK_SCORE',
        'growth_score', 'GROWTH_SCORE',
        'normalize_score', 'NORMALIZE_SCORE',
        'winsorize', 'WINSORIZE'
    ]

    print("\n1. 检查基本面因子是否注册:")
    missing_factors = []
    for factor in fundamental_factors:
        if factor in fe.context:
            print(f"   ✅ {factor}")
        else:
            print(f"   ❌ {factor} - 未找到")
            missing_factors.append(factor)

    if missing_factors:
        print(f"\n⚠️  警告: {len(missing_factors)} 个因子未注册")
        return False
    else:
        print(f"\n✅ 所有 {len(fundamental_factors)} 个基本面因子已成功注册!")

    return True


def test_fundamental_factor_calculation():
    """测试基本面因子计算"""

    print("\n" + "=" * 60)
    print("测试基本面因子计算")
    print("=" * 60)

    # 创建测试数据
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=5),
        'open': [10, 11, 12, 13, 14],
        'high': [11, 12, 13, 14, 15],
        'low': [9, 10, 11, 12, 13],
        'close': [10, 11, 12, 13, 14],
        'volume': [1000, 1100, 1200, 1300, 1400],
        'pe': [10, 20, 30, 40, 50],
        'pb': [1, 2, 3, 4, 5],
        'roe': [0.05, 0.10, 0.15, 0.20, 0.25],
        'total_mv': [20, 60, 200, 600, 1000]
    })

    df.set_index('date', inplace=True)

    fe = FactorExpr()

    # 测试1: PE评分
    print("\n2. 测试PE评分:")
    try:
        result = fe.calc_formula(df, 'pe_score(pe)')
        print(f"   表达式: pe_score(pe)")
        print(f"   结果:\n{result}\n")
        print("   ✅ PE评分计算成功")
    except Exception as e:
        print(f"   ❌ PE评分计算失败: {e}")
        return False

    # 测试2: 质量评分
    print("\n3. 测试综合质量评分:")
    try:
        result = fe.calc_formula(df, 'quality_score(pe, pb, roe)')
        print(f"   表达式: quality_score(pe, pb, roe)")
        print(f"   结果:\n{result}\n")
        print("   ✅ 综合质量评分计算成功")
    except Exception as e:
        print(f"   ❌ 综合质量评分计算失败: {e}")
        return False

    # 测试3: 市值过滤
    print("\n4. 测试市值过滤:")
    try:
        result = fe.calc_formula(df, 'total_mv_filter(total_mv, min_mv=50, max_mv=500)')
        print(f"   表达式: total_mv_filter(total_mv, min_mv=50, max_mv=500)")
        print(f"   结果:\n{result}\n")
        print("   ✅ 市值过滤计算成功")
    except Exception as e:
        print(f"   ❌ 市值过滤计算失败: {e}")
        return False

    # 测试4: 组合因子表达式
    print("\n5. 测试组合因子表达式:")
    try:
        expr = 'quality_score(pe, pb, roe) * 0.6 + pe_score(pe) * 0.4'
        result = fe.calc_formula(df, expr)
        print(f"   表达式: {expr}")
        print(f"   结果:\n{result}\n")
        print("   ✅ 组合因子表达式计算成功")
    except Exception as e:
        print(f"   ❌ 组合因子表达式计算失败: {e}")
        return False

    # 测试5: 技术因子 + 基本面因子组合
    print("\n6. 测试技术因子 + 基本面因子组合:")
    try:
        df['close'] = [10, 11, 12, 13, 14]
        expr = 'roc(close, 20) * 0.5 + quality_score(pe, pb, roe) * 0.5'
        result = fe.calc_formula(df, expr)
        print(f"   表达式: {expr}")
        print(f"   结果:\n{result}\n")
        print("   ✅ 技术+基本面组合因子计算成功")
    except Exception as e:
        print(f"   ❌ 技术+基本面组合因子计算失败: {e}")
        return False

    return True


def test_strategy_usage_example():
    """测试在策略中的使用示例"""

    print("\n" + "=" * 60)
    print("测试策略使用示例")
    print("=" * 60)

    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10),
        'open': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        'high': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        'low': [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        'close': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        'volume': [1000, 1200, 1100, 1300, 1250, 1400, 1350, 1500, 1450, 1600],
        'pe': [15, 18, 20, 22, 25, 28, 30, 32, 35, 38],
        'pb': [1.5, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0, 3.2, 3.5, 3.8],
        'roe': [0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19],
        'total_mv': [100, 120, 150, 180, 200, 220, 250, 280, 300, 350]
    })

    df.set_index('date', inplace=True)

    fe = FactorExpr()

    # 示例1: 价值选股策略条件
    print("\n7. 价值选股策略 - 买入条件:")
    buy_conditions = [
        'pe < 30',
        'pb < 3.0',
        'roe > 0.12'
    ]

    for condition in buy_conditions:
        try:
            result = fe.calc_formula(df, condition)
            print(f"   ✅ {condition}: {result.sum()} 只股票满足条件")
        except Exception as e:
            print(f"   ❌ {condition}: {e}")
            return False

    # 示例2: 多因子排序
    print("\n8. 多因子排序信号:")
    try:
        signal = fe.calc_formula(df, 'quality_score(pe, pb, roe)')
        print(f"   ✅ quality_score计算成功")
        print(f"   前3个值:\n{signal.head(3)}\n")
    except Exception as e:
        print(f"   ❌ quality_score计算失败: {e}")
        return False

    # 示例3: GARP策略组合
    print("\n9. GARP策略组合因子:")
    try:
        expr = '''
            quality_score(pe, pb, roe) * 0.5 +
            pe_score(pe) * 0.3 +
            roe * 0.2
        '''
        signal = fe.calc_formula(df, expr.strip())
        print(f"   ✅ GARP组合因子计算成功")
        print(f"   前3个值:\n{signal.head(3)}\n")
    except Exception as e:
        print(f"   ❌ GARP组合因子计算失败: {e}")
        return False

    return True


if __name__ == '__main__':
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "基本面因子集成测试" + " " * 30 + "║")
    print("╚" + "═" * 58 + "╝")

    success = True

    # 运行所有测试
    if not test_fundamental_factor_registration():
        success = False

    if not test_fundamental_factor_calculation():
        success = False

    if not test_strategy_usage_example():
        success = False

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    if success:
        print("\n✅ 所有测试通过!")
        print("\n📋 可用的基本面因子:")
        print("   - 估值因子: pe_score, pb_score, ps_score, value_score")
        print("   - 质量因子: roe_score, roa_score, profit_margin_score")
        print("   - 市值因子: total_mv_filter, log_market_cap, market_cap_category")
        print("   - 综合因子: quality_score, fundamental_rank_score, growth_score")
        print("   - 工具函数: normalize_score, winsorize")
        print("\n💡 现在可以在策略中使用基本面因子,例如:")
        print("   t.select_buy = ['pe < 20', 'roe > 0.12']")
        print("   t.order_by_signal = 'quality_score(pe, pb, roe)'")
    else:
        print("\n❌ 部分测试失败,请检查错误信息")
        exit(1)

    print("\n" + "=" * 60 + "\n")
