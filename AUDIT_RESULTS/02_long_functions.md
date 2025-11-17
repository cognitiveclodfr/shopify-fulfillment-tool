# Long Functions (>=100 lines)

Found 14 functions/methods with 100+ lines

### shopify_tool/core.py::run_full_analysis
- **Lines:** 422 (lines 238-659)
- **Complexity:** HIGH (cyclomatic: 56)
- **Max Nesting Depth:** 5
- **Parameters:** 10
- **Has Docstring:** Yes
- **Can be split:** YES - Critical refactoring needed
- **Suggestion:** High complexity - consider breaking into smaller functions
- **Suggestion:** Deep nesting detected - consider flattening logic
- **Suggestion:** Too many parameters - consider using a config object

### shopify_tool/analysis.py::run_analysis
- **Lines:** 364 (lines 77-440)
- **Complexity:** HIGH (cyclomatic: 42)
- **Max Nesting Depth:** 3
- **Parameters:** 5
- **Has Docstring:** Yes
- **Can be split:** YES - Critical refactoring needed
- **Suggestion:** High complexity - consider breaking into smaller functions

### gui/settings_window_pyside.py::SettingsWindow.save_settings
- **Lines:** 242 (lines 1334-1575)
- **Complexity:** HIGH (cyclomatic: 30)
- **Max Nesting Depth:** 5
- **Parameters:** 1
- **Has Docstring:** Yes
- **Can be split:** YES - Critical refactoring needed
- **Suggestion:** High complexity - consider breaking into smaller functions
- **Suggestion:** Deep nesting detected - consider flattening logic

### shopify_tool/packing_lists.py::create_packing_list
- **Lines:** 213 (lines 10-222)
- **Complexity:** HIGH (cyclomatic: 26)
- **Max Nesting Depth:** 6
- **Parameters:** 5
- **Has Docstring:** Yes
- **Can be split:** YES - Critical refactoring needed
- **Suggestion:** High complexity - consider breaking into smaller functions
- **Suggestion:** Deep nesting detected - consider flattening logic

### gui/actions_handler.py::ActionsHandler._generate_single_report
- **Lines:** 187 (lines 489-675)
- **Complexity:** HIGH (cyclomatic: 28)
- **Max Nesting Depth:** 5
- **Parameters:** 4
- **Has Docstring:** Yes
- **Can be split:** RECOMMENDED - Should be refactored
- **Suggestion:** High complexity - consider breaking into smaller functions
- **Suggestion:** Deep nesting detected - consider flattening logic

### gui/main_window_pyside.py::MainWindow.show_context_menu
- **Lines:** 123 (lines 866-988)
- **Complexity:** LOW (cyclomatic: 7)
- **Max Nesting Depth:** 3
- **Parameters:** 2
- **Has Docstring:** Yes
- **Can be split:** RECOMMENDED - Should be refactored

### shopify_tool/set_decoder.py::decode_sets_in_orders
- **Lines:** 118 (lines 17-134)
- **Complexity:** MEDIUM (cyclomatic: 11)
- **Max Nesting Depth:** 4
- **Parameters:** 2
- **Has Docstring:** Yes
- **Can be split:** RECOMMENDED - Should be refactored

### shopify_tool/csv_utils.py::merge_csv_files
- **Lines:** 117 (lines 273-389)
- **Complexity:** MEDIUM (cyclomatic: 17)
- **Max Nesting Depth:** 4
- **Parameters:** 7
- **Has Docstring:** Yes
- **Can be split:** RECOMMENDED - Should be refactored
- **Suggestion:** Too many parameters - consider using a config object

### gui/file_handler.py::FileHandler.select_orders_folder
- **Lines:** 115 (lines 321-435)
- **Complexity:** MEDIUM (cyclomatic: 10)
- **Max Nesting Depth:** 2
- **Parameters:** 1
- **Has Docstring:** Yes
- **Can be split:** RECOMMENDED - Should be refactored

### gui/file_handler.py::FileHandler.select_stock_folder
- **Lines:** 108 (lines 437-544)
- **Complexity:** MEDIUM (cyclomatic: 10)
- **Max Nesting Depth:** 2
- **Parameters:** 1
- **Has Docstring:** Yes
- **Can be split:** RECOMMENDED - Should be refactored

### shopify_tool/stock_export.py::create_stock_export
- **Lines:** 105 (lines 7-111)
- **Complexity:** MEDIUM (cyclomatic: 14)
- **Max Nesting Depth:** 5
- **Parameters:** 4
- **Has Docstring:** Yes
- **Can be split:** RECOMMENDED - Should be refactored
- **Suggestion:** Deep nesting detected - consider flattening logic

### gui/settings_window_pyside.py::SettingsWindow.create_mappings_tab
- **Lines:** 105 (lines 901-1005)
- **Complexity:** LOW (cyclomatic: 5)
- **Max Nesting Depth:** 3
- **Parameters:** 1
- **Has Docstring:** Yes
- **Can be split:** RECOMMENDED - Should be refactored

### gui/main_window_pyside.py::MainWindow._load_session_analysis
- **Lines:** 102 (lines 545-646)
- **Complexity:** MEDIUM (cyclomatic: 13)
- **Max Nesting Depth:** 5
- **Parameters:** 2
- **Has Docstring:** Yes
- **Can be split:** RECOMMENDED - Should be refactored
- **Suggestion:** Deep nesting detected - consider flattening logic

### gui/actions_handler.py::ActionsHandler.show_add_product_dialog
- **Lines:** 102 (lines 849-950)
- **Complexity:** HIGH (cyclomatic: 24)
- **Max Nesting Depth:** 4
- **Parameters:** 1
- **Has Docstring:** Yes
- **Can be split:** RECOMMENDED - Should be refactored
- **Suggestion:** High complexity - consider breaking into smaller functions


================================================================================

# Code Quality Metrics

Total functions analyzed: 692
Functions with docstrings: 678 (97%)
Average function length: 27 lines
Functions with high complexity (>15): 16
Functions with deep nesting (>4): 21
Functions with many parameters (>5): 6

