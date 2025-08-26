# Technical Documentation: Shopify Fulfillment Tool

This document provides a technical overview of the Shopify Fulfillment Tool, intended for developers and maintainers. It covers the application's architecture, core logic, GUI structure, and data flow.

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
