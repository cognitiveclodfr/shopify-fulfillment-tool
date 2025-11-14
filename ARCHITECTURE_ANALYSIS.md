# Architecture Analysis Report
## shopify-fulfillment-tool

**Generated:** 2025-11-14
**Analysis Type:** Comprehensive code architecture review

---

## 1. MODULE DEPENDENCIES GRAPH

### shopify_tool/ (Core Business Logic)

#### shopify_tool/core.py
**External Dependencies:**
- Standard Library: os, logging, json, shutil, pathlib, typing, datetime
- Third-party: pandas, numpy

**Internal Dependencies:**
- → shopify_tool.analysis (run_analysis, recalculate_statistics, toggle_order_fulfillment)
- → shopify_tool.packing_lists (create_packing_list)
- → shopify_tool.stock_export (create_stock_export)
- → shopify_tool.rules (RuleEngine)
- → shopify_tool.utils (get_persistent_data_path)
- → shopify_tool.csv_utils (normalize_sku)

#### shopify_tool/analysis.py
**External Dependencies:**
- Standard Library: logging
- Third-party: pandas, numpy

**Internal Dependencies:**
- → shopify_tool.csv_utils (normalize_sku)
- → shopify_tool.set_decoder (decode_sets_in_orders)
- → shopify_tool.tag_manager (add_tag)

#### shopify_tool/rules.py
**External Dependencies:**
- Third-party: pandas

**Internal Dependencies:**
- → shopify_tool.tag_manager (add_tag)

#### shopify_tool/profile_manager.py
**External Dependencies:**
- Standard Library: json, logging, os, re, shutil, time, datetime, pathlib, typing
- Platform-specific: msvcrt (Windows), fcntl (Unix) - for file locking

**Internal Dependencies:**
- None (self-contained)

#### shopify_tool/session_manager.py
**External Dependencies:**
- Standard Library: json, logging, os, datetime, pathlib, typing

**Internal Dependencies:**
- Depends on profile_manager instance (passed via constructor)

#### shopify_tool/utils.py
**External Dependencies:**
- Standard Library: os, sys, logging

**Internal Dependencies:**
- None (utility module)

#### shopify_tool/packing_lists.py
**External Dependencies:**
- Standard Library: os, logging, datetime
- Third-party: pandas

**Internal Dependencies:**
- → shopify_tool.csv_utils (normalize_sku, normalize_sku_for_matching)

#### shopify_tool/stock_export.py
**External Dependencies:**
- Standard Library: logging
- Third-party: pandas, xlwt

**Internal Dependencies:**
- None

#### shopify_tool/csv_utils.py
**External Dependencies:**
- Standard Library: csv, os, logging, typing
- Third-party: pandas

**Internal Dependencies:**
- None (utility module)

#### shopify_tool/tag_manager.py
**External Dependencies:**
- Standard Library: json, typing
- Third-party: pandas

**Internal Dependencies:**
- None (utility module)

#### shopify_tool/set_decoder.py
**External Dependencies:**
- Standard Library: logging, typing
- Third-party: pandas

**Internal Dependencies:**
- None

#### shopify_tool/undo_manager.py
**External Dependencies:**
- Standard Library: json, logging, os, datetime, pathlib, typing
- Third-party: pandas

**Internal Dependencies:**
- Depends on MainWindow instance (passed via constructor)

---

### gui/ (User Interface Layer)

#### gui/main_window_pyside.py
**External Dependencies:**
- Standard Library: sys, os, json, shutil, pickle, logging, datetime
- Third-party: pandas, PySide6.*

**Internal Dependencies:**
- → shopify_tool.utils (resource_path)
- → shopify_tool.analysis (recalculate_statistics)
- → shopify_tool.profile_manager (ProfileManager, NetworkError)
- → shopify_tool.session_manager (SessionManager)
- → shopify_tool.undo_manager (UndoManager)
- → gui.log_handler (QtLogHandler)
- → gui.ui_manager (UIManager)
- → gui.file_handler (FileHandler)
- → gui.actions_handler (ActionsHandler)
- → gui.client_selector_widget (ClientSelectorWidget)
- → gui.session_browser_widget (SessionBrowserWidget)
- → gui.profile_manager_dialog (ProfileManagerDialog)

#### gui/actions_handler.py
**External Dependencies:**
- Standard Library: os, logging, datetime
- Third-party: pandas, PySide6.*

**Internal Dependencies:**
- → gui.worker (Worker)
- → shopify_tool.core (run_full_analysis, create_packing_list_report, create_stock_export_report)
- → shopify_tool.analysis (toggle_order_fulfillment)
- → shopify_tool.packing_lists (create_packing_list)
- → shopify_tool.stock_export (create_stock_export)
- → gui.settings_window_pyside (SettingsWindow)
- → gui.report_selection_dialog (ReportSelectionDialog)
- → shared.stats_manager (StatsManager)

---

### shared/ (Cross-Application Utilities)

#### shared/stats_manager.py
**External Dependencies:**
- Standard Library: json, os, time, datetime, pathlib, typing, contextlib
- Platform-specific: msvcrt (Windows), fcntl (Unix) - for file locking

**Internal Dependencies:**
- None (shared utility)

---

## CIRCULAR DEPENDENCIES

**None detected** ✓

The architecture follows a clear layered approach:
- **Layer 1:** Utilities (utils, csv_utils, tag_manager) - no internal dependencies
- **Layer 2:** Core business logic (analysis, rules, set_decoder) - depend on Layer 1
- **Layer 3:** Orchestration (core) - depends on Layer 1 & 2
- **Layer 4:** Managers (profile_manager, session_manager, undo_manager) - independent or layer 3
- **Layer 5:** GUI (main_window, actions_handler, etc.) - depends on all lower layers

---

## UNUSED IMPORTS

Based on code review, no significant unused imports detected. Most imports are actively used.

**Minor observations:**
- Some test files may have optional imports for specific test scenarios
- Platform-specific imports (msvcrt/fcntl) are conditionally imported based on OS

---

## DEPENDENCY TREE DEPTH

**Maximum depth: 4 levels**

Example deepest chain:
```
gui/main_window_pyside.py
  → gui/actions_handler.py
    → shopify_tool/core.py
      → shopify_tool/analysis.py
        → shopify_tool/csv_utils.py (Level 4)
```

---

## 2. FUNCTION USAGE ANALYSIS

### shopify_tool/core.py

| Function | Usage Count | Called From |
|----------|-------------|-------------|
| `run_full_analysis()` | **10+ times** | ↳ gui/actions_handler.py:124<br>↳ tests/test_core.py (multiple)<br>↳ tests/test_scenarios.py<br>↳ tests/test_run_analysis.py<br>↳ tests/test_core_session_integration.py |
| `validate_csv_headers()` | **2 times** | ↳ gui/file_handler.py (likely)<br>↳ tests/test_core.py |
| `create_packing_list_report()` | **5+ times** | ↳ gui/actions_handler.py<br>↳ tests/test_packing_lists.py<br>↳ tests/test_scenarios.py |
| `create_stock_export_report()` | **5+ times** | ↳ gui/actions_handler.py<br>↳ tests/test_stock_export.py<br>↳ tests/test_scenarios.py |
| `get_unique_column_values()` | **2 times** | ↳ gui/ widgets (filters, selectors) |
| `_normalize_unc_path()` | **1 time** | ↳ shopify_tool/core.py:359 (internal only) |
| `_get_sku_dtype_dict()` | **2 times** | ↳ shopify_tool/core.py:367, 368 (internal only) |
| `_create_analysis_data_for_packing()` | **1 time** | ↳ shopify_tool/core.py:591 (internal only) |
| `_validate_dataframes()` | **1 time** | ↳ shopify_tool/core.py:429 (internal only) |

### shopify_tool/analysis.py

| Function | Usage Count | Called From |
|----------|-------------|-------------|
| `run_analysis()` | **10+ times** | ↳ shopify_tool/core.py:489<br>↳ tests/test_analysis.py (multiple)<br>↳ tests/test_sets_integration.py<br>↳ tests/test_column_mappings.py<br>↳ tests/test_analysis_exhaustive.py |
| `recalculate_statistics()` | **5+ times** | ↳ shopify_tool/analysis.py:438<br>↳ gui/main_window_pyside.py<br>↳ gui/actions_handler.py<br>↳ tests/test_analysis.py |
| `toggle_order_fulfillment()` | **5+ times** | ↳ gui/actions_handler.py<br>↳ tests/test_ui_logic.py<br>↳ tests/test_analysis.py |
| `_generalize_shipping_method()` | **1 time** | ↳ shopify_tool/analysis.py:334 (internal only) |

### shopify_tool/rules.py

| Class/Function | Usage Count | Called From |
|----------------|-------------|-------------|
| `RuleEngine` (class) | **5+ times** | ↳ shopify_tool/core.py:515<br>↳ tests/test_rules.py (multiple) |
| `RuleEngine.apply()` | **5+ times** | ↳ shopify_tool/core.py:516<br>↳ tests/test_rules.py |

### shopify_tool/profile_manager.py

| Class/Function | Usage Count | Called From |
|----------------|-------------|-------------|
| `ProfileManager` (class) | **10+ times** | ↳ gui/main_window_pyside.py:109<br>↳ gui/actions_handler.py:169<br>↳ tests/test_profile_manager.py (multiple) |
| `load_shopify_config()` | **10+ times** | ↳ gui/main_window_pyside.py:143<br>↳ gui/settings_window_pyside.py<br>↳ tests/test_profile_manager.py |
| `save_shopify_config()` | **5+ times** | ↳ gui/settings_window_pyside.py<br>↳ tests/test_profile_manager.py |
| `create_client_profile()` | **3 times** | ↳ gui/profile_manager_dialog.py<br>↳ tests/test_profile_manager.py |

### shopify_tool/session_manager.py

| Class/Function | Usage Count | Called From |
|----------------|-------------|-------------|
| `SessionManager` (class) | **5+ times** | ↳ gui/main_window_pyside.py:110<br>↳ gui/actions_handler.py<br>↳ tests/test_session_manager.py |
| `create_session()` | **5+ times** | ↳ gui/actions_handler.py:68<br>↳ shopify_tool/core.py:312<br>↳ tests/test_session_manager.py |
| `list_client_sessions()` | **3 times** | ↳ gui/session_browser_widget.py<br>↳ tests/test_session_manager.py |

### shopify_tool/utils.py

| Function | Usage Count | Called From |
|----------|-------------|-------------|
| `resource_path()` | **5+ times** | ↳ gui/main_window_pyside.py:16<br>↳ gui/settings_window_pyside.py<br>↳ Multiple GUI widgets |
| `get_persistent_data_path()` | **1 time** | ↳ shopify_tool/core.py:444 (fallback for tests) |

### shopify_tool/csv_utils.py

| Function | Usage Count | Called From |
|----------|-------------|-------------|
| `normalize_sku()` | **15+ times** | ↳ shopify_tool/core.py:462<br>↳ shopify_tool/analysis.py:214, 231<br>↳ Multiple test files |
| `normalize_sku_for_matching()` | **2 times** | ↳ shopify_tool/packing_lists.py:85, 86 |
| `detect_csv_delimiter()` | **3 times** | ↳ gui/file_handler.py<br>↳ tests/test_csv_utils.py |
| `merge_csv_files()` | **2 times** | ↳ gui/file_handler.py<br>↳ tests/test_csv_merge.py |

### shopify_tool/tag_manager.py

| Function | Usage Count | Called From |
|----------|-------------|-------------|
| `add_tag()` | **5+ times** | ↳ shopify_tool/analysis.py:363<br>↳ shopify_tool/rules.py:348<br>↳ gui/tag_delegate.py<br>↳ tests/ |
| `parse_tags()` | **5+ times** | ↳ gui/tag_delegate.py<br>↳ gui/widgets<br>↳ tests/ |

### shopify_tool/set_decoder.py

| Function | Usage Count | Called From |
|----------|-------------|-------------|
| `decode_sets_in_orders()` | **5+ times** | ↳ shopify_tool/analysis.py:242<br>↳ tests/test_set_decoder.py<br>↳ tests/test_sets_integration.py |
| `import_sets_from_csv()` | **2 times** | ↳ gui/settings_window_pyside.py<br>↳ tests/test_set_decoder.py |
| `export_sets_to_csv()` | **2 times** | ↳ gui/settings_window_pyside.py<br>↳ tests/test_set_decoder.py |

### shopify_tool/undo_manager.py

| Class/Function | Usage Count | Called From |
|----------------|-------------|-------------|
| `UndoManager` (class) | **1 time** | ↳ gui/main_window_pyside.py:88 |
| `record_operation()` | **5+ times** | ↳ gui/actions_handler.py (after each data modification) |
| `undo()` | **3+ times** | ↳ gui/main_window_pyside.py (undo button handler) |

### shared/stats_manager.py

| Class/Function | Usage Count | Called From |
|----------------|-------------|-------------|
| `StatsManager` (class) | **2 times** | ↳ gui/actions_handler.py:168<br>↳ tests/test_unified_stats_manager.py |
| `record_analysis()` | **2 times** | ↳ gui/actions_handler.py:186<br>↳ tests/test_unified_stats_manager.py |

---

## 3. CODE COMPLEXITY METRICS

### shopify_tool/

| Module | Lines* | Functions | Avg Length | Longest Function | Complexity** |
|--------|--------|-----------|------------|------------------|--------------|
| **core.py** | 855 | 9 | 95 lines | `run_full_analysis()` - 420 lines ⚠️ | Very High (50+ conditions) |
| **analysis.py** | 596 | 4 | 149 lines | `run_analysis()` - 310 lines ⚠️ | Very High (40+ conditions) |
| **rules.py** | 461 | 13 operators + 1 class | 35 lines | `apply()` - 67 lines | Medium (20+ conditions) |
| **profile_manager.py** | 1003 | ~30 methods | 33 lines | `save_shopify_config()` - 80 lines | Medium-High (25+ conditions) |
| **session_manager.py** | 502 | ~20 methods | 25 lines | `create_session()` - 77 lines | Low-Medium (15 conditions) |
| **utils.py** | 68 | 2 | 34 lines | `get_persistent_data_path()` - 33 lines | Low (5 conditions) |
| **packing_lists.py** | 223 | 1 | 223 lines | `create_packing_list()` - 223 lines ⚠️ | High (30+ conditions) |
| **stock_export.py** | 112 | 1 | 112 lines | `create_stock_export()` - 112 lines ⚠️ | Medium (15 conditions) |
| **csv_utils.py** | 390 | 6 | 65 lines | `merge_csv_files()` - 75 lines | Medium (20 conditions) |
| **tag_manager.py** | 133 | 7 | 19 lines | `parse_tags()` - 24 lines | Low (8 conditions) |
| **set_decoder.py** | 270 | 3 | 90 lines | `decode_sets_in_orders()` - 92 lines | Medium (15 conditions) |
| **undo_manager.py** | 412 | ~15 methods | 27 lines | `undo()` - 45 lines | Medium (18 conditions) |

**\*Lines:** Excluding blank lines and pure comment lines
**\*\*Complexity:** Approximated from if/for/while/except/elif count

### gui/

| Module | Lines* | Functions | Avg Length | Longest Function | Complexity** |
|--------|--------|-----------|------------|------------------|--------------|
| **main_window_pyside.py** | 800+ | ~40 methods | ~20 lines | `__init__()` - 100 lines | Medium-High |
| **actions_handler.py** | 600+ | ~15 methods | ~40 lines | `on_analysis_complete()` - 120 lines ⚠️ | Medium-High |
| **ui_manager.py** | 500+ | ~15 methods | ~33 lines | `create_widgets()` - 150 lines ⚠️ | Medium |
| **file_handler.py** | 300+ | ~8 methods | ~37 lines | `load_orders_file()` - 80 lines | Medium |

### shared/

| Module | Lines* | Functions | Avg Length | Longest Function | Complexity** |
|--------|--------|-----------|------------|------------------|--------------|
| **stats_manager.py** | 633 | ~12 methods | ~52 lines | `_atomic_update()` - 61 lines | Medium-High (20+ conditions) |

---

## 4. DEAD CODE CANDIDATES

### POTENTIALLY UNUSED FUNCTIONS

**None definitively detected** ✓

All major functions appear to be used. Some observations:

- `get_persistent_data_path()` in utils.py - Used as **fallback** in core.py:444 when profile_manager is unavailable
- Internal helper functions (prefixed with `_`) are used within their modules

### TEST-ONLY FUNCTIONS

Some functions are primarily called from tests:

- `validate_csv_headers()` - Main usage in tests, minimal GUI usage
- Various ProfileManager migration methods - Called automatically on config load

### LEGACY CODE MARKERS

No significant legacy code detected. The codebase appears actively maintained with recent v2 migrations.

---

## 5. CODE DUPLICATION

### PATTERN 1: File Locking (3 occurrences)

**Similarity:** ~90%

**Locations:**
1. `shopify_tool/profile_manager.py:_save_with_windows_lock()` (lines 842-878)
2. `shopify_tool/profile_manager.py:_save_with_unix_lock()` (lines 880-916)
3. `shared/stats_manager.py:_lock_file()` (lines 141-193)

**Code Pattern:**
```python
# Platform-specific file locking with retry logic
try:
    if WINDOWS_LOCKING_AVAILABLE:
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
    elif UNIX_LOCKING_AVAILABLE:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    # Write JSON with atomic operations
    json.dump(data, f, indent=2)
    shutil.move(temp_path, file_path)
finally:
    # Unlock
```

**Recommendation:**
Extract to `shared/file_lock_utils.py`:
```python
@contextmanager
def atomic_json_write(file_path: Path, data: Dict, max_retries: int = 5):
    """Atomic JSON write with cross-platform file locking"""
    # ... unified implementation
```

---

### PATTERN 2: DataFrame Column Validation (2 occurrences)

**Similarity:** ~75%

**Locations:**
1. `shopify_tool/core.py:_validate_dataframes()` (lines 130-193)
2. `shopify_tool/analysis.py` (inline validation, lines 220-223)

**Code Pattern:**
```python
missing_cols = [col for col in required if col not in df.columns]
if missing_cols:
    raise ValueError(f"Missing columns: {missing_cols}")
```

**Recommendation:**
Extract to `shopify_tool/csv_utils.py`:
```python
def validate_required_columns(df: pd.DataFrame,
                              required: List[str],
                              context: str = "DataFrame") -> List[str]:
    """Validate DataFrame has required columns"""
    return [col for col in required if col not in df.columns]
```

---

### PATTERN 3: JSON File Load/Save with Error Handling (4 occurrences)

**Similarity:** ~80%

**Locations:**
1. `shopify_tool/profile_manager.py:load_shopify_config()` (lines 593-645)
2. `shopify_tool/session_manager.py:get_session_info()` (lines 242-277)
3. `shopify_tool/undo_manager.py:_load_history()` (lines 379-404)
4. `shopify_tool/undo_manager.py:_save_history()` (lines 356-377)

**Code Pattern:**
```python
try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data
except json.JSONDecodeError:
    logger.warning("Corrupted JSON")
    return default_value
except Exception as e:
    logger.error(f"Failed to load: {e}")
    return default_value
```

**Recommendation:**
Extract to `shared/json_utils.py`:
```python
def load_json_safe(path: Path,
                   default: Any = None,
                   logger: Optional[logging.Logger] = None) -> Any:
    """Load JSON with comprehensive error handling"""
```

---

### PATTERN 4: SKU Normalization Loops (3+ occurrences)

**Similarity:** ~70%

**Locations:**
- `shopify_tool/analysis.py:214` - `orders_clean_df["SKU"] = orders_clean_df["SKU"].apply(normalize_sku)`
- `shopify_tool/analysis.py:231` - `stock_clean_df["SKU"] = stock_clean_df["SKU"].apply(normalize_sku)`
- `shopify_tool/core.py:462` - `history_df["SKU"] = history_df["SKU"].apply(normalize_sku)`

**Code Pattern:**
```python
if "SKU" in df.columns:
    df["SKU"] = df["SKU"].apply(normalize_sku)
```

**Recommendation:**
Already well-abstracted with `normalize_sku()` function. Consider adding:
```python
def normalize_dataframe_skus(df: pd.DataFrame,
                            sku_columns: List[str] = ["SKU"]) -> pd.DataFrame:
    """Normalize all SKU columns in DataFrame"""
```

---

### PATTERN 5: Order Number String Comparison (5+ occurrences)

**Similarity:** ~85%

**Locations:**
- `shopify_tool/analysis.py:535, 542` - Order toggle operations
- `shopify_tool/undo_manager.py:193, 229, 270` - Undo operations
- GUI widgets (filtering by order number)

**Code Pattern:**
```python
order_number_str = str(order_number).strip()
order_numbers_str = df["Order_Number"].astype(str).str.strip()
mask = order_numbers_str == order_number_str
```

**Recommendation:**
Extract to helper function:
```python
def find_order_rows(df: pd.DataFrame, order_number: Any) -> pd.Series:
    """Find rows matching order number (handles type conversion)"""
    order_str = str(order_number).strip()
    return df["Order_Number"].astype(str).str.strip() == order_str
```

---

## SUMMARY & RECOMMENDATIONS

### Architecture Strengths ✓

1. **Clean Layered Architecture** - Clear separation: utilities → core logic → managers → GUI
2. **No Circular Dependencies** - Excellent dependency management
3. **Good Modularity** - Single-responsibility modules (csv_utils, tag_manager, etc.)
4. **Comprehensive Testing** - High test coverage across core functionality
5. **Platform Independence** - Proper handling of Windows/Unix differences

### Areas for Improvement ⚠️

1. **Function Length** - Several functions exceed 100 lines (recommend max 50-80)
   - `run_full_analysis()` - 420 lines ⚠️ **HIGH PRIORITY**
   - `run_analysis()` - 310 lines ⚠️ **HIGH PRIORITY**
   - `create_packing_list()` - 223 lines
   - `on_analysis_complete()` - 120 lines

2. **Code Duplication** - 5 patterns identified for extraction
   - File locking logic (3 locations) - **MEDIUM PRIORITY**
   - JSON load/save patterns (4 locations) - **MEDIUM PRIORITY**
   - Order number comparison (5+ locations) - **LOW PRIORITY**

3. **Complexity Metrics** - Some modules have high cyclomatic complexity
   - Consider breaking down `core.py` and `analysis.py` into smaller modules
   - Extract validation logic to dedicated modules

4. **Documentation** - Add module-level docstrings for architectural overview

### Refactoring Priorities

**HIGH PRIORITY:**
1. Split `run_full_analysis()` into smaller functions:
   - `_setup_session_mode()`
   - `_load_and_validate_data()`
   - `_run_analysis_pipeline()`
   - `_save_reports_and_history()`
   - `_update_session_metadata()`

2. Split `run_analysis()` into smaller functions:
   - `_apply_column_mappings()`
   - `_clean_and_normalize_data()`
   - `_run_fulfillment_simulation()`
   - `_generate_summary_reports()`

**MEDIUM PRIORITY:**
3. Extract file locking to `shared/file_lock_utils.py`
4. Extract JSON utilities to `shared/json_utils.py`
5. Add DataFrame validation utilities to `csv_utils.py`

**LOW PRIORITY:**
6. Extract common order filtering patterns
7. Add architectural documentation
8. Consider splitting `profile_manager.py` (1000+ lines) into smaller modules

---

## Dependencies Summary

**Total Python Files:** 63
**Core Modules (shopify_tool/):** 13
**GUI Modules (gui/):** 16
**Shared Modules:** 1
**Test Files:** 30+
**Scripts:** 3+

**External Dependencies:**
- `pandas` - Data manipulation (used in 80% of modules)
- `PySide6` - GUI framework (gui/ modules only)
- `xlsxwriter`, `xlwt` - Excel export
- Standard library modules - Comprehensive usage

**Internal Coupling:**
- **Low coupling** between shopify_tool modules (good modularity)
- **Medium coupling** in GUI layer (expected for UI code)
- **Zero coupling** to tests from production code (excellent)

---

**End of Report**
