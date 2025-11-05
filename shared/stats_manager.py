"""Unified Statistics Manager for Shopify Fulfillment Tool and Packing Tool.

This module provides centralized statistics management across both tools.
It handles global statistics tracking, per-client metrics, and history logging
with thread-safe file locking.

Key Features:
    - Global statistics tracking (orders analyzed, packed, sessions)
    - Per-client metrics breakdown
    - Thread-safe file operations with locking
    - Automatic history logging
    - Support for concurrent access from both tools
    - Retry logic for network file operations
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from threading import Lock

logger = logging.getLogger("ShopifyToolLogger")


class StatsManagerError(Exception):
    """Base exception for StatsManager errors."""
    pass


class StatsManager:
    """Manages centralized statistics for both Shopify Tool and Packing Tool.

    This class provides:
    - Loading and saving global statistics
    - Recording analysis sessions (Shopify Tool)
    - Recording packing sessions (Packing Tool)
    - Per-client statistics breakdown
    - Thread-safe concurrent access with file locking
    - Automatic history logging

    Attributes:
        stats_dir (Path): Directory for statistics files
        global_stats_path (Path): Path to global_stats.json
        analysis_history_path (Path): Path to analysis_history.json
        packing_history_path (Path): Path to packing_history.json
    """

    # Class-level lock for thread safety
    _lock = Lock()

    def __init__(self, stats_dir: Path):
        """Initialize StatsManager with statistics directory.

        Args:
            stats_dir (Path): Path to Stats/ directory on file server

        Raises:
            StatsManagerError: If directory is not accessible
        """
        self.stats_dir = Path(stats_dir)
        self.global_stats_path = self.stats_dir / "global_stats.json"
        self.analysis_history_path = self.stats_dir / "analysis_history.json"
        self.packing_history_path = self.stats_dir / "packing_history.json"

        # Ensure directory exists
        try:
            self.stats_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise StatsManagerError(f"Cannot access stats directory: {e}")

        # Initialize files if they don't exist
        self._initialize_files()

        logger.info(f"StatsManager initialized at {self.stats_dir}")

    def _initialize_files(self):
        """Initialize statistics files with default structure if they don't exist."""
        # Initialize global_stats.json
        if not self.global_stats_path.exists():
            default_stats = {
                "total_orders_analyzed": 0,
                "total_orders_packed": 0,
                "total_sessions": 0,
                "by_client": {},
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            self._write_json_with_lock(self.global_stats_path, default_stats)
            logger.info("Created global_stats.json with defaults")

        # Initialize analysis_history.json
        if not self.analysis_history_path.exists():
            self._write_json_with_lock(self.analysis_history_path, [])
            logger.info("Created analysis_history.json")

        # Initialize packing_history.json
        if not self.packing_history_path.exists():
            self._write_json_with_lock(self.packing_history_path, [])
            logger.info("Created packing_history.json")

    def _read_json_with_lock(self, file_path: Path, max_retries: int = 5) -> Any:
        """Read JSON file with retry logic for network files.

        Args:
            file_path (Path): Path to JSON file
            max_retries (int): Maximum number of retry attempts

        Returns:
            Any: Parsed JSON data

        Raises:
            StatsManagerError: If read fails after retries
        """
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data

            except (IOError, OSError, json.JSONDecodeError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Read failed (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise StatsManagerError(f"Failed to read {file_path} after {max_retries} attempts: {e}")

        return None

    def _write_json_with_lock(self, file_path: Path, data: Any, max_retries: int = 5) -> bool:
        """Write JSON file with file locking and retry logic.

        Uses platform-specific file locking to prevent concurrent write conflicts.
        Writes to temporary file first, then atomically moves to target.

        Args:
            file_path (Path): Path to JSON file
            data (Any): Data to write (must be JSON-serializable)
            max_retries (int): Maximum number of retry attempts

        Returns:
            bool: True if write succeeded

        Raises:
            StatsManagerError: If write fails after retries
        """
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                if os.name == 'nt':  # Windows
                    success = self._write_with_windows_lock(file_path, data)
                else:  # Unix-like
                    success = self._write_with_unix_lock(file_path, data)

                if success:
                    return True

            except (IOError, OSError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Write locked (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise StatsManagerError(
                        f"Statistics file is locked. Please try again in a moment."
                    )

        return False

    def _write_with_windows_lock(self, file_path: Path, data: Any) -> bool:
        """Write file with Windows file locking.

        Args:
            file_path (Path): Path to file
            data (Any): Data to write

        Returns:
            bool: True if write succeeded
        """
        import msvcrt
        import os

        # Use unique temp file name to avoid conflicts
        import uuid
        temp_path = file_path.with_suffix(f'.tmp.{uuid.uuid4().hex[:8]}')

        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                except IOError:
                    if temp_path.exists():
                        try:
                            temp_path.unlink()
                        except:
                            pass
                    return False

                try:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data is written to disk
                finally:
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

            # Atomic replace
            try:
                os.replace(str(temp_path), str(file_path))
                return True
            except Exception as e:
                logger.error(f"Failed to replace file: {e}")
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except:
                        pass
                return False

        except Exception as e:
            logger.error(f"Failed to write with Windows lock: {e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
            return False

    def _write_with_unix_lock(self, file_path: Path, data: Any) -> bool:
        """Write file with Unix file locking.

        Args:
            file_path (Path): Path to file
            data (Any): Data to write

        Returns:
            bool: True if write succeeded
        """
        import fcntl
        import os

        # Use unique temp file name to avoid conflicts
        import uuid
        temp_path = file_path.with_suffix(f'.tmp.{uuid.uuid4().hex[:8]}')

        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except IOError:
                    if temp_path.exists():
                        try:
                            temp_path.unlink()
                        except:
                            pass
                    return False

                try:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data is written to disk
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Atomic replace
            try:
                os.replace(str(temp_path), str(file_path))
                return True
            except Exception as e:
                logger.error(f"Failed to replace file: {e}")
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except:
                        pass
                return False

        except Exception as e:
            logger.error(f"Failed to write with Unix lock: {e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
            return False

    def get_global_stats(self) -> Dict[str, Any]:
        """Load current global statistics.

        Returns:
            Dict[str, Any]: Global statistics dictionary
        """
        with self._lock:
            return self._read_json_with_lock(self.global_stats_path)

    def get_client_stats(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific client.

        Args:
            client_id (str): Client ID

        Returns:
            Optional[Dict[str, Any]]: Client statistics or None if not found
        """
        stats = self.get_global_stats()
        client_id = client_id.upper()
        return stats.get("by_client", {}).get(client_id)

    def record_analysis(
        self,
        client_id: str,
        session_id: str,
        orders_count: int,
        fulfillable_count: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record an analysis session from Shopify Tool.

        Updates global statistics and appends to analysis history.

        Args:
            client_id (str): Client ID
            session_id (str): Session identifier (e.g., "2025-11-04_1")
            orders_count (int): Total number of orders analyzed
            fulfillable_count (int): Number of fulfillable orders
            metadata (Optional[Dict]): Additional metadata

        Returns:
            bool: True if recorded successfully
        """
        with self._lock:
            try:
                client_id = client_id.upper()
                timestamp = datetime.now().isoformat()

                # Update global stats
                stats = self._read_json_with_lock(self.global_stats_path)

                # Update totals
                stats["total_orders_analyzed"] = stats.get("total_orders_analyzed", 0) + orders_count
                stats["total_sessions"] = stats.get("total_sessions", 0) + 1
                stats["last_updated"] = timestamp

                # Update per-client stats
                if "by_client" not in stats:
                    stats["by_client"] = {}

                if client_id not in stats["by_client"]:
                    stats["by_client"][client_id] = {
                        "orders_analyzed": 0,
                        "orders_packed": 0,
                        "sessions": 0
                    }

                stats["by_client"][client_id]["orders_analyzed"] += orders_count
                stats["by_client"][client_id]["sessions"] += 1

                # Save updated global stats
                self._write_json_with_lock(self.global_stats_path, stats)

                # Append to analysis history
                history = self._read_json_with_lock(self.analysis_history_path)

                history_entry = {
                    "timestamp": timestamp,
                    "client_id": client_id,
                    "session_id": session_id,
                    "orders_count": orders_count,
                    "fulfillable_count": fulfillable_count,
                    "tool": "shopify",
                    "metadata": metadata or {}
                }

                history.append(history_entry)

                # Keep only last 1000 entries to prevent unbounded growth
                if len(history) > 1000:
                    history = history[-1000:]

                self._write_json_with_lock(self.analysis_history_path, history)

                logger.info(
                    f"Recorded analysis: {client_id} - {orders_count} orders "
                    f"({fulfillable_count} fulfillable)"
                )

                return True

            except Exception as e:
                logger.error(f"Failed to record analysis: {e}", exc_info=True)
                return False

    def record_packing(
        self,
        client_id: str,
        session_id: str,
        orders_packed: int,
        worker_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record a packing session from Packing Tool.

        Updates global statistics and appends to packing history.

        Args:
            client_id (str): Client ID
            session_id (str): Session identifier
            orders_packed (int): Number of orders packed
            worker_id (Optional[str]): Worker who packed the orders
            metadata (Optional[Dict]): Additional metadata

        Returns:
            bool: True if recorded successfully
        """
        with self._lock:
            try:
                client_id = client_id.upper()
                timestamp = datetime.now().isoformat()

                # Update global stats
                stats = self._read_json_with_lock(self.global_stats_path)

                # Update totals
                stats["total_orders_packed"] = stats.get("total_orders_packed", 0) + orders_packed
                stats["last_updated"] = timestamp

                # Update per-client stats
                if "by_client" not in stats:
                    stats["by_client"] = {}

                if client_id not in stats["by_client"]:
                    stats["by_client"][client_id] = {
                        "orders_analyzed": 0,
                        "orders_packed": 0,
                        "sessions": 0
                    }

                stats["by_client"][client_id]["orders_packed"] += orders_packed

                # Save updated global stats
                self._write_json_with_lock(self.global_stats_path, stats)

                # Append to packing history
                history = self._read_json_with_lock(self.packing_history_path)

                history_entry = {
                    "timestamp": timestamp,
                    "client_id": client_id,
                    "session_id": session_id,
                    "orders_packed": orders_packed,
                    "worker_id": worker_id,
                    "tool": "packer",
                    "metadata": metadata or {}
                }

                history.append(history_entry)

                # Keep only last 1000 entries
                if len(history) > 1000:
                    history = history[-1000:]

                self._write_json_with_lock(self.packing_history_path, history)

                logger.info(
                    f"Recorded packing: {client_id} - {orders_packed} orders "
                    f"by {worker_id or 'Unknown'}"
                )

                return True

            except Exception as e:
                logger.error(f"Failed to record packing: {e}", exc_info=True)
                return False

    def get_analysis_history(
        self,
        client_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get analysis history, optionally filtered by client.

        Args:
            client_id (Optional[str]): Filter by client ID
            limit (Optional[int]): Maximum number of entries to return

        Returns:
            List[Dict[str, Any]]: List of analysis history entries
        """
        with self._lock:
            history = self._read_json_with_lock(self.analysis_history_path)

            if client_id:
                client_id = client_id.upper()
                history = [h for h in history if h.get("client_id") == client_id]

            if limit:
                history = history[-limit:]

            return history

    def get_packing_history(
        self,
        client_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get packing history, optionally filtered by client.

        Args:
            client_id (Optional[str]): Filter by client ID
            limit (Optional[int]): Maximum number of entries to return

        Returns:
            List[Dict[str, Any]]: List of packing history entries
        """
        with self._lock:
            history = self._read_json_with_lock(self.packing_history_path)

            if client_id:
                client_id = client_id.upper()
                history = [h for h in history if h.get("client_id") == client_id]

            if limit:
                history = history[-limit:]

            return history

    def reset_stats(self, confirm: bool = False) -> bool:
        """Reset all statistics to defaults.

        WARNING: This will delete all statistics and history!

        Args:
            confirm (bool): Must be True to actually reset

        Returns:
            bool: True if reset successfully
        """
        if not confirm:
            logger.warning("Reset stats called without confirmation")
            return False

        with self._lock:
            try:
                # Reset global stats
                default_stats = {
                    "total_orders_analyzed": 0,
                    "total_orders_packed": 0,
                    "total_sessions": 0,
                    "by_client": {},
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
                self._write_json_with_lock(self.global_stats_path, default_stats)

                # Reset histories
                self._write_json_with_lock(self.analysis_history_path, [])
                self._write_json_with_lock(self.packing_history_path, [])

                logger.warning("All statistics have been reset!")
                return True

            except Exception as e:
                logger.error(f"Failed to reset stats: {e}")
                return False
