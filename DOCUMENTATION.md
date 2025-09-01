# Shopify Fulfillment Tool v8.1.8 - User Guide

## 1. Project Overview

The **Shopify Fulfillment Tool** is a desktop application designed to streamline and automate the order fulfillment process for e-commerce stores running on Shopify.

Its primary purpose is to analyze order and stock export files, determine which orders are fulfillable, and generate necessary documents like packing lists and courier export files. The graphical user interface (GUI) makes it accessible for warehouse staff without requiring command-line knowledge.

## 2. Key Features

### What's New in v8.1.8

-   **Low Stock Alerts:** A new `Stock_Alert` column in the analysis table will automatically flag items that fall below a configurable threshold after fulfillment.
-   **Exclude SKUs from Packing Lists:** You can now specify a list of SKUs to be completely excluded from packing list reports, giving you more control over the output.
-   **Enhanced Statistics:** The "Statistics" tab is now more detailed, providing a breakdown of completed orders and repeat orders by courier.
-   **Improved Report Information:** The main `fulfillment_analysis.xlsx` report now includes a "Report Info" sheet that records the exact time the report was generated.

### What's New in v8.1.0

-   **Modernized UI:** The main analysis table has been updated with a cleaner, more modern look, improved fonts, and better row spacing for enhanced readability.
-   **New Data Columns:** The analysis table now includes two new columns:
    -   `Total Price`: Displays the total price of the order, taken from the "Total" column of your Shopify export.
    -   `System_note`: Shows system-generated tags, such as `Repeat` for orders from returning customers.
-   **Row Highlighting:** Rows with a `System_note` (e.g., 'Repeat' orders) are now automatically highlighted in yellow, making them easy to spot.
-   **Enhanced Context Menu:** You can now right-click a line item and select **"Copy SKU"** to quickly copy the product's SKU to your clipboard.
-   **Expanded Filtering:** `Order_Number` has been added as a filterable field in the Settings window for Rules, Packing Lists, and Stock Exports, allowing for more granular control.

### Core Features (v8.0.0)

-   **Persistent Settings:** All your configurations for Rules, Packing Lists, and Stock Exports are now automatically saved in a user-specific directory.
-   **Session Management:** Automatically saves the current analysis state upon closing the app and prompts to restore it on the next launch.
-   **Advanced Rule Engine:** A powerful IF/THEN rule builder to automate workflows.
-   **Enhanced Interactive Data Table:**
    -   **Frozen Column:** The `Order_Number` column is locked in place for easy reference.
    -   **Column Management:** Show, hide, and reorder columns to create a personalized view.
    -   **Context Menu:** A right-click menu provides quick access to common actions.
    -   **Manual Override:** Double-click an order to toggle its fulfillment status.
-   **Advanced Logging:** A structured, color-coded log viewer with filtering and search capabilities.
-   **Flexible Report Generation:** Create custom packing lists and stock export files.

## 3. User Guide

### Step 1: Launching the Application & Managing Sessions

-   **Launch:** Run the `.exe` file. On first launch, the application will create a settings folder in your user directory (e.g., `C:\Users\YourUser\AppData\Roaming\ShopifyFulfillmentTool`) to store your configurations.
-   **Restoring a Session:** If you have a previously saved session, a dialog box will appear asking if you want to restore it. Click "Yes" to load your previous work.
-   **Creating a New Session:** If you start fresh, click the **"Create New Session"** button. The tool will create a unique, dated folder for all the reports generated during your work session.

### Step 2: Loading Data Files

-   Click **"Load Orders File (.csv)"** to select your orders export file from Shopify.
-   Click **"Load Stock File (.csv)"** to select your current inventory/stock file.
-   Next to each file name, a status icon will appear. A green check (✓) means the file is valid. A red cross (✗) means required columns are missing; hover over the icon to see which ones.

### Step 3: Running the Analysis

-   Once both files are loaded and validated, the large **"Run Analysis"** button will become active. Click it to start the analysis.
-   The application will process the data, and the results will appear in the "Analysis Data" and "Statistics" tabs.

### Step 4: Interacting with the Data Table

The "Analysis Data" table is now highly interactive and includes new information:

-   **New Columns:** You will now see `Total Price`, `System_note`, and `Stock_Alert` columns. Rows with system notes (like `Repeat`) will be highlighted in yellow. The `Stock_Alert` column will display 'Low Stock' for any item whose inventory falls below the threshold you define in the settings.
-   **Change Status (Double-Click):** Double-click any row of an order to toggle its fulfillment status between "Fulfillable" and "Not Fulfillable". Be aware that "force-fulfilling" an order with insufficient stock may result in negative final stock values for the affected items.
-   **Context Menu (Right-Click):** Right-click any row to open a context menu. It now includes **`Copy SKU`** in addition to `Change Status`, `Copy Order Number`, etc.
-   **Manage Columns:** Click the **"Manage Columns"** button above the table to show, hide, and reorder columns, including the new `Total Price`, `System_note`, and `Stock_Alert` columns.

### Step 5: Configuring Rules, Reports, and Settings

1.  Click the **Settings button (⚙️)** in the bottom right of the main action panel.
2.  The Settings window will open with four tabs: "General & Paths", "Rules", "Packing Lists", and "Stock Exports".
3.  **General Settings:**
    -   In the **"General & Paths"** tab, you can now set a **"Low Stock Threshold"**. If an item's final stock level drops below this number, it will be flagged in the `Stock_Alert` column.
4.  **Packing List Settings:**
    -   In the **"Packing Lists"** tab, when you add or edit a report, you will see a new field: **"Exclude SKUs"**.
    -   Enter a comma-separated list of SKUs (e.g., `SKU001,SKU002,SKU003`) that you want to be completely ignored and left out of that specific packing list report.
5.  When creating or editing rules and report filters, you can now select **`Order_Number`** and **`Total Price`** from the list of filterable fields.
6.  Click **"Save and Close"**. Your changes will be saved permanently and will be available the next time you open the application.

### Step 6: Generating Reports

-   After a successful analysis, the report buttons on the left of the main action panel become active.
-   Click **"Create Packing List"** or **"Create Stock Export"** to open a window with your configured reports.
-   Select the desired report. The generated file will be saved in the current session's output folder.
-   The main Excel export, `fulfillment_analysis.xlsx`, now contains a new sheet called **"Report Info"** which shows the exact date and time the report was created.
