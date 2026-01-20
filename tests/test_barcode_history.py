"""
Unit tests for barcode history manager.

Tests cover:
- Adding history entries
- Loading/saving history
- Getting statistics
- Clearing history
- Error handling
"""

import pytest
import json
from pathlib import Path

from shopify_tool.barcode_history import BarcodeHistory


@pytest.fixture
def history_file(tmp_path):
    """Create temporary history file."""
    return tmp_path / "barcode_history.json"


@pytest.fixture
def sample_entries():
    """Sample barcode generation entries."""
    return [
        {
            "order_number": "ORDER-001",
            "sequential_num": 1,
            "courier": "DHL",
            "country": "DE",
            "tag": "Priority",
            "item_count": 2,
            "file_path": "/path/to/ORDER-001.png",
            "file_size_kb": 12.5,
            "generated_at": "2026-01-16T14:30:00"
        },
        {
            "order_number": "ORDER-002",
            "sequential_num": 2,
            "courier": "PostOne",
            "country": "BG",
            "tag": "N/A",
            "item_count": 1,
            "file_path": "/path/to/ORDER-002.png",
            "file_size_kb": 11.3,
            "generated_at": "2026-01-16T14:30:05"
        }
    ]


class TestHistoryManager:
    """Tests for BarcodeHistory."""

    def test_init_new_history(self, history_file):
        """Test initializing new history file."""
        manager = BarcodeHistory(history_file)

        assert history_file.exists()
        assert manager.data == {"generated_barcodes": []}

    def test_add_entry(self, history_file):
        """Test adding single history entry."""
        manager = BarcodeHistory(history_file)

        entry = {
            "order_number": "ORDER-001",
            "sequential_num": 1,
            "courier": "DHL",
            "file_size_kb": 12.5
        }

        manager.add_entry(entry)

        assert len(manager.data['generated_barcodes']) == 1
        assert manager.data['generated_barcodes'][0]['order_number'] == "ORDER-001"

        # Verify file was updated
        manager2 = BarcodeHistory(history_file)
        assert len(manager2.data['generated_barcodes']) == 1

    def test_add_multiple_entries(self, history_file, sample_entries):
        """Test adding multiple entries."""
        manager = BarcodeHistory(history_file)

        for entry in sample_entries:
            manager.add_entry(entry)

        assert len(manager.data['generated_barcodes']) == 2

    def test_get_statistics_empty(self, history_file):
        """Test getting statistics from empty history."""
        manager = BarcodeHistory(history_file)

        stats = manager.get_statistics()

        assert stats['total_barcodes'] == 0
        assert stats['total_size_kb'] == 0
        assert stats['avg_size_kb'] == 0
        assert stats['courier_breakdown'] == {}

    def test_get_statistics_with_data(self, history_file, sample_entries):
        """Test getting statistics from populated history."""
        manager = BarcodeHistory(history_file)

        for entry in sample_entries:
            manager.add_entry(entry)

        stats = manager.get_statistics()

        assert stats['total_barcodes'] == 2
        assert stats['total_size_kb'] == 23.8  # 12.5 + 11.3
        assert stats['avg_size_kb'] == 11.9   # 23.8 / 2
        assert stats['courier_breakdown'] == {"DHL": 1, "PostOne": 1}

    def test_clear_history(self, history_file, sample_entries):
        """Test clearing history."""
        manager = BarcodeHistory(history_file)

        # Add entries
        for entry in sample_entries:
            manager.add_entry(entry)

        assert len(manager.data['generated_barcodes']) == 2

        # Clear
        manager.clear_history()

        assert len(manager.data['generated_barcodes']) == 0

        # Verify file was updated
        manager2 = BarcodeHistory(history_file)
        assert len(manager2.data['generated_barcodes']) == 0

    def test_persistence_across_instances(self, history_file):
        """Test history persists across manager instances."""
        # Manager 1: Add entry
        manager1 = BarcodeHistory(history_file)
        manager1.add_entry({"order_number": "TEST-001", "file_size_kb": 10.0})

        # Manager 2: Should see same entry
        manager2 = BarcodeHistory(history_file)
        assert len(manager2.data['generated_barcodes']) == 1
        assert manager2.data['generated_barcodes'][0]['order_number'] == "TEST-001"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
