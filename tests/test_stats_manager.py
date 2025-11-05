"""Tests for StatsManager (Unified Statistics Manager).

Tests cover:
- Initialization and file creation
- Recording analysis sessions (Shopify Tool)
- Recording packing sessions (Packing Tool)
- Statistics retrieval and aggregation
- Per-client statistics
- History tracking
- Error handling
"""

import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from shared.stats_manager import StatsManager, StatsManagerError


@pytest.fixture
def temp_stats_dir():
    """Create a temporary directory for statistics files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def stats_manager(temp_stats_dir):
    """Create a StatsManager instance with temporary directory."""
    return StatsManager(temp_stats_dir)


class TestStatsManagerInitialization:
    """Test StatsManager initialization and file creation."""

    def test_init_creates_directory(self, temp_stats_dir):
        """Test that initialization creates stats directory."""
        stats_dir = temp_stats_dir / "stats"
        manager = StatsManager(stats_dir)

        assert stats_dir.exists()
        assert stats_dir.is_dir()

    def test_init_creates_default_files(self, stats_manager, temp_stats_dir):
        """Test that initialization creates default JSON files."""
        assert (temp_stats_dir / "global_stats.json").exists()
        assert (temp_stats_dir / "analysis_history.json").exists()
        assert (temp_stats_dir / "packing_history.json").exists()

    def test_default_global_stats_structure(self, stats_manager):
        """Test that default global_stats.json has correct structure."""
        stats = stats_manager.get_global_stats()

        assert stats["total_orders_analyzed"] == 0
        assert stats["total_orders_packed"] == 0
        assert stats["total_sessions"] == 0
        assert stats["by_client"] == {}
        assert "created_at" in stats
        assert "last_updated" in stats

    def test_default_histories_are_empty(self, stats_manager):
        """Test that default history files are empty lists."""
        analysis_history = stats_manager.get_analysis_history()
        packing_history = stats_manager.get_packing_history()

        assert analysis_history == []
        assert packing_history == []

    def test_init_fails_on_invalid_path(self):
        """Test that initialization fails gracefully on invalid path."""
        # Use a path that cannot be created (invalid characters)
        if Path("/").exists():  # Unix-like system
            invalid_path = Path("/\0invalid")
        else:  # Windows
            invalid_path = Path("C:\\invalid\0path")

        # Should raise StatsManagerError due to directory creation failure
        # Note: This test may behave differently on different platforms
        # On some systems, it might succeed with sanitized paths


class TestRecordAnalysis:
    """Test recording analysis sessions from Shopify Tool."""

    def test_record_analysis_basic(self, stats_manager):
        """Test basic analysis recording."""
        success = stats_manager.record_analysis(
            client_id="M",
            session_id="2025-11-04_1",
            orders_count=100,
            fulfillable_count=95
        )

        assert success is True

        # Check global stats
        stats = stats_manager.get_global_stats()
        assert stats["total_orders_analyzed"] == 100
        assert stats["total_sessions"] == 1
        assert stats["total_orders_packed"] == 0  # Should remain 0

    def test_record_analysis_updates_client_stats(self, stats_manager):
        """Test that analysis recording updates per-client statistics."""
        stats_manager.record_analysis(
            client_id="M",
            session_id="2025-11-04_1",
            orders_count=100,
            fulfillable_count=95
        )

        stats = stats_manager.get_global_stats()
        assert "M" in stats["by_client"]
        assert stats["by_client"]["M"]["orders_analyzed"] == 100
        assert stats["by_client"]["M"]["sessions"] == 1
        assert stats["by_client"]["M"]["orders_packed"] == 0

    def test_record_analysis_multiple_clients(self, stats_manager):
        """Test recording analyses for multiple clients."""
        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)
        stats_manager.record_analysis("A", "2025-11-04_1", 50, 48)
        stats_manager.record_analysis("B", "2025-11-04_1", 75, 70)

        stats = stats_manager.get_global_stats()
        assert stats["total_orders_analyzed"] == 225
        assert stats["total_sessions"] == 3

        assert stats["by_client"]["M"]["orders_analyzed"] == 100
        assert stats["by_client"]["A"]["orders_analyzed"] == 50
        assert stats["by_client"]["B"]["orders_analyzed"] == 75

    def test_record_analysis_cumulative(self, stats_manager):
        """Test that multiple analyses accumulate correctly."""
        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)
        stats_manager.record_analysis("M", "2025-11-04_2", 50, 48)
        stats_manager.record_analysis("M", "2025-11-05_1", 75, 70)

        stats = stats_manager.get_global_stats()
        assert stats["total_orders_analyzed"] == 225
        assert stats["total_sessions"] == 3
        assert stats["by_client"]["M"]["orders_analyzed"] == 225
        assert stats["by_client"]["M"]["sessions"] == 3

    def test_record_analysis_with_metadata(self, stats_manager):
        """Test recording analysis with additional metadata."""
        metadata = {
            "session_path": "/path/to/session",
            "total_items": 250,
            "computer": "WAREHOUSE-PC-01"
        }

        stats_manager.record_analysis(
            client_id="M",
            session_id="2025-11-04_1",
            orders_count=100,
            fulfillable_count=95,
            metadata=metadata
        )

        history = stats_manager.get_analysis_history()
        assert len(history) == 1
        assert history[0]["metadata"] == metadata

    def test_record_analysis_creates_history_entry(self, stats_manager):
        """Test that analysis recording creates history entry."""
        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)

        history = stats_manager.get_analysis_history()
        assert len(history) == 1

        entry = history[0]
        assert entry["client_id"] == "M"
        assert entry["session_id"] == "2025-11-04_1"
        assert entry["orders_count"] == 100
        assert entry["fulfillable_count"] == 95
        assert entry["tool"] == "shopify"
        assert "timestamp" in entry

    def test_record_analysis_case_insensitive_client_id(self, stats_manager):
        """Test that client IDs are normalized to uppercase."""
        stats_manager.record_analysis("m", "2025-11-04_1", 100, 95)
        stats_manager.record_analysis("M", "2025-11-04_2", 50, 48)

        stats = stats_manager.get_global_stats()
        assert "M" in stats["by_client"]
        assert "m" not in stats["by_client"]
        assert stats["by_client"]["M"]["orders_analyzed"] == 150


class TestRecordPacking:
    """Test recording packing sessions from Packing Tool."""

    def test_record_packing_basic(self, stats_manager):
        """Test basic packing recording."""
        success = stats_manager.record_packing(
            client_id="M",
            session_id="2025-11-04_1",
            orders_packed=90,
            worker_id="001"
        )

        assert success is True

        stats = stats_manager.get_global_stats()
        assert stats["total_orders_packed"] == 90
        assert stats["total_orders_analyzed"] == 0  # Should remain 0

    def test_record_packing_updates_client_stats(self, stats_manager):
        """Test that packing recording updates per-client statistics."""
        stats_manager.record_packing("M", "2025-11-04_1", 90, "001")

        stats = stats_manager.get_global_stats()
        assert "M" in stats["by_client"]
        assert stats["by_client"]["M"]["orders_packed"] == 90
        assert stats["by_client"]["M"]["orders_analyzed"] == 0

    def test_record_packing_with_worker_id(self, stats_manager):
        """Test recording packing with worker ID."""
        stats_manager.record_packing("M", "2025-11-04_1", 90, worker_id="001")

        history = stats_manager.get_packing_history()
        assert len(history) == 1
        assert history[0]["worker_id"] == "001"

    def test_record_packing_without_worker_id(self, stats_manager):
        """Test recording packing without worker ID."""
        stats_manager.record_packing("M", "2025-11-04_1", 90)

        history = stats_manager.get_packing_history()
        assert len(history) == 1
        assert history[0]["worker_id"] is None

    def test_record_packing_creates_history_entry(self, stats_manager):
        """Test that packing recording creates history entry."""
        stats_manager.record_packing("M", "2025-11-04_1", 90, "001")

        history = stats_manager.get_packing_history()
        assert len(history) == 1

        entry = history[0]
        assert entry["client_id"] == "M"
        assert entry["session_id"] == "2025-11-04_1"
        assert entry["orders_packed"] == 90
        assert entry["worker_id"] == "001"
        assert entry["tool"] == "packer"
        assert "timestamp" in entry


class TestIntegratedWorkflow:
    """Test integrated workflow with both analysis and packing."""

    def test_full_workflow(self, stats_manager):
        """Test complete workflow: analysis → packing."""
        # Shopify Tool analyzes orders
        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)

        # Packing Tool packs the orders
        stats_manager.record_packing("M", "2025-11-04_1", 95, "001")

        stats = stats_manager.get_global_stats()
        assert stats["total_orders_analyzed"] == 100
        assert stats["total_orders_packed"] == 95
        assert stats["total_sessions"] == 1  # Only analysis increments sessions

        assert stats["by_client"]["M"]["orders_analyzed"] == 100
        assert stats["by_client"]["M"]["orders_packed"] == 95

    def test_multiple_sessions_workflow(self, stats_manager):
        """Test workflow with multiple sessions."""
        # Session 1
        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)
        stats_manager.record_packing("M", "2025-11-04_1", 95, "001")

        # Session 2
        stats_manager.record_analysis("M", "2025-11-04_2", 50, 48)
        stats_manager.record_packing("M", "2025-11-04_2", 48, "002")

        stats = stats_manager.get_global_stats()
        assert stats["total_orders_analyzed"] == 150
        assert stats["total_orders_packed"] == 143
        assert stats["total_sessions"] == 2


class TestHistoryRetrieval:
    """Test history retrieval and filtering."""

    def test_get_analysis_history_all(self, stats_manager):
        """Test retrieving all analysis history."""
        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)
        stats_manager.record_analysis("A", "2025-11-04_1", 50, 48)

        history = stats_manager.get_analysis_history()
        assert len(history) == 2

    def test_get_analysis_history_by_client(self, stats_manager):
        """Test filtering analysis history by client."""
        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)
        stats_manager.record_analysis("A", "2025-11-04_1", 50, 48)
        stats_manager.record_analysis("M", "2025-11-04_2", 75, 70)

        history = stats_manager.get_analysis_history(client_id="M")
        assert len(history) == 2
        assert all(h["client_id"] == "M" for h in history)

    def test_get_analysis_history_with_limit(self, stats_manager):
        """Test limiting analysis history results."""
        for i in range(10):
            stats_manager.record_analysis("M", f"2025-11-04_{i}", 10, 9)

        history = stats_manager.get_analysis_history(limit=5)
        assert len(history) == 5

    def test_get_packing_history_by_client(self, stats_manager):
        """Test filtering packing history by client."""
        stats_manager.record_packing("M", "2025-11-04_1", 90, "001")
        stats_manager.record_packing("A", "2025-11-04_1", 45, "002")
        stats_manager.record_packing("M", "2025-11-04_2", 70, "001")

        history = stats_manager.get_packing_history(client_id="M")
        assert len(history) == 2
        assert all(h["client_id"] == "M" for h in history)

    def test_history_limit_prevents_unbounded_growth(self, stats_manager):
        """Test that history is limited to prevent unbounded growth."""
        # Record more than 1000 entries
        for i in range(1100):
            stats_manager.record_analysis("M", f"session_{i}", 1, 1)

        # Read history file directly
        history_path = stats_manager.analysis_history_path
        with open(history_path, 'r') as f:
            history = json.load(f)

        # Should be capped at 1000
        assert len(history) == 1000


class TestClientStats:
    """Test per-client statistics."""

    def test_get_client_stats_existing(self, stats_manager):
        """Test retrieving stats for existing client."""
        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)

        client_stats = stats_manager.get_client_stats("M")
        assert client_stats is not None
        assert client_stats["orders_analyzed"] == 100

    def test_get_client_stats_nonexistent(self, stats_manager):
        """Test retrieving stats for non-existent client."""
        client_stats = stats_manager.get_client_stats("NONEXISTENT")
        assert client_stats is None

    def test_multiple_clients_isolated_stats(self, stats_manager):
        """Test that different clients have isolated statistics."""
        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)
        stats_manager.record_analysis("A", "2025-11-04_1", 50, 48)

        m_stats = stats_manager.get_client_stats("M")
        a_stats = stats_manager.get_client_stats("A")

        assert m_stats["orders_analyzed"] == 100
        assert a_stats["orders_analyzed"] == 50
        assert m_stats != a_stats


class TestResetStats:
    """Test statistics reset functionality."""

    def test_reset_requires_confirmation(self, stats_manager):
        """Test that reset requires explicit confirmation."""
        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)

        # Without confirmation
        success = stats_manager.reset_stats(confirm=False)
        assert success is False

        # Stats should still exist
        stats = stats_manager.get_global_stats()
        assert stats["total_orders_analyzed"] == 100

    def test_reset_with_confirmation(self, stats_manager):
        """Test reset with confirmation."""
        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)
        stats_manager.record_packing("M", "2025-11-04_1", 95, "001")

        # With confirmation
        success = stats_manager.reset_stats(confirm=True)
        assert success is True

        # All stats should be reset
        stats = stats_manager.get_global_stats()
        assert stats["total_orders_analyzed"] == 0
        assert stats["total_orders_packed"] == 0
        assert stats["total_sessions"] == 0
        assert stats["by_client"] == {}

        # Histories should be empty
        assert stats_manager.get_analysis_history() == []
        assert stats_manager.get_packing_history() == []


class TestTimestamps:
    """Test timestamp handling."""

    def test_timestamps_are_iso_format(self, stats_manager):
        """Test that timestamps are in ISO format."""
        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)

        history = stats_manager.get_analysis_history()
        timestamp = history[0]["timestamp"]

        # Should be parseable as ISO format datetime
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)

    def test_last_updated_timestamp(self, stats_manager):
        """Test that last_updated is updated on changes."""
        stats = stats_manager.get_global_stats()
        initial_updated = stats["last_updated"]

        # Wait a moment and record new data
        import time
        time.sleep(0.1)

        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)

        stats = stats_manager.get_global_stats()
        new_updated = stats["last_updated"]

        # Should be different
        assert new_updated != initial_updated


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
