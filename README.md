# Shopify Fulfillment Tool

## What is this project?

The Shopify Fulfillment Tool is a desktop application designed to streamline the order fulfillment process for Shopify stores. It helps warehouse managers and logistics personnel to efficiently analyze orders, check stock availability, and generate necessary reports like packing lists and stock exports for various couriers.

The tool provides a clear, color-coded user interface to quickly identify which orders are fulfillable, which are not, and which require special attention (e.g., repeat orders).

## How It Works

The application follows a straightforward workflow:
1.  **Start a Session**: The user creates a new session, which generates a unique, dated folder to store all output reports for the current work cycle.
2.  **Load Data**: The user loads a Shopify orders export CSV and a current inventory/stock CSV file.
3.  **Run Analysis**: The core analysis engine processes the data. It simulates the fulfillment process by prioritizing multi-item orders, checks for previously fulfilled orders, and calculates final stock levels.
4.  **Apply Rules**: A powerful, configurable rule engine automatically tags orders, sets priorities, or changes statuses based on user-defined conditions (e.g., tag all orders going to a specific country).
5.  **Review and Edit**: The results are displayed in an interactive table where the user can manually change an order's fulfillment status, add notes, or remove items.
6.  **Generate Reports**: Once the analysis is finalized, the user can generate various reports, such as filtered packing lists for different couriers or stock export files based on custom templates.

## Main Features

-   **Session-Based Workflow**: All generated reports for a work session are saved in a unique, dated folder.
-   **Order & Stock Analysis**: Load Shopify order exports and current stock files to run a fulfillment simulation.
-   **Interactive Data Table**: View all order lines with fulfillment status, stock levels, and other key details.
    -   **Color-Coded Status**: Green for 'Fulfillable', Red for 'Not Fulfillable', Yellow for 'Repeat Order'.
    -   **Context Menu**: Quickly change an order's status or copy key information like Order Number or SKU.
    -   **Filtering and Sorting**: The main data table can be sorted by any column and filtered by text across all columns or a specific column.
-   **Configurable Rule Engine**: Automate your workflow by creating custom rules in the settings. For example, automatically tag all orders from a specific country or set a high priority for orders over a certain value.
-   **Flexible Report Generation**:
    -   **Packing Lists**: Create multiple, filtered packing lists for different couriers or packing stations.
    -   **Stock Exports**: Generate stock export files (e.g., for couriers) by populating data into pre-defined `.xls` templates.
    -   **Custom Reports**: Build your own one-off reports with a simple report builder UI.
-   **Session Persistence**: Close the app and restore your previous session's data on the next launch.

## Codebase Overview

The project is organized into two main packages: `shopify_tool` (backend) and `gui` (frontend).

### `shopify_tool` (Backend)

This package contains all the core data processing and business logic, designed to be independent of the user interface.

-   **`core.py`**: The main orchestrator of the backend. It acts as the primary API for the GUI, coordinating the analysis and report generation processes.
-   **`analysis.py`**: Contains the core fulfillment simulation logic. It takes cleaned DataFrames and determines order statuses, calculates final stock, and generates summary statistics.
-   **`rules.py`**: Implements the configurable rule engine. It applies user-defined rules from the config to tag or modify orders.
-   **`packing_lists.py`**: Handles the creation of formatted packing list reports in Excel, including advanced filtering and sorting.
-   **`stock_export.py`**: Manages the generation of stock export files, often used for courier systems.
-   **`utils.py`**: A collection of helper functions, primarily for handling file paths in a cross-platform and bundled-application context.
-   **`logger_config.py`**: Sets up the application-wide logger.

### `gui` (Frontend)

This package contains all the PySide6 UI code and related helper classes.

-   **`main_window_pyside.py`**: The main application window. It orchestrates the UI and connects user actions to the backend handlers.
-   **`ui_manager.py`**: Responsible for creating, laying out, and managing the state of all widgets in the main window.
-   **`actions_handler.py`**: Connects UI events (like button clicks) to the corresponding backend logic, often by running tasks in a background thread.
-   **`file_handler.py`**: Manages file dialogs, loading, and validation of input CSV files.
-   **`pandas_model.py`**: A custom `QAbstractTableModel` that serves as an interface between pandas DataFrames and `QTableView` widgets, enabling the display of tabular data.
-   **Dialogs (`settings_window_pyside.py`, `profile_manager_dialog.py`, etc.)**: Each dialog is implemented in its own module, handling specific user interactions like editing settings or managing profiles.
-   **`worker.py`**: A generic, reusable `QRunnable` worker for executing any function in a background thread to keep the UI responsive.

## Configuration

The application's behavior is controlled by a `config.json` file.
-   **Location**: On first launch, a default `config.json` is copied from the project resources to a persistent user data directory (e.g., `%APPDATA%/ShopifyFulfillmentTool` on Windows, `~/.local/share/ShopifyFulfillmentTool` on Linux).
-   **Editing**: You can edit this file directly or through the **Settings** window (⚙️) in the application.
-   **Contents**: The configuration allows you to define:
    -   Required columns for your input files.
    -   Paths for templates and output directories.
    -   The automation rules for the rule engine.
    -   The structure and filters for your standard packing lists and stock exports.

## Installation and Setup (for Developers)

To set up the development environment, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd shopify-fulfillment-tool
    ```

2.  **Create a virtual environment (recommended):**
    This project is tested with Python 3.9+.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    The project uses two requirements files:
    -   `requirements.txt`: For core application dependencies.
    -   `requirements-dev.txt`: For development tools (like pytest and ruff).

    Install both using pip:
    ```bash
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    ```

4.  **Run the application:**
    ```bash
    python gui_main.py
    ```

## Code Style and Linting

This project uses `ruff` for code formatting and linting. The rules are defined in `pyproject.toml`.

-   **To format the code:**
    ```bash
    ruff format .
    ```
-   **To check for linting errors:**
    ```bash
    ruff check .
    ```

## Contributing

Contributions are welcome! If you would like to contribute to the development of this tool, please follow these steps:

1.  **Fork the repository** on GitHub.
2.  **Create a new branch** for your feature or bug fix:
    ```bash
    git checkout -b feature/your-feature-name
    ```
3.  **Make your changes** and ensure the code adheres to the existing style.
4.  **Run the tests** to make sure you haven't introduced any regressions:
    ```bash
    pytest
    ```
5.  **Commit your changes** with a clear and descriptive commit message.
6.  **Push your branch** to your fork:
    ```bash
    git push origin feature/your-feature-name
    ```
7.  **Open a pull request** from your fork to the main repository.
