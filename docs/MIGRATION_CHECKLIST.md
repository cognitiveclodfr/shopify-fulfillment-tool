# Migration Checklist - Server-Based Architecture

This document provides step-by-step instructions for migrating from the old local-based system to the new centralized file server architecture.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Migration Overview](#migration-overview)
- [Step-by-Step Migration](#step-by-step-migration)
- [First Client Profile Setup](#first-client-profile-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Rollback Plan](#rollback-plan)

---

## Prerequisites

### Infrastructure Requirements

✅ **File Server**:
- Windows Server or NAS with SMB/CIFS share
- Example path: `\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment`
- Minimum free space: 10 GB (per client)
- Network speed: Minimum 100 Mbps

✅ **Network**:
- Stable local network connection
- All PCs can access file server
- No firewall blocking SMB ports (445, 139)

✅ **Permissions**:
- Read/write access to file server for all users
- Ability to create directories
- Ability to lock files (for concurrent access)

✅ **Software**:
- Python 3.9+ installed
- All dependencies from `requirements.txt`
- Updated Shopify Tool codebase (includes ProfileManager, SessionManager, StatsManager)

### Pre-Migration Backup

⚠️ **IMPORTANT**: Backup existing data before migration

```bash
# 1. Backup local configuration
cp %APPDATA%/ShopifyFulfillmentTool/config.json config_backup.json

# 2. Backup local history
cp %APPDATA%/ShopifyFulfillmentTool/fulfillment_history.csv history_backup.csv

# 3. Backup session data (if any)
cp -r data/output/* output_backup/
```

---

## Migration Overview

### What Changes?

| Component | Old System | New System |
|-----------|------------|------------|
| **Configuration** | Local JSON file per PC | Centralized per client on server |
| **Session Storage** | Local `data/output/` directory | Server `Sessions/CLIENT_{ID}/` |
| **History** | Local CSV file | Integrated into session metadata |
| **Statistics** | None | Unified `Stats/global_stats.json` |
| **Multi-PC** | Not supported | Full support with file locking |
| **Integration** | None | Direct integration with Packing Tool |

### Migration Path

```
Old System                    New System
──────────                    ──────────

Local PC 1                    File Server
  config.json      ─┐           ├─ Clients/CLIENT_M/
  history.csv      ─┤             │  └─ shopify_config.json
  data/output/     ─┤             ├─ Sessions/CLIENT_M/
                    │             │  └─ 2025-11-05_1/
Local PC 2         │             ├─ Stats/
  config.json      ─┘             │  └─ global_stats.json
  ...                             └─ Logs/
```

---

## Step-by-Step Migration

### Phase 1: File Server Setup

#### 1.1 Create Directory Structure

On the file server, create the base directory structure:

```bash
# If using Windows Server
mkdir \\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment
cd \\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment

mkdir Clients
mkdir Sessions
mkdir Stats
mkdir Logs
mkdir Logs\shopify_tool
```

Alternatively, create a script `setup_server.bat`:

```batch
@echo off
set BASE_PATH=\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment

echo Creating directory structure on file server...

mkdir "%BASE_PATH%"
mkdir "%BASE_PATH%\Clients"
mkdir "%BASE_PATH%\Sessions"
mkdir "%BASE_PATH%\Stats"
mkdir "%BASE_PATH%\Logs"
mkdir "%BASE_PATH%\Logs\shopify_tool"

echo.
echo ✓ Directory structure created successfully
echo.
echo Base path: %BASE_PATH%
pause
```

Run as administrator: `setup_server.bat`

#### 1.2 Set Permissions

Ensure all warehouse PCs have read/write access:

1. Right-click on `0UFulfilment` folder
2. Properties → Sharing → Advanced Sharing
3. Check "Share this folder"
4. Permissions → Add users → Grant "Full Control"
5. Apply and OK

#### 1.3 Test Connectivity

Create test file from each PC:

```python
# test_connection.py
from pathlib import Path

base_path = Path(r"\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment")

try:
    # Test write access
    test_file = base_path / ".connection_test"
    test_file.touch()

    # Test read access
    if test_file.exists():
        print("✓ Connection successful")
        test_file.unlink()  # Clean up
    else:
        print("✗ Cannot read from server")

except Exception as e:
    print(f"✗ Connection failed: {e}")
```

Run on each PC: `python test_connection.py`

### Phase 2: Application Update

#### 2.1 Update Codebase

```bash
# Pull latest code with migration support
git pull origin main

# Verify migration modules exist
python -c "from shopify_tool.profile_manager import ProfileManager; print('✓ ProfileManager available')"
python -c "from shopify_tool.session_manager import SessionManager; print('✓ SessionManager available')"
python -c "from shared.stats_manager import StatsManager; print('✓ StatsManager available')"
```

#### 2.2 Install Dependencies

```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Verify installation
pip list | grep -E "(msvcrt|fcntl)"  # File locking support
```

### Phase 3: Initial Configuration

#### 3.1 Initialize ProfileManager

Create initialization script `init_profile_manager.py`:

```python
"""Initialize ProfileManager and verify connectivity."""

from shopify_tool.profile_manager import ProfileManager, NetworkError
import sys

# Configure your file server path
BASE_PATH = r"\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment"

def main():
    print("Initializing ProfileManager...")
    print(f"Base path: {BASE_PATH}")
    print()

    try:
        # Initialize ProfileManager
        profile_mgr = ProfileManager(BASE_PATH)

        print("✓ ProfileManager initialized successfully")
        print(f"  Network available: {profile_mgr.is_network_available}")
        print(f"  Clients directory: {profile_mgr.clients_dir}")
        print(f"  Sessions directory: {profile_mgr.sessions_dir}")
        print(f"  Stats directory: {profile_mgr.stats_dir}")
        print(f"  Logs directory: {profile_mgr.logs_dir}")
        print()

        # List existing clients
        clients = profile_mgr.list_clients()
        print(f"Existing clients: {clients if clients else 'None'}")
        print()

        return True

    except NetworkError as e:
        print(f"✗ Network Error: {e}")
        print()
        print("Troubleshooting steps:")
        print("  1. Verify file server is online")
        print("  2. Check network connection")
        print("  3. Verify BASE_PATH is correct")
        print("  4. Check SMB/CIFS access permissions")
        return False

    except Exception as e:
        print(f"✗ Unexpected Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

Run: `python init_profile_manager.py`

Expected output:
```
Initializing ProfileManager...
Base path: \\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment

✓ ProfileManager initialized successfully
  Network available: True
  Clients directory: \\192.168.88.101\...\Clients
  Sessions directory: \\192.168.88.101\...\Sessions
  Stats directory: \\192.168.88.101\...\Stats
  Logs directory: \\192.168.88.101\...\Logs\shopify_tool

Existing clients: None
```

---

## First Client Profile Setup

### Step 1: Create Client Profile

Create script `create_client.py`:

```python
"""Create first client profile."""

from shopify_tool.profile_manager import ProfileManager, ValidationError
import sys

BASE_PATH = r"\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment"

def create_client(client_id: str, client_name: str):
    """Create a new client profile."""

    print(f"Creating client profile...")
    print(f"  Client ID: {client_id}")
    print(f"  Client Name: {client_name}")
    print()

    try:
        # Initialize ProfileManager
        profile_mgr = ProfileManager(BASE_PATH)

        # Validate client ID
        is_valid, error_msg = ProfileManager.validate_client_id(client_id)
        if not is_valid:
            print(f"✗ Invalid client ID: {error_msg}")
            return False

        # Create client profile
        success = profile_mgr.create_client_profile(client_id, client_name)

        if success:
            print("✓ Client profile created successfully")
            print()
            print(f"Directory: {profile_mgr.get_client_directory(client_id)}")
            print()
            print("Created files:")
            print("  • client_config.json")
            print("  • shopify_config.json")
            print("  • backups/ directory")
            print()
            return True
        else:
            print("ℹ Client already exists")
            return True

    except ValidationError as e:
        print(f"✗ Validation Error: {e}")
        return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    # Replace with your client details
    CLIENT_ID = "M"
    CLIENT_NAME = "M Cosmetics"

    success = create_client(CLIENT_ID, CLIENT_NAME)
    sys.exit(0 if success else 1)
```

Run: `python create_client.py`

Expected output:
```
Creating client profile...
  Client ID: M
  Client Name: M Cosmetics

✓ Client profile created successfully

Directory: \\192.168.88.101\...\Clients\CLIENT_M

Created files:
  • client_config.json
  • shopify_config.json
  • backups/ directory
```

### Step 2: Migrate Existing Configuration (Optional)

If you have existing configuration from old system:

```python
"""Migrate existing configuration to client profile."""

import json
from pathlib import Path
from shopify_tool.profile_manager import ProfileManager

BASE_PATH = r"\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment"
OLD_CONFIG_PATH = Path(r"%APPDATA%\ShopifyFulfillmentTool\config.json").expanduser()

def migrate_config(client_id: str):
    """Migrate old config to new client profile."""

    if not OLD_CONFIG_PATH.exists():
        print("No old configuration found, using defaults")
        return True

    print(f"Migrating configuration from: {OLD_CONFIG_PATH}")

    try:
        # Load old config
        with open(OLD_CONFIG_PATH, 'r', encoding='utf-8') as f:
            old_config = json.load(f)

        # Initialize ProfileManager
        profile_mgr = ProfileManager(BASE_PATH)

        # Load current shopify config
        shopify_config = profile_mgr.load_shopify_config(client_id)

        # Migrate settings
        if "active_profile" in old_config:
            active_profile_name = old_config["active_profile"]

            if "profiles" in old_config and active_profile_name in old_config["profiles"]:
                old_profile = old_config["profiles"][active_profile_name]

                # Merge settings
                if "rules" in old_profile:
                    shopify_config["rules"] = old_profile["rules"]

                if "packing_lists" in old_profile:
                    shopify_config["packing_list_configs"] = old_profile["packing_lists"]

                if "stock_exports" in old_profile:
                    shopify_config["stock_export_configs"] = old_profile["stock_exports"]

                if "column_mappings" in old_profile:
                    shopify_config["column_mappings"] = old_profile["column_mappings"]

                if "settings" in old_profile:
                    shopify_config["settings"].update(old_profile["settings"])

        # Save migrated config
        profile_mgr.save_shopify_config(client_id, shopify_config)

        print("✓ Configuration migrated successfully")
        print()
        print("Migrated:")
        print(f"  • {len(shopify_config.get('rules', []))} rules")
        print(f"  • {len(shopify_config.get('packing_list_configs', []))} packing list configs")
        print(f"  • {len(shopify_config.get('stock_export_configs', []))} stock export configs")

        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False

if __name__ == "__main__":
    CLIENT_ID = "M"
    migrate_config(CLIENT_ID)
```

### Step 3: Verify Client Profile

```python
"""Verify client profile configuration."""

from shopify_tool.profile_manager import ProfileManager
import json

BASE_PATH = r"\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment"

def verify_client(client_id: str):
    """Verify client profile is correctly set up."""

    print(f"Verifying client profile: {client_id}")
    print()

    profile_mgr = ProfileManager(BASE_PATH)

    # Check existence
    if not profile_mgr.client_exists(client_id):
        print(f"✗ Client {client_id} does not exist")
        return False

    print("✓ Client exists")

    # Load configs
    client_config = profile_mgr.load_client_config(client_id)
    shopify_config = profile_mgr.load_shopify_config(client_id)

    if not client_config or not shopify_config:
        print("✗ Configuration files missing")
        return False

    print("✓ Configuration files loaded")
    print()

    # Display summary
    print("Client Configuration:")
    print(f"  ID: {client_config.get('client_id')}")
    print(f"  Name: {client_config.get('client_name')}")
    print(f"  Created: {client_config.get('created_at')}")
    print()

    print("Shopify Configuration:")
    print(f"  Rules: {len(shopify_config.get('rules', []))}")
    print(f"  Packing lists: {len(shopify_config.get('packing_list_configs', []))}")
    print(f"  Stock exports: {len(shopify_config.get('stock_export_configs', []))}")
    print(f"  Low stock threshold: {shopify_config.get('settings', {}).get('low_stock_threshold', 'N/A')}")
    print()

    print("✓ Client profile verified successfully")
    return True

if __name__ == "__main__":
    CLIENT_ID = "M"
    verify_client(CLIENT_ID)
```

---

## Verification

### Test 1: Create Test Session

```python
"""Test session creation."""

from shopify_tool.profile_manager import ProfileManager
from shopify_tool.session_manager import SessionManager

BASE_PATH = r"\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment"

profile_mgr = ProfileManager(BASE_PATH)
session_mgr = SessionManager(profile_mgr)

# Create test session
session_path = session_mgr.create_session("M")
print(f"✓ Test session created: {session_path}")

# Verify session info
session_info = session_mgr.get_session_info(session_path)
print(f"✓ Session info loaded")
print(f"  Status: {session_info['status']}")
print(f"  Created at: {session_info['created_at']}")
print(f"  PC: {session_info['pc_name']}")
```

### Test 2: Record Statistics

```python
"""Test statistics recording."""

from shared.stats_manager import StatsManager

BASE_PATH = r"\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment"

stats_mgr = StatsManager(BASE_PATH)

# Record test analysis
stats_mgr.record_analysis(
    client_id="M",
    session_id="2025-11-05_1",
    orders_count=10,
    metadata={"test": True}
)

# Get statistics
stats = stats_mgr.get_global_stats()
print(f"✓ Statistics recorded")
print(f"  Total analyzed: {stats['total_orders_analyzed']}")
```

### Test 3: Multi-PC Access

Run this script on **two different PCs** simultaneously:

```python
"""Test concurrent access from multiple PCs."""

from shopify_tool.profile_manager import ProfileManager
import time
import os

BASE_PATH = r"\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment"

profile_mgr = ProfileManager(BASE_PATH)

print(f"PC: {os.environ.get('COMPUTERNAME', 'Unknown')}")
print(f"Testing concurrent config save...")

# Load config
config = profile_mgr.load_shopify_config("M")
print(f"✓ Config loaded")

# Modify config
config["test_timestamp"] = time.time()
config["test_pc"] = os.environ.get('COMPUTERNAME', 'Unknown')

# Save config (with file locking)
try:
    profile_mgr.save_shopify_config("M", config)
    print(f"✓ Config saved successfully with file locking")
except Exception as e:
    print(f"ℹ Config locked by another PC (expected): {e}")
```

Expected: Second PC should wait and retry until first PC releases lock.

---

## Troubleshooting

### Problem 1: Cannot Connect to File Server

**Symptoms**:
```
NetworkError: Cannot connect to file server at \\server\path
```

**Solutions**:

1. **Verify server is online**:
   ```bash
   ping 192.168.88.101
   ```

2. **Test SMB access**:
   ```bash
   # Windows
   net use \\192.168.88.101\Z_GreenDelivery

   # Should show "The command completed successfully"
   ```

3. **Check firewall**:
   - Allow SMB ports: 139, 445
   - Temporarily disable firewall to test

4. **Verify path**:
   ```python
   from pathlib import Path
   path = Path(r"\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment")
   print(path.exists())  # Should print: True
   ```

5. **Check permissions**:
   - Right-click folder → Properties → Security
   - Ensure your user has "Full Control"

### Problem 2: File Locked Error

**Symptoms**:
```
ProfileManagerError: Configuration is locked by another user
```

**Solutions**:

1. **Wait and retry** (automatic after 5 attempts):
   - System will retry with backoff
   - Usually resolves in <5 seconds

2. **Check for hung processes**:
   ```bash
   # Windows - kill hung Python processes
   taskkill /F /IM python.exe
   ```

3. **Manual lock file removal** (last resort):
   ```python
   # Only if you're sure no other PC is using it
   from pathlib import Path
   lock_file = Path(r"\\server\...\Clients\CLIENT_M\shopify_config.json.tmp")
   if lock_file.exists():
       lock_file.unlink()
   ```

### Problem 3: Session Not Found

**Symptoms**:
```
SessionManagerError: Session not found
```

**Solutions**:

1. **Verify session exists**:
   ```python
   from pathlib import Path
   session_path = Path(r"\\server\...\Sessions\CLIENT_M\2025-11-05_1")
   print(f"Exists: {session_path.exists()}")
   print(f"Is directory: {session_path.is_dir()}")
   ```

2. **Check client ID**:
   ```python
   from shopify_tool.session_manager import SessionManager
   sessions = session_mgr.list_client_sessions("M")
   print(f"Available sessions: {[s['session_name'] for s in sessions]}")
   ```

3. **Verify session_info.json**:
   ```python
   session_info_file = session_path / "session_info.json"
   print(f"session_info.json exists: {session_info_file.exists()}")
   ```

### Problem 4: Cache Issues

**Symptoms**:
- Changes not reflected immediately
- Old configuration still loading

**Solutions**:

1. **Wait for cache timeout** (60 seconds)

2. **Clear cache manually**:
   ```python
   from shopify_tool.profile_manager import ProfileManager

   # Clear class-level cache
   ProfileManager._config_cache.clear()
   ```

3. **Restart application**

### Problem 5: Permission Denied

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied: '\\\\server\\...'
```

**Solutions**:

1. **Check user permissions**:
   - File server → Properties → Security
   - Add user with "Modify" permission

2. **Run as administrator** (temporary):
   ```bash
   # Windows - right-click PowerShell
   # "Run as administrator"
   ```

3. **Check file/folder attributes**:
   ```bash
   # Windows
   attrib \\server\path\file

   # Remove read-only if needed
   attrib -R \\server\path\file
   ```

### Problem 6: Statistics Not Updating

**Symptoms**:
- `record_analysis()` succeeds but stats don't change
- File lock errors on `global_stats.json`

**Solutions**:

1. **Verify stats file exists and is writable**:
   ```python
   from pathlib import Path
   stats_file = Path(r"\\server\...\Stats\global_stats.json")
   print(f"Exists: {stats_file.exists()}")
   print(f"Writable: {os.access(stats_file, os.W_OK)}")
   ```

2. **Check for file lock**:
   ```bash
   # Windows - check file handles
   handle.exe \\server\...\Stats\global_stats.json
   ```

3. **Manually inspect stats file**:
   ```python
   import json
   with open(stats_file, 'r') as f:
       stats = json.load(f)
   print(json.dumps(stats, indent=2))
   ```

---

## Rollback Plan

If migration fails or causes issues:

### Step 1: Backup Server Data

```bash
# Create backup of server data
xcopy /E /I /H /Y \\server\...\0UFulfilment E:\backup\0UFulfilment_backup_%DATE%
```

### Step 2: Revert Application Code

```bash
# Revert to pre-migration version
git checkout <previous-commit-hash>

# Or use backup
cp -r application_backup/* .
```

### Step 3: Restore Local Configuration

```bash
# Restore local config
cp config_backup.json %APPDATA%\ShopifyFulfillmentTool\config.json

# Restore local history
cp history_backup.csv %APPDATA%\ShopifyFulfillmentTool\fulfillment_history.csv
```

### Step 4: Resume Old Workflow

Continue using local configuration until migration issues are resolved.

---

## Post-Migration Tasks

### ✅ All PCs Migrated Checklist

- [ ] All PCs can access file server
- [ ] All PCs using new client profiles
- [ ] Old local configs backed up
- [ ] Test session created and verified
- [ ] Statistics recording tested
- [ ] Concurrent access tested (2+ PCs)
- [ ] Packing Tool integration tested (if applicable)
- [ ] All users trained on new workflow

### 📋 Documentation Updates

- [ ] Update internal wiki/docs with new paths
- [ ] Document client IDs for each business unit
- [ ] Create quick reference guide for users
- [ ] Update backup procedures

### 🔄 Ongoing Maintenance

- [ ] Weekly backup of `\\server\...\0UFulfilment`
- [ ] Monitor disk space on file server
- [ ] Review statistics monthly
- [ ] Archive old sessions quarterly

---

## Getting Help

### Documentation References

- **Architecture**: See `docs/ARCHITECTURE.md`
- **API Reference**: See `docs/API.md`
- **Integration**: See `docs/INTEGRATION.md`
- **Packing Tool Migration**: See `docs/MIGRATION_GUIDE.md`

### Common Commands

```python
# Test connection
from shopify_tool.profile_manager import ProfileManager
profile_mgr = ProfileManager(r"\\server\...\0UFulfilment")

# List clients
clients = profile_mgr.list_clients()

# List sessions
from shopify_tool.session_manager import SessionManager
session_mgr = SessionManager(profile_mgr)
sessions = session_mgr.list_client_sessions("M")

# Get statistics
from shared.stats_manager import StatsManager
stats_mgr = StatsManager(r"\\server\...\0UFulfilment")
stats = stats_mgr.get_global_stats()
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-05
**Part of**: Unified Development Plan (Phase 1.7)
