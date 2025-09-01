# Technical Documentation: Shopify Fulfillment Tool v8.1.8

This document provides a technical overview of the Shopify Fulfillment Tool, intended for developers and maintainers. It covers the application's architecture, core logic, GUI structure, and data flow.

## Version 8.1.8 Changes

This release introduces several new features focused on providing more detailed feedback to the user, enhancing report customization, and improving the robustness of the core logic. A major focus was also placed on increasing the quality and coverage of the unit test suite.

-   **Low Stock Alerts (`core.py`):**
    -   The `run_full_analysis` function can now apply a low stock warning. After the main analysis, it checks if a `low_stock_threshold` is defined in the config.
    -   If it is, it uses a `np.where` clause to create a new `Stock_Alert` column, marking any item where `Final_Stock` < `threshold`.

-   **Exclude SKUs from Packing Lists (`core.py`, `packing_lists.py`):**
    -   The `create_packing_list_report` function in `core.py` now accepts an `exclude_skus` parameter from the report's configuration.
    -   This list of SKUs to exclude is passed down to `packing_lists.create_packing_list`, where the main DataFrame is filtered to remove these SKUs before the report is generated.

-   **Core Analysis Logic (`analysis.py`):**
    -   **`toggle_order_fulfillment`:** This function has been heavily refactored for robustness. It now includes a pre-flight check to see if a "force-fulfill" is possible by checking available stock. It can also handle orders containing unlisted SKUs (items not in the stock file) by dynamically adding them to the DataFrame to track their negative stock.
    -   **`recalculate_statistics`:** A new standalone function that computes a rich dictionary of statistics from the main analysis frame. This separates the calculation from the main analysis loop and produces a structured `couriers_stats` list. If no stats are available, it returns `None` as per the spec for the GUI.
    -   **Improved Summary_Missing:** The logic for generating the `summary_missing_df` has been corrected to only include items that are truly out of stock (`Quantity` > `Stock`), making the report more accurate.

-   **Data Validation and Export (`core.py`):**
    -   **`validate_csv_headers`:** A new utility function has been added to `core.py` to quickly validate the headers of input CSVs against a list of required columns before loading the full file. This provides faster and clearer error feedback to the user.
    -   **Report Info Sheet:** The `run_full_analysis` function now adds a `Report Info` worksheet to the `fulfillment_analysis.xlsx` export, containing a timestamp of when the report was generated.

## Version 8.1.0 Changes

This release focuses on improving the data model, enhancing the user interface, and expanding configuration options.

-   **Data Model Changes (`analysis.py`):**
    -   A new `System_note` column has been added to the main analysis DataFrame. It replaces the previous use of the `Status_Note` column for housing system-generated tags (e.g., `Repeat`). This change helps to separate machine-generated data from user notes.
    -   A new `Total Price` column has been added, sourced from the `Total` field in the Shopify order export. This is handled during the initial data cleaning phase.

-   **GUI Enhancements (`gui_main.py`):**
    -   The main analysis table (`ttk.Treeview`) has been restyled for a more modern look, using the central `STYLE` dictionary for all fonts and colors, and an increased row height for better readability.
    -   A new tag, `SystemNoteHighlight`, has been added to apply a yellow background to any row containing data in the `System_note` column.
    -   The right-click context menu (`_show_context_menu`) now includes a "Copy SKU" command, which copies the SKU of the selected line item to the clipboard.

-   **Configuration Enhancements (`gui/settings_window.py`):**
    -   The `CONDITION_FIELDS` (for Rules) and `FILTERABLE_COLUMNS` (for Packing Lists and Stock Exports) constants have been updated and synchronized.
    -   They now include `Order_Number`, `Total Price`, and `System_note`, making these fields available for creating automation rules and report filters.

---

## 1. Architecture Overview

The application is a desktop program built with Python, using `customtkinter` for the user interface and `pandas` for data manipulation. It is designed to be packaged into a single executable using PyInstaller.

The architecture is divided into two main components:
- **Backend Logic (`shopify_tool/`)**: A package containing all the core data processing, analysis, and report generation logic. It is designed to be independent of the user interface.
- **Frontend GUI (`gui/` and `gui_main.py`)**: The user-facing part of the application that provides controls for loading data, running analysis, and viewing results. It acts as a client to the `shopify_tool` backend.

The application's lifecycle and user-specific data are managed by `gui_main.py`, which is the main entry point.

## 2. Backend Logic (`shopify_tool` package)

The `shopify_tool` package is the engine of the application.

### Key Modules:

- **`utils.py`**: A new module containing shared helper functions, such as `get_persistent_data_path` for accessing the user's application data directory and `resource_path` for accessing bundled application files.

- **`core.py`**: The central orchestrator of the backend. It acts as the primary API for the GUI.
  - `run_full_analysis()`: The main workflow function. It now uses `get_persistent_data_path` to read and write the `fulfillment_history.csv` file, ensuring it works correctly from any location (including network shares). It also normalizes file paths to handle UNC paths robustly.
  - `create_packing_list_report()`: A wrapper that calls `packing_lists.create_packing_list()` to generate a specific packing list report.
  - `create_stock_export_report()`: A wrapper that calls `stock_export.create_stock_export()` to generate a stock export file.

- **`analysis.py`**: Contains the core business logic for the fulfillment simulation.
  - `run_analysis()`: A pure computation function that takes pandas DataFrames, simulates fulfillment based on a multi-item > single-item priority, and returns the results.
  - `toggle_order_fulfillment()`: Contains the complex logic to manually mark an order as "Fulfillable" or "Not Fulfillable" and recalculates the stock accordingly.

- **`rules.py`**: Implements a flexible rule engine. Its `apply()` method iterates through the rules defined in `config.json` and applies them to the dataset.

- **`packing_lists.py` & `stock_export.py`**: These modules contain the logic for generating the final report files. They now parse a robust list-of-objects filter format from `config.json`.

## 3. Graphical User Interface (GUI)

The GUI is built using `customtkinter` and is managed primarily by `gui_main.py`.

### Key Components:

- **`gui_main.py` - `App` class**:
  - **Initialization (`__init__`)**: Now handles the robust initialization of the user configuration. On first launch, it copies a default `config.json` from the application's resources to a persistent user-specific directory (e.g., `AppData`). All subsequent sessions read from and write to this user-specific config file.
  - **UI Layout:** The `create_widgets` method has been refactored to create a more organized action panel, with report buttons grouped separately from the main "Run Analysis" button.
  - **Theming:** A centralized `STYLE` dictionary defines the application's color palette, fonts, and corner radius for a consistent look and feel.

- **`gui/settings_window.py` - `SettingsWindow` class**:
  - This class creates the modal "Settings" window.
  - The `save_settings()` method now saves configurations for rules, packing lists, and stock exports using a flexible list-of-objects format, which allows for more complex filtering logic (e.g., multiple conditions on the same field).
  - The layout has been improved to ensure content areas expand to fill the window, preventing large empty spaces.

## 4. Configuration and Data

- **Persistent User Data:** Critical user-specific files are now stored in a persistent application data folder (e.g., `C:\Users\YourUser\AppData\Roaming\ShopifyFulfillmentTool`). This includes:
    - `config.json`: Stores all user configurations for rules, reports, and paths.
    - `fulfillment_history.csv`: Tracks previously fulfilled orders to identify repeats.
    - `session_data.pkl`: Stores the state of the last session for potential restoration.
- **`config.json` Filter Format:** The format for filters in `packing_lists` and `stock_exports` has been updated to a list of objects for clarity and power.
    - **Old format:** `"filters": {"Order_Type": "Multi"}`
    - **New format:** `"filters": [{"field": "Order_Type", "operator": "==", "value": "Multi"}]`
- **`data/` directory**: This directory in the application bundle now only holds default templates. User-generated output is saved to session-specific folders.

## 5. Data Flow (Example: Generating a Packing List)

The data flow remains largely the same, but the underlying configuration and file paths are now more robust.

1.  **User Action**: The user clicks a button for a specific packing list.
2.  **Orchestration (`gui_main.py`)**: The `report_config` for the selected report is retrieved from `self.config` (loaded from the persistent `config.json`).
3.  **Core Logic (`core.py`)**: The `create_packing_list_report` function is called.
4.  **Filtering and Generation (`packing_lists.py`)**: `create_packing_list()` now receives the new filter format. It loops through the list of filter objects, dynamically building a pandas query string (e.g., `\`Order_Type\` == 'Multi' & \`Shipping_Provider\` != 'DHL'`). It then filters the DataFrame and generates the report.

## 6. Test Coverage Review (v8.1.8)

A comprehensive effort was undertaken to improve the quality and coverage of the unit test suite. All tests pass, and the final coverage results are as follows:

**Overall Coverage: 96%**

| Module File                 | Coverage | Notes                                                                   |
| --------------------------- | :------: | ----------------------------------------------------------------------- |
| `shopify_tool/analysis.py`      |   95%    | Coverage maintained.                                                    |
| `shopify_tool/logger_config.py` |   96%    | Coverage maintained.                                                    |
| `shopify_tool/packing_lists.py` |   94%    | **Improved.** Added tests for edge cases.                               |
| `shopify_tool/rules.py`         |   99%    | **Improved.** Added comprehensive tests for all operators & edge cases. |
| `shopify_tool/core.py`          |   97%    | **Improved.** Added tests for error handling and all major code paths.  |
| `shopify_tool/stock_export.py`  |   94%    | **Improved.** Added tests for filtering logic and error handling.       |
| `shopify_tool/utils.py`         |  100%    | **Improved.** Full coverage achieved.                                   |

**Summary of Improvements:**
-   Unit test coverage was increased from 85% to 96%.
-   Added new test files and numerous new tests to cover error handling, edge cases, and all logical operators in the rule engine.
-   All modules identified as needing improvement now have coverage of 94% or higher.
