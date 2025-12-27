"""
ETF和股票数据自动更新脚本
每天收盘后一小时自动更新数据
支持 CSV 和 DuckDB 双存储
"""
import time
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime
from tqdm import tqdm
from scripts.get_data import fetch_stock_history_with_proxy, fetch_etf_history, fetch_stock_history, is_etf
from database.db_manager import get_db

DATA_DIR = './data/akshare_data'

# 是否启用 DuckDB 存储
ENABLE_DUCKDB = True
DUCKDB_PATH = '/data/home/yy/data/duckdb/trading.db'


def update_symbol_data(symbol):
    """更新单个股票/ETF数据，只保存到DuckDB

    Args:
        symbol: 股票/ETF代码，格式如 '510300.SH' 或 '000001'

    Returns:
        bool: 更新是否成功
    """
    try:
        # 判断是ETF还是股票
        is_etf_symbol = is_etf(symbol)

        # 获取代码部分（去掉市场后缀）
        code = symbol.split('.')[0]

        # 获取最新数据
        print(f'  正在更新 {symbol}...')
        if is_etf_symbol:
            df_new = fetch_stock_history_with_proxy(code, func=fetch_etf_history)
        else:
            df_new = fetch_stock_history_with_proxy(code, func=fetch_stock_history)

        if df_new is None or df_new.empty:
            print(f'    [{symbol}] 获取到的数据为空')
            return False

        # 检查数据库中最新日期
        last_db_date = None
        if ENABLE_DUCKDB:
            try:
                db = get_db(DUCKDB_PATH)
                if is_etf_symbol:
                    last_db_date = db.get_latest_date(symbol)
                else:
                    last_db_date = db.get_stock_latest_date(symbol)
            except Exception as e:
                print(f'    [{symbol}] 获取数据库最新日期失败: {e}')

        # 转换新数据日期
        if '日期' in df_new.columns:
            df_new['日期'] = pd.to_datetime(df_new['日期'])

        # 保存最新日期的引用用于打印
        latest_date = df_new['日期'].max()

        # 如果有历史数据，只保留新数据
        if last_db_date is not None:
            df_new = df_new[df_new['日期'] > last_db_date]

            if df_new.empty:
                print(f'    [{symbol}] 数据已是最新，无需更新')
                return True

        # ========== 保存到 DuckDB ==========
        if ENABLE_DUCKDB:
            try:
                db = get_db(DUCKDB_PATH)

                # 准备数据（重命名列为英文）
                df_to_db = df_new.copy()
                if '日期' in df_to_db.columns:
                    df_to_db.rename(columns={
                        '日期': 'date',
                        '开盘': 'open',
                        '收盘': 'close',
                        '最高': 'high',
                        '最低': 'low',
                        '成交量': 'volume',
                        '成交额': 'amount',
                        '振幅': 'amplitude',
                        '涨跌幅': 'change_pct',
                        '涨跌额': 'change_amount',
                        '换手率': 'turnover_rate'
                    }, inplace=True)

                # 追加到数据库
                if is_etf_symbol:
                    db.append_etf_history(df_to_db, symbol)
                else:
                    db.append_stock_history(df_to_db, symbol)

                print(f'    [{symbol}] DuckDB: 已追加 {len(df_new)} 条新数据')

            except Exception as e:
                print(f'    [{symbol}] DuckDB 保存失败: {e}')
                return False

        # 打印最新5条数据
        print(f'    [{symbol}] 成功: 已追加 {len(df_new)} 条新数据 (最新日期: {latest_date.strftime("%Y-%m-%d")})')
        print(f'    最新5条数据:')
        for _, row in df_new.tail(5).iterrows():
            date_str = row['日期'].strftime('%Y-%m-%d') if pd.notna(row['日期']) else 'N/A'
            open_val = f"{row['开盘']:.2f}" if pd.notna(row.get('开盘')) else 'N/A'
            close_val = f"{row['收盘']:.2f}" if pd.notna(row.get('收盘')) else 'N/A'
            volume_val = f"{row.get('成交量', 0):,.0f}" if pd.notna(row.get('成交量')) else 'N/A'
            print(f'      {date_str}: 开={open_val}, 收={close_val}, 成交量={volume_val}')
        return True

    except Exception as e:
        print(f'    [{symbol}] 更新失败: {e}')
        return False


def get_etf_symbols_from_db():
    """从 DuckDB 数据库的 etf_codes 表获取所有 ETF 代码"""
    try:
        db = get_db(DUCKDB_PATH)
        symbols = db.conn.sql("""
            SELECT symbol
            FROM etf_codes
            ORDER BY symbol
        """).df()['symbol'].tolist()

        print(f'从数据库获取到 {len(symbols)} 个 ETF 代码')
        return symbols
    except Exception as e:
        print(f'从数据库获取 ETF 代码失败: {e}')
        return []


def update_all_etf_data():
    """更新所有ETF数据"""
    print('='*60)
    print(f'开始更新ETF数据 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*60)

    # 从数据库获取 ETF 代码列表
    etf_symbols = get_etf_symbols_from_db()

    if not etf_symbols:
        print('没有找到 ETF 代码，跳过 ETF 更新')
        return

    # 统计
    success_count = 0
    failed_count = 0
    skip_count = 0

    print(f'\n待更新ETF数量: {len(etf_symbols)}\n')

    # 遍历所有ETF
    for i, symbol in enumerate(etf_symbols, 1):
        print(f'[{i}/{len(etf_symbols)}] {symbol}')

        # 更新数据
        result = update_symbol_data(symbol)
        if result:
            success_count += 1
        else:
            failed_count += 1

        # 避免请求过快
        time.sleep(0.5)

    # 输出统计信息
    print('\n' + '='*60)
    print('ETF更新完成！')
    print(f'  总计: {len(etf_symbols)} 个ETF')
    print(f'  成功: {success_count}')
    print(f'  失败: {failed_count}')
    print(f'  跳过: {skip_count}')
    print(f'完成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*60)


def get_stock_symbols_from_db():
    """从 DuckDB 数据库的 stock_codes 表获取所有股票代码"""
    try:
        db = get_db(DUCKDB_PATH)
        symbols = db.conn.sql("""
            SELECT symbol
            FROM stock_codes
            ORDER BY symbol
        """).df()['symbol'].tolist()

        print(f'从数据库获取到 {len(symbols)} 个股票代码')
        return symbols
    except Exception as e:
        print(f'从数据库获取股票代码失败: {e}')
        return []


def update_all_stock_data():
    """更新所有股票数据"""
    # 从数据库获取股票代码列表
    stock_codes = get_stock_symbols_from_db()

    if not stock_codes:
        print('没有找到股票代码，跳过股票更新')
        return

    print('='*60)
    print(f'开始更新股票数据 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*60)

    # 统计
    success_count = 0
    failed_count = 0
    skip_count = 0

    print(f'\n待更新股票数量: {len(stock_codes)}\n')

    # 遍历所有股票，使用进度条
    for code in tqdm(stock_codes, desc='更新股票', unit='只'):
        # 更新数据
        if update_symbol_data(code):
            success_count += 1
        else:
            failed_count += 1

        # 避免请求过快
        time.sleep(0.1)  # 每个股票之间稍作停顿

    # 输出统计信息
    print('\n' + '='*60)
    print('股票更新完成！')
    print(f'  总计: {len(stock_codes)} 个股票')
    print(f'  成功: {success_count}')
    print(f'  失败: {failed_count}')
    print(f'  跳过: {skip_count}')
    print(f'完成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*60)


def update_etf_list():
    """更新ETF列表文件"""
    # 从数据库获取 ETF 列表
    etf_symbols = get_etf_symbols_from_db()

    if not etf_symbols:
        print('没有 ETF 代码可保存')
        return

    list_file = f'{DATA_DIR}/etf_symbols.txt'

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(list_file, 'w', encoding='utf-8') as f:
        for symbol in etf_symbols:
            f.write(f'{symbol}\n')

    print(f'\nETF列表已保存到: {list_file}')
    print(f'共 {len(etf_symbols)} 个ETF')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='更新股票和ETF数据')
    parser.add_argument('--type', choices=['etf', 'stock', 'all'], default='all',
                        help='更新类型: etf(仅ETF), stock(仅股票), all(全部)')

    args = parser.parse_args()

    # 更新ETF列表文件
    update_etf_list()

    # 根据参数决定更新内容
    if args.type == 'etf':
        # 仅更新ETF
        update_all_etf_data()
    elif args.type == 'stock':
        # 仅更新股票
        update_all_stock_data()
    else:
        # 更新全部（先ETF后股票）
        update_all_etf_data()
        update_all_stock_data()
