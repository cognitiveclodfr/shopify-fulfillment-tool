# Code Duplication Analysis

## 1. File Locking Patterns

No file locking patterns found.

## 2. JSON Operations

**Total JSON operations:** 32

### `json.load()` - 8 occurrences
- shopify_tool/session_manager.py: 2 times
- shopify_tool/profile_manager.py: 2 times
- gui/main_window_pyside.py: 2 times
- shopify_tool/undo_manager.py: 1 times
- gui/actions_handler.py: 1 times
### `json.dump()` - 16 occurrences
- shopify_tool/profile_manager.py: 4 times
- shopify_tool/session_manager.py: 3 times
- shared/stats_manager.py: 3 times
- shopify_tool/core.py: 2 times
- gui/actions_handler.py: 2 times
### `json.loads()` - 4 occurrences
- shared/stats_manager.py: 2 times
- shopify_tool/tag_manager.py: 1 times
- gui/settings_window_pyside.py: 1 times
### `json.dumps()` - 4 occurrences
- gui/settings_window_pyside.py: 2 times
- shopify_tool/logger_config.py: 1 times
- shopify_tool/tag_manager.py: 1 times

**Recommendation:** 🟢 JSON operations are varied, but consider utility functions for common patterns
**Priority:** LOW

## 3. DataFrame Column Validation Patterns

**Total validation patterns:** 22

### required_columns - 1 occurrences
- shopify_tool/set_decoder.py: 1 times

### missing_cols - 2 occurrences
- gui/file_handler.py: 2 times

### column_check - 19 occurrences
- gui/actions_handler.py: 2 times
- gui/main_window_pyside.py: 1 times
- gui/pandas_model.py: 1 times
- shopify_tool/analysis.py: 3 times
- shopify_tool/core.py: 3 times

**Recommendation:** 🟡 Create `shopify_tool/dataframe_validators.py` with common validation patterns
**Priority:** MEDIUM

## 4. Error Handling Patterns

### broad_except - 6 occurrences
- gui/settings_window_pyside.py: lines 826
- gui/worker.py: lines 65
- shared/stats_manager.py: lines 192
- shopify_tool/core.py: lines 770
- shopify_tool/csv_utils.py: lines 126
- shopify_tool/utils.py: lines 65

### bare_except - 1 occurrences
- gui/session_browser_widget.py: lines 187

### specific_except - 13 occurrences
- gui/pandas_model.py: lines 77, 132
- shared/stats_manager.py: lines 49, 55, 164, 177
- shopify_tool/core.py: lines 228, 464, 741, 847
- shopify_tool/profile_manager.py: lines 862, 900
- shopify_tool/set_decoder.py: lines 166

**⚠️ Warning:** Found broad `except Exception:` blocks
**Recommendation:** 🔴 Replace with specific exception types where possible
**Priority:** HIGH

**⚠️ Warning:** Found bare `except:` blocks (catches everything including KeyboardInterrupt)
**Recommendation:** 🔴 Replace with specific exception types
**Priority:** CRITICAL

## 5. Logger Initialization Patterns

**Found:** 16 logger initializations

**Files with loggers:** 15

**Logger usage breakdown:**
- logger.debug(): 17 calls
- logger.info(): 107 calls
- logger.warning(): 37 calls
- logger.error(): 48 calls

**Recommendation:** ✅ Consistent logger usage detected
**Priority:** LOW - No action needed

## 6. Functions with Same Names (Potential Duplicates)

**Found:** 4 function names appearing in multiple files


**Recommendation:** 🟡 Review these functions - some may be legitimate, others may benefit from consolidation
**Priority:** MEDIUM


## Summary of Duplication Issues

| Pattern Type | Occurrences | Priority | Action Needed |
|--------------|-------------|----------|---------------|
| File Locking | 0 | 🟡 MEDIUM | Create utility module |
| JSON Operations | 32 | 🟢 LOW | Consider utility functions |
| DataFrame Validations | 22 | 🟡 MEDIUM | Create validator module |
| Broad Exception Catching | 6 | 🔴 HIGH | Use specific exceptions |
| Bare Exception Catching | 1 | 🔴 CRITICAL | Use specific exceptions |
| Duplicate Function Names | 4 | 🟡 MEDIUM | Review and consolidate |
