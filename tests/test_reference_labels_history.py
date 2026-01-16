"""
Unit tests for Reference Labels History Manager.
"""

import pytest
from pathlib import Path
from datetime import datetime

from shopify_tool.reference_labels_history import ReferenceLabelsHistory


class TestReferenceLabelsHistory:
    """Tests for Reference Labels History Manager."""

    def test_init_creates_directory(self, tmp_path):
        """Test that initialization creates directory."""
        session_dir = tmp_path / "test_session"

        history = ReferenceLabelsHistory(session_dir)

        assert session_dir.exists()
        assert history.history_file == session_dir / "reference_labels_history.json"

    def test_add_entry(self, tmp_path):
        """Test adding entry to history."""
        history = ReferenceLabelsHistory(tmp_path)

        history.add_entry(
            input_pdf="test.pdf",
            input_csv="mapping.csv",
            output_pdf="test_processed.pdf",
            pages_processed=10,
            matched=8,
            unmatched=2,
            processing_time=1.5
        )

        entries = history.get_entries()
        assert len(entries) == 1
        assert entries[0]['input_pdf'] == "test.pdf"
        assert entries[0]['matched'] == 8

    def test_get_entries_sorted(self, tmp_path):
        """Test that entries are returned newest first."""
        history = ReferenceLabelsHistory(tmp_path)

        # Add multiple entries with slight delay
        history.add_entry("first.pdf", "map.csv", "out1.pdf", 10, 8, 2, 1.0)
        history.add_entry("second.pdf", "map.csv", "out2.pdf", 5, 4, 1, 0.5)

        entries = history.get_entries()

        assert len(entries) == 2
        assert entries[0]['input_pdf'] == "second.pdf"  # Newest first
        assert entries[1]['input_pdf'] == "first.pdf"

    def test_get_entries_with_limit(self, tmp_path):
        """Test getting limited number of entries."""
        history = ReferenceLabelsHistory(tmp_path)

        for i in range(5):
            history.add_entry(f"file{i}.pdf", "map.csv", f"out{i}.pdf", 1, 1, 0, 0.1)

        entries = history.get_entries(limit=3)

        assert len(entries) == 3

    def test_clear_history(self, tmp_path):
        """Test clearing history."""
        history = ReferenceLabelsHistory(tmp_path)

        history.add_entry("test.pdf", "map.csv", "out.pdf", 10, 8, 2, 1.0)
        assert len(history.get_entries()) == 1

        history.clear()
        assert len(history.get_entries()) == 0

    def test_get_statistics(self, tmp_path):
        """Test getting statistics."""
        history = ReferenceLabelsHistory(tmp_path)

        history.add_entry("file1.pdf", "map.csv", "out1.pdf", 10, 8, 2, 1.5)
        history.add_entry("file2.pdf", "map.csv", "out2.pdf", 5, 4, 1, 0.5)

        stats = history.get_statistics()

        assert stats['total_files'] == 2
        assert stats['total_pages'] == 15
        assert stats['total_matched'] == 12
        assert stats['total_unmatched'] == 3
        assert stats['avg_processing_time'] == 1.0
        assert stats['success_rate'] == 100.0

    def test_persistence(self, tmp_path):
        """Test that history persists across instances."""
        history1 = ReferenceLabelsHistory(tmp_path)
        history1.add_entry("test.pdf", "map.csv", "out.pdf", 10, 8, 2, 1.0)

        # Create new instance
        history2 = ReferenceLabelsHistory(tmp_path)
        entries = history2.get_entries()

        assert len(entries) == 1
        assert entries[0]['input_pdf'] == "test.pdf"

    def test_corrupted_json_recovery(self, tmp_path):
        """Test recovery from corrupted JSON file."""
        history = ReferenceLabelsHistory(tmp_path)

        # Write corrupted JSON
        history.history_file.write_text("{ invalid json }")

        # Create new instance - should recover
        history2 = ReferenceLabelsHistory(tmp_path)
        entries = history2.get_entries()

        assert len(entries) == 0  # Fresh start
        assert (tmp_path / "reference_labels_history.json.backup").exists()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
