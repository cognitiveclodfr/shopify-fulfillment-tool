# Shopify Tool & Packing Tool Integration Guide

This document describes the integration between Shopify Fulfillment Tool and Packing Tool via the centralized file server architecture.

## Table of Contents
- [Overview](#overview)
- [Workflow](#workflow)
- [File Formats](#file-formats)
- [Integration Points](#integration-points)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

---

## Overview

### Architecture

The integration uses a **shared file server** (`0UFulfilment`) as the central coordination point:

```
┌──────────────────┐         ┌──────────────────┐
│  Shopify Tool    │         │  Packing Tool    │
│  (Analysis)      │         │  (Execution)     │
└────────┬─────────┘         └────────┬─────────┘
         │                            │
         │    ┌──────────────────┐   │
         └───►│  File Server     │◄──┘
              │  (0UFulfilment)  │
              └──────────────────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
     Clients/    Sessions/    Stats/
```

### Key Principles

1. **Single Source of Truth**: All data stored centrally on file server
2. **Workflow Separation**: Shopify Tool creates analysis → Packing Tool executes
3. **Data Handoff**: Session directory is the integration point
4. **Unified Statistics**: Both tools write to same stats database

---

## Workflow

### Complete Order Fulfillment Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    SHOPIFY TOOL                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Select Client (e.g., "M")                               │
│                                                              │
│  2. Create Session                                          │
│     └─> Sessions/CLIENT_M/2025-11-05_1/                    │
│                                                              │
│  3. Load Data                                               │
│     • Orders CSV from Shopify export                        │
│     • Stock CSV from inventory system                       │
│     └─> Save to: input/                                     │
│                                                              │
│  4. Run Analysis                                            │
│     • Prioritize orders (multi-item first)                  │
│     • Simulate stock allocation                             │
│     • Apply automation rules                                │
│     • Calculate statistics                                  │
│     └─> Save to: analysis/analysis_data.xlsx               │
│                                                              │
│  5. Generate Reports                                        │
│     • Packing lists per courier (DHL, DPD, etc.)           │
│     └─> Save to: packing_lists/                            │
│     • Stock writeoff exports                                │
│     └─> Save to: stock_exports/                            │
│                                                              │
│  6. Update Session Info                                     │
│     • Mark analysis_completed = true                        │
│     • Record statistics                                     │
│                                                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Session ready for packing
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    PACKING TOOL                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Select Client (e.g., "M")                               │
│                                                              │
│  2. Browse Sessions                                         │
│     • List all CLIENT_M sessions                            │
│     • Filter: status="active", analysis_completed=true      │
│                                                              │
│  3. Load Session                                            │
│     • Read: packing_lists/DHL_packing.xlsx                 │
│     • Acquire session lock (prevent conflicts)              │
│                                                              │
│  4. Worker Packing                                          │
│     • Scan barcodes                                         │
│     • Track order completion                                │
│     • Generate package labels                               │
│                                                              │
│  5. Update Statistics                                       │
│     • Record packing completion                             │
│     • Worker performance metrics                            │
│                                                              │
│  6. Complete Session                                        │
│     • Release lock                                          │
│     • Update session status                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## File Formats

### 1. session_info.json

**Location**: `Sessions/CLIENT_{ID}/{session}/session_info.json`

**Purpose**: Session metadata and integration state

**Format**:
```json
{
  "created_by_tool": "shopify",
  "created_at": "2025-11-05T10:30:00.123456",
  "client_id": "M",
  "session_name": "2025-11-05_1",
  "status": "active",
  "pc_name": "WAREHOUSE-PC-1",

  "orders_file": "input/orders_export.csv",
  "stock_file": "input/inventory.csv",

  "analysis_completed": true,
  "analysis_timestamp": "2025-11-05T10:35:45.789012",

  "packing_lists_generated": [
    "packing_lists/DHL_packing.xlsx",
    "packing_lists/DPD_packing.xlsx",
    "packing_lists/Speedy_packing.xlsx"
  ],

  "stock_exports_generated": [
    "stock_exports/DHL_stock.xls",
    "stock_exports/DPD_stock.xls"
  ],

  "statistics": {
    "total_orders": 150,
    "fulfillable_orders": 142,
    "total_items": 450,
    "courier_breakdown": {
      "DHL": 80,
      "DPD": 62
    }
  }
}
```

**Fields**:
- `created_by_tool`: Always "shopify" for Shopify Tool
- `created_at`: ISO 8601 timestamp
- `client_id`: Client identifier (matches directory name)
- `session_name`: Directory name (YYYY-MM-DD_N)
- `status`: "active" | "completed" | "abandoned"
- `pc_name`: Computer name that created session
- `orders_file`: Relative path to orders CSV
- `stock_file`: Relative path to stock CSV
- `analysis_completed`: Boolean flag (Packing Tool checks this)
- `packing_lists_generated`: List of generated packing list files
- `stock_exports_generated`: List of generated stock export files
- `statistics`: Summary statistics from analysis

### 2. analysis_data.xlsx

**Location**: `Sessions/CLIENT_{ID}/{session}/analysis/analysis_data.xlsx`

**Purpose**: Complete analysis results from Shopify Tool

**Structure**:

| Sheet Name | Description |
|------------|-------------|
| `Analysis Data` | Main order line items with fulfillment decisions |
| `Summary Present` | SKUs that will be fulfilled |
| `Summary Missing` | SKUs in unfulfillable orders |

**Key Columns in "Analysis Data"**:
```
Order_Number              - Shopify order number
Order_Type                - "Single" or "Multi"
SKU                       - Product SKU
Product_Name              - Product name
Quantity                  - Quantity ordered
Stock                     - Initial stock level
Final_Stock               - Stock after simulation
Stock_Alert               - Low stock warning
Order_Fulfillment_Status  - "Fulfillable" or "Not Fulfillable"
Shipping_Provider         - DHL, DPD, Speedy, etc.
Destination_Country       - For international orders
System_note               - System notes (e.g., "Repeat")
Status_Note               - User/rule notes
Priority                  - "Normal", "High", etc.
```

**Usage by Packing Tool**:
- Not directly used (packing lists are pre-filtered)
- Available for troubleshooting/auditing
- Contains complete context for each order

### 3. Packing List Format

**Location**: `Sessions/CLIENT_{ID}/{session}/packing_lists/{Courier}_packing.xlsx`

**Purpose**: Filtered order list for specific courier

**Format** (Excel .xlsx):

| Destination_Country | Order_Number | SKU | Product_Name | Quantity | Shipping_Provider |
|---------------------|--------------|-----|--------------|----------|-------------------|
| Bulgaria | 12345 | SKU-001 | Product A | 2 | DHL |
| | 12345 | SKU-002 | Product B | 1 | DHL |
| Greece | 12346 | SKU-001 | Product A | 3 | DHL |

**Features**:
- Only includes **Fulfillable** orders
- Filtered by specific courier (e.g., DHL)
- Sorted by: Shipping_Provider → Order_Number → SKU
- Grouped by order (borders between orders)
- Excludes SKUs marked for exclusion
- Print-ready formatting (A4 landscape)

**Used by Packing Tool**:
```python
# Packing Tool reads this file
packing_list_path = f"{session_path}/packing_lists/DHL_packing.xlsx"
df = pd.read_excel(packing_list_path, sheet_name="Packing List")

# Iterate through orders
for order_num in df['Order_Number'].unique():
    order_items = df[df['Order_Number'] == order_num]
    # Worker scans and packs items...
```

### 4. Stock Export Format

**Location**: `Sessions/CLIENT_{ID}/{session}/stock_exports/{Courier}_stock.xls`

**Purpose**: Stock writeoff file for courier system integration

**Format** (Excel .xls for compatibility):

| Артикул | Наличност |
|---------|-----------|
| SKU-001 | 15 |
| SKU-002 | 8 |
| SKU-003 | 23 |

**Features**:
- Aggregated by SKU (sum of quantities)
- Only includes fulfillable orders
- Filtered by courier
- Compatible with courier inventory systems
- Bulgarian column headers (legacy requirement)

### 5. global_stats.json

**Location**: `Stats/global_stats.json`

**Purpose**: Unified statistics from both tools

**Format**:
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
    "A": {
      "orders_analyzed": 1800,
      "orders_packed": 1650,
      "sessions": 98
    }
  },

  "analysis_history": [
    {
      "timestamp": "2025-11-05T10:35:45.789012",
      "client_id": "M",
      "session_id": "2025-11-05_1",
      "orders_count": 150,
      "metadata": {
        "fulfillable_orders": 142,
        "courier_breakdown": {"DHL": 80, "DPD": 62}
      }
    }
  ],

  "packing_history": [
    {
      "timestamp": "2025-11-05T12:30:15.456789",
      "client_id": "M",
      "session_id": "2025-11-05_1",
      "worker_id": "001",
      "orders_count": 142,
      "items_count": 450,
      "metadata": {
        "start_time": "2025-11-05T10:00:00",
        "end_time": "2025-11-05T12:30:00",
        "duration_seconds": 9000
      }
    }
  ],

  "last_updated": "2025-11-05T12:30:15.789012",
  "version": "1.0"
}
```

**Updated by**:
- **Shopify Tool**: Increments `total_orders_analyzed`, adds to `analysis_history`
- **Packing Tool**: Increments `total_orders_packed`, `total_sessions`, adds to `packing_history`

---

## Integration Points

### Point 1: Session Creation

**Shopify Tool**:
```python
from shopify_tool.profile_manager import ProfileManager
from shopify_tool.session_manager import SessionManager

# Initialize managers
profile_mgr = ProfileManager(base_path="\\\\server\\...\\0UFulfilment")
session_mgr = SessionManager(profile_mgr)

# Create new session
session_path = session_mgr.create_session("M")
# Returns: "\\\\server\\...\\Sessions\\CLIENT_M\\2025-11-05_1"

# Session directory structure is automatically created:
# - input/
# - analysis/
# - packing_lists/
# - stock_exports/
# - session_info.json
```

### Point 2: Analysis Completion

**Shopify Tool**:
```python
# After analysis completes, update session info
session_mgr.update_session_info(
    session_path,
    {
        "analysis_completed": True,
        "analysis_timestamp": datetime.now().isoformat(),
        "packing_lists_generated": [
            "packing_lists/DHL_packing.xlsx",
            "packing_lists/DPD_packing.xlsx"
        ],
        "stock_exports_generated": [
            "stock_exports/DHL_stock.xls",
            "stock_exports/DPD_stock.xls"
        ],
        "statistics": {
            "total_orders": 150,
            "fulfillable_orders": 142,
            "courier_breakdown": {"DHL": 80, "DPD": 62}
        }
    }
)
```

### Point 3: Session Discovery

**Packing Tool**:
```python
# List available sessions for client
sessions = session_mgr.list_client_sessions("M", status_filter="active")

# Filter for completed analysis
ready_sessions = [
    s for s in sessions
    if s.get("analysis_completed") == True
]

# Display to user for selection
for session in ready_sessions:
    print(f"{session['session_name']}: {session['statistics']['total_orders']} orders")
```

### Point 4: Packing List Loading

**Packing Tool**:
```python
# User selects session and courier
session_path = "\\\\server\\...\\Sessions\\CLIENT_M\\2025-11-05_1"
courier = "DHL"

# Get packing list path
packing_lists_dir = session_mgr.get_packing_lists_dir(session_path)
packing_list_file = packing_lists_dir / f"{courier}_packing.xlsx"

# Load packing list
import pandas as pd
df = pd.read_excel(packing_list_file, sheet_name="Packing List")

# Begin packing workflow...
```

### Point 5: Statistics Recording

**Shopify Tool** (after analysis):
```python
from shared.stats_manager import StatsManager

stats_mgr = StatsManager(base_path="\\\\server\\...\\0UFulfilment")

stats_mgr.record_analysis(
    client_id="M",
    session_id="2025-11-05_1",
    orders_count=150,
    metadata={
        "fulfillable_orders": 142,
        "courier_breakdown": {"DHL": 80, "DPD": 62}
    }
)
```

**Packing Tool** (after packing):
```python
stats_mgr.record_packing(
    client_id="M",
    session_id="2025-11-05_1",
    worker_id="001",
    orders_count=142,
    items_count=450,
    metadata={
        "start_time": "2025-11-05T10:00:00",
        "end_time": "2025-11-05T12:30:00",
        "duration_seconds": 9000
    }
)
```

---

## Usage Examples

### Example 1: Complete Shopify Tool Workflow

```python
from shopify_tool.profile_manager import ProfileManager
from shopify_tool.session_manager import SessionManager
from shopify_tool import core
from shared.stats_manager import StatsManager

# 1. Initialize managers
profile_mgr = ProfileManager(base_path="\\\\192.168.88.101\\Z_GreenDelivery\\WAREHOUSE\\0UFulfilment")
session_mgr = SessionManager(profile_mgr)
stats_mgr = StatsManager(base_path="\\\\192.168.88.101\\Z_GreenDelivery\\WAREHOUSE\\0UFulfilment")

# 2. Create session
client_id = "M"
session_path = session_mgr.create_session(client_id)
print(f"Session created: {session_path}")

# 3. Copy input files to session
import shutil
input_dir = session_mgr.get_input_dir(session_path)
shutil.copy("orders_export.csv", input_dir / "orders.csv")
shutil.copy("inventory.csv", input_dir / "stock.csv")

# 4. Load client configuration
config = profile_mgr.load_shopify_config(client_id)

# 5. Run analysis
analysis_dir = session_mgr.get_analysis_dir(session_path)
success, output_path, df, stats = core.run_full_analysis(
    stock_file_path=str(input_dir / "stock.csv"),
    orders_file_path=str(input_dir / "orders.csv"),
    output_dir_path=str(analysis_dir),
    stock_delimiter=";",
    config=config
)

if success:
    print(f"Analysis completed: {output_path}")

    # 6. Generate packing lists
    packing_lists_dir = session_mgr.get_packing_lists_dir(session_path)

    for packing_list_config in config["packing_lists"]:
        success, msg = core.create_packing_list_report(df, packing_list_config)
        if success:
            print(f"Packing list created: {msg}")

    # 7. Generate stock exports
    stock_exports_dir = session_mgr.get_stock_exports_dir(session_path)

    for stock_export_config in config["stock_exports"]:
        success, msg = core.create_stock_export_report(df, stock_export_config)
        if success:
            print(f"Stock export created: {msg}")

    # 8. Update session info
    session_mgr.update_session_info(
        session_path,
        {
            "analysis_completed": True,
            "analysis_timestamp": datetime.now().isoformat(),
            "statistics": stats
        }
    )

    # 9. Record statistics
    stats_mgr.record_analysis(
        client_id=client_id,
        session_id=Path(session_path).name,
        orders_count=stats["total_orders_completed"] + stats["total_orders_not_completed"],
        metadata={
            "fulfillable_orders": stats["total_orders_completed"],
            "courier_breakdown": {
                c["courier_id"]: c["orders_assigned"]
                for c in stats.get("couriers_stats", [])
            }
        }
    )

    print("✓ Session ready for packing")
```

### Example 2: Packing Tool Session Discovery

```python
from shopify_tool.profile_manager import ProfileManager
from shopify_tool.session_manager import SessionManager

# Initialize managers
profile_mgr = ProfileManager(base_path="\\\\192.168.88.101\\Z_GreenDelivery\\WAREHOUSE\\0UFulfilment")
session_mgr = SessionManager(profile_mgr)

# List sessions for client
client_id = "M"
sessions = session_mgr.list_client_sessions(client_id, status_filter="active")

# Filter for ready sessions
ready_sessions = []
for session in sessions:
    session_info = session_mgr.get_session_info(session["session_path"])

    if session_info and session_info.get("analysis_completed"):
        ready_sessions.append({
            "name": session_info["session_name"],
            "created_at": session_info["created_at"],
            "total_orders": session_info.get("statistics", {}).get("total_orders", 0),
            "path": session_info["session_path"]
        })

# Display to user
print("Available sessions for packing:")
for idx, session in enumerate(ready_sessions, 1):
    print(f"{idx}. {session['name']} - {session['total_orders']} orders - {session['created_at']}")
```

### Example 3: Cross-Tool Statistics Query

```python
from shared.stats_manager import StatsManager

stats_mgr = StatsManager(base_path="\\\\192.168.88.101\\Z_GreenDelivery\\WAREHOUSE\\0UFulfilment")

# Get global statistics
global_stats = stats_mgr.get_global_stats()
print(f"Total orders analyzed: {global_stats['total_orders_analyzed']}")
print(f"Total orders packed: {global_stats['total_orders_packed']}")
print(f"Packing efficiency: {global_stats['total_orders_packed'] / global_stats['total_orders_analyzed'] * 100:.1f}%")

# Get client-specific statistics
client_stats = stats_mgr.get_client_stats("M")
print(f"\nClient M:")
print(f"  Analyzed: {client_stats['orders_analyzed']}")
print(f"  Packed: {client_stats['orders_packed']}")
print(f"  Sessions: {client_stats['sessions']}")

# Get recent analysis history
recent_analysis = stats_mgr.get_analysis_history(client_id="M", limit=10)
for record in recent_analysis:
    print(f"{record['timestamp']}: {record['orders_count']} orders")
```

---

## Best Practices

### 1. Session Naming

- Use `SessionManager.create_session()` to ensure unique names
- Format: `{YYYY-MM-DD_N}` where N auto-increments
- Never manually create session directories

### 2. File Locking

- Both tools use file locking for concurrent safety
- Shopify Tool: Locks during config saves
- Packing Tool: Locks entire session during packing
- Respect lock timeouts and retry logic

### 3. Error Handling

```python
from shopify_tool.profile_manager import NetworkError, ProfileManagerError
from shopify_tool.session_manager import SessionManagerError

try:
    profile_mgr = ProfileManager(base_path=server_path)
except NetworkError as e:
    print(f"Cannot connect to file server: {e}")
    # Fallback: work in offline mode or retry
except ProfileManagerError as e:
    print(f"Configuration error: {e}")
```

### 4. Session Status Management

```python
# Shopify Tool: Mark session as completed after analysis
session_mgr.update_session_status(session_path, "completed")

# Packing Tool: Mark as completed after packing
session_mgr.update_session_status(session_path, "completed")

# Either tool: Mark as abandoned if cancelled
session_mgr.update_session_status(session_path, "abandoned")
```

### 5. Data Validation

- Always check `analysis_completed` before loading in Packing Tool
- Verify file existence before reading
- Validate data structure after loading

### 6. Performance Optimization

- Use caching for frequently accessed configs (60-second TTL)
- Load only required columns from analysis data
- Filter sessions before loading full metadata

### 7. Backup and Recovery

- ProfileManager automatically backs up configs (last 10)
- Session directories can be manually backed up
- Statistics file should be backed up regularly

---

**Document Version**: 1.0
**Last Updated**: 2025-11-05
**Part of**: Unified Development Plan (Phase 1.7)
