# Code Quality Analysis

## Overall Statistics

- **Total Files Analyzed:** 30
- **Total Lines:** 13,692
- **Code Lines:** 10,029 (73%)
- **Comment Lines:** 1,127 (8%)
- **Total Functions:** 328
- **Total Classes:** 32

## 1. Type Hints Coverage

**Functions with type hints:** 117/328 (35%)

**Status:** 🟡 MEDIUM - Moderate type hint coverage
**Recommendation:** Continue adding type hints to new and modified functions
**Priority:** MEDIUM

### Files with No/Low Type Hints

- `gui/ui_manager.py`: 0/35 functions (0%)
- `gui/settings_window_pyside.py`: 0/32 functions (0%)
- `shopify_tool/rules.py`: 0/23 functions (0%)
- `gui/actions_handler.py`: 0/19 functions (0%)
- `gui/add_product_dialog.py`: 0/14 functions (0%)
- `gui/log_viewer.py`: 0/7 functions (0%)
- `gui/column_mapping_widget.py`: 0/6 functions (0%)
- `gui/profile_manager_dialog.py`: 0/5 functions (0%)
- `gui/report_selection_dialog.py`: 0/5 functions (0%)
- `shopify_tool/analysis.py`: 0/4 functions (0%)

## 2. Docstrings Coverage

**Functions with docstrings:** 317/328 (96%)

**Status:** ✅ GOOD - Well documented code
**Priority:** LOW

## 3. Long Lines (>120 characters)

**Total long lines:** 7

### Files with Most Long Lines

- `shopify_tool/analysis.py`: 2 long lines
- `shopify_tool/core.py`: 2 long lines
- `shopify_tool/logger_config.py`: 1 long lines
- `shopify_tool/packing_lists.py`: 1 long lines
- `gui/actions_handler.py`: 1 long lines

## 4. Deep Nesting (>4 levels)

**Total deep nesting occurrences:** 24

### Files with Deep Nesting

- `shopify_tool/rules.py`: 18 occurrences
- `gui/actions_handler.py`: 2 occurrences
- `shopify_tool/analysis.py`: 1 occurrences
- `shopify_tool/undo_manager.py`: 1 occurrences
- `gui/session_browser_widget.py`: 1 occurrences
- `gui/report_selection_dialog.py`: 1 occurrences

**Status:** 🔴 HIGH - Excessive deep nesting
**Recommendation:** Refactor deeply nested code to reduce complexity
**Priority:** HIGH

## 5. Magic Numbers

**Total magic numbers:** 207

### Files with Most Magic Numbers

- `gui/ui_manager.py`: 47 magic numbers
- `gui/settings_window_pyside.py`: 38 magic numbers
- `gui/session_browser_widget.py`: 19 magic numbers
- `shared/stats_manager.py`: 17 magic numbers
- `gui/log_viewer.py`: 14 magic numbers
- `gui/column_mapping_widget.py`: 10 magic numbers
- `gui/tag_delegate.py`: 10 magic numbers
- `shopify_tool/packing_lists.py`: 8 magic numbers
- `gui/file_handler.py`: 8 magic numbers
- `gui/main_window_pyside.py`: 8 magic numbers

**Status:** 🟡 MEDIUM - Many hardcoded numbers
**Recommendation:** Extract magic numbers to named constants
**Priority:** MEDIUM

## 6. Global Variables

**Total global variables:** 30

### Global Variables Found

- `gui/actions_handler.py:39` - `data_changed`
- `gui/add_product_dialog.py:21` - `logger`
- `gui/client_selector_widget.py:132` - `client_changed`
- `gui/client_selector_widget.py:17` - `logger`
- `gui/column_mapping_widget.py:14` - `logger`
- `gui/column_mapping_widget.py:32` - `mappings_changed`
- `gui/log_handler.py:21` - `log_message_received`
- `gui/main_window_pyside.py:1007` - `app`
- `gui/main_window_pyside.py:1008` - `window`
- `gui/report_selection_dialog.py:21` - `reportSelected`
- `gui/session_browser_widget.py:18` - `logger`
- `gui/session_browser_widget.py:34` - `session_selected`
- `gui/settings_window_pyside.py:1760` - `app`
- `gui/settings_window_pyside.py:1788` - `dialog`
- `gui/settings_window_pyside.py:1761` - `dummy_config`
- `gui/worker.py:17` - `error`
- `gui/worker.py:16` - `finished`
- `gui/worker.py:18` - `result`
- `shared/stats_manager.py:599` - `base_path`
- `shared/stats_manager.py:631` - `client_stats`
- ... and 10 more

**Status:** 🟡 MEDIUM - Multiple global variables found
**Recommendation:** Consider using classes or module-level configuration
**Priority:** MEDIUM


## Summary

| Metric | Value | Status | Priority |
|--------|-------|--------|----------|
| Type Hints Coverage | 117/328 (35%) | 🟡 | MEDIUM |
| Docstrings Coverage | 317/328 (96%) | ✅ | LOW |
| Long Lines (>120) | 7 | 🟢 | LOW |
| Deep Nesting (>4) | 24 | 🔴 | HIGH |
| Magic Numbers | 207 | 🟡 | MEDIUM |
| Global Variables | 30 | 🟡 | MEDIUM |
