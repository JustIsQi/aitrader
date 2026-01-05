#!/usr/bin/env python3
"""
测试批量查询性能改进
"""
import time
from datafeed.db_dataloader import DbDataLoader

def test_batch_query():
    """测试批量查询"""
    print("=" * 100)
    print("批量查询性能测试")
    print("=" * 100)

    # 测试数据
    test_symbols = ['510300.SH', '513100.SH', '159915.SZ', '518880.SH', '512100.SH']

    print(f"\n测试标的: {test_symbols}")
    print(f"标的数量: {len(test_symbols)}")

    # 测试批量查询
    print("\n开始批量查询...")
    start = time.time()

    loader = DbDataLoader()
    dfs = loader.read_dfs(symbols=test_symbols, start_date='20240101', end_date='20241231')

    elapsed = time.time() - start

    print(f"\n✓ 查询完成！")
    print(f"  耗时: {elapsed:.3f}秒")
    print(f"  成功获取: {len(dfs)}/{len(test_symbols)} 个标的")

    for symbol, df in dfs.items():
        print(f"    {symbol}: {len(df)} 条记录")

    print("\n" + "=" * 100)
    if elapsed < 1.0:
        print(f"✅ 性能优秀！批量查询仅耗时 {elapsed:.3f}秒")
    elif elapsed < 3.0:
        print(f"✓ 性能良好，耗时 {elapsed:.3f}秒")
    else:
        print(f"⚠️  性能待优化，耗时 {elapsed:.3f}秒")
    print("=" * 100)

if __name__ == '__main__':
    test_batch_query()
