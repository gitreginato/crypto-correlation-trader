"""Universe: definition of tradable assets.

Filters Binance symbols by volume, quote asset, and history length.
Provides a default universe of major USDT pairs with metadata.
"""
from typing import Optional

# Default universe: top USDT pairs by volume and reliability
DEFAULT_UNIVERSE = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "DOTUSDT",
    "MATICUSDT", "TRXUSDT", "LTCUSDT", "BCHUSDT", "ATOMUSDT",
    "UNIUSDT", "NEARUSDT", "APTUSDT", "FILUSDT", "ARBUSDT",
    "OPUSDT", "INJUSDT", "SUIUSDT", "SEIUSDT", "TIAUSDT",
]

# Metadata for known symbols (category for grouping)
SYMBOL_METADATA = {
    "BTCUSDT": {"symbol": "BTCUSDT", "category": "large_cap", "name": "Bitcoin"},
    "ETHUSDT": {"symbol": "ETHUSDT", "category": "large_cap", "name": "Ethereum"},
    "BNBUSDT": {"symbol": "BNBUSDT", "category": "exchange_token", "name": "BNB"},
    "SOLUSDT": {"symbol": "SOLUSDT", "category": "large_cap", "name": "Solana"},
    "XRPUSDT": {"symbol": "XRPUSDT", "category": "large_cap", "name": "Ripple"},
    "ADAUSDT": {"symbol": "ADAUSDT", "category": "large_cap", "name": "Cardano"},
    "AVAXUSDT": {"symbol": "AVAXUSDT", "category": "mid_cap", "name": "Avalanche"},
    "DOGEUSDT": {"symbol": "DOGEUSDT", "category": "meme", "name": "Dogecoin"},
    "LINKUSDT": {"symbol": "LINKUSDT", "category": "oracle", "name": "Chainlink"},
    "DOTUSDT": {"symbol": "DOTUSDT", "category": "large_cap", "name": "Polkadot"},
    "MATICUSDT": {"symbol": "MATICUSDT", "category": "large_cap", "name": "Polygon"},
    "TRXUSDT": {"symbol": "TRXUSDT", "category": "large_cap", "name": "TRON"},
    "LTCUSDT": {"symbol": "LTCUSDT", "category": "large_cap", "name": "Litecoin"},
    "BCHUSDT": {"symbol": "BCHUSDT", "category": "large_cap", "name": "Bitcoin Cash"},
    "ATOMUSDT": {"symbol": "ATOMUSDT", "category": "mid_cap", "name": "Cosmos"},
    "UNIUSDT": {"symbol": "UNIUSDT", "category": "defi", "name": "Uniswap"},
    "NEARUSDT": {"symbol": "NEARUSDT", "category": "mid_cap", "name": "NEAR Protocol"},
    "APTUSDT": {"symbol": "APTUSDT", "category": "mid_cap", "name": "Aptos"},
    "FILUSDT": {"symbol": "FILUSDT", "category": "mid_cap", "name": "Filecoin"},
    "ARBUSDT": {"symbol": "ARBUSDT", "category": "layer2", "name": "Arbitrum"},
    "OPUSDT": {"symbol": "OPUSDT", "category": "layer2", "name": "Optimism"},
    "INJUSDT": {"symbol": "INJUSDT", "category": "defi", "name": "Injective"},
    "SUIUSDT": {"symbol": "SUIUSDT", "category": "mid_cap", "name": "Sui"},
    "SEIUSDT": {"symbol": "SEIUSDT", "category": "mid_cap", "name": "Sei"},
    "TIAUSDT": {"symbol": "TIAUSDT", "category": "layer2", "name": "Celestia"},
}


class Universe:
    """Defines the set of tradable assets for the bot."""

    def __init__(
        self,
        min_volume_usd: float = 1e8,
        min_history_days: int = 365,
        max_symbols: int = 50,
        quote_asset: str = "USDT",
    ):
        self.min_volume_usd = min_volume_usd
        self.min_history_days = min_history_days
        self.max_symbols = max_symbols
        self.quote_asset = quote_asset

    def filter_symbols(self, ticker_data: list[dict]) -> list[str]:
        """Filter symbols from Binance 24h ticker data.

        Args:
            ticker_data: List of dicts from GET /api/v3/ticker/24hr

        Returns:
            List of symbol names, filtered and sorted by volume descending.
        """
        candidates = []
        for ticker in ticker_data:
            symbol = ticker.get("symbol", "")
            if not symbol.endswith(self.quote_asset):
                continue
            try:
                volume = float(ticker.get("quoteVolume", 0))
            except (ValueError, TypeError):
                continue
            if volume >= self.min_volume_usd:
                candidates.append((symbol, volume))

        candidates.sort(key=lambda x: x[1], reverse=True)
        symbols = [s for s, _ in candidates[: self.max_symbols]]
        return symbols

    def get_default_universe(self) -> list[str]:
        """Return the predefined default universe of major USDT pairs."""
        return DEFAULT_UNIVERSE.copy()

    def get_metadata(self, symbol: str) -> Optional[dict]:
        """Return metadata for a known symbol, or None if unknown."""
        return SYMBOL_METADATA.get(symbol)

    def get_all_metadata(self) -> dict[str, dict]:
        """Return metadata for all known symbols."""
        return SYMBOL_METADATA.copy()
