# Shopify Fulfillment Tool - Architecture Documentation

## Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Data Flow](#data-flow)
- [Core Components](#core-components)
- [Design Patterns](#design-patterns)
- [Threading Model](#threading-model)
- [Configuration Management](#configuration-management)

## Overview

The Shopify Fulfillment Tool is a desktop application built with Python and PySide6 (Qt for Python) that automates and streamlines the order fulfillment process for Shopify e-commerce stores. The application follows a Model-View-Controller (MVC) architecture with clear separation between business logic (backend), user interface (frontend), and data processing.

## System Architecture

The application is structured in three main layers:

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│    (PySide6 GUI - gui/ directory)       │
│  - Main Window                          │
│  - Dialogs & Widgets                    │
│  - Event Handlers                       │
└────────────┬────────────────────────────┘
             │
             │ Qt Signals/Slots
             │
┌────────────▼────────────────────────────┐
│       Business Logic Layer              │
│  (shopify_tool/ directory)              │
│  - Core Analysis Engine                 │
│  - Rule Engine                          │
│  - Report Generators                    │
└────────────┬────────────────────────────┘
             │
             │ pandas DataFrames
             │
┌────────────▼────────────────────────────┐
│         Data Layer                      │
│  - CSV File I/O                         │
│  - Excel Report Generation              │
│  - Configuration (JSON)                 │
│  - Session Persistence (Pickle)         │
└─────────────────────────────────────────┘
```

## Technology Stack

### Core Technologies
- **Python 3.9+**: Main programming language
- **PySide6 (Qt 6)**: GUI framework for cross-platform desktop interface
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations for analysis

### Data Processing
- **openpyxl**: Modern Excel file creation (.xlsx)
- **xlsxwriter**: Excel file creation with advanced formatting
- **xlwt/xlrd/xlutils**: Legacy Excel format support (.xls)

### Development Tools
- **pytest**: Testing framework
- **pytest-qt**: Qt testing utilities
- **pytest-mock**: Mocking for tests
- **ruff**: Code linting and formatting
- **PyInstaller**: Executable packaging

### Logging & Utilities
- **logging**: Standard Python logging
- **python-dateutil**: Date/time handling
- **pytz**: Timezone support

## Project Structure

```
shopify-fulfillment-tool/
├── shopify_tool/           # Backend business logic
│   ├── __init__.py
│   ├── core.py            # Orchestration & validation
│   ├── analysis.py        # Fulfillment simulation engine
│   ├── rules.py           # Configurable rule engine
│   ├── packing_lists.py   # Packing list generation
│   ├── stock_export.py    # Stock export generation
│   ├── utils.py           # Utility functions
│   └── logger_config.py   # Logging configuration
│
├── gui/                    # Frontend UI components
│   ├── __init__.py
│   ├── main_window_pyside.py       # Main application window
│   ├── settings_window_pyside.py   # Settings dialog
│   ├── actions_handler.py          # User action handlers
│   ├── ui_manager.py               # UI widget manager
│   ├── file_handler.py             # File I/O handling
│   ├── report_builder_window_pyside.py  # Custom report builder
│   ├── pandas_model.py             # DataFrame table model
│   ├── profile_manager_dialog.py   # Profile management
│   ├── report_selection_dialog.py  # Report selection UI
│   ├── worker.py                   # Background thread worker
│   ├── log_handler.py              # Qt logging handler
│   └── log_viewer.py               # Log viewing widget
│
├── tests/                  # Test suite
│   ├── test_analysis.py
│   ├── test_core.py
│   ├── test_rules.py
│   ├── test_packing_lists.py
│   ├── test_stock_export.py
│   └── ...
│
├── data/                   # Data files & templates
│   ├── templates/          # Excel templates
│   ├── input/             # Sample input files
│   └── output/            # Generated reports
│
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md    # This file
│   ├── API.md            # API reference
│   └── FUNCTIONS.md      # Function catalog
│
├── gui_main.py            # Application entry point
├── config.json            # Default configuration
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── pyproject.toml        # Project configuration
└── README.md             # Project overview
```

## Data Flow

### 1. Initial Setup Flow
```
User → New Session → Create Dated Folder
     → Load Orders CSV → Validate Headers
     → Load Stock CSV → Validate Headers
     → Ready for Analysis
```

### 2. Analysis Flow
```
Input Files (CSV)
    ↓
core.run_full_analysis()
    ↓
analysis.run_analysis() ← History Data
    ├─ Data Cleaning
    ├─ Order Prioritization (Multi-item first)
    ├─ Stock Simulation
    ├─ Final Stock Calculation
    └─ Summary Generation
    ↓
rules.RuleEngine.apply() ← Configuration Rules
    ├─ Match Conditions
    └─ Execute Actions
    ↓
Output: DataFrame + Statistics
    ↓
Save to Excel + Update History
```

### 3. Report Generation Flow
```
Analysis DataFrame
    ↓
Filter by Criteria (packing_lists/stock_exports)
    ↓
Apply Template/Formatting
    ↓
Generate Excel File → Session Folder
```

## Core Components

### 1. Backend (shopify_tool/)

#### core.py - Orchestration Layer
- **Purpose**: Main entry point for all backend operations
- **Key Functions**:
  - `run_full_analysis()`: Orchestrates entire analysis workflow
  - `validate_csv_headers()`: Pre-validation of input files
  - `create_packing_list_report()`: Report generation wrapper
  - `create_stock_export_report()`: Stock export wrapper
- **Responsibilities**:
  - File I/O coordination
  - Data validation
  - History management
  - Excel report generation

#### analysis.py - Analysis Engine
- **Purpose**: Core fulfillment simulation logic
- **Key Functions**:
  - `run_analysis()`: Main simulation engine
  - `recalculate_statistics()`: Stats computation
  - `toggle_order_fulfillment()`: Manual status override
- **Algorithm**:
  1. Clean and standardize data
  2. Prioritize orders (multi-item first for completion maximization)
  3. Simulate stock allocation
  4. Calculate final stock levels
  5. Generate summaries

#### rules.py - Rule Engine
- **Purpose**: Configurable automation of order processing
- **Architecture**:
  - Operator functions (contains, equals, greater_than, etc.)
  - `RuleEngine` class for rule application
- **Capabilities**:
  - Conditional logic (ALL/ANY matching)
  - Actions: ADD_TAG, SET_STATUS, SET_PRIORITY, EXCLUDE_FROM_REPORT
  - Field-based filtering on any DataFrame column

#### packing_lists.py - Report Generator
- **Purpose**: Generate formatted packing lists
- **Features**:
  - Multi-filter support
  - SKU exclusion
  - Advanced Excel formatting (borders, colors, print settings)
  - Courier-based sorting

#### stock_export.py - Export Generator
- **Purpose**: Create stock export files
- **Features**:
  - Template-free generation
  - Aggregation by SKU
  - Multiple format support (.xls, .xlsx)

### 2. Frontend (gui/)

#### main_window_pyside.py - Main Window
- **Purpose**: Primary application interface
- **Components**:
  - Session management
  - File loading
  - Data table display (with sorting/filtering)
  - Statistics display
  - Activity logging
- **Pattern**: Orchestrator that delegates to specialized handlers

#### Specialized Handlers

1. **ui_manager.py**: UI widget creation and layout
2. **file_handler.py**: File selection and validation
3. **actions_handler.py**: Business logic integration
4. **worker.py**: Background task execution

#### Dialog Windows

1. **settings_window_pyside.py**: Configuration editor
2. **report_builder_window_pyside.py**: Custom report creator
3. **profile_manager_dialog.py**: Profile management
4. **report_selection_dialog.py**: Report picker

#### Data Models

1. **pandas_model.py**: Qt table model for pandas DataFrames
   - Custom row coloring based on status
   - Efficient large dataset handling

## Design Patterns

### 1. Model-View-Controller (MVC)
- **Model**: pandas DataFrames (business data)
- **View**: PySide6 widgets (UI components)
- **Controller**: Handler classes (actions_handler, file_handler)

### 2. Observer Pattern
- **Implementation**: Qt Signals/Slots
- **Usage**: `data_changed` signal triggers UI refresh across components

### 3. Strategy Pattern
- **Implementation**: Rule Engine operators
- **Usage**: Different comparison strategies for rule conditions

### 4. Worker Pattern
- **Implementation**: `Worker` class with `QRunnable`
- **Usage**: Background execution of long-running tasks

### 5. Facade Pattern
- **Implementation**: `core.py` module
- **Usage**: Simplified interface to complex backend subsystems

## Threading Model

### Main Thread (GUI Thread)
- Handles all UI updates
- Receives signals from worker threads
- Manages user interactions

### Worker Threads (QThreadPool)
- **Analysis Worker**: Runs `core.run_full_analysis()`
- **Report Workers**: Generate packing lists and stock exports
- **Signals**:
  - `finished`: Task completion
  - `result`: Success with data
  - `error`: Exception with traceback

### Thread Safety
- All DataFrame modifications occur in worker threads
- Results passed back via Qt signals
- UI updates only in main thread

## Recent Architecture Improvements (v1.8)

### Refactored Core Functions

#### Before Refactoring (v1.7)
```
run_full_analysis()           run_analysis()
├─ 422 lines                  ├─ 364 lines
├─ Complexity: 56             ├─ Complexity: 42
├─ 10 parameters              ├─ 5 parameters
├─ Max nesting: 5             ├─ Max nesting: 3
└─ Monolithic structure       └─ Sequential processing
```

#### After Refactoring (v1.8)
```
run_full_analysis() [80 lines, complexity: ~10]
├─ _validate_and_prepare_inputs()      [84 lines]
├─ _load_and_validate_files()          [118 lines]
├─ _load_history_data()                [75 lines]
├─ _run_analysis_and_rules()           [73 lines]
└─ _save_results_and_reports()         [193 lines]

run_analysis() [65 lines, complexity: ~10]
├─ _clean_and_prepare_data()           [157 lines]
├─ _prioritize_orders()                [54 lines]
├─ _simulate_fulfillment()             [112 lines]
│  ├─ _is_order_fulfillable()         [helper]
│  └─ _deduct_stock()                 [helper]
├─ _calculate_final_stock()            [52 lines]
├─ _merge_results_to_dataframe()       [83 lines]
└─ _generate_summary_reports()         [32 lines]
```

### Benefits Achieved

**Maintainability:**
- Each function has ONE clear responsibility
- Functions average 50-120 lines (optimal size)
- Easy to locate and fix bugs
- Clear entry points for modifications

**Testability:**
- Individual phases can be unit tested
- Mock dependencies easily
- Test edge cases without full workflow
- Faster test execution

**Readability:**
- Main functions read like narratives
- Self-documenting code structure
- Clear data flow between phases
- Logical progression of operations

**Performance:**
- Vectorized operations (no df.iterrows())
- Efficient data structures
- Optimized for large datasets
- 10-50x speed improvement

### Design Patterns Applied

**Single Responsibility Principle:**
- Each phase function handles one aspect of processing
- Clear boundaries between validation, loading, processing, and saving

**Pipeline Pattern:**
- Data flows through sequential phases
- Each phase transforms data for next phase
- Error handling at each boundary

**Modular Architecture:**
- Functions can be reused independently
- Easy to swap implementations
- Clear interfaces between modules

---

## Server Architecture (Phase 1 - Unified Development)

### Centralized File Server Structure

The application uses a **centralized file server architecture** for multi-PC warehouse operations:

```
\\Server\Share\0UFulfilment\
├── Clients/
│   ├── CLIENT_M/
│   │   ├── client_config.json      # General client settings
│   │   ├── shopify_config.json     # Shopify-specific config
│   │   └── backups/                # Automatic config backups
│   └── CLIENT_{ID}/
│       └── ...
├── Sessions/
│   ├── CLIENT_M/
│   │   ├── 2025-11-05_1/
│   │   │   ├── session_info.json   # Session metadata
│   │   │   ├── input/              # Orders & stock CSV files
│   │   │   ├── analysis/           # Analysis results
│   │   │   ├── packing_lists/      # Generated packing lists
│   │   │   └── stock_exports/      # Stock writeoff exports
│   │   └── 2025-11-05_2/
│   │       └── ...
│   └── CLIENT_{ID}/
│       └── ...
├── Stats/
│   └── global_stats.json           # Unified statistics
└── Logs/
    └── shopify_tool/                # Centralized logging
```

### Integration with Packing Tool

```
┌─────────────────────────────────────────────────────────┐
│                  File Server (0UFulfilment)              │
├─────────────────────────────────────────────────────────┤
│  Clients/  │  Sessions/  │  Stats/  │  Logs/            │
└──────┬──────────────┬────────────┬──────────────────────┘
       │              │            │
       ▼              ▼            ▼
┌──────────────┐  ┌──────────────┐
│ Shopify Tool │  │ Packing Tool │
├──────────────┤  ├──────────────┤
│ 1. Analysis  │──►│ 1. Load      │
│    - Orders  │  │    session    │
│    - Stock   │  │              │
│              │  │              │
│ 2. Generate  │  │ 2. Worker    │
│    - Packing │──►│    packing   │
│      lists   │  │              │
│    - Stock   │  │              │
│      exports │  │ 3. Stats     │
│              │  │    tracking  │
│ 3. Session   │◄─┤              │
│    info      │  │              │
└──────────────┘  └──────────────┘
       │                 │
       └─────────┬───────┘
                 ▼
         ┌───────────────┐
         │ StatsManager  │
         │ (Unified)     │
         └───────────────┘
```

### Profile Management System

#### ProfileManager
**Location**: `shopify_tool/profile_manager.py`

Manages client-specific configurations on the file server with:
- Client profile CRUD operations
- Configuration caching (60-second TTL)
- File locking for concurrent access
- Network connectivity testing
- Automatic backups (keeps last 10)
- Validation of client IDs

**Key Features**:
```python
# Create new client profile
profile_mgr.create_client_profile(
    client_id="M",
    client_name="M Cosmetics"
)

# Load configuration with caching
config = profile_mgr.load_shopify_config("M")

# Save with file locking and backup
profile_mgr.save_shopify_config("M", updated_config)
```

#### SessionManager
**Location**: `shopify_tool/session_manager.py`

Manages session lifecycle for client work sessions:
- Create timestamped sessions (`{YYYY-MM-DD_N}`)
- Session directory structure setup
- Metadata management (`session_info.json`)
- Session listing and querying
- Status updates (active/completed/abandoned)

**Session Workflow**:
```
1. create_session("M")
   └─> Creates: Sessions/CLIENT_M/2025-11-05_1/
       - session_info.json
       - input/
       - analysis/
       - packing_lists/
       - stock_exports/

2. Run analysis → Save to analysis/

3. Generate reports → Save to packing_lists/, stock_exports/

4. update_session_status("completed")
```

#### StatsManager (Unified)
**Location**: `shared/stats_manager.py`

Provides unified statistics tracking for both Shopify and Packing tools:
- Centralized storage (`Stats/global_stats.json`)
- File locking for concurrent multi-PC access
- Separate tracking for analysis and packing
- Per-client statistics breakdown
- Thread-safe and process-safe operations

**Statistics Structure**:
```json
{
  "total_orders_analyzed": 5420,    // From Shopify Tool
  "total_orders_packed": 4890,      // From Packing Tool
  "total_sessions": 312,
  "by_client": {
    "M": {
      "orders_analyzed": 2100,
      "orders_packed": 1950,
      "sessions": 145
    }
  },
  "analysis_history": [...],
  "packing_history": [...]
}
```

## Configuration Management

### Configuration Structure
```json
{
  "profiles": {
    "Default": {
      "settings": { ... },
      "paths": { ... },
      "rules": [ ... ],
      "packing_lists": [ ... ],
      "stock_exports": [ ... ],
      "column_mappings": { ... }
    }
  },
  "active_profile": "Default"
}
```

### Profile System
- **Purpose**: Support multiple configurations for different warehouses/workflows
- **Location**: `%APPDATA%/ShopifyFulfillmentTool/config.json` (Windows) - **Deprecated**
- **New Location**: File server `Clients/CLIENT_{ID}/shopify_config.json`
- **Migration**: Automatic upgrade from old format to server-based profiles

### Persistent Data
- **Client Config**: `Clients/CLIENT_{ID}/client_config.json` on file server
- **Shopify Config**: `Clients/CLIENT_{ID}/shopify_config.json` on file server
- **Session Info**: `Sessions/CLIENT_{ID}/{session}/session_info.json`
- **Statistics**: `Stats/global_stats.json` (unified)

## Error Handling

### Validation Layers
1. **Pre-validation**: CSV header checks before loading
2. **Data validation**: Required columns check after loading
3. **Type validation**: Data type conversions with error handling

### User Feedback
- **Status Labels**: Visual indicators (✓/✗) for file validity
- **Message Boxes**: Critical errors and confirmations
- **Logs**: Detailed activity and execution logs
- **Color Coding**: Visual status indication in data tables

## Performance Considerations

### Optimization Strategies
1. **Lazy Loading**: Load only headers for validation
2. **Vectorized Operations**: Use pandas/numpy for bulk operations
3. **Background Processing**: Long operations in worker threads
4. **Proxy Model**: Efficient filtering/sorting with `QSortFilterProxyModel`

### Scalability
- Tested with datasets up to 10,000+ order lines
- Efficient memory usage with pandas DataFrame operations
- Streaming approach for file I/O where applicable

## Security Considerations

1. **File Access**: Limited to user-selected files and app data directory
2. **Configuration**: JSON validation to prevent malformed configs
3. **Logging**: Sensitive data not logged (only metadata)
4. **Permissions**: Standard user-level permissions (no admin required)

## Extension Points

### Adding New Features

1. **New Report Type**:
   - Add generator function in `shopify_tool/`
   - Add UI in `settings_window_pyside.py`
   - Add handler in `actions_handler.py`

2. **New Rule Action**:
   - Add action type to `rules.py`
   - Update `_execute_actions()` method
   - Add UI option in settings

3. **New Column/Field**:
   - Update `analysis.py` to include column
   - Add to output columns list
   - Update config for required columns if needed

## Testing Strategy

### Test Coverage
- **Unit Tests**: Individual function testing
- **Integration Tests**: Module interaction testing
- **GUI Tests**: UI component testing with pytest-qt
- **Mock Tests**: External dependency mocking

### Test Organization
- Mirror source structure in `tests/` directory
- Fixtures for common test data
- Parametrized tests for multiple scenarios

## Build & Deployment

### Development
```bash
python gui_main.py
```

### Testing
```bash
pytest
```

### Building Executable
```bash
pyinstaller --onefile --windowed gui_main.py
```

### CI/CD Pipeline
- **Linting**: ruff check on push
- **Testing**: pytest on push/PR
- **Building**: PyInstaller on release creation
- **Deployment**: Automatic GitHub release asset upload

---

**Document Version**: 1.0
**Last Updated**: 2025-11-04
**Maintained By**: Development Team
