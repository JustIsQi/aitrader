"""
清空交易记录和持仓数据

使用方法:
    python clear_trading_data.py
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.db_manager import get_db

def clear_all_trading_data():
    """清空所有交易相关数据"""
    print("=" * 60)
    print("清空交易数据")
    print("=" * 60)

    db = get_db('/data/home/yy/data/duckdb/trading.db')

    # 显示当前数据
    print("\n📊 清空前数据检查:")

    positions = db.get_positions()
    if positions.empty:
        print("  当前无持仓")
    else:
        print(f"  持仓数量: {len(positions)}")
        for _, row in positions.iterrows():
            print(f"    {row['symbol']}: {row['quantity']:.0f}股")

    transactions = db.get_transactions()
    if transactions.empty:
        print("  当前无交易记录")
    else:
        print(f"  交易记录数: {len(transactions)}")

    # 确认清空
    print("\n⚠️  即将清空以下数据:")
    print("  - 所有持仓记录 (positions)")
    print("  - 所有交易记录 (transactions)")

    confirm = input("\n确认清空? (输入 'yes' 继续): ")

    if confirm.lower() == 'yes':
        db.clear_trading_data()
        print("\n✅ 清空完成!")
    else:
        print("\n❌ 已取消清空操作")

    # 验证清空结果
    print("\n📊 清空后验证:")
    positions = db.get_positions()
    transactions = db.get_transactions()

    if positions.empty and transactions.empty:
        print("  ✅ 所有交易数据已清空")
    else:
        print(f"  持仓: {len(positions)} 条")
        print(f"  交易记录: {len(transactions)} 条")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    clear_all_trading_data()
