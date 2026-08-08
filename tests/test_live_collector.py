"""Tests for LiveCollector and CollectorConfig: initialization and configuration.

Covers config defaults, custom config, buffer setup, and output directory creation.
No network I/O is exercised; only synchronous initialization logic is tested.
"""
from pathlib import Path

import pytest

from src.data.live_collector import CollectorConfig, LiveCollector
from src.data.universe import DEFAULT_UNIVERSE, Universe


# Buffer categories expected in a fully initialized LiveCollector
EXPECTED_BUFFERS: list[str] = [
    "order_book",
    "trades",
    "funding",
    "liquidations",
    "open_interest",
    "long_short",
    "fear_greed",
]


class TestCollectorConfigDefaults:
    def test_default_symbols_come_from_universe(self):
        """Default symbols must be the first 5 entries of Universe default, not hardcoded."""
        config = CollectorConfig()
        expected = Universe().get_default_universe()[:5]
        assert config.symbols == expected

    def test_default_symbols_are_first_five_of_default_universe(self):
        """Default symbols must equal DEFAULT_UNIVERSE[:5] (Universe returns a copy)."""
        config = CollectorConfig()
        assert config.symbols == DEFAULT_UNIVERSE[:5]

    def test_default_symbols_count_is_five(self):
        """Default config must select exactly 5 symbols."""
        config = CollectorConfig()
        assert len(config.symbols) == 5

    def test_default_symbols_are_uppercase_binance_pairs(self):
        """Default symbols should be uppercase USDT pairs as defined by Universe."""
        config = CollectorConfig()
        for sym in config.symbols:
            assert sym.isupper()
            assert sym.endswith("USDT")

    def test_default_output_dir(self):
        """Default output_dir should be the project live data path."""
        config = CollectorConfig()
        assert config.output_dir == "data/live"

    def test_default_flush_interval(self):
        """Default flush_interval should be 10 seconds."""
        config = CollectorConfig()
        assert config.flush_interval == 10.0

    def test_default_open_interest_interval(self):
        """Default open_interest_interval should be 30 seconds."""
        config = CollectorConfig()
        assert config.open_interest_interval == 30.0

    def test_default_long_short_interval(self):
        """Default long_short_interval should be 60 seconds."""
        config = CollectorConfig()
        assert config.long_short_interval == 60.0

    def test_default_depth_levels(self):
        """Default depth_levels should be 20."""
        config = CollectorConfig()
        assert config.depth_levels == 20

    def test_default_reconnect_settings(self):
        """Default reconnect delay and max attempts should match documented values."""
        config = CollectorConfig()
        assert config.reconnect_delay == 5.0
        assert config.max_reconnect_attempts == 100

    def test_default_max_buffer_size(self):
        """Default max_buffer_size should be 100000 rows."""
        config = CollectorConfig()
        assert config.max_buffer_size == 100_000


class TestCollectorConfigCustom:
    def test_custom_symbols_are_used(self):
        """Passing custom symbols should override the Universe defaults."""
        config = CollectorConfig(symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        assert config.symbols == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    def test_custom_output_dir(self, tmp_path: Path):
        """Passing a custom output_dir should override the default path."""
        custom_dir = str(tmp_path / "custom_live")
        config = CollectorConfig(output_dir=custom_dir)
        assert config.output_dir == custom_dir

    def test_custom_flush_interval(self):
        """Passing a custom flush_interval should override the default."""
        config = CollectorConfig(flush_interval=5.0)
        assert config.flush_interval == 5.0

    def test_custom_open_interest_interval(self):
        """Passing a custom open_interest_interval should override the default."""
        config = CollectorConfig(open_interest_interval=15.0)
        assert config.open_interest_interval == 15.0

    def test_custom_long_short_interval(self):
        """Passing a custom long_short_interval should override the default."""
        config = CollectorConfig(long_short_interval=120.0)
        assert config.long_short_interval == 120.0

    def test_custom_depth_levels(self):
        """Passing a custom depth_levels should override the default."""
        config = CollectorConfig(depth_levels=10)
        assert config.depth_levels == 10

    def test_custom_reconnect_settings(self):
        """Passing custom reconnect settings should override the defaults."""
        config = CollectorConfig(reconnect_delay=2.0, max_reconnect_attempts=50)
        assert config.reconnect_delay == 2.0
        assert config.max_reconnect_attempts == 50

    def test_custom_max_buffer_size(self):
        """Passing a custom max_buffer_size should override the default."""
        config = CollectorConfig(max_buffer_size=50_000)
        assert config.max_buffer_size == 50_000

    def test_custom_all_fields_combined(self, tmp_path: Path):
        """All custom fields set together should be respected by the dataclass."""
        config = CollectorConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            output_dir=str(tmp_path / "combined"),
            flush_interval=1.0,
            open_interest_interval=2.0,
            long_short_interval=3.0,
            depth_levels=5,
            reconnect_delay=1.0,
            max_reconnect_attempts=10,
            max_buffer_size=1_000,
        )
        assert config.symbols == ["BTCUSDT", "ETHUSDT"]
        assert config.output_dir == str(tmp_path / "combined")
        assert config.flush_interval == 1.0
        assert config.open_interest_interval == 2.0
        assert config.long_short_interval == 3.0
        assert config.depth_levels == 5
        assert config.reconnect_delay == 1.0
        assert config.max_reconnect_attempts == 10
        assert config.max_buffer_size == 1_000


class TestLiveCollectorInit:
    @pytest.fixture
    def config(self, tmp_path: Path) -> CollectorConfig:
        """Create a CollectorConfig pointing at a temporary output directory."""
        return CollectorConfig(
            symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            output_dir=str(tmp_path / "live"),
        )

    def test_symbols_converted_to_lowercase(self, config: CollectorConfig):
        """LiveCollector should store symbols in lowercase for stream names."""
        collector = LiveCollector(config)
        assert collector.symbols == ["btcusdt", "ethusdt", "solusdt"]

    def test_symbols_lowercase_even_if_already_lower(self, tmp_path: Path):
        """Lowercase input symbols should remain lowercase after initialization."""
        cfg = CollectorConfig(symbols=["btcusdt", "ethusdt"], output_dir=str(tmp_path / "live"))
        collector = LiveCollector(cfg)
        assert collector.symbols == ["btcusdt", "ethusdt"]

    def test_symbols_lowercase_with_mixed_case(self, tmp_path: Path):
        """Mixed case input symbols should be normalized to lowercase."""
        cfg = CollectorConfig(symbols=["BtcUsdt", "EtHusDt"], output_dir=str(tmp_path / "live"))
        collector = LiveCollector(cfg)
        assert collector.symbols == ["btcusdt", "ethusdt"]

    def test_config_is_stored(self, config: CollectorConfig):
        """LiveCollector should keep a reference to the provided config."""
        collector = LiveCollector(config)
        assert collector.config is config

    def test_buffers_initialized_as_empty_lists(self, config: CollectorConfig):
        """Every buffer category should start as an empty list."""
        collector = LiveCollector(config)
        for name in EXPECTED_BUFFERS:
            assert name in collector._buffers
            assert collector._buffers[name] == []

    def test_buffers_contain_all_expected_categories(self, config: CollectorConfig):
        """The buffer dict should contain exactly the expected category keys."""
        collector = LiveCollector(config)
        assert set(collector._buffers.keys()) == set(EXPECTED_BUFFERS)

    def test_buffer_count_matches_expected(self, config: CollectorConfig):
        """There should be exactly 7 buffer categories."""
        collector = LiveCollector(config)
        assert len(collector._buffers) == len(EXPECTED_BUFFERS)

    def test_individual_buffer_categories_present(self, config: CollectorConfig):
        """Each expected buffer category should be present and empty."""
        collector = LiveCollector(config)
        for category in EXPECTED_BUFFERS:
            assert category in collector._buffers, f"Missing buffer: {category}"
            assert isinstance(collector._buffers[category], list)
            assert len(collector._buffers[category]) == 0

    def test_output_dir_created_if_not_exists(self, tmp_path: Path):
        """Constructor should create the output directory tree if it does not exist."""
        output_dir = tmp_path / "new_live_dir" / "subdir"
        cfg = CollectorConfig(symbols=["BTCUSDT"], output_dir=str(output_dir))
        LiveCollector(cfg)
        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_output_dir_creation_is_idempotent(self, tmp_path: Path):
        """Creating a collector twice with the same dir should not raise."""
        output_dir = tmp_path / "live_idempotent"
        cfg = CollectorConfig(symbols=["BTCUSDT"], output_dir=str(output_dir))
        LiveCollector(cfg)
        # Second construction should not fail even though dir already exists
        LiveCollector(cfg)
        assert output_dir.exists()

    def test_running_flag_starts_false(self, config: CollectorConfig):
        """The _running flag should be False until start() is called."""
        collector = LiveCollector(config)
        assert collector._running is False

    def test_ws_session_starts_none(self, config: CollectorConfig):
        """The WebSocket session handle should be None before connecting."""
        collector = LiveCollector(config)
        assert collector._ws_session is None

    def test_stats_initialized_as_defaultdict(self, config: CollectorConfig):
        """Stats should be a defaultdict(int) starting empty."""
        collector = LiveCollector(config)
        assert len(collector._stats) == 0
        # defaultdict(int) returns 0 for missing keys
        assert collector._stats["nonexistent_key"] == 0

    def test_buffer_lock_is_asyncio_lock(self, config: CollectorConfig):
        """The buffer lock should be an asyncio.Lock instance."""
        import asyncio
        collector = LiveCollector(config)
        assert isinstance(collector._buffer_lock, asyncio.Lock)
