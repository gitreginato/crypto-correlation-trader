"""Returns: log-return and simple-return calculations.

Aligns multi-asset price data and computes returns for correlation analysis.
"""
from typing import Literal

import numpy as np
import pandas as pd

ReturnMethod = Literal["log", "simple"]


def calculate_returns(
    prices: pd.DataFrame,
    method: ReturnMethod = "log",
) -> pd.DataFrame:
    """Calculate returns from a price DataFrame.

    Args:
        prices: DataFrame where each column is an asset's price series.
        method: "log" for log returns, "simple" for simple returns.

    Returns:
        DataFrame of returns, same columns as input, one fewer row.
    """
    if method not in ("log", "simple"):
        raise ValueError(f"method must be 'log' or 'simple', got '{method}'")

    returns: pd.DataFrame
    if method == "log":
        returns = pd.DataFrame(np.log(prices / prices.shift(1)))
    else:
        returns = prices.pct_change()

    return returns.dropna(how="all")


def align_returns(
    data: pd.DataFrame,
    max_fill_gap: int = 1,
    min_valid_ratio: float = 0.5,
) -> pd.DataFrame:
    """Align multi-asset data by filling gaps and dropping sparse columns.

    Args:
        data: DataFrame with potentially misaligned indices and missing values.
        max_fill_gap: Maximum number of consecutive NaNs to forward-fill.
        min_valid_ratio: Minimum ratio of non-NaN values to keep a column.

    Returns:
        Aligned DataFrame with gaps filled and sparse columns removed.
    """
    # Drop columns with too many NaNs
    valid_ratio = data.notna().sum() / len(data)
    valid_cols = valid_ratio[valid_ratio >= min_valid_ratio].index
    data = data[valid_cols]

    # Forward-fill small gaps, then backward-fill
    data = data.ffill(limit=max_fill_gap)
    data = data.bfill(limit=max_fill_gap)

    # Drop any remaining rows with NaN
    data = data.dropna()

    return data
