"""行业中性化工具。"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd


logger = logging.getLogger(__name__)


def industry_neutralize_scores(
    scores: pd.Series,
    *,
    metadata: pd.DataFrame,
    industry_column: str = "sw_level2",
) -> pd.Series:
    """对每个行业内的分数做 z-score 中性化（demean / std），然后跨行业重排。

    metadata 至少含 `symbol` 和 industry_column 两列。
    缺行业的标的归到 ``__NA__`` 桶。
    """
    if scores.empty:
        return scores
    if metadata is None or metadata.empty or industry_column not in metadata.columns:
        logger.warning("行业元数据缺失 (column=%s)，跳过中性化", industry_column)
        return scores

    md = metadata.set_index("symbol") if "symbol" in metadata.columns else metadata
    industry = md[industry_column].fillna("__NA__")
    aligned = pd.DataFrame({"score": scores, "industry": industry.reindex(scores.index).fillna("__NA__")})
    aligned = aligned.dropna(subset=["score"])
    if aligned.empty:
        return scores

    grouped = aligned.groupby("industry")["score"]
    z = (aligned["score"] - grouped.transform("mean")) / grouped.transform("std").replace(0.0, pd.NA)
    z = z.fillna(0.0)
    return z.reindex(scores.index).fillna(0.0)
