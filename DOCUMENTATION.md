# Shopify Fulfillment Tool v8.0 - User Guide

## 1. Project Overview

The **Shopify Fulfillment Tool** is a desktop application designed to streamline and automate the order fulfillment process for e-commerce stores running on Shopify.

Its primary purpose is to analyze order and stock export files, determine which orders are fulfillable, and generate necessary documents like packing lists and courier export files. The graphical user interface (GUI) makes it accessible for warehouse staff without requiring command-line knowledge.

## 2. Key Features

This version includes a major UI/UX overhaul and significant new functionality:

-   **Session Management:** Automatically saves the current analysis state upon closing the app and prompts to restore it on the next launch, preventing data loss.
-   **Advanced Rule Engine:** A powerful IF/THEN rule builder to automate workflows. Users can create rules to tag orders, change fulfillment status, set priorities, and more based on a combination of conditions (e.g., `IF Shipping_Provider is 'DHL' AND Order_Type is 'Multi' THEN Add Note 'EXPRESS'`).
-   **Enhanced Interactive Data Table:**
    -   **Frozen Column:** The `Order_Number` column is locked in place during horizontal scrolling for easy reference.
    -   **Column Management:** Users can now show, hide, and reorder columns to create a personalized view.
    -   **Context Menu:** A right-click menu on any order provides quick access to common actions like changing status, copying the order number, or removing items.
    -   **Manual Override:** Double-click an order to toggle its fulfillment status. The application automatically recalculates stock levels and all related statistics.
-   **Advanced Logging:** The "Execution Log" tab now features a structured, color-coded log viewer with filtering and search capabilities, making it easier to monitor the application's activity and diagnose issues.
-   **Real-time File Validation:** Instantly validates required columns when loading `.csv` files, preventing errors during analysis.
-   **Flexible Report Generation:** Create custom packing lists and stock export files based on a powerful filtering system.

## 3. User Guide

### Step 1: Launching the Application & Managing Sessions

-   **Launch:** Run the `.exe` file.
-   **Restoring a Session:** If you have a previously saved session, a dialog box will appear asking if you want to restore it. Click "Yes" to load your previous work.
-   **Creating a New Session:** If you start fresh, click the **"Create New Session"** button. The tool will create a unique, dated folder for all the reports generated during your work session.

### Step 2: Loading Data Files

-   Click **"Load Orders File (.csv)"** to select your orders export file from Shopify.
-   Click **"Load Stock File (.csv)"** to select your current inventory/stock file.
-   Next to each file name, a status icon will appear. A green check (✓) means the file is valid. A red cross (✗) means required columns are missing; hover over the icon to see which ones.

### Step 3: Running the Analysis

-   Once both files are loaded and validated, the **"Run Analysis"** button will become active. Click it to start the analysis.
-   The application will process the data, and the results will appear in the "Analysis Data" and "Statistics" tabs. The "Execution Log" will show a detailed breakdown of the process.

### Step 4: Interacting with the Data Table

The "Analysis Data" table is now highly interactive:

-   **Change Status (Double-Click):** Double-click any row of an order to toggle its fulfillment status between "Fulfillable" and "Not Fulfillable".
-   **Context Menu (Right-Click):** Right-click any row to open a context menu with these actions:
    -   `Change Status`: Same as double-clicking.
    -   `Copy Order Number`: Copies the order number to your clipboard.
    -   `Add Tag Manually...`: Opens a dialog to add a custom note to the `Status_Note` column for that order.
    -   `Remove This Item from Order`: Deletes the specific line item from the analysis (requires confirmation).
    -   `Remove Entire Order`: Deletes all line items for that order from the analysis (requires confirmation).
-   **Manage Columns:** Click the **"Manage Columns"** button above the table to open a window where you can show, hide, and reorder columns.
-   **Horizontal Scrolling:** Scroll horizontally to see all data. The `Order_Number` column will remain frozen on the left.

### Step 5: Using the Rule Engine (Settings)

The **Settings** window contains the powerful new Rule Builder.

1.  Click the **"Settings"** button on the main window.
2.  Go to the **"Rules"** tab.
3.  Click **"Add New Rule"**. A new block for your rule will appear.
4.  **Configure the Rule:**
    -   **Rule Name:** Give your rule a descriptive name (e.g., "High-Value DHL Orders").
    -   **Match Logic:** Choose "ALL" (AND) or "ANY" (OR) to determine if all or any of the conditions must be met.
    -   **Conditions (IF):**
        -   Click **"Add Condition"**.
        -   Select a `Field` (e.g., `Shipping_Provider`), an `Operator` (e.g., `equals`), and a `Value` (e.g., `DHL`).
        -   Add more conditions as needed.
    -   **Actions (THEN):**
        -   Click **"Add Action"**.
        -   Select an `Action Type` (e.g., `ADD_TAG`) and a `Value` (e.g., `PRIORITY`).
        -   The `ADD_TAG` action will append the value to the `Status_Note` column.
5.  Click **"Save and Close"**. The new rules will be applied the next time you run an analysis.

**Example Rule:**

-   **Name:** Tag Express Multi-Item Orders
-   **Match:** ALL
-   **Conditions:**
    1.  `Shipping_Provider` `contains` `DHL`
    2.  `Order_Type` `equals` `Multi`
-   **Actions:**
    1.  `ADD_TAG` with value `EXPRESS-MULTI`

### Step 6: Generating Reports

-   After a successful analysis, the **"Create Packing List"** and **"Create Stock Export"** buttons become active.
-   Click a button and select the desired report type from the list that appears.
-   The generated file will be saved in the current session's output folder.
