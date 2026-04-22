"""
MySQL reader for Wind A-share daily prices and derivative indicators.

The reader keeps the historical-price contract used by DbDataLoader while
moving the source of truth to Wind MySQL tables:
- ASHAREEODPRICES for OHLCV prices.
- ASHAREEODDERIVATIVEINDICATOR for PE/PB/turnover/market-cap fields.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Optional
from urllib.parse import unquote, urlparse

import pandas as pd
import pymysql

DEFAULT_READ_CHUNK_SIZE = 200
MARKET_CAP_UNIT_DIVISOR = 10000.0  # Wind market-cap fields are in 10k RMB; convert to 100M RMB.

_LATEST_TRADE_DATE_CACHE: dict[tuple[str, str], str] = {}
_DERIVATIVE_SNAPSHOT_CACHE: dict[tuple, pd.DataFrame] = {}
_DERIVATIVE_HISTORY_CACHE: dict[tuple, pd.DataFrame] = {}
_STOCK_METADATA_CACHE: dict[tuple, pd.DataFrame] = {}


PRICE_COLUMNS = [
    "date",
    "symbol",
    "real_open",
    "real_close",
    "real_low",
    "open",
    "close",
    "high",
    "low",
    "vwap",
    "volume",
    "amount",
    "change_pct",
    "turnover_rate",
    "free_turnover_rate",
    "pe",
    "pe_ttm",
    "pb",
    "ps",
    "ps_ttm",
    "total_mv",
    "circ_mv",
    "total_shares",
    "float_shares",
    "free_shares",
    "up_down_limit_status",
]

DERIVATIVE_COLUMNS = [
    "date",
    "symbol",
    "pe_ratio",
    "pe_ttm",
    "pb_ratio",
    "ps_ratio",
    "ps_ttm",
    "total_mv",
    "circ_mv",
    "turnover_rate",
    "free_turnover_rate",
    "total_shares",
    "float_shares",
    "free_shares",
    "up_down_limit_status",
]

METADATA_COLUMNS = [
    "symbol",
    "name",
    "list_date",
    "delist_date",
    "list_board_name",
    "sw_ind_name",
    "sector",
    "sw_level2",
    "industry",
]


class MySQLAshareReaderConfigError(RuntimeError):
    """Raised when MySQL reader configuration is incomplete."""


class MySQLAshareReaderQueryError(RuntimeError):
    """Raised when the MySQL price query fails."""


@dataclass(frozen=True)
class MySQLAshareReaderConfig:
    """Connection configuration for the Wind MySQL database."""

    mysql_url: Optional[str] = None
    host: Optional[str] = None
    port: int = 3306
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None

    @classmethod
    def from_env(cls) -> "MySQLAshareReaderConfig":
        # Ensure direct script entrypoints (for example research runners) pick up
        # the project .env without requiring users to source it in the shell.
        try:
            from aitrader.infrastructure.config.settings import get_settings

            get_settings()
        except Exception:
            pass

        port = os.getenv("MYSQL_PORT", "3306").strip()
        try:
            parsed_port = int(port)
        except ValueError as exc:
            raise MySQLAshareReaderConfigError("MYSQL_PORT must be an integer") from exc

        def clean_env(name: str) -> Optional[str]:
            value = os.getenv(name)
            return value.strip() if value else None

        return cls(
            mysql_url=clean_env("MYSQL_URL"),
            host=clean_env("MYSQL_HOST"),
            port=parsed_port,
            user=clean_env("MYSQL_USER"),
            password=clean_env("MYSQL_PASSWORD"),
            database=clean_env("MYSQL_DATABASE"),
        )

    def to_connection_kwargs(self) -> dict:
        if self.mysql_url:
            parsed = urlparse(self.mysql_url)
            return {
                "host": parsed.hostname,
                "port": parsed.port or 3306,
                "user": unquote(parsed.username or ""),
                "password": unquote(parsed.password or ""),
                "database": parsed.path.lstrip("/"),
            }

        missing = [
            name
            for name, value in {
                "MYSQL_HOST": self.host,
                "MYSQL_USER": self.user,
                "MYSQL_PASSWORD": self.password,
                "MYSQL_DATABASE": self.database,
            }.items()
            if not value
        ]
        if missing:
            missing_list = ", ".join(missing)
            raise MySQLAshareReaderConfigError(
                "Missing MySQL configuration. Set MYSQL_URL or provide "
                f"all component variables: {missing_list}"
            )

        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
        }


class MySQLAshareReader:
    """Read A-share daily price and derivative data from Wind MySQL tables."""

    def __init__(
        self,
        config: Optional[MySQLAshareReaderConfig] = None,
        mysql_url: Optional[str] = None,
        connection_factory: Callable[..., object] = pymysql.connect,
    ):
        self.config = config or (
            MySQLAshareReaderConfig(mysql_url=mysql_url)
            if mysql_url
            else MySQLAshareReaderConfig.from_env()
        )
        self.connection_factory = connection_factory

    def _batched(self, items: list[str], batch_size: int):
        for start in range(0, len(items), batch_size):
            yield items[start:start + batch_size]

    def connect(self):
        kwargs = self.config.to_connection_kwargs()
        return self.connection_factory(
            **kwargs,
            connect_timeout=10,
            read_timeout=120,
            write_timeout=120,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )

    def read_prices(
        self,
        symbols: Iterable[str],
        start_date: str,
        end_date: str,
        include_derivatives: bool = True,
    ) -> pd.DataFrame:
        symbols = sorted({symbol for symbol in symbols if symbol})
        if not symbols:
            return pd.DataFrame(columns=PRICE_COLUMNS)

        query, params = self.build_price_only_query(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
        )

        try:
            price_df = self.read_query(query, params)
            if include_derivatives:
                derivative_df = self.read_derivative_indicator_history(
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                )
                if not derivative_df.empty:
                    derivative_df = derivative_df.rename(
                        columns={
                            "date": "trade_date",
                            "symbol": "stock_code",
                            "pe_ratio": "pe",
                            "pb_ratio": "pb",
                            "pb_ratio": "pb",
                            "ps_ratio": "ps",
                        }
                    )
                    derivative_df["trade_date"] = derivative_df["trade_date"].astype(str).str.replace("-", "")
                    for column in ("total_mv", "circ_mv"):
                        if column in derivative_df.columns:
                            derivative_df[column] = pd.to_numeric(derivative_df[column], errors="coerce") * MARKET_CAP_UNIT_DIVISOR
                    merge_columns = [
                        "trade_date",
                        "stock_code",
                        "turnover_rate",
                        "free_turnover_rate",
                        "pe",
                        "pe_ttm",
                        "pb",
                        "ps",
                        "ps_ttm",
                        "total_mv",
                        "circ_mv",
                        "total_shares",
                        "float_shares",
                        "free_shares",
                        "up_down_limit_status",
                    ]
                    derivative_df = derivative_df[merge_columns]
                    price_df = price_df.merge(
                        derivative_df,
                        on=["trade_date", "stock_code"],
                        how="left",
                    )
        except Exception as exc:
            raise MySQLAshareReaderQueryError(
                "Failed to read A-share prices from MySQL"
            ) from exc

        return self.normalize_prices(price_df)

    def read_latest_derivative_indicators(
        self,
        symbols: Optional[Iterable[str]] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Read the latest derivative-indicator row per symbol up to end_date."""
        normalized_symbols = sorted({symbol for symbol in (symbols or []) if symbol})
        end_bound = self._normalize_bound(end_date or datetime.now().strftime("%Y%m%d"))
        trade_date = self.get_latest_trade_date(end_bound=end_bound)
        cache_key = (tuple(normalized_symbols), trade_date)
        cached = _DERIVATIVE_SNAPSHOT_CACHE.get(cache_key)
        if cached is not None:
            return cached.copy()

        try:
            frames: list[pd.DataFrame] = []
            if normalized_symbols:
                for batch in self._batched(normalized_symbols, DEFAULT_READ_CHUNK_SIZE):
                    query, params = self.build_derivative_snapshot_query(
                        symbols=batch,
                        trade_date=trade_date,
                    )
                    df = self.read_query(query, params)
                    if not df.empty:
                        frames.append(df)
            else:
                query, params = self.build_derivative_snapshot_query(
                    symbols=None,
                    trade_date=trade_date,
                )
                df = self.read_query(query, params)
                if not df.empty:
                    frames.append(df)
        except Exception as exc:
            raise MySQLAshareReaderQueryError(
                "Failed to read A-share derivative indicators from MySQL"
            ) from exc

        merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        normalized = self.normalize_derivative_indicators(merged)
        _DERIVATIVE_SNAPSHOT_CACHE[cache_key] = normalized
        return normalized.copy()

    def read_derivative_indicator_history(
        self,
        symbols: Iterable[str],
        start_date: str,
        end_date: str,
        chunk_size: int = DEFAULT_READ_CHUNK_SIZE,
    ) -> pd.DataFrame:
        normalized_symbols = sorted({symbol for symbol in symbols if symbol})
        if not normalized_symbols:
            return pd.DataFrame(columns=DERIVATIVE_COLUMNS)

        start_bound = self._normalize_bound(start_date)
        end_bound = self._normalize_bound(end_date)
        cache_key = (tuple(normalized_symbols), start_bound, end_bound)
        cached = _DERIVATIVE_HISTORY_CACHE.get(cache_key)
        if cached is not None:
            return cached.copy()

        frames: list[pd.DataFrame] = []
        try:
            for batch in self._batched(normalized_symbols, chunk_size):
                query, params = self.build_derivative_history_query(
                    symbols=batch,
                    start_date=start_bound,
                    end_date=end_bound,
                )
                df = self.read_query(query, params)
                if not df.empty:
                    frames.append(df)
        except Exception as exc:
            raise MySQLAshareReaderQueryError(
                "Failed to read A-share derivative-indicator history from MySQL"
            ) from exc

        merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        normalized = self.normalize_derivative_indicators(merged)
        _DERIVATIVE_HISTORY_CACHE[cache_key] = normalized
        return normalized.copy()

    def get_latest_trade_date(self, end_bound: Optional[str] = None) -> str:
        end_bound = self._normalize_bound(end_bound or datetime.now().strftime("%Y%m%d"))
        cache_key = ("ASHAREEODPRICES", end_bound)
        cached = _LATEST_TRADE_DATE_CACHE.get(cache_key)
        if cached is not None:
            return cached

        query = """
            SELECT MAX(TRADE_DT) AS trade_date
            FROM ASHAREEODPRICES
            WHERE TRADE_DT <= %s
        """
        df = self.read_query(query, [end_bound])
        trade_date = ""
        if not df.empty:
            trade_date = str(df.iloc[0]["trade_date"] or "")
        if not trade_date:
            raise MySQLAshareReaderQueryError(
                f"Failed to resolve latest Wind trade date up to {end_bound}"
            )
        _LATEST_TRADE_DATE_CACHE[cache_key] = trade_date
        return trade_date

    def read_stock_metadata(
        self,
        symbols: Optional[Iterable[str]] = None,
        as_of_date: Optional[str] = None,
        chunk_size: int = DEFAULT_READ_CHUNK_SIZE,
    ) -> pd.DataFrame:
        normalized_symbols = sorted({symbol for symbol in (symbols or []) if symbol})
        as_of_bound = self._normalize_bound(as_of_date or datetime.now().strftime("%Y%m%d"))
        cache_key = (tuple(normalized_symbols), as_of_bound)
        cached = _STOCK_METADATA_CACHE.get(cache_key)
        if cached is not None:
            return cached.copy()

        frames: list[pd.DataFrame] = []
        try:
            if normalized_symbols:
                for batch in self._batched(normalized_symbols, chunk_size):
                    query, params = self.build_stock_metadata_query(
                        symbols=batch,
                        as_of_date=as_of_bound,
                    )
                    df = self.read_query(query, params)
                    if not df.empty:
                        frames.append(df)
            else:
                query, params = self.build_stock_metadata_query(
                    symbols=None,
                    as_of_date=as_of_bound,
                )
                df = self.read_query(query, params)
                if not df.empty:
                    frames.append(df)
        except Exception as exc:
            raise MySQLAshareReaderQueryError(
                "Failed to read A-share metadata from MySQL"
            ) from exc

        merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        normalized = self.normalize_stock_metadata(merged)
        _STOCK_METADATA_CACHE[cache_key] = normalized
        return normalized.copy()

    def normalize_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=PRICE_COLUMNS)

        df = df.copy()
        df.rename(
            columns={
                "trade_date": "date",
                "stock_code": "symbol",
            },
            inplace=True,
        )

        optional_columns = {
            "amount",
            "change_pct",
            "turnover_rate",
            "free_turnover_rate",
            "pe",
            "pe_ttm",
            "pb",
            "ps",
            "ps_ttm",
            "total_mv",
            "circ_mv",
            "total_shares",
            "float_shares",
            "free_shares",
            "up_down_limit_status",
        }
        for column in optional_columns:
            if column not in df.columns:
                df[column] = pd.NA

        missing = [
            column
            for column in PRICE_COLUMNS
            if column not in df.columns and column not in optional_columns
        ]
        if missing:
            missing_list = ", ".join(missing)
            raise MySQLAshareReaderQueryError(
                f"MySQL price query returned missing columns: {missing_list}"
            )

        df["date"] = pd.to_datetime(
            df["date"].astype(str),
            format="%Y%m%d",
            errors="coerce",
        ).dt.strftime("%Y%m%d")
        df["symbol"] = df["symbol"].astype(str)
        self._coerce_numeric_columns(df, exclude={"date", "symbol"})
        self._normalize_market_cap_units(df)
        df = df[PRICE_COLUMNS].sort_values(["symbol", "date"]).reset_index(drop=True)
        return df

    def normalize_derivative_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=DERIVATIVE_COLUMNS)

        df = df.copy()
        df.rename(
            columns={
                "trade_date": "date",
                "stock_code": "symbol",
            },
            inplace=True,
        )

        for column in DERIVATIVE_COLUMNS:
            if column not in df.columns:
                df[column] = pd.NA

        df["date"] = pd.to_datetime(
            df["date"].astype(str),
            format="%Y%m%d",
            errors="coerce",
        ).dt.strftime("%Y-%m-%d")
        df["symbol"] = df["symbol"].astype(str)
        self._coerce_numeric_columns(df, exclude={"date", "symbol"})
        self._normalize_market_cap_units(df)
        return df[DERIVATIVE_COLUMNS].sort_values(["symbol", "date"]).reset_index(drop=True)

    def normalize_stock_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=METADATA_COLUMNS)

        df = df.copy()
        df.rename(
            columns={
                "stock_code": "symbol",
                "stock_name": "name",
            },
            inplace=True,
        )

        for column in METADATA_COLUMNS:
            if column not in df.columns:
                df[column] = pd.NA

        df["symbol"] = df["symbol"].astype(str)
        for column in ("name", "list_board_name", "sw_ind_name"):
            df[column] = df[column].astype("string").str.strip()
            df[column] = df[column].replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})

        for column in ("list_date", "delist_date"):
            df[column] = pd.to_datetime(
                df[column].astype("string").str.strip(),
                format="%Y%m%d",
                errors="coerce",
            ).dt.strftime("%Y-%m-%d")

        parsed = df["sw_ind_name"].apply(self._parse_sw_industry_path)
        parsed_df = pd.DataFrame(parsed.tolist(), columns=["sector", "sw_level2", "industry"])
        df[["sector", "sw_level2", "industry"]] = parsed_df

        return (
            df[METADATA_COLUMNS]
            .drop_duplicates(subset=["symbol"], keep="first")
            .sort_values("symbol")
            .reset_index(drop=True)
        )

    def read_query(self, query: str, params: list) -> pd.DataFrame:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
        return pd.DataFrame(rows)

    def build_price_only_query(
        self,
        symbols: Optional[Iterable[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        codes = list(symbols or [])
        placeholders = ", ".join(["%s"] * len(codes)) or "NULL"
        query = f"""
            SELECT
                p.TRADE_DT AS trade_date,
                p.S_INFO_WINDCODE AS stock_code,
                p.S_DQ_OPEN AS real_open,
                p.S_DQ_CLOSE AS real_close,
                p.S_DQ_LOW AS real_low,
                p.S_DQ_ADJOPEN AS open,
                p.S_DQ_ADJCLOSE AS close,
                p.S_DQ_ADJHIGH AS high,
                p.S_DQ_ADJLOW AS low,
                p.S_DQ_AVGPRICE AS vwap,
                p.S_DQ_VOLUME AS volume,
                p.S_DQ_AMOUNT AS amount,
                p.S_DQ_PCTCHANGE AS change_pct
            FROM ASHAREEODPRICES p
            WHERE p.S_INFO_WINDCODE IN ({placeholders})
              AND p.TRADE_DT >= %s
              AND p.TRADE_DT <= %s
            ORDER BY p.S_INFO_WINDCODE ASC, p.TRADE_DT ASC
            """
        params = [
            *codes,
            self._normalize_bound(start_date or "19000101"),
            self._normalize_bound(end_date or datetime.now().strftime("%Y%m%d")),
        ]
        return query, params

    def build_derivative_history_query(
        self,
        symbols: Optional[Iterable[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        codes = list(symbols or [])
        placeholders = ", ".join(["%s"] * len(codes)) or "NULL"
        query = f"""
            SELECT
                d.TRADE_DT AS trade_date,
                d.S_INFO_WINDCODE AS stock_code,
                d.S_VAL_PE AS pe_ratio,
                d.S_VAL_PE_TTM AS pe_ttm,
                d.S_VAL_PB_NEW AS pb_ratio,
                d.S_VAL_PS AS ps_ratio,
                d.S_VAL_PS_TTM AS ps_ttm,
                d.S_VAL_MV AS total_mv,
                d.S_DQ_MV AS circ_mv,
                d.S_DQ_TURN AS turnover_rate,
                d.S_DQ_FREETURNOVER AS free_turnover_rate,
                d.TOT_SHR_TODAY AS total_shares,
                d.FLOAT_A_SHR_TODAY AS float_shares,
                d.FREE_SHARES_TODAY AS free_shares,
                d.UP_DOWN_LIMIT_STATUS AS up_down_limit_status
            FROM ASHAREEODDERIVATIVEINDICATOR d FORCE INDEX (WIDX214134828_DATE_WINDCODE_WI)
            WHERE d.TRADE_DT >= %s
              AND d.TRADE_DT <= %s
              AND d.S_INFO_WINDCODE IN ({placeholders})
            ORDER BY d.S_INFO_WINDCODE ASC, d.TRADE_DT ASC
        """
        params = [
            self._normalize_bound(start_date or "19000101"),
            self._normalize_bound(end_date or datetime.now().strftime("%Y%m%d")),
            *codes,
        ]
        return query, params

    def build_derivative_snapshot_query(
        self,
        symbols: Optional[Iterable[str]],
        trade_date: str,
    ):
        codes = list(symbols or [])
        filter_codes = bool(codes)
        placeholders = ", ".join(["%s"] * len(codes)) or "NULL"
        code_filter = f"AND d.S_INFO_WINDCODE IN ({placeholders})" if filter_codes else ""
        query = f"""
            SELECT
                d.TRADE_DT AS trade_date,
                d.S_INFO_WINDCODE AS stock_code,
                d.S_VAL_PE AS pe_ratio,
                d.S_VAL_PE_TTM AS pe_ttm,
                d.S_VAL_PB_NEW AS pb_ratio,
                d.S_VAL_PS AS ps_ratio,
                d.S_VAL_PS_TTM AS ps_ttm,
                d.S_VAL_MV AS total_mv,
                d.S_DQ_MV AS circ_mv,
                d.S_DQ_TURN AS turnover_rate,
                d.S_DQ_FREETURNOVER AS free_turnover_rate,
                d.TOT_SHR_TODAY AS total_shares,
                d.FLOAT_A_SHR_TODAY AS float_shares,
                d.FREE_SHARES_TODAY AS free_shares,
                d.UP_DOWN_LIMIT_STATUS AS up_down_limit_status
            FROM ASHAREEODDERIVATIVEINDICATOR d FORCE INDEX (WIDX214134828_DATE_WINDCODE_WI)
            WHERE d.TRADE_DT = %s
            {code_filter}
            ORDER BY d.S_INFO_WINDCODE ASC
        """
        params = [self._normalize_bound(trade_date)]
        if filter_codes:
            params.extend(codes)
        return query, params

    def build_stock_metadata_query(
        self,
        symbols: Optional[Iterable[str]] = None,
        as_of_date: Optional[str] = None,
    ):
        codes = list(symbols or [])
        filter_codes = bool(codes)
        placeholders = ", ".join(["%s"] * len(codes)) or "NULL"
        code_filter = f"AND d.S_INFO_WINDCODE IN ({placeholders})" if filter_codes else ""
        as_of_bound = self._normalize_bound(as_of_date or datetime.now().strftime("%Y%m%d"))
        query = f"""
            SELECT
                d.S_INFO_WINDCODE AS stock_code,
                COALESCE(NULLIF(CAST(i.S_INFO_NAME AS CHAR), ''), d.S_INFO_NAME) AS stock_name,
                COALESCE(NULLIF(CAST(i.S_INFO_LISTDATE AS CHAR), ''), d.S_INFO_LISTDATE) AS list_date,
                COALESCE(NULLIF(CAST(i.S_INFO_DELISTDATE AS CHAR), ''), d.S_INFO_DELISTDATE) AS delist_date,
                COALESCE(NULLIF(CAST(i.S_INFO_LISTBOARDNAME AS CHAR), ''), d.S_INFO_LISTBOARDNAME) AS list_board_name,
                CAST(i.SW_IND_NAME AS CHAR) AS sw_ind_name
            FROM ASHAREDESCRIPTION d
            LEFT JOIN ASHAREINTRODUCTIONE_EXT_DF i
              ON i.S_INFO_WINDCODE = d.S_INFO_WINDCODE
            WHERE d.S_INFO_WINDCODE REGEXP '^[0-9]{{6}}\\.(SH|SZ|BJ)$'
              AND d.S_INFO_LISTDATE IS NOT NULL
              AND d.S_INFO_LISTDATE <> ''
              AND d.S_INFO_LISTDATE <= %s
              AND (
                    d.S_INFO_DELISTDATE IS NULL
                    OR d.S_INFO_DELISTDATE = ''
                    OR d.S_INFO_DELISTDATE >= %s
                  )
              {code_filter}
            ORDER BY d.S_INFO_WINDCODE ASC
        """
        params = [as_of_bound, as_of_bound]
        if filter_codes:
            params.extend(codes)
        return query, params

    def build_latest_derivative_query(
        self,
        symbols: Optional[Iterable[str]] = None,
        end_date: Optional[str] = None,
        filter_codes: Optional[bool] = None,
    ):
        codes = list(symbols or [])
        if filter_codes is None:
            filter_codes = bool(codes)
        placeholders = ", ".join(["%s"] * len(codes)) or "NULL"
        code_filter = f"AND S_INFO_WINDCODE IN ({placeholders})" if filter_codes else ""
        query = f"""
            SELECT
                d.TRADE_DT AS trade_date,
                d.S_INFO_WINDCODE AS stock_code,
                d.S_VAL_PE AS pe_ratio,
                d.S_VAL_PE_TTM AS pe_ttm,
                d.S_VAL_PB_NEW AS pb_ratio,
                d.S_VAL_PS AS ps_ratio,
                d.S_VAL_PS_TTM AS ps_ttm,
                d.S_VAL_MV AS total_mv,
                d.S_DQ_MV AS circ_mv,
                d.S_DQ_TURN AS turnover_rate,
                d.S_DQ_FREETURNOVER AS free_turnover_rate,
                d.TOT_SHR_TODAY AS total_shares,
                d.FLOAT_A_SHR_TODAY AS float_shares,
                d.FREE_SHARES_TODAY AS free_shares,
                d.UP_DOWN_LIMIT_STATUS AS up_down_limit_status
            FROM ASHAREEODDERIVATIVEINDICATOR d
            JOIN (
                SELECT
                    S_INFO_WINDCODE,
                    MAX(TRADE_DT) AS TRADE_DT
                FROM ASHAREEODDERIVATIVEINDICATOR
                WHERE TRADE_DT <= %s
                {code_filter}
                GROUP BY S_INFO_WINDCODE
            ) latest
              ON latest.S_INFO_WINDCODE = d.S_INFO_WINDCODE
             AND latest.TRADE_DT = d.TRADE_DT
            ORDER BY d.S_INFO_WINDCODE ASC, d.TRADE_DT ASC
            """
        params = [self._normalize_bound(end_date or datetime.now().strftime("%Y%m%d"))]
        if filter_codes:
            params.extend(codes)
        return query, params

    def _normalize_bound(self, value: str) -> str:
        return str(value).replace("-", "")

    def _parse_sw_industry_path(self, value: object) -> tuple[object, object, object]:
        if value is None or pd.isna(value):
            return pd.NA, pd.NA, pd.NA

        parts = [part.strip() for part in str(value).split("-") if part and part.strip()]
        if parts and "申万行业分类" in parts[0]:
            parts = parts[1:]
        if not parts:
            return pd.NA, pd.NA, pd.NA

        sector = parts[0]
        sw_level2 = parts[1] if len(parts) > 1 else pd.NA
        industry = parts[-1]
        return sector, sw_level2, industry

    def _normalize_market_cap_units(self, df: pd.DataFrame) -> None:
        for column in ("total_mv", "circ_mv"):
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors="coerce") / MARKET_CAP_UNIT_DIVISOR

    def _coerce_numeric_columns(self, df: pd.DataFrame, exclude: set[str]) -> None:
        for column in df.columns:
            if column not in exclude:
                df[column] = pd.to_numeric(df[column], errors="coerce")
