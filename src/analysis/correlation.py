"""Correlation: correlation matrix computation.

Supports Pearson, Spearman, and Kendall methods.
Provides rolling correlation, distance matrix, and edge extraction.
"""
from typing import Literal

import numpy as np
import pandas as pd

CorrMethod = Literal["pearson", "spearman", "kendall"]


class CorrelationMatrix:
    """Compute and analyze correlation matrices for asset returns."""

    def __init__(self, method: CorrMethod = "pearson"):
        if method not in ("pearson", "spearman", "kendall"):
            raise ValueError(f"method must be 'pearson', 'spearman', or 'kendall', got '{method}'")
        self.method = method

    def compute(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Compute the correlation matrix.

        Args:
            returns: DataFrame where each column is an asset's return series.

        Returns:
            Square correlation matrix (assets x assets).
        """
        return returns.corr(method=self.method)

    def compute_rolling(
        self,
        returns: pd.DataFrame,
        window: int = 30,
        step: int = 1,
    ) -> dict[pd.Timestamp, pd.DataFrame]:
        """Compute rolling correlation matrices over time.

        Args:
            returns: DataFrame of asset returns.
            window: Rolling window size (number of periods).
            step: Step size between windows (to reduce computation).

        Returns:
            Dict mapping the end-timestamp of each window to its correlation matrix.
        """
        results: dict[pd.Timestamp, pd.DataFrame] = {}
        n = len(returns)
        for i in range(window, n, step):
            window_data = returns.iloc[i - window : i]
            results[returns.index[i]] = window_data.corr(method=self.method)
        return results

    def to_distance_matrix(self, corr: pd.DataFrame) -> pd.DataFrame:
        """Convert correlation matrix to distance matrix.

        Distance: d = sqrt(2 * (1 - corr))

        Args:
            corr: Correlation matrix.

        Returns:
            Distance matrix (same shape, non-negative values).
        """
        distance = np.sqrt(np.clip(2 * (1 - corr), 0, None))
        return pd.DataFrame(distance, index=corr.index, columns=corr.columns)

    def get_edges(
        self,
        corr: pd.DataFrame,
        threshold: float = 0.5,
    ) -> list[tuple[str, str, float]]:
        """Extract edges from correlation matrix above a threshold.

        Args:
            corr: Correlation matrix.
            threshold: Minimum absolute correlation to include an edge.

        Returns:
            List of (symbol1, symbol2, correlation) tuples, upper triangle only.
        """
        edges: list[tuple[str, str, float]] = []
        symbols = corr.columns
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                value = float(corr.iloc[i, j])  # type: ignore[arg-type]
                if abs(value) >= threshold:
                    edges.append((symbols[i], symbols[j], value))
        return edges
