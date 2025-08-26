# Shopify Fulfillment Tool v8.0.0 - User Guide

## 1. Project Overview

The **Shopify Fulfillment Tool** is a desktop application designed to streamline and automate the order fulfillment process for e-commerce stores running on Shopify.

Its primary purpose is to analyze order and stock export files, determine which orders are fulfillable, and generate necessary documents like packing lists and courier export files. The graphical user interface (GUI) makes it accessible for warehouse staff without requiring command-line knowledge.

## 2. Key Features

This version includes a major UI/UX overhaul and significant new functionality:

-   **Persistent Settings:** All your configurations for Rules, Packing Lists, and Stock Exports are now automatically saved in a user-specific directory. Your settings will be remembered every time you open the app.
-   **Session Management:** Automatically saves the current analysis state upon closing the app and prompts to restore it on the next launch, preventing data loss.
-   **Advanced Rule Engine:** A powerful IF/THEN rule builder to automate workflows. Users can create rules to tag orders, change fulfillment status, set priorities, and more based on a combination of conditions.
-   **Enhanced Interactive Data Table:**
    -   **Frozen Column:** The `Order_Number` column is locked in place during horizontal scrolling for easy reference.
    -   **Column Management:** Users can now show, hide, and reorder columns to create a personalized view.
    -   **Context Menu:** A right-click menu on any order provides quick access to common actions like changing status, copying the order number, or removing items.
    -   **Manual Override:** Double-click an order to toggle its fulfillment status. The application automatically recalculates stock levels and all related statistics.
-   **Advanced Logging:** The "Execution Log" tab now features a structured, color-coded log viewer with filtering and search capabilities.
-   **Flexible Report Generation:** Create custom packing lists and stock export files based on a powerful and flexible filtering system.

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

The "Analysis Data" table is now highly interactive:

-   **Change Status (Double-Click):** Double-click any row of an order to toggle its fulfillment status between "Fulfillable" and "Not Fulfillable".
-   **Context Menu (Right-Click):** Right-click any row to open a context menu with actions like `Change Status`, `Copy Order Number`, etc.
-   **Manage Columns:** Click the **"Manage Columns"** button above the table to open a window where you can show, hide, and reorder columns.

### Step 5: Configuring Rules, Reports, and Settings

1.  Click the **Settings button (⚙️)** in the bottom right of the main action panel.
2.  The Settings window will open with four tabs: "General & Paths", "Rules", "Packing Lists", and "Stock Exports".
3.  Navigate to the desired tab to add, edit, or delete configurations.
4.  **Example: Adding a Rule**
    -   Go to the **"Rules"** tab and click **"Add New Rule"**.
    -   Configure the rule's name, conditions (IF), and actions (THEN).
5.  Click **"Save and Close"**. Your changes will be saved permanently and will be available the next time you open the application.

### Step 6: Generating Reports

-   After a successful analysis, the report buttons on the left of the main action panel become active.
-   Click **"Create Packing List"** or **"Create Stock Export"** to open a window with your configured reports.
-   Select the desired report. The generated file will be saved in the current session's output folder.
