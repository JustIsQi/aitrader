"""
Cross Section Operators
"""

import polars as pl

from .utility import DataProxy


def cs_rank(feature: DataProxy) -> DataProxy:
    """Perform cross-sectional ranking"""
    df: pl.DataFrame = feature.df.select(
        pl.col("date"),
        pl.col("symbol"),
        pl.col("data").rank().over("date")
    )
    return DataProxy(df)


def cs_mean(feature: DataProxy) -> DataProxy:
    """Calculate cross-sectional mean"""
    df: pl.DataFrame = feature.df.select(
        pl.col("date"),
        pl.col("symbol"),
        pl.col("data").mean().over("date")
    )
    return DataProxy(df)


def cs_std(feature: DataProxy) -> DataProxy:
    """Calculate cross-sectional standard deviation"""
    df: pl.DataFrame = feature.df.select(
        pl.col("date"),
        pl.col("symbol"),
        pl.col("data").std().over("date")
    )
    return DataProxy(df)
