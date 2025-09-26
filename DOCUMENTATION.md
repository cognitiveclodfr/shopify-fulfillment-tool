# Shopify Fulfillment Tool - Comprehensive User Guide

## 1. Introduction

Welcome to the Shopify Fulfillment Tool! This powerful desktop application is designed to revolutionize your order fulfillment workflow. Built for efficiency and flexibility, it automates the tedious process of figuring out which orders can be shipped, allowing your warehouse team to focus on what they do best: packing and shipping.

The tool takes your raw Shopify order exports and your current stock levels, analyzes them, and produces a clear, interactive list of fulfillable orders. With its advanced features like the Rule Engine, customizable reports, and settings profiles, you can tailor the application to your specific business needs, whether you're a small boutique or a large warehouse.

This guide will walk you through every feature, from initial setup to advanced automation, to help you get the most out of the tool.

## 2. Core Concepts

Before diving into the step-by-step guide, it's important to understand a few core concepts that the application is built around.

| Concept             | Description                                                                                                                                                                                            |
| :------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Session**         | Each time you run an analysis, you are working within a **Session**. All the reports and logs you generate are saved into a unique, timestamped folder for that session, keeping your work organized.         |
| **Profiles**        | A **Profile** is a complete, saved collection of your settings. This includes your automation rules, report templates, and path configurations. You can create multiple profiles (e.g., "EU Warehouse," "US Warehouse") and switch between them instantly. This is the key to managing different workflows. |
| **Rules**           | The **Rule Engine** is where you define your business logic. A rule is an "IF/THEN" statement. For example, **IF** an order's shipping country is "Germany," **THEN** add a "DE-WAREHOUSE" tag. This lets you automate tagging, prioritizing, and status changes. |
| **Reports**         | A **Report** is a final, formatted output file, typically an Excel spreadsheet. The two main types are **Packing Lists** (for your warehouse team to pick items) and **Stock Exports** (for inventory management). You can create multiple, highly-customizable templates for each type. |
| **Mappings**        | The **Mappings** feature makes the tool incredibly flexible. It allows you to "map" the column names from your specific CSV exports to the names the tool expects. You can also standardize courier names, so "DHL Express" and "dhl_de" can both be treated as "DHL." |

## 3. Getting Started: A Step-by-Step Guide

This section will walk you through setting up and using the application for the first time.

### Step 1: Initial Launch and Profile Creation

When you first launch the application, it creates a default set of configurations. Your settings are organized into **Profiles**. A profile stores all your rules, report templates, and path settings.

The first thing you should do is create your own profile.

1.  In the main window, find the **Profiles** dropdown menu (it will initially show `default`).
2.  Click the **"Manage Profiles"** button next to it.
3.  In the Profile Manager window, click **"Add New..."**.
4.  You will be prompted to enter a name. Let's call it `My_Warehouse`.
    -   This new profile is created as a *copy* of the currently active profile (`default`).
5.  Your new profile (`My_Warehouse`) is now active. All changes you make will be saved to this profile.

> **Pro Tip:** Use profiles to manage different workflows. For example, you could have separate profiles for different e-commerce stores, warehouses, or for handling domestic vs. international shipments. Each can have its own unique set of rules and report templates.

### Step 2: Configuring Mappings (Crucial for First Use!)

Before you can analyze your files, you must tell the tool where to find the data it needs. This is done in the **Mappings** tab in the Settings window.

1.  Click the **Settings button (⚙️)** to open the Settings window.
2.  Go to the **"Mappings"** tab.

#### Column Mappings

This section tells the tool which column in your CSV file corresponds to a piece of data it needs.

-   **Orders CSV:** You need to map the columns from your Shopify orders export. The tool needs to know the column names for the order number, SKU, quantity, and shipping provider. Fill in the text boxes with the exact header names from your CSV file.
-   **Stock CSV:** You need to map the columns from your inventory file for the SKU and the available stock count.

**Example:** If your stock file has a column named "Item Code" for the SKU and "Qty" for the stock level, your mapping would look like this:
-   `Sku:` Item Code
-   `Stock:` Qty

#### Courier Mappings

This powerful feature lets you standardize the names of your shipping providers. Your store might use many variations (e.g., "DHL Express," "DHL DE," "dhlpaket"), but for reporting, you might want to group them all as "DHL."

1.  Click **"Add Mapping"**.
2.  In the **"Original Name"** box, enter the name exactly as it appears in your orders file (e.g., "DHL Express").
3.  In the **"Standardized Name"** box, enter the name you want to use in your reports (e.g., "DHL").
4.  Repeat this for all variations.

After configuring your mappings, click **"Save"** at the bottom of the Settings window.

### Step 3: General Settings

Navigate to the **"General & Paths"** tab in the Settings window. Here you can configure:

-   **Stock CSV Delimiter:** The character that separates columns in your stock file. This is usually a comma (`,`) or a semicolon (`;`).
-   **Low Stock Threshold:** Set a number here (e.g., `10`). If fulfilling an order causes an item's stock to drop below this number, it will be flagged with a "Low Stock" alert in the analysis table.
-   **Paths:** You can optionally specify default folders for your report templates and stock export outputs.

### Step 4: Loading Data and Running the Analysis

Now you are ready to run your first analysis.

1.  **Load Files:**
    -   Back in the main window, click **"Load Orders File (.csv)"** and select your Shopify orders export.
    -   Click **"Load Stock File (.csv)"** and select your inventory file.
    -   A green check (✓) next to the filename means the file has loaded and the mapped columns were found. A red cross (✗) means some mapped columns are missing.

2.  **Run Analysis:**
    -   Once both files are loaded successfully, the large **"Run Analysis"** button will become active. Click it.
    -   The tool will perform the fulfillment simulation. The results will appear in the "Analysis Data" and "Statistics" tabs.

### Step 5: Interacting with the Results

The **"Analysis Data"** tab contains a detailed, interactive table of your orders.

-   **Fulfillment Status:** The `Order_Fulfillment_Status` column shows you which orders are "Fulfillable," "Not Fulfillable" (due to stock), or have a custom status you've set with rules.
-   **Manual Override:** You can double-click any row of an order to manually change its fulfillment status. For example, you can force-fulfill an order that's out of stock if you know you have more inventory arriving.
-   **Column Management:** Click the **"Manage Columns"** button to show, hide, or reorder columns to create your perfect view.
-   **Right-Click Menu:** Right-click on any row for quick actions like copying the order number or SKU.
-   **Highlighted Rows:** Rows with a `System_note` (like `Repeat` for a returning customer) will be highlighted in yellow, making them easy to spot.

## 4. In-Depth Guide: The Rule Engine

The Rule Engine is where you can encode your business's unique logic to automate order processing. To configure rules, go to **Settings (⚙️) > Rules**.

Each rule consists of **Conditions** (the "IF" part) and **Actions** (the "THEN" part). You can specify whether **ALL** conditions must be true or if **ANY** one of them is enough to trigger the actions.

### Rule Conditions

| Operator            | Description                                                                    | Example Usage                                |
| :------------------ | :----------------------------------------------------------------------------- | :------------------------------------------- |
| `equals`            | The field value is exactly the same as the specified value.                    | `Shipping_Country` equals `Germany`          |
| `does not equal`    | The field value is not the same as the specified value.                        | `Shipping_Provider` does not equal `DHL`     |
| `contains`          | The field value contains the specified text (not case-sensitive).              | `SKU` contains `-FRAGILE`                    |
| `does not contain`  | The field value does not contain the specified text (not case-sensitive).      | `Customer_Name` does not contain `TEST`      |
| `is greater than`   | The field value (must be a number) is greater than the specified value.        | `Total Price` is greater than `200`          |
| `is less than`      | The field value (must be a number) is less than the specified value.           | `Weight` is less than `0.5`                  |
| `starts with`       | The field value begins with the specified text.                                | `Order_Number` starts with `#EU`             |
| `ends with`         | The field value ends with the specified text.                                  | `SKU` ends with `.SAMPLE`                    |
| `is empty`          | The field has no value (it is blank).                                          | `Discount_Code` is empty                     |
| `is not empty`      | The field has any value (it is not blank).                                     | `Notes` is not empty                         |

### Rule Actions

| Action                  | Description                                                                                                                                                                                                                                                                                                                                                     |
| :---------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`ADD_TAG`**             | Adds a custom tag to the `Status_Note` column. Useful for flagging orders for manual review.                                                                                                                                                                                                                                                                     |
| **`SET_STATUS`**          | Changes the `Order_Fulfillment_Status`. For example, you could automatically set certain orders to "On Hold." **Note:** This overrides the default fulfillment logic.                                                                                                                                                                                             |
| **`SET_PRIORITY`**        | Sets the `Priority` of the order (e.g., to "High"). This can be used with report filters to create high-priority packing lists.                                                                                                                                                                                                                                  |
| **`EXCLUDE_FROM_REPORT`** | Hides the order from all generated reports. The order remains visible in the main table.                                                                                                                                                                                                                                                                          |
| **`EXCLUDE_SKU`**         | A specialized action that sets the quantity of a specific SKU within a matching order to zero, effectively removing it from fulfillment for that order. **Use with caution,** as it can lead to partial shipments. The SKU to exclude is specified in the "Value" field of the action. |
| **`REMOVE_TAG`**          | Removes a specific tag from the `Status_Note` column. The value should be the exact tag to remove.                                                                                                                                                                                                                                  |
| **`REPLACE_TAG`**         | Replaces an existing tag with a new one. The value must be in the format `OLD_TAG,NEW_TAG`.                                                                                                                                                                                                                                          |
| **`CLEAR_TAGS`**          | Completely removes all tags from the `Status_Note` column, leaving it blank.                                                                                                                                                                                                                                                            |
| **`ADD_TAG_TO_ORDER`**    | Similar to `ADD_TAG`, but designed for order-level rules. It applies a tag to all line items of an order that matches an order-level condition.                                                                                                                                                                                         |

### Advanced: Order-Level Rules

The Rule Engine can now analyze an entire order at once, not just individual line items. This allows for powerful rules based on combinations of items within an order.

To enable this, set the **`match_level`** property of a rule to **`"order"`**. When you do this, you gain access to new fields and operators.

**New Aggregated Fields for Order-Level Rules:**

| Field Name          | Description                                         | Example Value                  |
| :------------------ | :-------------------------------------------------- | :----------------------------- |
| `order_skus_list`   | A list of all SKUs present in the entire order.     | `['SKU-A', 'SKU-B', 'SKU-C']`  |
| `order_tags_set`    | A unique set of all tags applied to the entire order. | `{'FRAGILE', 'BOX'}`           |

**New Operators for Order-Level Rules:**

These operators are designed to work with the new list/set fields. The `value` for these operators should be a comma-separated string of items.

| Operator          | Description                                                                    | Example Usage                                                    |
| :---------------- | :----------------------------------------------------------------------------- | :--------------------------------------------------------------- |
| `contains all`    | The field (e.g., `order_skus_list`) contains every one of the specified items. | `order_skus_list` contains all `SKU-A,SKU-B`                     |
| `contains any`    | The field contains at least one of the specified items.                        | `order_skus_list` contains any `PROMO-1,PROMO-2`                 |
| `contains only`   | The field contains *exactly* the specified items and no others.                | `order_skus_list` contains only `SKU-C` (for single-item orders) |

**Example Order-Level Rule:**

This rule applies the `Double Tracking` tag to any order that contains **both** `01-FACE-1001` and `02-FACE-1001`.

```json
{
  "name": "Set Double Tracking for specific SKU combination",
  "match_level": "order",
  "conditions": [
    { "field": "order_skus_list", "operator": "contains all", "value": "01-FACE-1001,02-FACE-1001" }
  ],
  "actions": [
    { "type": "ADD_TAG_TO_ORDER", "value": "Double Tracking" }
  ]
}
```

## 5. In-Depth Guide: Reports and Exports

You can create templates for two types of reports in the Settings window: **Packing Lists** and **Stock Exports**.

### Report Configuration

When creating a report template, you can define:
- **Name:** A descriptive name (e.g., "DHL Express Packing List").
- **Output Filename:** The name of the generated file.
- **Filters:** Conditions to determine which orders are included in the report.
- **Exclude SKUs (Packing Lists Only):** A comma-separated list of SKUs to completely ignore for a specific packing list.

### Report Filters

Filters in reports use a different, more direct set of operators than the Rule Engine.

| Operator       | Description                                                                          | Example Usage                                           |
| :------------- | :----------------------------------------------------------------------------------- | :------------------------------------------------------ |
| `==`           | **Equals**: The field value must exactly match the specified value.                  | `Shipping_Provider` == `DHL`                            |
| `!=`           | **Does Not Equal**: The field value must not match.                                  | `Destination_Country` != `Spain`                        |
| `in`           | **Is In**: The field value must be one of the values in a comma-separated list.      | `Order_Type` in `Single,Multi`                          |
| `not in`       | **Is Not In**: The field value must not be in the comma-separated list.              | `SKU` not in `PROMO-ITEM,GIFT-CARD`                     |
| `contains`     | **Contains**: The field value must contain the specified text (case-sensitive).      | `Tags` contains `VIP`                                   |

### Generating a Report

1.  After a successful analysis, click **"Create Packing List"** or **"Create Stock Export"**.
2.  A dialog will appear showing your configured report templates.
3.  Select a report and click "Generate". The file will be saved in the current session's output folder.

## 6. Packaging Material Automation

The tool can automatically add packaging materials (like boxes, tape, and bubble wrap) to your **Stock Exports**. This allows you to accurately track and write off your packaging inventory.

This feature works by linking tags on an order to specific packaging SKUs.

### How It Works

1.  You define your packaging rules in your profile's `config.json` file.
2.  You use the **Rule Engine** to tag orders (e.g., add a "BOX" tag to all single-item orders).
3.  When you generate a **Stock Export**, the tool looks at the tags on each fulfillable order in that report.
4.  If an order's tag matches a rule in your packaging configuration, the specified packaging SKUs are automatically added to the final stock export list.

### Configuration

To set this up, you need to manually edit your profile's `config.json` file. You can access this by going to **Settings > Profiles > Open Profiles Folder**.

Add a new section called `packaging_rules` to your config file. This section contains key-value pairs where:
-   The **key** is the tag from the `Status_Note` column.
-   The **value** is an object where each key is a packaging SKU and its value is the quantity to add.

**Example `packaging_rules` in `config.json`:**

```json
"packaging_rules": {
  "BOX": {
    "PACK-BOX-S": 1
  },
  "Double": {
    "PACK-BOX-M": 1,
    "PACK-TAPE": 1
  },
  "FRAGILE": {
    "PACK-BUBBLE": 2
  }
}
```

**In this example:**
-   Any order with the `BOX` tag will add 1 `PACK-BOX-S` to the stock export.
-   Any order with the `Double` tag will add 1 `PACK-BOX-M` and 1 `PACK-TAPE`.
-   If an order has both `FRAGILE` and `BOX` tags, it will get materials from both rules (`PACK-BUBBLE`: 2 and `PACK-BOX-S`: 1).

## 7. Advanced Topics & FAQ

**How do I handle orders with both fragile and non-fragile items?**
- Create a rule that adds a "FRAGILE" tag if an order contains a fragile SKU. Then, create two packing lists: one that *includes* only orders with the "FRAGILE" tag, and another that *excludes* them. This lets you process them in separate batches.
- You can also link the "FRAGILE" tag to bubble wrap using the **Packaging Material Automation** feature to ensure it's deducted from your stock.

**Can I prepare a report for a specific courier?**
- Yes. Create a new Packing List template. Add a filter where `Shipping_Provider` == `[Courier Name]`. When you generate this report, it will only contain orders for that courier.

**What's the difference between `System_note` and `Status_Note`?**
- `System_note` is for tags added automatically by the application itself (e.g., `Repeat` for returning customers). `Status_Note` is for tags you add yourself using the `ADD_TAG` action in the Rule Engine. This keeps system information separate from your custom workflows.
