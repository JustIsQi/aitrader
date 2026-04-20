from __future__ import annotations

from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if not df.empty:
        return df.replace({np.nan: None})
    return df


def clean_dataframes(*dfs: pd.DataFrame):
    cleaned = [clean_dataframe(df) for df in dfs]
    return cleaned if len(cleaned) > 1 else cleaned[0]


def safe_value(value: Any) -> Any:
    if isinstance(value, np.generic):
        value = value.item()
    try:
        if isinstance(value, float) and (pd.isna(value) or np.isnan(value)):
            return None
    except TypeError:
        pass
    return value


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value) or np.isnan(value):
            return None
    except TypeError:
        pass
    return float(value)


def format_date(value: Any, fmt: str = '%Y-%m-%d') -> Any:
    if isinstance(value, (datetime, date)):
        return value.strftime(fmt)
    return value


def format_record_dates(record: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    formatted = {key: safe_value(value) for key, value in record.items()}
    for field, fmt in mapping.items():
        if field in formatted and formatted[field]:
            formatted[field] = format_date(formatted[field], fmt)
    return formatted


def dataframe_to_records(df: pd.DataFrame, date_formats: dict[str, str] | None = None) -> list[dict[str, Any]]:
    if df.empty:
        return []
    cleaned = clean_dataframe(df)
    formats = date_formats or {}
    return [format_record_dates(record, formats) for record in cleaned.to_dict('records')]


def model_to_dict(model: Any) -> dict[str, Any] | None:
    if model is None:
        return None
    result = {}
    for column in model.__table__.columns:
        result[column.name] = safe_value(getattr(model, column.name))
    return result
