"""
将现有 CSV 历史数据导入 DuckDB
自动识别股票和ETF，分别导入到不同的表
"""
import pandas as pd
from pathlib import Path
from loguru import logger
from database.db_manager import get_db
from tqdm import tqdm
from get_data import is_etf

# 配置
DATA_DIR = Path('./data/akshare_data')
DUCKDB_PATH = '/data/home/yy/data/duckdb/trading.db'

# ETF 列表（用于优先导入ETF）
ETF_SYMBOLS = [
    "510300.SH",  # 沪深300 ETF
    "563300.SH", "159509.SZ", "518880.SH", "513100.SH", "513520.SH",
    "588000.SH", "513330.SH", "512100.SH", "162719.SZ", "513030.SH",
    "513380.SH", "513290.SH", "159560.SZ", "588100.SH", "513040.SH",
    "561600.SH", "515880.SH", "513090.SH", "159819.SZ", "515790.SH",
    "515030.SH", "159752.SZ", "159761.SZ", "512480.SH", "560800.SH",
    "513500.SH"
]


def import_csv_to_duckdb(symbol: str, db, force_update=False, is_etf_symbol=False):
    """
    将单个股票/ETF 的 CSV 数据导入 DuckDB

    Args:
        symbol: 股票/ETF 代码
        db: DuckDBManager 实例
        force_update: 是否强制更新（覆盖已有数据）
        is_etf_symbol: 是否为ETF

    Returns:
        (success, count) 成功状态和导入记录数
    """
    csv_path = DATA_DIR / f'{symbol}_history.csv'

    if not csv_path.exists():
        logger.warning(f'CSV 文件不存在: {csv_path}')
        return False, 0

    try:
        # 读取 CSV
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        # 重命名列为英文
        if '日期' in df.columns:
            df.rename(columns={
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

        # 选择所有可能的列（如果某列不存在会自动跳过）
        all_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount',
                      'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
        df = df[[col for col in all_columns if col in df.columns]].copy()

        # 转换日期格式（自动检测格式）
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['date'] = df['date'].dt.date

        # 删除日期为空的行
        df = df.dropna(subset=['date'])

        # 检查数据库中是否已有数据
        if is_etf_symbol:
            last_db_date = db.get_latest_date(symbol)
        else:
            last_db_date = db.get_stock_latest_date(symbol)

        if last_db_date and not force_update:
            # 只追加新数据
            df = df[df['date'] > last_db_date.date()]
            if df.empty:
                return True, 0

        # 添加 symbol 列
        df['symbol'] = symbol

        if force_update:
            # 覆盖模式：先删除旧数据
            if is_etf_symbol:
                db.conn.sql(f"DELETE FROM etf_history WHERE symbol = '{symbol}'")
            else:
                db.conn.sql(f"DELETE FROM stock_history WHERE symbol = '{symbol}'")

        # 插入到对应的表
        if is_etf_symbol:
            db.conn.sql(f"""
                INSERT INTO etf_history
                (symbol, date, open, high, low, close, volume, amount, amplitude, change_pct, change_amount, turnover_rate)
                SELECT symbol, date, open, high, low, close, volume, amount, amplitude, change_pct, change_amount, turnover_rate
                FROM df
            """)
        else:
            db.conn.sql(f"""
                INSERT INTO stock_history
                (symbol, date, open, high, low, close, volume, amount, amplitude, change_pct, change_amount, turnover_rate)
                SELECT symbol, date, open, high, low, close, volume, amount, amplitude, change_pct, change_amount, turnover_rate
                FROM df
            """)

        return True, len(df)

    except Exception as e:
        logger.error(f'导入 {symbol} 失败: {e}')
        return False, 0


def import_all_data(force_update=False):
    """导入所有股票和ETF历史数据"""
    logger.info('='*80)
    logger.info('开始导入历史数据到 DuckDB')
    logger.info('='*80)

    # 确认操作
    if force_update:
        print('⚠️  警告：强制更新模式会删除数据库中的现有数据！')
        confirm = input('确定要继续吗？(yes/no): ')
        if confirm.lower() != 'yes':
            print('操作已取消')
            return

    db = get_db(DUCKDB_PATH)

    # 清空数据
    if force_update:
        logger.info('清空现有数据...')
        db.conn.sql("DELETE FROM etf_history;")
        db.conn.sql("DELETE FROM stock_history;")

    # 获取所有CSV文件
    csv_files = list(DATA_DIR.glob('*_history.csv'))
    logger.info(f'找到 {len(csv_files)} 个CSV文件')

    # 统计
    etf_success = 0
    etf_failed = 0
    etf_records = 0
    stock_success = 0
    stock_failed = 0
    stock_records = 0

    # 导入进度条
    for csv_file in tqdm(csv_files, desc='导入进度'):
        # 从文件名提取symbol
        filename = csv_file.stem
        symbol = filename.replace('_history', '')

        # 判断是ETF还是股票
        is_etf_symbol = is_etf(symbol)

        # 导入
        success, count = import_csv_to_duckdb(symbol, db, force_update, is_etf_symbol)

        if is_etf_symbol:
            if success:
                etf_success += 1
                etf_records += count
            else:
                etf_failed += 1
        else:
            if success:
                stock_success += 1
                stock_records += count
            else:
                stock_failed += 1

    # 输出统计
    logger.info('='*80)
    logger.info('导入完成！')
    logger.info(f'ETF:')
    logger.info(f'  成功: {etf_success} 个')
    logger.info(f'  失败: {etf_failed} 个')
    logger.info(f'  总记录数: {etf_records} 条')
    logger.info(f'股票:')
    logger.info(f'  成功: {stock_success} 个')
    logger.info(f'  失败: {stock_failed} 个')
    logger.info(f'  总记录数: {stock_records} 条')
    logger.info('='*80)

    # 显示数据库统计
    logger.info('\n数据库统计:')

    # ETF统计
    etf_stats = db.conn.sql("""
        SELECT
            COUNT(DISTINCT symbol) as total_symbols,
            COUNT(*) as total_records,
            MIN(date) as earliest_date,
            MAX(date) as latest_date
        FROM etf_history
    """).df()
    logger.info(f'ETF表:')
    logger.info(f'  代码数量: {etf_stats["total_symbols"].iloc[0]}')
    logger.info(f'  总记录数: {etf_stats["total_records"].iloc[0]}')
    logger.info(f'  数据范围: {etf_stats["earliest_date"].iloc[0]} ~ {etf_stats["latest_date"].iloc[0]}')

    # 股票统计
    stock_stats = db.conn.sql("""
        SELECT
            COUNT(DISTINCT symbol) as total_symbols,
            COUNT(*) as total_records,
            MIN(date) as earliest_date,
            MAX(date) as latest_date
        FROM stock_history
    """).df()
    logger.info(f'股票表:')
    logger.info(f'  代码数量: {stock_stats["total_symbols"].iloc[0]}')
    logger.info(f'  总记录数: {stock_stats["total_records"].iloc[0]}')
    logger.info(f'  数据范围: {stock_stats["earliest_date"].iloc[0]} ~ {stock_stats["latest_date"].iloc[0]}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='导入历史数据到 DuckDB')
    parser.add_argument('--force', action='store_true',
                        help='强制更新（覆盖已有数据）')

    args = parser.parse_args()

    import_all_data(force_update=args.force)
