"""
测试 DuckDB 集成
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.db_manager import get_db
from datafeed.csv_dataloader import CsvDataLoader
from datetime import datetime

def test_db_manager():
    """测试数据库管理器"""
    print("="*80)
    print("测试 DuckDB 管理器")
    print("="*80)

    db = get_db('/data/home/yy/data/duckdb/trading.db')

    # 获取统计信息
    stats = db.get_statistics()
    print(f'\n数据库统计:')
    print(f'  ETF 数量: {stats["total_symbols"]}')
    print(f'  总记录数: {stats["total_records"]}')
    print(f'  数据范围: {stats["earliest_date"]} ~ {stats["latest_date"]}')

    # 获取所有 ETF
    symbols = db.get_all_symbols()
    print(f'\n所有 ETF ({len(symbols)} 个):')
    print(f'  {", ".join(symbols[:10])}...')

    # 测试查询
    if symbols:
        test_symbol = symbols[0]
        print(f'\n测试查询 {test_symbol}:')
        df = db.get_etf_history(test_symbol)
        print(df.tail())

    print('\n✅ 数据库管理器测试完成\n')


def test_csv_loader():
    """测试 CSV DataLoader"""
    print("="*80)
    print("测试 CsvDataLoader (DuckDB 模式)")
    print("="*80)

    # 使用 DuckDB 模式
    loader = CsvDataLoader(use_duckdb=True)

    # 测试读取数据
    symbols = ['510300.SH', '513100.SH']
    print(f'\n读取 {symbols} 数据...')

    try:
        dfs = loader.read_dfs(
            symbols=symbols,
            start_date='20240101',
            end_date=datetime.now().strftime('%Y%m%d')
        )

        for symbol, df in dfs.items():
            print(f'\n{symbol}:')
            print(f'  记录数: {len(df)}')
            print(f'  日期范围: {df["date"].min()} ~ {df["date"].max()}')
            print(f'  最新收盘价: {df["close"].iloc[-1]:.3f}')

        print('\n✅ CsvDataLoader 测试完成\n')
    except Exception as e:
        print(f'\n❌ 测试失败: {e}')
        print('提示: 请先运行 python import_to_duckdb.py 导入数据\n')


if __name__ == '__main__':
    test_db_manager()
    test_csv_loader()
