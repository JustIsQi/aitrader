"""
ETF数据自动更新脚本
每天收盘后一小时自动更新ETF数据
"""
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from get_data import fetch_stock_history_with_proxy, fetch_etf_history, is_etf

# ETF列表（来自backtrader_engine.py）
ETF_SYMBOLS = [
    "563300.SH",
    "159509.SZ",
    "518880.SH",
    "513100.SH",
    "513520.SH",
    "588000.SH",
    "513330.SH",
    "512100.SH",
    "162719.SZ",
    "513030.SH",
    "513380.SH",
    "513290.SH",
    "159560.SZ",
    "588100.SH",
    "513040.SH",
    "561600.SH",
    "515880.SH",
    "513090.SH",
    "159819.SZ",
    "515790.SH",
    "515030.SH",
    "159752.SZ",
    "159761.SZ",
    "512480.SH",
    "560800.SH",
    "513500.SH"
]

DATA_DIR = './data/akshare_data'


def update_etf_data(symbol):
    """更新单个ETF数据，只下载最新的数据并追加到文件

    Args:
        symbol: ETF代码，格式如 '510300.SH'

    Returns:
        bool: 更新是否成功
    """
    csv_path = f'{DATA_DIR}/{symbol}_history.csv'

    try:
        # 获取代码部分（去掉市场后缀）
        code = symbol.split('.')[0]

        # 获取最新数据
        print(f'  正在更新 {symbol}...')
        df_new = fetch_stock_history_with_proxy(code, func=fetch_etf_history)

        if df_new is None or df_new.empty:
            print(f'    [{symbol}] 获取到的数据为空')
            return False

        # 如果文件已存在，读取并合并
        if os.path.exists(csv_path):
            df_old = pd.read_csv(csv_path)

            # 转换日期列
            if '日期' in df_old.columns:
                df_old['日期'] = pd.to_datetime(df_old['日期'])
            if '日期' in df_new.columns:
                df_new['日期'] = pd.to_datetime(df_new['日期'])

            # 获取旧数据的最后日期
            last_date = df_old['日期'].max()

            # 只保留新数据中比旧数据新的记录
            df_new = df_new[df_new['日期'] > last_date]

            if df_new.empty:
                print(f'    [{symbol}] 数据已是最新，无需更新')
                return True
    
            # 追加新数据
            df_combined = pd.concat([df_old, df_new], ignore_index=True)
            df_combined.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f'    [{symbol}] 已追加 {len(df_new)} 条新数据 (最新日期: {df_new["日期"].max().strftime("%Y-%m-%d")})')
        else:
            # 文件不存在，直接保存
            os.makedirs(DATA_DIR, exist_ok=True)
            df_new.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f'    [{symbol}] 已创建新文件，共 {len(df_new)} 条数据')

        return True

    except Exception as e:
        print(f'    [{symbol}] 更新失败: {e}')
        return False


def update_all_etf_data():
    """更新所有ETF数据"""
    print('='*60)
    print(f'开始更新ETF数据 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*60)

    # 确保数据目录存在
    os.makedirs(DATA_DIR, exist_ok=True)

    # 统计
    success_count = 0
    failed_count = 0
    skip_count = 0
    updated_count = 0

    print(f'\n待更新ETF数量: {len(ETF_SYMBOLS)}\n')

    # 遍历所有ETF
    for i, symbol in enumerate(ETF_SYMBOLS, 1):
        print(f'[{i}/{len(ETF_SYMBOLS)}] {symbol}')

        csv_path = f'{DATA_DIR}/{symbol}_history.csv'

        # 检查文件是否存在
        if not os.path.exists(csv_path):
            print(f'    首次下载，创建新数据文件...')
            updated_count += 1
        else:
            # 检查是否需要更新（如果今天是交易日且数据已更新则跳过）
            try:
                df_old = pd.read_csv(csv_path)
                if '日期' in df_old.columns:
                    df_old['日期'] = pd.to_datetime(df_old['日期'])
                    last_date = df_old['日期'].max()

                    # 如果最后一个交易日是今天或昨天，可能不需要更新
                    today = datetime.now().date()
                    yesterday = (datetime.now() - timedelta(days=1)).date()

                    if last_date.date() >= today:
                        print(f'    数据已是最新 (最新日期: {last_date.strftime("%Y-%m-%d")})')
                        skip_count += 1
                        continue
                    elif last_date.date() >= yesterday:
                        print(f'    数据较新 (最新日期: {last_date.strftime("%Y-%m-%d")})，尝试更新...')
                    else:
                        print(f'    数据较旧 (最新日期: {last_date.strftime("%Y-%m-%d")})，需要更新...')
            except Exception as e:
                print(f'    读取旧数据失败: {e}，将重新下载')

            updated_count += 1

        # 更新数据
        if update_etf_data(symbol):
            success_count += 1
        else:
            failed_count += 1

        # 避免请求过快
        time.sleep(0.5)

    # 输出统计信息
    print('\n' + '='*60)
    print('更新完成！')
    print(f'  总计: {len(ETF_SYMBOLS)} 个ETF')
    print(f'  成功: {success_count}')
    print(f'  失败: {failed_count}')
    print(f'  跳过: {skip_count}')
    print(f'  已更新: {updated_count}')
    print(f'完成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*60)


def update_etf_list():
    """更新ETF列表文件"""
    list_file = f'{DATA_DIR}/etf_symbols.txt'

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(list_file, 'w', encoding='utf-8') as f:
        for symbol in ETF_SYMBOLS:
            f.write(f'{symbol}\n')

    print(f'\nETF列表已保存到: {list_file}')
    print(f'共 {len(ETF_SYMBOLS)} 个ETF')


if __name__ == '__main__':
    # 更新ETF列表文件
    update_etf_list()

    # 更新所有ETF数据
    update_all_etf_data()
