# Shopify Fulfillment Tool

## What is this project?

The Shopify Fulfillment Tool is a desktop application designed to streamline the order fulfillment process for Shopify stores. It helps warehouse managers and logistics personnel to efficiently analyze orders, check stock availability, and generate necessary reports like packing lists and stock exports for various couriers.

The tool provides a clear, color-coded user interface to quickly identify which orders are fulfillable, which are not, and which require special attention (e.g., repeat orders).

## Main Features

-   **Session-Based Workflow**: All generated reports for a work session are saved in a unique, dated folder.
-   **Order & Stock Analysis**: Load Shopify order exports and current stock files to run a fulfillment simulation.
-   **Interactive Data Table**: View all order lines with fulfillment status, stock levels, and other key details.
    -   **Color-Coded Status**: Green for 'Fulfillable', Red for 'Not Fulfillable', Yellow for 'Repeat Order'.
    -   **Context Menu**: Quickly change an order's status or copy key information like Order Number or SKU.
    -   **Customizable View**: Show, hide, and reorder columns to fit your workflow.
-   **Rule Engine**: Automatically tag orders based on custom rules (e.g., tag orders from a specific country).
-   **Report Generation**:
    -   **Packing Lists**: Create custom packing lists with specific filters (e.g., by shipping provider).
    -   **Stock Exports**: Generate stock export files based on templates for different couriers.
    -   **Custom Reports**: Build your own reports with custom filters and columns.
-   **Session Persistence**: Close the app and restore your previous session's data on next launch.

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
