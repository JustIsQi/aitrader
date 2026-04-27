"""价格面板加载器 + parquet 持久化缓存。"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from aitrader.infrastructure.market_data.mysql_reader import MySQLAshareReader


logger = logging.getLogger(__name__)


_DEFAULT_CACHE_DIR = (
    Path(__file__).resolve().parents[5]
    / "papers"
    / "arxiv"
    / "processed"
    / "_cache"
)


def _normalize_date(value: pd.Timestamp | str) -> str:
    return pd.Timestamp(value).strftime("%Y%m%d")


@dataclass
class PricePanels:
    """价格面板集合（多维度复权 / 不复权 / 流动性 / 涨跌停）。"""

    close_adj: pd.DataFrame  # 后复权收盘
    open_adj: pd.DataFrame   # 后复权开盘
    high_adj: pd.DataFrame
    low_adj: pd.DataFrame
    close_unadj: pd.DataFrame  # 真实收盘（用于涨跌停判定）
    open_unadj: pd.DataFrame
    volume: pd.DataFrame
    amount: pd.DataFrame
    up_down_limit_status: pd.DataFrame  # +/-1 涨跌停, 0 正常, NaN 无数据

    @property
    def trade_dates(self) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(self.close_adj.index)

    @property
    def symbols(self) -> list[str]:
        return list(self.close_adj.columns)

    def returns(self) -> pd.DataFrame:
        """复权收盘日收益率（首行 NaN）。"""
        return self.close_adj.pct_change()

    def restrict(self, symbols: Iterable[str]) -> "PricePanels":
        """裁剪到给定股票子集，缺失列填 NaN。"""
        symbols = list(symbols)
        return PricePanels(
            close_adj=self.close_adj.reindex(columns=symbols),
            open_adj=self.open_adj.reindex(columns=symbols),
            high_adj=self.high_adj.reindex(columns=symbols),
            low_adj=self.low_adj.reindex(columns=symbols),
            close_unadj=self.close_unadj.reindex(columns=symbols),
            open_unadj=self.open_unadj.reindex(columns=symbols),
            volume=self.volume.reindex(columns=symbols),
            amount=self.amount.reindex(columns=symbols),
            up_down_limit_status=self.up_down_limit_status.reindex(columns=symbols),
        )


class PanelLoader:
    """从 Wind MySQL 加载多维度价格面板，带 parquet 持久化缓存。"""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        reader: Optional[MySQLAshareReader] = None,
    ) -> None:
        self.cache_dir = Path(cache_dir or _DEFAULT_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._reader = reader or MySQLAshareReader()
        self._memory_cache: dict[str, pd.DataFrame] = {}

    def _cache_path(self, symbols: list[str], start_date: str, end_date: str) -> Path:
        key_src = "|".join(sorted(symbols)) + f"|{start_date}|{end_date}"
        digest = hashlib.sha256(key_src.encode("utf-8")).hexdigest()[:16]
        n = len(symbols)
        return self.cache_dir / f"prices_n{n}_{start_date}_{end_date}_{digest}.parquet"

    def load_long(
        self,
        symbols: Iterable[str],
        start_date: pd.Timestamp | str,
        end_date: pd.Timestamp | str,
    ) -> pd.DataFrame:
        """返回 long format 的价格 DataFrame，缓存命中时不查 MySQL。"""
        unique = sorted({s for s in symbols if s})
        if not unique:
            raise ValueError("没有可读取的股票代码")

        start_norm = _normalize_date(start_date)
        end_norm = _normalize_date(end_date)
        path = self._cache_path(unique, start_norm, end_norm)
        memory_key = str(path)
        if memory_key in self._memory_cache:
            return self._memory_cache[memory_key].copy()
        if path.exists():
            logger.info("价格面板缓存命中: %s", path.name)
            df = pd.read_parquet(path)
            self._memory_cache[memory_key] = df
            return df.copy()

        logger.info(
            "价格面板缓存未命中，查询 MySQL: n=%d, %s ~ %s",
            len(unique),
            start_norm,
            end_norm,
        )
        df = self._reader.read_prices(
            symbols=unique,
            start_date=start_norm,
            end_date=end_norm,
            include_derivatives=True,
        )
        if df.empty:
            raise ValueError(
                f"价格表中未读取到数据: {start_norm} ~ {end_norm}, 标的数={len(unique)}"
            )

        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
        df = df.dropna(subset=["date"]).reset_index(drop=True)

        try:
            df.to_parquet(path, index=False)
            logger.info("价格面板已缓存: %s", path.name)
        except Exception as exc:  # 缓存失败不阻塞主流程
            logger.warning("写入 parquet 缓存失败: %s", exc)

        self._memory_cache[memory_key] = df
        return df.copy()

    def load_panels(
        self,
        symbols: Iterable[str],
        start_date: pd.Timestamp | str,
        end_date: pd.Timestamp | str,
    ) -> PricePanels:
        """返回多维度面板。"""
        long_df = self.load_long(symbols, start_date, end_date)
        long_df = long_df.sort_values(["date", "symbol"])

        def pivot(field: str, ffill: bool = False) -> pd.DataFrame:
            if field not in long_df.columns:
                return pd.DataFrame()
            panel = long_df.pivot_table(
                index="date",
                columns="symbol",
                values=field,
                aggfunc="last",
            ).sort_index()
            if ffill:
                panel = panel.ffill()
            return panel

        return PricePanels(
            close_adj=pivot("close", ffill=True),
            open_adj=pivot("open", ffill=True),
            high_adj=pivot("high", ffill=True),
            low_adj=pivot("low", ffill=True),
            close_unadj=pivot("real_close", ffill=False),
            open_unadj=pivot("real_open", ffill=False),
            volume=pivot("volume"),
            amount=pivot("amount"),
            up_down_limit_status=pivot("up_down_limit_status"),
        )
