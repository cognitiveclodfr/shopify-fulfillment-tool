# Shopify Fulfillment Tool

## What is this project?

The Shopify Fulfillment Tool is a desktop application designed to streamline the order fulfillment process for Shopify stores. It helps warehouse managers and logistics personnel to efficiently analyze orders, check stock availability, and generate necessary reports like packing lists and stock exports for various couriers.

The tool provides a clear, color-coded user interface to quickly identify which orders are fulfillable, which are not, and which require special attention (e.g., repeat orders). It is built with Python and uses the PySide6 (Qt) framework for its graphical user interface, with pandas for data manipulation.

## Main Features

-   **Session-Based Workflow**: All generated reports for a work session are saved in a unique, dated folder, preventing accidental overwrites.
-   **Order & Stock Analysis**: Load Shopify order exports and current stock files to run a fulfillment simulation. The tool intelligently prioritizes orders with multiple items to maximize the number of completed shipments.
-   **Interactive Data Table**: View all order lines with fulfillment status, stock levels, and other key details in a sortable and filterable table.
    -   **Color-Coded Status**: Green for 'Fulfillable', Red for 'Not Fulfillable', and Yellow for 'Repeat Order' provide at-a-glance status information.
    -   **Context Menu**: Right-click on any order to quickly change its fulfillment status, add a tag, remove items, or copy key information like Order Number or SKU.
    -   **Advanced Filtering and Sorting**: The main data table can be sorted by any column and filtered by text across all columns or a specific column, with case-sensitive options.
-   **Configurable Rule Engine**: Create custom rules in the settings to automatically tag or modify orders based on specific conditions (e.g., tag all orders from Germany, set high priority for orders over a certain value).
-   **Dynamic Report Generation**:
    -   **Packing Lists**: Create custom packing lists with specific filters (e.g., by shipping provider, country, or order type).
    -   **Stock Exports**: Generate stock export files based on `.xls` templates for different couriers.
    -   **Custom Reports**: A dedicated report builder allows for the creation of one-off reports with any combination of columns and filters.
-   **Session Persistence**: Close the app and be prompted to restore your previous session's data on the next launch, allowing you to pick up right where you left off.

## Project Structure

The repository is organized into two main Python packages:

-   `shopify_tool/`: This is the core engine of the application. It contains all the business logic for data analysis, fulfillment simulation, report generation, and the rule engine. It is completely independent of the user interface.
-   `gui/`: This package contains all the code related to the graphical user interface, built with PySide6. It handles window management, user input, and displaying data. It uses the `shopify_tool` package as its backend.

The main entry point for the application is `gui_main.py`.

## Installation and Setup (for Developers)

To set up the development environment, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd shopify-fulfillment-tool
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    The project uses two requirements files:
    -   `requirements.txt`: For core application dependencies.
    -   `requirements-dev.txt`: For development, testing, and linting tools.

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
