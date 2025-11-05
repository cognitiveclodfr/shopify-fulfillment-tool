# StatsManager Integration Guide

## Overview

The `StatsManager` is a unified statistics tracking system designed to work across both **Shopify Fulfillment Tool** and **Packing Tool**. It provides centralized statistics management with thread-safe file operations and comprehensive tracking capabilities.

## Location

The StatsManager module is located at:
- `shared/stats_manager.py`

This file should be **identical** in both projects. You can either:
1. Copy the file to the Packing Tool project
2. Use a git submodule for sharing
3. Create a symlink (if on the same filesystem)

## Features

- **Global Statistics Tracking**: Orders analyzed, orders packed, total sessions
- **Per-Client Metrics**: Breakdown by client ID
- **Thread-Safe Operations**: File locking prevents data corruption
- **History Tracking**: Separate history for analysis and packing sessions
- **Retry Logic**: Automatic retry on network file conflicts
- **Concurrent Access**: Supports multiple users/tools accessing simultaneously

## Architecture

### File Structure

```
Stats/
├── global_stats.json       # Global statistics
├── analysis_history.json   # History of analysis sessions
└── packing_history.json    # History of packing sessions
```

### global_stats.json Structure

```json
{
  "total_orders_analyzed": 5420,
  "total_orders_packed": 4890,
  "total_sessions": 312,
  "by_client": {
    "M": {
      "orders_analyzed": 2100,
      "orders_packed": 1950,
      "sessions": 145
    },
    "A": { ... },
    "B": { ... }
  },
  "created_at": "2025-11-04T14:30:00",
  "last_updated": "2025-11-04T14:30:00"
}
```

## Integration for Shopify Fulfillment Tool

### Already Integrated ✅

The Shopify Tool integration is complete. After each analysis session, statistics are automatically recorded.

**Location**: `shopify_tool/core.py:422-460`

**Example**:
```python
from shared.stats_manager import StatsManager

# In run_full_analysis(), after successful analysis:
stats_manager = StatsManager(profile_manager.get_stats_path())

success = stats_manager.record_analysis(
    client_id="M",
    session_id="2025-11-04_1",
    orders_count=100,
    fulfillable_count=95,
    metadata={
        "session_path": "/path/to/session",
        "computer": "WAREHOUSE-PC-01"
    }
)
```

## Integration for Packing Tool

### Step-by-Step Integration

#### 1. Copy StatsManager Module

Copy `shared/stats_manager.py` to the Packing Tool project:

```bash
# Option 1: Direct copy
cp shopify-fulfillment-tool/shared/stats_manager.py packing-tool/shared/

# Option 2: Create shared directory if needed
mkdir -p packing-tool/shared
cp shopify-fulfillment-tool/shared/*.py packing-tool/shared/
```

#### 2. Import StatsManager

In your packing session manager (e.g., `src/packer_logic.py`):

```python
from shared.stats_manager import StatsManager, StatsManagerError
```

#### 3. Record Packing Statistics

Add statistics recording **after** completing a packing session:

```python
def complete_packing_session(self, session_path, orders_packed, worker_id):
    """Complete a packing session and record statistics.

    Args:
        session_path (str): Path to session directory
        orders_packed (int): Number of orders packed
        worker_id (str): ID of worker who packed the orders
    """
    try:
        # Get client_id and session_id from session_path
        # Example: Sessions/CLIENT_M/2025-11-04_1
        session_path_obj = Path(session_path)
        session_id = session_path_obj.name  # "2025-11-04_1"
        client_id = session_path_obj.parent.name.replace("CLIENT_", "")  # "M"

        # Initialize StatsManager
        stats_dir = Path(self.base_path) / "Stats"  # From ProfileManager
        stats_manager = StatsManager(stats_dir)

        # Record packing statistics
        metadata = {
            "session_path": str(session_path),
            "computer": os.environ.get('COMPUTERNAME', 'Unknown'),
            "duration_minutes": self.get_session_duration()
        }

        success = stats_manager.record_packing(
            client_id=client_id,
            session_id=session_id,
            orders_packed=orders_packed,
            worker_id=worker_id,
            metadata=metadata
        )

        if success:
            logger.info(f"Statistics recorded: {orders_packed} orders packed by {worker_id}")
        else:
            logger.warning("Failed to record packing statistics")

    except StatsManagerError as e:
        logger.error(f"Stats manager error: {e}")
        # Continue with workflow even if stats recording fails
    except Exception as e:
        logger.error(f"Unexpected error recording statistics: {e}", exc_info=True)
        # Continue with workflow even if stats recording fails
```

#### 4. Example Integration Points

**Location 1: After completing all packing in a session**
```python
# In session_manager.py or packer_logic.py
def finalize_session(self):
    # ... existing packing completion logic ...

    # Record statistics
    self.record_statistics()
```

**Location 2: In session close/complete handler**
```python
# When user clicks "Complete Session" button
def on_complete_session_clicked(self):
    orders_packed = self.get_completed_orders_count()
    worker_id = self.current_worker_id

    # Record statistics
    self.complete_packing_session(
        session_path=self.current_session_path,
        orders_packed=orders_packed,
        worker_id=worker_id
    )

    # ... rest of completion logic ...
```

### 5. Testing the Integration

Create tests for Packing Tool integration:

```python
# tests/test_packer_stats_integration.py
import pytest
from shared.stats_manager import StatsManager

def test_record_packing_integration(temp_stats_dir):
    """Test that packing statistics are recorded correctly."""
    stats_manager = StatsManager(temp_stats_dir)

    # Simulate packing session
    success = stats_manager.record_packing(
        client_id="M",
        session_id="2025-11-04_1",
        orders_packed=95,
        worker_id="001"
    )

    assert success is True

    # Verify statistics
    stats = stats_manager.get_global_stats()
    assert stats["total_orders_packed"] == 95
    assert stats["by_client"]["M"]["orders_packed"] == 95

    # Verify history
    history = stats_manager.get_packing_history()
    assert len(history) == 1
    assert history[0]["worker_id"] == "001"
```

## API Reference

### StatsManager Class

#### Initialization

```python
from shared.stats_manager import StatsManager

stats_manager = StatsManager(stats_dir_path)
```

**Parameters**:
- `stats_dir` (Path): Path to Stats/ directory on file server

#### Methods

##### record_analysis()

Record an analysis session from Shopify Tool.

```python
success = stats_manager.record_analysis(
    client_id="M",
    session_id="2025-11-04_1",
    orders_count=100,
    fulfillable_count=95,
    metadata={"session_path": "/path/to/session"}
)
```

**Parameters**:
- `client_id` (str): Client ID (e.g., "M", "A", "B")
- `session_id` (str): Session identifier (e.g., "2025-11-04_1")
- `orders_count` (int): Total number of orders analyzed
- `fulfillable_count` (int): Number of fulfillable orders
- `metadata` (Optional[Dict]): Additional metadata

**Returns**: `bool` - True if recorded successfully

##### record_packing()

Record a packing session from Packing Tool.

```python
success = stats_manager.record_packing(
    client_id="M",
    session_id="2025-11-04_1",
    orders_packed=95,
    worker_id="001",
    metadata={"session_path": "/path/to/session"}
)
```

**Parameters**:
- `client_id` (str): Client ID
- `session_id` (str): Session identifier
- `orders_packed` (int): Number of orders packed
- `worker_id` (Optional[str]): Worker who packed the orders
- `metadata` (Optional[Dict]): Additional metadata

**Returns**: `bool` - True if recorded successfully

##### get_global_stats()

Get current global statistics.

```python
stats = stats_manager.get_global_stats()
```

**Returns**: `Dict[str, Any]` - Global statistics dictionary

##### get_client_stats()

Get statistics for a specific client.

```python
client_stats = stats_manager.get_client_stats("M")
```

**Parameters**:
- `client_id` (str): Client ID

**Returns**: `Optional[Dict[str, Any]]` - Client statistics or None

##### get_analysis_history()

Get analysis history, optionally filtered.

```python
history = stats_manager.get_analysis_history(
    client_id="M",  # Optional: filter by client
    limit=10        # Optional: limit results
)
```

**Returns**: `List[Dict[str, Any]]` - List of analysis history entries

##### get_packing_history()

Get packing history, optionally filtered.

```python
history = stats_manager.get_packing_history(
    client_id="M",  # Optional: filter by client
    limit=10        # Optional: limit results
)
```

**Returns**: `List[Dict[str, Any]]` - List of packing history entries

## Error Handling

The StatsManager uses custom exceptions:

```python
from shared.stats_manager import StatsManagerError

try:
    stats_manager = StatsManager(stats_dir)
except StatsManagerError as e:
    logger.error(f"Cannot access stats directory: {e}")
```

**Best Practice**: Always wrap statistics recording in try-except blocks and continue with the main workflow even if statistics recording fails.

## Thread Safety and Concurrent Access

The StatsManager is designed for concurrent access:

- **File Locking**: Uses platform-specific file locking (fcntl on Unix, msvcrt on Windows)
- **Unique Temp Files**: Uses UUID-based temp file names to avoid conflicts
- **Atomic Operations**: Uses `os.replace()` for atomic file updates
- **Retry Logic**: Automatically retries on lock contention (5 attempts with exponential backoff)

This allows:
- Multiple users on different PCs to update statistics simultaneously
- Shopify Tool and Packing Tool to record concurrently
- High-concurrency scenarios without data corruption

## Performance Considerations

- **Network Files**: Designed for network file shares (UNC paths)
- **Caching**: No caching on reads to ensure fresh data
- **History Limit**: Automatically limits history to last 1000 entries
- **File Size**: JSON files with pretty printing for readability

## Troubleshooting

### Issue: "Statistics file is locked"

**Cause**: High concurrent access or network latency

**Solution**:
- Automatic retry logic will handle most cases
- If persistent, check network connection
- Verify no manual file locks

### Issue: Statistics not updating

**Possible Causes**:
1. Incorrect stats_dir path
2. Permission issues
3. Network connectivity problems

**Debug Steps**:
```python
# Check if stats directory is accessible
stats_dir = Path(r"\\server\share\0UFulfilment\Stats")
print(f"Stats dir exists: {stats_dir.exists()}")
print(f"Can write: {os.access(stats_dir, os.W_OK)}")

# Enable debug logging
import logging
logging.getLogger("ShopifyToolLogger").setLevel(logging.DEBUG)
```

### Issue: Concurrent test failures

**Note**: Concurrent tests require proper file locking support. Some filesystems (especially network shares or virtualized filesystems) may have limited locking capabilities.

## Example: Complete Workflow

```python
# Shopify Tool analyzes orders
shopify_stats = StatsManager(stats_dir)
shopify_stats.record_analysis(
    client_id="M",
    session_id="2025-11-04_1",
    orders_count=100,
    fulfillable_count=95
)

# Packing Tool packs the orders
packer_stats = StatsManager(stats_dir)
packer_stats.record_packing(
    client_id="M",
    session_id="2025-11-04_1",
    orders_packed=95,
    worker_id="001"
)

# View combined statistics
stats = StatsManager(stats_dir).get_global_stats()
print(f"Total analyzed: {stats['total_orders_analyzed']}")
print(f"Total packed: {stats['total_orders_packed']}")
print(f"Client M stats: {stats['by_client']['M']}")
```

## Next Steps

1. **Copy** `shared/stats_manager.py` to Packing Tool
2. **Integrate** statistics recording after session completion
3. **Test** with integration tests
4. **Verify** statistics are updating correctly
5. **Monitor** for any file locking issues in production

## Support

For issues or questions:
- Check logs: Look for StatsManager errors in application logs
- Review tests: See `tests/test_stats_manager.py` for examples
- Check file permissions: Ensure write access to Stats/ directory
