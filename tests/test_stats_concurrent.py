"""Tests for concurrent access to StatsManager.

Tests verify that file locking prevents data corruption when multiple
processes/threads access statistics files simultaneously.

This simulates real-world scenarios where:
- Multiple users run analysis on different PCs
- Shopify Tool and Packing Tool update stats concurrently
- Network latency causes delayed file operations
"""

import json
import pytest
import tempfile
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from shared.stats_manager import StatsManager


@pytest.fixture
def temp_stats_dir():
    """Create a temporary directory for statistics files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def stats_manager(temp_stats_dir):
    """Create a StatsManager instance with temporary directory."""
    return StatsManager(temp_stats_dir)


class TestConcurrentWrites:
    """Test concurrent write operations."""

    def test_concurrent_analysis_recording(self, temp_stats_dir):
        """Test multiple threads recording analysis simultaneously."""
        num_threads = 10
        orders_per_thread = 50

        def record_analysis(thread_id):
            """Record analysis from a thread."""
            manager = StatsManager(temp_stats_dir)
            return manager.record_analysis(
                client_id="M",
                session_id=f"session_{thread_id}",
                orders_count=orders_per_thread,
                fulfillable_count=orders_per_thread - 2
            )

        # Execute concurrent recordings
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(record_analysis, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert all(results)

        # Verify final statistics
        manager = StatsManager(temp_stats_dir)
        stats = manager.get_global_stats()

        expected_total = num_threads * orders_per_thread
        assert stats["total_orders_analyzed"] == expected_total
        assert stats["total_sessions"] == num_threads
        assert stats["by_client"]["M"]["orders_analyzed"] == expected_total

    def test_concurrent_packing_recording(self, temp_stats_dir):
        """Test multiple threads recording packing simultaneously."""
        num_threads = 10
        orders_per_thread = 30

        def record_packing(thread_id):
            """Record packing from a thread."""
            manager = StatsManager(temp_stats_dir)
            return manager.record_packing(
                client_id="M",
                session_id=f"session_{thread_id}",
                orders_packed=orders_per_thread,
                worker_id=f"worker_{thread_id % 3}"
            )

        # Execute concurrent recordings
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(record_packing, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert all(results)

        # Verify final statistics
        manager = StatsManager(temp_stats_dir)
        stats = manager.get_global_stats()

        expected_total = num_threads * orders_per_thread
        assert stats["total_orders_packed"] == expected_total
        assert stats["by_client"]["M"]["orders_packed"] == expected_total

    def test_mixed_concurrent_operations(self, temp_stats_dir):
        """Test concurrent analysis and packing recordings."""
        num_analysis = 5
        num_packing = 5

        def record_analysis(thread_id):
            """Record analysis."""
            manager = StatsManager(temp_stats_dir)
            return manager.record_analysis(
                client_id="M",
                session_id=f"analysis_{thread_id}",
                orders_count=100,
                fulfillable_count=95
            )

        def record_packing(thread_id):
            """Record packing."""
            manager = StatsManager(temp_stats_dir)
            return manager.record_packing(
                client_id="M",
                session_id=f"packing_{thread_id}",
                orders_packed=90,
                worker_id=f"worker_{thread_id}"
            )

        # Execute mixed operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            analysis_futures = [executor.submit(record_analysis, i) for i in range(num_analysis)]
            packing_futures = [executor.submit(record_packing, i) for i in range(num_packing)]

            all_futures = analysis_futures + packing_futures
            results = [f.result() for f in as_completed(all_futures)]

        # All should succeed
        assert all(results)

        # Verify final statistics
        manager = StatsManager(temp_stats_dir)
        stats = manager.get_global_stats()

        assert stats["total_orders_analyzed"] == num_analysis * 100
        assert stats["total_orders_packed"] == num_packing * 90
        assert stats["total_sessions"] == num_analysis

    def test_concurrent_multi_client_recording(self, temp_stats_dir):
        """Test concurrent recordings for multiple clients."""
        clients = ["M", "A", "B", "C"]
        recordings_per_client = 5

        def record_for_client(client_id, recording_id):
            """Record analysis for a client."""
            manager = StatsManager(temp_stats_dir)
            return manager.record_analysis(
                client_id=client_id,
                session_id=f"{client_id}_session_{recording_id}",
                orders_count=50,
                fulfillable_count=48
            )

        # Execute concurrent recordings for all clients
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for client_id in clients:
                for i in range(recordings_per_client):
                    futures.append(executor.submit(record_for_client, client_id, i))

            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert all(results)

        # Verify final statistics
        manager = StatsManager(temp_stats_dir)
        stats = manager.get_global_stats()

        total_recordings = len(clients) * recordings_per_client
        assert stats["total_orders_analyzed"] == total_recordings * 50
        assert stats["total_sessions"] == total_recordings

        # Each client should have correct stats
        for client_id in clients:
            assert stats["by_client"][client_id]["orders_analyzed"] == recordings_per_client * 50


class TestConcurrentReads:
    """Test concurrent read operations."""

    def test_concurrent_stats_reading(self, stats_manager):
        """Test multiple threads reading stats simultaneously."""
        # First, populate some data
        stats_manager.record_analysis("M", "2025-11-04_1", 100, 95)

        num_readers = 20
        results = []

        def read_stats():
            """Read global stats."""
            return stats_manager.get_global_stats()

        # Execute concurrent reads
        with ThreadPoolExecutor(max_workers=num_readers) as executor:
            futures = [executor.submit(read_stats) for _ in range(num_readers)]
            results = [f.result() for f in as_completed(futures)]

        # All reads should succeed and return same data
        assert len(results) == num_readers
        assert all(r["total_orders_analyzed"] == 100 for r in results)

    def test_concurrent_history_reading(self, stats_manager):
        """Test multiple threads reading history simultaneously."""
        # Populate history
        for i in range(10):
            stats_manager.record_analysis("M", f"session_{i}", 10, 9)

        num_readers = 15

        def read_history():
            """Read analysis history."""
            return stats_manager.get_analysis_history()

        # Execute concurrent reads
        with ThreadPoolExecutor(max_workers=num_readers) as executor:
            futures = [executor.submit(read_history) for _ in range(num_readers)]
            results = [f.result() for f in as_completed(futures)]

        # All reads should succeed and return same count
        assert len(results) == num_readers
        assert all(len(r) == 10 for r in results)


class TestReadWriteConcurrency:
    """Test concurrent reads and writes."""

    def test_concurrent_read_write(self, temp_stats_dir):
        """Test simultaneous reading and writing."""
        # Initialize with some data
        manager = StatsManager(temp_stats_dir)
        manager.record_analysis("M", "initial", 50, 48)

        num_readers = 10
        num_writers = 5
        results = {"reads": [], "writes": []}

        def read_stats():
            """Read stats."""
            m = StatsManager(temp_stats_dir)
            return m.get_global_stats()

        def write_stats(writer_id):
            """Write stats."""
            m = StatsManager(temp_stats_dir)
            return m.record_analysis(
                client_id="M",
                session_id=f"writer_{writer_id}",
                orders_count=10,
                fulfillable_count=9
            )

        # Execute concurrent reads and writes
        with ThreadPoolExecutor(max_workers=15) as executor:
            read_futures = [executor.submit(read_stats) for _ in range(num_readers)]
            write_futures = [executor.submit(write_stats, i) for i in range(num_writers)]

            for f in as_completed(read_futures):
                results["reads"].append(f.result())

            for f in as_completed(write_futures):
                results["writes"].append(f.result())

        # All operations should succeed
        assert len(results["reads"]) == num_readers
        assert all(results["writes"])

        # Final stats should be consistent
        final_manager = StatsManager(temp_stats_dir)
        final_stats = final_manager.get_global_stats()

        # Initial 50 + (5 writers * 10 each)
        assert final_stats["total_orders_analyzed"] == 50 + (num_writers * 10)


class TestRetryLogic:
    """Test retry logic for file locking conflicts."""

    def test_retry_on_lock_contention(self, temp_stats_dir):
        """Test that operations retry on lock contention."""
        # This test simulates high contention by having many threads
        # try to write simultaneously
        num_threads = 20

        def aggressive_write(thread_id):
            """Aggressively write without delay."""
            manager = StatsManager(temp_stats_dir)
            return manager.record_analysis(
                client_id="M",
                session_id=f"session_{thread_id}",
                orders_count=1,
                fulfillable_count=1
            )

        # Execute with high contention
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(aggressive_write, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # Despite high contention, all should eventually succeed
        assert all(results)

        # Verify all writes were recorded
        manager = StatsManager(temp_stats_dir)
        stats = manager.get_global_stats()
        assert stats["total_orders_analyzed"] == num_threads


class TestDataIntegrity:
    """Test data integrity under concurrent access."""

    def test_no_data_corruption(self, temp_stats_dir):
        """Test that concurrent writes don't corrupt data."""
        num_threads = 15

        def record_with_known_data(thread_id):
            """Record with specific data."""
            manager = StatsManager(temp_stats_dir)
            return manager.record_analysis(
                client_id="M",
                session_id=f"session_{thread_id}",
                orders_count=thread_id * 10,  # Distinct values
                fulfillable_count=thread_id * 10 - 1
            )

        # Execute concurrent writes
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(record_with_known_data, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        assert all(results)

        # Verify data integrity
        manager = StatsManager(temp_stats_dir)

        # Check global stats JSON is valid
        stats = manager.get_global_stats()
        assert isinstance(stats, dict)
        assert "total_orders_analyzed" in stats

        # Check history JSON is valid
        history = manager.get_analysis_history()
        assert isinstance(history, list)
        assert len(history) == num_threads

        # Verify no duplicate sessions
        session_ids = [h["session_id"] for h in history]
        assert len(session_ids) == len(set(session_ids))

    def test_json_structure_preserved(self, temp_stats_dir):
        """Test that JSON structure remains valid under concurrent access."""
        num_threads = 10

        def record_data(thread_id):
            """Record data."""
            manager = StatsManager(temp_stats_dir)
            manager.record_analysis("M", f"s_{thread_id}", 10, 9)
            manager.record_packing("M", f"s_{thread_id}", 9, f"w_{thread_id}")

        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(record_data, i) for i in range(num_threads)]
            for f in as_completed(futures):
                f.result()

        # Verify all JSON files are valid and parseable
        manager = StatsManager(temp_stats_dir)

        # Read files directly to ensure they're valid JSON
        with open(manager.global_stats_path, 'r') as f:
            global_stats = json.load(f)
        assert isinstance(global_stats, dict)

        with open(manager.analysis_history_path, 'r') as f:
            analysis_history = json.load(f)
        assert isinstance(analysis_history, list)

        with open(manager.packing_history_path, 'r') as f:
            packing_history = json.load(f)
        assert isinstance(packing_history, list)


class TestStressTest:
    """Stress tests with high volume concurrent operations."""

    @pytest.mark.slow
    def test_high_volume_concurrent_operations(self, temp_stats_dir):
        """Stress test with high volume of concurrent operations."""
        num_threads = 50
        operations_per_thread = 10

        def perform_operations(thread_id):
            """Perform multiple operations."""
            manager = StatsManager(temp_stats_dir)
            successes = 0

            for i in range(operations_per_thread):
                if i % 2 == 0:
                    success = manager.record_analysis(
                        f"CLIENT_{thread_id % 5}",
                        f"t{thread_id}_s{i}",
                        5,
                        4
                    )
                else:
                    success = manager.record_packing(
                        f"CLIENT_{thread_id % 5}",
                        f"t{thread_id}_s{i}",
                        4,
                        f"worker_{thread_id % 3}"
                    )

                if success:
                    successes += 1

            return successes

        # Execute stress test
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(perform_operations, i) for i in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # Most operations should succeed (allow for some failures under extreme stress)
        total_operations = num_threads * operations_per_thread
        successful_operations = sum(results)
        success_rate = successful_operations / total_operations

        # Expect at least 95% success rate
        assert success_rate >= 0.95, f"Success rate too low: {success_rate:.2%}"

        # Verify data integrity
        manager = StatsManager(temp_stats_dir)
        stats = manager.get_global_stats()

        # Stats should be consistent
        assert isinstance(stats["total_orders_analyzed"], int)
        assert isinstance(stats["total_orders_packed"], int)
        assert stats["total_orders_analyzed"] >= 0
        assert stats["total_orders_packed"] >= 0


class TestEdgeCases:
    """Test edge cases in concurrent scenarios."""

    def test_concurrent_first_time_initialization(self, temp_stats_dir):
        """Test multiple threads initializing StatsManager simultaneously."""
        num_threads = 10

        def initialize_manager():
            """Initialize a new StatsManager."""
            return StatsManager(temp_stats_dir)

        # Execute concurrent initializations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(initialize_manager) for _ in range(num_threads)]
            managers = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert len(managers) == num_threads

        # Files should exist and be valid
        assert (temp_stats_dir / "global_stats.json").exists()
        assert (temp_stats_dir / "analysis_history.json").exists()
        assert (temp_stats_dir / "packing_history.json").exists()

    def test_concurrent_operations_different_clients(self, temp_stats_dir):
        """Test concurrent operations on different clients don't interfere."""
        clients = ["M", "A", "B"]
        operations_per_client = 10

        def record_for_client(client_id):
            """Record multiple operations for a client."""
            manager = StatsManager(temp_stats_dir)
            for i in range(operations_per_client):
                manager.record_analysis(client_id, f"s{i}", 10, 9)

        # Execute for all clients concurrently
        with ThreadPoolExecutor(max_workers=len(clients)) as executor:
            futures = [executor.submit(record_for_client, c) for c in clients]
            for f in as_completed(futures):
                f.result()

        # Verify each client has correct stats
        manager = StatsManager(temp_stats_dir)
        stats = manager.get_global_stats()

        for client_id in clients:
            assert stats["by_client"][client_id]["orders_analyzed"] == operations_per_client * 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])
