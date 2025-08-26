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

- **`core.py`**: The central orchestrator of the backend. It acts as the primary API for the GUI.
  - `run_full_analysis()`: The main workflow function. It loads data from CSVs, calls `analysis.run_analysis()` to perform the simulation, applies business rules via `rules.RuleEngine`, and saves the main analysis report.
  - `create_packing_list_report()`: A wrapper that calls `packing_lists.create_packing_list()` to generate a specific packing list report based on a configuration from `config.json`.
  - `create_stock_export_report()`: A wrapper that calls `stock_export.create_stock_export()` to generate a stock export file.

- **`analysis.py`**: Contains the core business logic for the fulfillment simulation.
  - `run_analysis()`: This is a pure computation function. It takes pandas DataFrames for stock, orders, and history as input. It cleans the data, prioritizes multi-item orders, simulates fulfillment by decrementing a dictionary representing live stock, and calculates the final stock levels. It returns the final detailed DataFrame and a dictionary of statistics.
  - `recalculate_statistics()`: Calculates summary stats from a DataFrame.
  - `toggle_order_fulfillment()`: Contains the logic to manually mark an order as "Fulfillable" or "Not Fulfillable" and recalculates the stock accordingly.

- **`rules.py`**: Implements a flexible rule engine.
  - `RuleEngine`: A class that takes a list of rule configurations. Its `apply()` method iterates through the rules, evaluates the conditions against the main DataFrame, and applies the specified actions (e.g., adding a tag, setting a status).

- **`packing_lists.py`**:
  - `create_packing_list()`: Takes a DataFrame and a filter configuration. It uses `pandas.DataFrame.query()` to filter the data and then uses `xlsxwriter` to create a formatted Excel packing list.

- **`stock_export.py`**:
  - `create_stock_export()`: Similar to `packing_lists.py`, but it generates a different format. It filters the data, summarizes it by SKU, and writes the results into a pre-existing `.xls` template file using `xlrd` and `xlutils`.

- **`logger_config.py`**: Sets up a `RotatingFileHandler` for logging application events to `logs/app_history.log`.

## 3. Graphical User Interface (GUI)

The GUI is built using `customtkinter` and is managed primarily by `gui_main.py`.

### Key Components:

- **`gui_main.py` - `App` class**: This is the main application class that inherits from `ctk.CTk`.
  - **Initialization (`__init__`)**: Sets up the main window, loads the configuration from `config.json`, and creates all the main widgets (buttons, tabs, data tables). It handles the logic for persistent configuration, copying a default `config.json` to a user's app data directory if one doesn't exist.
  - **Event Handling**: Contains methods that are bound to button clicks (e.g., `select_orders_file`, `start_analysis_thread`).
  - **Threading**: Long-running tasks like analysis and report generation are correctly offloaded to separate threads (`threading.Thread`) to prevent the GUI from freezing. Results from the thread are passed back to the main GUI thread using `self.after()`.
  - **State Management**: The `App` class holds the main application state, including the loaded `analysis_results_df`, the `config` dictionary, and paths to files.

- **`gui/settings_window.py` - `SettingsWindow` class**:
  - This class creates the modal "Settings" window.
  - It reads the `config` object from the main `App` instance to populate the UI with the current settings for paths, rules, packing lists, and stock exports.
  - The `save_settings()` method is crucial: it collects all the data from the UI widgets, constructs a new `config` dictionary, updates the parent's (`App`) config object in memory, and then overwrites the `config.json` file on disk with the new settings.

- **Other GUI Windows**:
  - `report_builder_window.py`: A UI for building one-off custom reports.
  - `column_manager_window.py`: A UI for showing/hiding columns in the main data table.
  - `log_viewer.py`: A custom widget for displaying color-coded logs.

## 4. Configuration and Data

- **`config.json`**: The central file for configuring the application's behavior without changing the code.
  - `paths`: Defines default file paths. The `output_dir_stock` is used to create dated session folders.
  - `settings`: General parameters like `low_stock_threshold`.
  - `column_mappings`: Defines the required columns for input CSV files, allowing the app to validate files before processing.
  - `rules`, `packing_lists`, `stock_exports`: Lists of predefined objects that control the automation and report generation features. The UI in `SettingsWindow` is responsible for editing these sections.

- **`data/` directory**:
  - `input/`: Placeholder for user's input CSV files.
  - `output/`: Default directory where session folders are created.
  - `templates/`: Contains `.xls` templates that `stock_export.py` uses as a base to write data into.

## 5. Data Flow (Example: Generating a Packing List)

1.  **User Action**: The user clicks the "Create Packing List" button in the main window (`gui_main.py`).
2.  **Window Creation**: `open_packing_list_window()` is called. It creates a new `CTkToplevel` window and populates it with buttons, one for each report defined in the `packing_lists` section of `self.config`.
3.  **User Selection**: The user clicks a button for a specific packing list (e.g., "Multi-Item Orders (DHL)").
4.  **Background Thread**: The button's command calls `start_report_thread()`, which starts a new thread running `run_report_logic()`. This prevents the GUI from freezing. The `report_config` dictionary for the selected report is passed to the thread.
5.  **Orchestration (`gui_main.py`)**: `run_report_logic()` gets the `analysis_results_df` from the main app state and calls the backend API: `core.create_packing_list_report()`, passing the DataFrame and the specific `report_config`.
6.  **Core Logic (`core.py`)**: `create_packing_list_report()` receives the data. It prepares the output path and then calls the low-level function `packing_lists.create_packing_list()`, passing the DataFrame and the filters from the `report_config`.
7.  **Filtering and Generation (`packing_lists.py`)**: `create_packing_list()` uses the `filters` dictionary to build a pandas query string. It filters the DataFrame, formats the result, and writes the final data to an Excel file using `xlsxwriter`.
8.  **Feedback**: The success/failure result is passed all the way back to `run_report_logic()` in `gui_main.py`, which then uses `self.after()` to schedule a UI update on the main thread (either showing an error message or logging the success).
