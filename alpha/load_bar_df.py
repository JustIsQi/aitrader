import glob
import os
from datetime import datetime

import polars as pl
from typing import Union, List, Optional

from numpy.conftest import dtype


def load_all_data_polars(
        data_sources: Union[str, List[str]],
        start_date: str,
        end_date: str,
        columns: List[str]
):
    """使用Polars加载所有CSV文件"""
    all_files = []
    for path in data_sources:
        path_files = glob.glob(os.path.join(path, "*.csv"))
        path_files = [f for f in path_files if ".BJ" not in f]
        all_files += path_files

    if not all_files:
        print("未找到任何CSV文件")
        return pl.DataFrame()

    print(f"找到 {len(all_files)} 个CSV文件")

    # 将日期字符串转换为日期对象
    start_dt = datetime.strptime(start_date, '%Y%m%d').date()
    end_dt = datetime.strptime(end_date, '%Y%m%d').date()

    # 方法1: 使用scan_csv进行惰性加载（推荐）
    try:
        # 创建惰性框架
        lf = pl.scan_csv(
            all_files,
            dtypes={
                'symbol': pl.Utf8,
                'date': pl.Utf8,  # 先作为字符串读入
                'end_date':pl.Utf8,
                'real_close': pl.Float32,
                'close': pl.Float32,
                'volume': pl.Float32,
                'circ_mv':pl.Float32,
                #'': pl.Float32,
            }
    #     ).with_columns(
    # (pl.col("circ_mv") / 1e4).alias("circ_mv")  # Divide by 100 million
)


        # lf = pl.scan_csv(
        #     all_files,
        #     dtypes={col: pl.Utf8 for col in ['date', 'end_date', 'symbol']
        #             }  # 将关键列作为字符串读取
        # )

        # 转换日期列并筛选
        lf = lf.with_columns(
            pl.col('date').str.to_date('%Y%m%d').alias('date')
        ).filter(
            (pl.col('date') >= start_dt) &
            (pl.col('date') <= end_dt)
        ).select(columns)

        # 执行查询
        return lf.collect()

    except Exception as e:
        print(f"使用scan_csv失败: {str(e)}，尝试使用read_csv回退方案")

        # 方法2: 使用read_csv回退
        dfs = []
        for file in all_files:
            try:
                # df = pl.read_csv(file, dtypes={
                #     'symbol': pl.Utf8,
                #     'date': pl.Utf8,
                #     'close': pl.Float64,
                #     'volume': pl.Float64,
                #     'high': pl.Float64,
                #     'open': pl.Float64,
                #     'low': pl.Float64,
                # })
                # 尝试多种方式读取文件
                try:
                    # 首先尝试自动推断类型
                    df = pl.read_csv(file)
                except:
                    # 如果失败，将所有列作为字符串读取
                    df = pl.read_csv(file, infer_schema_length=0)

                # 确保日期列是字符串类型，然后转换
                if df.schema.get('date') != pl.Utf8:
                    df = df.with_columns(pl.col('date').cast(pl.Utf8))
                # 转换日期列
                df = df.with_columns(
                    pl.col('date').str.to_date('%Y%m%d').alias('date'),
                    pl.col('close').str.parse_float().alias('close'),
                )

                # 筛选日期范围
                df = df.filter(
                    (pl.col('date') >= start_dt) &
                    (pl.col('date') <= end_dt)
                ).select(columns)

                if not df.is_empty():
                    dfs.append(df)

            except Exception as file_e:
                print(f"加载文件 {os.path.basename(file)} 失败: {str(file_e)}")

        if not dfs:
            return pl.DataFrame()

        # 合并所有数据帧
        return pl.concat(dfs)


def load_bar_df(
        data_sources: Union[str, List[str]],
        symbols: Union[str, List[str]],
        start_date: str,
        end_date: str,
        columns: List[str]
) -> pl.DataFrame:
    """
    从CSV文件加载股票数据并组合成DataFrame

    参数:
    data_sources : 单个目录路径或目录路径列表
    symbols      : 单个股票代码或股票代码列表
    start_date   : 起始日期 (包含), 格式 "YYYY-MM-DD"
    end_date     : 结束日期 (包含), 格式 "YYYY-MM-DD"
    columns      : 需要加载的列名列表 (必须包含'date'和'symbol')

    返回:
    pl.DataFrame : 包含所有符合条件数据的Polars DataFrame
    """
    """使用Polars加载并合并数据"""
    all_data = []

    for symbol in symbols:
        dfs = []
        # 准备文件路径
        if type(data_sources) is str:
            data_sources = [data_sources]
        for data_path in data_sources:
            path = os.path.join(data_path, f"{symbol}.csv")
            # 加载历史数据
            df_path = pl.DataFrame()
            if os.path.exists(path):
                df_path = pl.read_csv(path, columns=columns)
                df_path = df_path.with_columns(pl.lit(symbol).cast(pl.Utf8).alias("symbol"))

                df_path = df_path.with_columns(
                    pl.col("date").cast(pl.String),
                    # pl.col("high").cast(pl.Float32),
                    # pl.col("low").cast(pl.Float32),
                    pl.col("close").cast(pl.Float32),
                    #pl.col("circ_mv").cast(pl.Float32),

                )


                print(df_path)

            dfs.append(df_path)

        # 合并数据
        df_combined = pl.concat(dfs, how="vertical")
        # 将日期字符串转换为日期对象
        # start_dt = datetime.strptime(start_date, '%Y%m%d').date()
        # end_dt = datetime.strptime(end_date, '%Y%m%d').date()
        #
        # # 转换日期列


        # # 筛选日期范围
        # df_combined = df_combined.filter(
        #     (pl.col('date') >= start_dt) &
        #     (pl.col('date') <= end_dt)
        # ).select(columns)



        # 筛选日期范围
        if not df_combined.is_empty():
            df_filtered = (
                df_combined
                .filter(
                    (pl.col("date") >= start_date) &
                    (pl.col("date") <= end_date)
                )
                .select(columns)
            )
            # df_filtered = df_filtered.with_columns(
            #     pl.col('date').str.to_date('%Y%m%d').alias('date'),
            # )
            all_data.append(df_filtered)


    # 合并所有股票数据
    if all_data:
        return pl.concat(all_data, how="vertical")

    return pl.DataFrame()

