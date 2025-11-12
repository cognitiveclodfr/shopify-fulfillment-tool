# Sets Decoding System Audit

**Date:** 2025-11-12
**Purpose:** Analyze current state and design sets/bundles decoding system for Shopify Fulfillment Tool
**Repository:** cognitiveclodfr/shopify-fulfillment-tool

---

## Executive Summary

**Status:** ❌ Sets/Bundles decoding system is **NOT implemented**

**Key Findings:**
- Configuration field exists (`set_decoders: {}`) but is unused
- No decoding logic in order processing pipeline
- No UI for managing set definitions
- Orders containing set SKUs are processed as regular SKUs and fail fulfillment

**Impact:**
- Orders with bundle SKUs (e.g., SET-WINTER-KIT) are marked as "Not Fulfillable" even when all component items are in stock
- Warehouse cannot efficiently process bundle orders
- Manual intervention required for every bundle order

**Recommendation:** Implement full sets decoding system (estimated 16-21 hours)

---

## 1. Current State Analysis

### 1.1 Set Configuration

**Location:** `shopify_tool/profile_manager.py:498`

**Current Structure:**
```json
{
  "set_decoders": {}
}
```

**Findings:**
- ✅ Configuration field exists in default shopify_config template
- ✅ Field is persisted per client in `shopify_config.json`
- ❌ Field is always empty (no sets defined)
- ❌ No code reads or uses this field
- ✅ Tests verify field exists (test_profile_manager.py:352, test_migration.py:190)

**Evidence:**
```python
# profile_manager.py:438-500
def _create_default_shopify_config(self, client_id: str, client_name: str) -> Dict:
    return {
        "client_id": client_id,
        "client_name": client_name,
        # ... other fields ...
        "set_decoders": {},  # ← EXISTS BUT UNUSED
        "packaging_rules": []
    }
```

---

### 1.2 Order Processing Pipeline

**File:** `shopify_tool/analysis.py`

**Current Flow:**
```
Orders CSV → Load → Clean → Normalize SKU → Match with Stock → Fulfillment Simulation → Reports
```

**Detailed Analysis:**

#### Step 1: Data Loading (Lines 82-133)
```python
# Column mappings applied
orders_df = orders_df.rename(columns=orders_rename_map)
stock_df = stock_df.rename(columns=stock_rename_map)
```
**Finding:** No set detection at load time

#### Step 2: Data Cleaning (Lines 136-161)
```python
orders_clean_df = orders_df[columns_to_keep_existing].copy()
orders_clean_df = orders_clean_df.dropna(subset=["SKU"])
```
**Finding:** SKUs processed as-is, no expansion

#### Step 3: SKU Normalization (Lines 163-183)
```python
from .csv_utils import normalize_sku
orders_clean_df["SKU"] = orders_clean_df["SKU"].apply(normalize_sku)
stock_clean_df["SKU"] = stock_clean_df["SKU"].apply(normalize_sku)
```
**Finding:** `normalize_sku()` only handles formatting (whitespace, float artifacts, leading zeros). No set detection.

#### Step 4: Stock Matching (Lines 218-231)
```python
final_df = pd.merge(orders_clean_df, stock_clean_df, on="SKU", how="left")
```
**Finding:** Simple merge by SKU. If order has "SET-WINTER-KIT" but stock only has components ("SKU-HAT", "SKU-GLOVES", "SKU-SCARF"), merge fails → Stock column becomes NaN → Order marked as Not Fulfillable

#### Step 5: Fulfillment Simulation (Lines 197-212)
```python
for order_number in prioritized_orders["Order_Number"]:
    order_items = orders_with_counts[orders_with_counts["Order_Number"] == order_number]
    can_fulfill_order = True
    for _, item in order_items.iterrows():
        sku, required_qty = item["SKU"], item["Quantity"]
        if required_qty > live_stock.get(sku, 0):  # ← Checks SKU directly
            can_fulfill_order = False
            break
```
**Finding:** Checks if `live_stock[sku]` has enough quantity. For set SKUs, `live_stock.get("SET-WINTER-KIT", 0)` returns 0 (not in stock) → Order fails

**Root Cause:**
Set SKUs are never decoded into their component SKUs, so stock matching fails at merge time.

---

### 1.3 Settings UI

**File:** `gui/settings_window_pyside.py`

**Existing Tabs:**
```python
# Lines 251, 267, 502, 620, 780, 917
self.tab_widget.addTab(tab, "General")
self.tab_widget.addTab(tab, "Rules")
self.tab_widget.addTab(tab, "Order Rules")
self.tab_widget.addTab(tab, "Packing Lists")
self.tab_widget.addTab(tab, "Stock Exports")
self.tab_widget.addTab(tab, "Mappings")
```

**Findings:**
- ❌ No "Sets" or "Bundles" tab
- ❌ No UI widgets for adding/editing set definitions
- ❌ No CSV import functionality for sets
- ❌ No visual indication when sets are configured

**Impact:**
Users have no way to define sets through the UI. Even if sets were manually added to config JSON, there's no way to view or edit them.

---

### 1.4 Stock System Integration

**Current Stock File Format:**
```csv
SKU,Product_Name,Stock
SKU-HAT,Winter Hat,50
SKU-GLOVES,Gloves,30
SKU-SCARF,Scarf,0
```

**Observations:**
- Stock files contain individual SKUs, NOT set SKUs
- This is correct behavior (sets are virtual, components are real)
- Stock calculation for sets must aggregate component availability

**Expected Behavior (Not Implemented):**
```python
# Pseudo-code for set stock calculation
SET-WINTER-KIT requires:
  - SKU-HAT (qty: 1)
  - SKU-GLOVES (qty: 1)
  - SKU-SCARF (qty: 1)

Stock:
  - SKU-HAT: 50 → can make 50 sets
  - SKU-GLOVES: 30 → can make 30 sets
  - SKU-SCARF: 0 → can make 0 sets

Available sets: min(50, 30, 0) = 0
```

**Current Behavior:**
```python
# What actually happens
Stock lookup for "SET-WINTER-KIT" → Not found → Stock = 0 → Not Fulfillable
```

---

## 2. Problem Illustration

### Use Case: Winter Bundle Order

**Scenario:**
```
Order #1001:
  - SKU: SET-WINTER-BUNDLE
  - Quantity: 2

Set Definition (not implemented):
  SET-WINTER-BUNDLE =
    - SKU-HAT (1x)
    - SKU-GLOVES (1x)
    - SKU-SCARF (1x)

Stock:
  - SKU-HAT: 50
  - SKU-GLOVES: 30
  - SKU-SCARF: 0
```

**Expected Behavior:**
```
1. Decode SET-WINTER-BUNDLE → 3 components
2. Check stock for each component
3. Calculate: min(50/1, 30/1, 0/1) = 0 sets available
4. Result: "Not Fulfillable" (missing SKU-SCARF)
5. Report shows: "Missing: SKU-SCARF (2 units needed, 0 in stock)"
```

**Actual Behavior:**
```
1. No decoding happens
2. Lookup stock for "SET-WINTER-BUNDLE" → Not found
3. Stock = NaN → 0
4. Result: "Not Fulfillable"
5. Report shows: "SKU not in stock: SET-WINTER-BUNDLE"
```

**Problem:**
User doesn't know if ALL components are missing or just ONE. Cannot prioritize restocking.

---

## 3. Proposed Architecture

### 3.1 Set Definition Format

**Recommendation:** Use existing `set_decoders` field with structured format

**Proposed Structure (Variant A - Simple):**
```json
{
  "set_decoders": {
    "SET-WINTER-BUNDLE": [
      {"sku": "SKU-HAT", "quantity": 1},
      {"sku": "SKU-GLOVES", "quantity": 1},
      {"sku": "SKU-SCARF", "quantity": 1}
    ],
    "SET-PICNIC-KIT": [
      {"sku": "SKU-PLATE", "quantity": 4},
      {"sku": "SKU-FORK", "quantity": 4},
      {"sku": "SKU-CUP", "quantity": 4},
      {"sku": "SKU-NAPKIN", "quantity": 8}
    ]
  }
}
```

**Alternative (Variant B - With Metadata):**
```json
{
  "set_decoders": {
    "SET-WINTER-BUNDLE": {
      "name": "Winter Bundle",
      "enabled": true,
      "components": [
        {"sku": "SKU-HAT", "quantity": 1, "required": true},
        {"sku": "SKU-GLOVES", "quantity": 1, "required": true},
        {"sku": "SKU-SCARF", "quantity": 1, "required": false}
      ]
    }
  }
}
```

**Recommendation:** Start with **Variant A** (simpler, sufficient for MVP)

**Rationale:**
- Simpler to implement and validate
- Easier UI (less fields to manage)
- Can migrate to Variant B later if needed
- `required` field adds complexity without clear use case

---

### 3.2 Set Detection Strategy

**Recommendation:** Explicit list lookup (safest, most accurate)

```python
def is_set_sku(sku: str, set_decoders: dict) -> bool:
    """
    Check if SKU is a defined set.

    Args:
        sku: SKU to check
        set_decoders: Set definitions from config

    Returns:
        True if SKU is a set
    """
    return sku in set_decoders
```

**Alternative Approaches (NOT recommended):**

❌ **Prefix pattern:**
```python
def is_set_sku(sku: str) -> bool:
    return sku.startswith("SET-")
```
**Problem:** False positives if client uses "SET-" for non-bundle SKUs

❌ **Regex pattern:**
```python
def is_set_sku(sku: str) -> bool:
    return bool(re.match(r"^SET-", sku))
```
**Problem:** Same issue as prefix, adds complexity

---

### 3.3 Decoding Strategy

**Recommendation:** Early expansion (decode immediately after data cleaning)

**Modified Order Processing Flow:**
```
┌─────────────────────────────────────┐
│ Load Orders CSV                     │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Clean Data                          │
│ (columns, normalize SKU)            │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 🆕 DECODE SETS                      │
│ For each row:                       │
│   if SKU in set_decoders:           │
│     - Save original set SKU         │
│     - Expand to component rows      │
│     - Multiply quantity             │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Match with Stock                    │
│ (now components match!)             │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Fulfillment Simulation              │
│ (existing logic works)              │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Generate Reports                    │
│ (optionally group by original SKU)  │
└─────────────────────────────────────┘
```

**Key Implementation:**
```python
def decode_sets_in_orders(orders_df, set_decoders):
    """
    Expand set SKUs into component SKUs.

    Example:
        Input:
            Order_Number | SKU              | Quantity
            1001         | SET-WINTER-KIT   | 2

        Output:
            Order_Number | SKU         | Quantity | Original_SKU
            1001         | SKU-HAT     | 2        | SET-WINTER-KIT
            1001         | SKU-GLOVES  | 2        | SET-WINTER-KIT
            1001         | SKU-SCARF   | 2        | SET-WINTER-KIT
    """
    expanded_rows = []

    for idx, row in orders_df.iterrows():
        sku = row["SKU"]

        if sku in set_decoders:
            # This is a set - expand it
            components = set_decoders[sku]
            order_qty = row["Quantity"]

            for component in components:
                new_row = row.copy()
                new_row["SKU"] = component["sku"]
                new_row["Quantity"] = order_qty * component["quantity"]
                new_row["Original_SKU"] = sku  # Track original set
                expanded_rows.append(new_row)
        else:
            # Regular SKU - keep as-is
            row_copy = row.copy()
            row_copy["Original_SKU"] = sku
            expanded_rows.append(row_copy)

    return pd.DataFrame(expanded_rows)
```

**Alternative (Late expansion - NOT recommended):**
Decode during stock matching phase.

**Why rejected:**
- More complex logic (must handle sets separately during fulfillment)
- Harder to debug
- Report generation becomes complicated
- Early expansion is cleaner and integrates better

---

### 3.4 Stock Calculation for Sets

**After early expansion, stock calculation happens automatically:**

```
Order after expansion:
  Order_Number | SKU         | Quantity | Original_SKU
  1001         | SKU-HAT     | 2        | SET-WINTER-KIT
  1001         | SKU-GLOVES  | 2        | SET-WINTER-KIT
  1001         | SKU-SCARF   | 2        | SET-WINTER-KIT

Stock matching (existing code works):
  Merge on SKU → each component gets stock value

Fulfillment simulation (existing code works):
  For order 1001:
    - Check SKU-HAT: need 2, have 50 ✓
    - Check SKU-GLOVES: need 2, have 30 ✓
    - Check SKU-SCARF: need 2, have 0 ✗
  Result: Not Fulfillable
```

**Advantage:** No changes needed to fulfillment logic! Existing code handles expanded orders correctly.

---

### 3.5 Report Generation

**Recommendation:** Expanded view with grouping

**Report Format (Packing List example):**
```
Order_Number | SKU              | Quantity | Status      | Notes
─────────────┼──────────────────┼──────────┼─────────────┼─────────────────
1001         | SET-WINTER-KIT   | 2        | Not Fulfill | (Set - expanded)
1001         |   └─ SKU-HAT     | 2        | ✓           |
1001         |   └─ SKU-GLOVES  | 2        | ✓           |
1001         |   └─ SKU-SCARF   | 2        | ✗ Missing   |
1002         | SKU-SINGLE       | 1        | Fulfillable |
```

**Implementation:**
```python
def format_report_with_sets(df):
    """
    Group components back to original set for display.
    """
    output_rows = []

    for order_num in df["Order_Number"].unique():
        order_df = df[df["Order_Number"] == order_num]

        # Group by Original_SKU
        for original_sku in order_df["Original_SKU"].unique():
            items = order_df[order_df["Original_SKU"] == original_sku]

            if original_sku in set_decoders:
                # Show set header
                output_rows.append({
                    "Order_Number": order_num,
                    "SKU": original_sku,
                    "Quantity": items.iloc[0]["Original_Quantity"],  # Need to track this
                    "Status": items.iloc[0]["Order_Fulfillment_Status"],
                    "Notes": "(Set)"
                })

                # Show components indented
                for _, item in items.iterrows():
                    output_rows.append({
                        "Order_Number": "",
                        "SKU": f"  └─ {item['SKU']}",
                        "Quantity": item["Quantity"],
                        "Status": "✓" if item["Stock"] >= item["Quantity"] else "✗",
                        "Notes": ""
                    })
            else:
                # Regular item
                output_rows.append(items.iloc[0].to_dict())

    return pd.DataFrame(output_rows)
```

---

## 4. Required Changes

### 4.1 Config Management

**File:** `shopify_tool/profile_manager.py`

**Changes:**
```python
class ProfileManager:

    def get_set_decoders(self, client_id: str) -> dict:
        """
        Get set decoder definitions for client.

        Returns:
            dict: Set definitions
                {"SET-SKU": [{"sku": "COMP-1", "quantity": 1}, ...], ...}
        """
        config = self.load_shopify_config(client_id)
        return config.get("set_decoders", {})

    def save_set_decoders(self, client_id: str, set_decoders: dict):
        """
        Save set decoder definitions.

        Args:
            client_id: Client ID
            set_decoders: Set definitions dict
        """
        config = self.load_shopify_config(client_id)
        config["set_decoders"] = set_decoders
        self.save_shopify_config(client_id, config)

    def add_set(self, client_id: str, set_sku: str, components: list):
        """
        Add or update a single set definition.

        Args:
            client_id: Client ID
            set_sku: Set SKU (e.g., "SET-WINTER-KIT")
            components: List of {"sku": "...", "quantity": N}

        Raises:
            ValidationError: If components are invalid
        """
        # Validate
        if not set_sku:
            raise ValidationError("Set SKU cannot be empty")

        if not components:
            raise ValidationError("Set must have at least one component")

        for comp in components:
            if "sku" not in comp or "quantity" not in comp:
                raise ValidationError("Each component must have 'sku' and 'quantity'")
            if comp["quantity"] <= 0:
                raise ValidationError("Component quantity must be positive")

        # Save
        set_decoders = self.get_set_decoders(client_id)
        set_decoders[set_sku] = components
        self.save_set_decoders(client_id, set_decoders)

        logger.info(f"Set '{set_sku}' saved with {len(components)} components")

    def delete_set(self, client_id: str, set_sku: str) -> bool:
        """
        Delete a set definition.

        Returns:
            bool: True if deleted, False if not found
        """
        set_decoders = self.get_set_decoders(client_id)

        if set_sku in set_decoders:
            del set_decoders[set_sku]
            self.save_set_decoders(client_id, set_decoders)
            logger.info(f"Set '{set_sku}' deleted")
            return True

        return False
```

**Effort:** 2-3 hours

---

### 4.2 Analysis Engine

**File:** `shopify_tool/analysis.py`

**Location:** Insert after line 161 (after data cleaning)

**Changes:**
```python
# NEW: Import set decoder logic
from .set_decoder import decode_sets_in_orders

def run_analysis(stock_df, orders_df, history_df, column_mappings=None):
    # ... existing code up to line 161 ...

    orders_clean_df = orders_df[columns_to_keep_existing].copy()
    orders_clean_df = orders_clean_df.dropna(subset=["SKU"])

    # CRITICAL: Normalize SKU to standard format for consistent merging
    from .csv_utils import normalize_sku
    orders_clean_df["SKU"] = orders_clean_df["SKU"].apply(normalize_sku)

    # 🆕 NEW: Decode sets into components
    # Get set_decoders from column_mappings or use empty dict
    set_decoders = column_mappings.get("set_decoders", {}) if column_mappings else {}
    if set_decoders:
        logger.info(f"Decoding {len(set_decoders)} set definitions...")
        orders_clean_df = decode_sets_in_orders(orders_clean_df, set_decoders)
        logger.info(f"Orders after set expansion: {len(orders_clean_df)} rows")

    # ... rest of existing code continues ...
```

**New File:** `shopify_tool/set_decoder.py`

```python
"""Set/Bundle decoding logic for Shopify Fulfillment Tool."""

import pandas as pd
import logging

logger = logging.getLogger("ShopifyToolLogger")


def decode_sets_in_orders(orders_df: pd.DataFrame, set_decoders: dict) -> pd.DataFrame:
    """
    Expand set/bundle SKUs into their component SKUs.

    This function identifies rows where the SKU is defined as a set in the
    set_decoders configuration, and expands each set into multiple rows
    (one per component). The quantity is multiplied accordingly.

    Example:
        Input:
            Order_Number | SKU            | Quantity | Product_Name
            1001         | SET-WINTER-KIT | 2        | Winter Bundle

        Set Definition:
            "SET-WINTER-KIT": [
                {"sku": "SKU-HAT", "quantity": 1},
                {"sku": "SKU-GLOVES", "quantity": 1}
            ]

        Output:
            Order_Number | SKU         | Quantity | Product_Name  | Original_SKU    | Original_Quantity
            1001         | SKU-HAT     | 2        | Winter Bundle | SET-WINTER-KIT  | 2
            1001         | SKU-GLOVES  | 2        | Winter Bundle | SET-WINTER-KIT  | 2

    Args:
        orders_df: DataFrame with order line items
        set_decoders: Dictionary of set definitions
            Format: {"SET-SKU": [{"sku": "COMP-SKU", "quantity": N}, ...], ...}

    Returns:
        DataFrame with sets expanded into components
    """
    if not set_decoders:
        # No sets configured - return as-is with tracking columns
        orders_df["Original_SKU"] = orders_df["SKU"]
        orders_df["Original_Quantity"] = orders_df["Quantity"]
        orders_df["Is_Set_Component"] = False
        return orders_df

    expanded_rows = []
    sets_decoded_count = 0

    for idx, row in orders_df.iterrows():
        sku = row["SKU"]

        if sku in set_decoders:
            # This is a set - expand it
            components = set_decoders[sku]
            order_qty = row["Quantity"]
            sets_decoded_count += 1

            logger.debug(f"Decoding set {sku} (qty: {order_qty}) → {len(components)} components")

            for component in components:
                new_row = row.copy()
                new_row["SKU"] = component["sku"]
                new_row["Quantity"] = order_qty * component["quantity"]
                new_row["Original_SKU"] = sku  # Track original set SKU
                new_row["Original_Quantity"] = order_qty  # Track original order quantity
                new_row["Is_Set_Component"] = True
                expanded_rows.append(new_row)
        else:
            # Regular SKU - keep as-is but add tracking columns
            row_copy = row.copy()
            row_copy["Original_SKU"] = sku
            row_copy["Original_Quantity"] = row["Quantity"]
            row_copy["Is_Set_Component"] = False
            expanded_rows.append(row_copy)

    logger.info(f"Decoded {sets_decoded_count} set orders into components")

    return pd.DataFrame(expanded_rows)


def import_sets_from_csv(csv_path: str) -> dict:
    """
    Import set definitions from CSV file.

    CSV Format:
        Set_SKU,Component_SKU,Component_Quantity
        SET-WINTER-KIT,SKU-HAT,1
        SET-WINTER-KIT,SKU-GLOVES,1
        SET-WINTER-KIT,SKU-SCARF,1
        SET-PICNIC-KIT,SKU-PLATE,4
        SET-PICNIC-KIT,SKU-FORK,4

    Args:
        csv_path: Path to CSV file

    Returns:
        dict: Set definitions in standard format

    Raises:
        ValueError: If CSV format is invalid
    """
    try:
        df = pd.read_csv(csv_path)

        # Validate columns
        required_cols = ["Set_SKU", "Component_SKU", "Component_Quantity"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        # Group by Set_SKU
        set_decoders = {}
        for set_sku, group in df.groupby("Set_SKU"):
            components = []
            for _, row in group.iterrows():
                components.append({
                    "sku": str(row["Component_SKU"]).strip(),
                    "quantity": int(row["Component_Quantity"])
                })
            set_decoders[str(set_sku).strip()] = components

        logger.info(f"Imported {len(set_decoders)} sets from CSV")
        return set_decoders

    except Exception as e:
        logger.error(f"Failed to import sets from CSV: {e}")
        raise ValueError(f"Invalid CSV format: {e}")


def export_sets_to_csv(set_decoders: dict, csv_path: str):
    """
    Export set definitions to CSV file.

    Args:
        set_decoders: Set definitions dict
        csv_path: Path to output CSV file
    """
    rows = []

    for set_sku, components in set_decoders.items():
        for component in components:
            rows.append({
                "Set_SKU": set_sku,
                "Component_SKU": component["sku"],
                "Component_Quantity": component["quantity"]
            })

    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False)
    logger.info(f"Exported {len(set_decoders)} sets to {csv_path}")
```

**Effort:** 4-5 hours

---

### 4.3 Settings UI

**File:** `gui/settings_window_pyside.py`

**Location:** After line 917 (after Mappings tab)

**Changes:**
```python
# Add to __init__ method after line 145
self.tab_widget.addTab(self._build_sets_tab(), "Sets")

# Add new method (around line 920)
def _build_sets_tab(self):
    """Build the Sets/Bundles management tab."""
    from PySide6.QtWidgets import (
        QTableWidget, QTableWidgetItem, QHeaderView,
        QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
        QFileDialog, QMessageBox
    )

    tab = QWidget()
    layout = QVBoxLayout(tab)

    # Header
    header_label = QLabel("Set/Bundle Definitions")
    header_label.setStyleSheet("font-size: 14px; font-weight: bold;")
    layout.addWidget(header_label)

    # Table for sets
    self.sets_table = QTableWidget()
    self.sets_table.setColumnCount(3)
    self.sets_table.setHorizontalHeaderLabels(["Set SKU", "Components", "Actions"])
    self.sets_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    self.sets_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    self.sets_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

    # Populate table
    self._populate_sets_table()

    layout.addWidget(self.sets_table)

    # Buttons
    button_layout = QHBoxLayout()

    add_btn = QPushButton("➕ Add Set")
    add_btn.clicked.connect(self._add_set_dialog)
    button_layout.addWidget(add_btn)

    import_btn = QPushButton("📁 Import from CSV")
    import_btn.clicked.connect(self._import_sets_from_csv)
    button_layout.addWidget(import_btn)

    export_btn = QPushButton("💾 Export to CSV")
    export_btn.clicked.connect(self._export_sets_to_csv)
    button_layout.addWidget(export_btn)

    button_layout.addStretch()
    layout.addLayout(button_layout)

    # Help text
    help_text = QLabel(
        "ℹ️ Sets allow you to define bundle SKUs that contain multiple components.\n"
        "Example: SET-WINTER-KIT = 1x SKU-HAT + 1x SKU-GLOVES + 1x SKU-SCARF"
    )
    help_text.setStyleSheet("color: #666; margin-top: 10px;")
    layout.addWidget(help_text)

    return tab

def _populate_sets_table(self):
    """Populate sets table with current configuration."""
    set_decoders = self.config_data.get("set_decoders", {})

    self.sets_table.setRowCount(len(set_decoders))

    for row_idx, (set_sku, components) in enumerate(set_decoders.items()):
        # Set SKU
        self.sets_table.setItem(row_idx, 0, QTableWidgetItem(set_sku))

        # Components summary
        comp_text = ", ".join([f"{c['sku']}({c['quantity']}x)" for c in components])
        self.sets_table.setItem(row_idx, 1, QTableWidgetItem(comp_text))

        # Actions buttons
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(4, 4, 4, 4)

        edit_btn = QPushButton("✏️ Edit")
        edit_btn.clicked.connect(lambda checked, sku=set_sku: self._edit_set_dialog(sku))
        actions_layout.addWidget(edit_btn)

        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(lambda checked, sku=set_sku: self._delete_set(sku))
        actions_layout.addWidget(delete_btn)

        self.sets_table.setCellWidget(row_idx, 2, actions_widget)

def _add_set_dialog(self):
    """Show dialog to add new set."""
    # TODO: Implement set editor dialog
    # For now, show simple input dialog
    from PySide6.QtWidgets import QInputDialog

    set_sku, ok = QInputDialog.getText(self, "Add Set", "Enter Set SKU:")
    if ok and set_sku:
        # TODO: Open component editor
        QMessageBox.information(self, "TODO", "Set editor dialog not yet implemented")

def _edit_set_dialog(self, set_sku):
    """Show dialog to edit existing set."""
    # TODO: Implement
    QMessageBox.information(self, "TODO", f"Edit set: {set_sku}")

def _delete_set(self, set_sku):
    """Delete a set definition."""
    reply = QMessageBox.question(
        self,
        "Delete Set",
        f"Are you sure you want to delete '{set_sku}'?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )

    if reply == QMessageBox.StandardButton.Yes:
        if "set_decoders" in self.config_data:
            self.config_data["set_decoders"].pop(set_sku, None)
            self._populate_sets_table()

def _import_sets_from_csv(self):
    """Import sets from CSV file."""
    from shopify_tool.set_decoder import import_sets_from_csv

    file_path, _ = QFileDialog.getOpenFileName(
        self,
        "Import Sets from CSV",
        "",
        "CSV Files (*.csv)"
    )

    if file_path:
        try:
            set_decoders = import_sets_from_csv(file_path)
            self.config_data["set_decoders"] = set_decoders
            self._populate_sets_table()
            QMessageBox.information(
                self,
                "Success",
                f"Imported {len(set_decoders)} sets from CSV"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import: {e}")

def _export_sets_to_csv(self):
    """Export sets to CSV file."""
    from shopify_tool.set_decoder import export_sets_to_csv

    file_path, _ = QFileDialog.getSaveFileName(
        self,
        "Export Sets to CSV",
        "sets_export.csv",
        "CSV Files (*.csv)"
    )

    if file_path:
        try:
            set_decoders = self.config_data.get("set_decoders", {})
            export_sets_to_csv(set_decoders, file_path)
            QMessageBox.information(self, "Success", f"Exported to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")
```

**Effort:** 5-6 hours (including component editor dialog)

---

### 4.4 Integration with Main Window

**File:** `gui/main_window_pyside.py`

**Changes:** Pass set_decoders to analysis

```python
# Find where run_analysis is called (likely in ui_manager.py or main_window.py)
# Modify to include set_decoders in column_mappings

column_mappings = {
    "orders": config.get("column_mappings", {}).get("orders", {}),
    "stock": config.get("column_mappings", {}).get("stock", {}),
    "set_decoders": config.get("set_decoders", {})  # 🆕 NEW
}

final_df, summary_present_df, summary_missing_df, stats = run_analysis(
    stock_df,
    orders_df,
    history_df,
    column_mappings=column_mappings
)
```

**Effort:** 1 hour

---

## 5. Implementation Plan

### Phase 1: Core Decoding Logic (6-8 hours)
1. Create `shopify_tool/set_decoder.py` ✅
2. Implement `decode_sets_in_orders()` function ✅
3. Add import/export CSV functions ✅
4. Write unit tests for decoding logic
5. Integrate with `analysis.py`

### Phase 2: Config Management (2-3 hours)
1. Add methods to `ProfileManager`:
   - `get_set_decoders()`
   - `save_set_decoders()`
   - `add_set()`
   - `delete_set()`
2. Write unit tests

### Phase 3: Settings UI (5-7 hours)
1. Add "Sets" tab to Settings window
2. Implement sets table view
3. Implement Add/Edit/Delete dialogs
4. Implement CSV import/export buttons
5. Add validation and error handling

### Phase 4: Testing & Polish (3-4 hours)
1. Integration tests with real data
2. Test edge cases:
   - Set with missing component in stock
   - Set with zero quantity component
   - Nested sets (set containing another set)
   - Orders with mix of sets and regular SKUs
3. UI polish and error messages
4. Documentation updates

### Total Effort: 16-22 hours

---

## 6. Questions for User / Decision Points

### 6.1 Set SKU Identification
**Question:** How should we identify which SKUs are sets?

**Options:**
- ✅ **Recommended:** Explicit list (check if SKU exists in `set_decoders`)
- ⚠️ Prefix pattern (e.g., all SKUs starting with "SET-")
- ⚠️ Regex pattern

**Decision Needed:** Confirm explicit list approach

---

### 6.2 Report Format
**Question:** How should sets be displayed in reports?

**Options:**
- **A) Expanded view:** Show set + indented components
  ```
  SET-WINTER-KIT (2x)
    └─ SKU-HAT (2x)
    └─ SKU-GLOVES (2x)
    └─ SKU-SCARF (2x) ✗ Missing
  ```
- **B) Collapsed view:** Show only set
  ```
  SET-WINTER-KIT (2x) - Not Fulfillable
  ```
- **C) Both:** Two sheets in Excel (Summary + Detailed)

**Decision Needed:** Preferred report format for warehouse

---

### 6.3 Partial Fulfillment
**Question:** What if only some components are available?

**Example:**
```
SET-WINTER-KIT needs:
  - SKU-HAT: ✓ Available
  - SKU-GLOVES: ✓ Available
  - SKU-SCARF: ✗ Missing
```

**Options:**
- **A) All-or-nothing:** Mark entire set as "Not Fulfillable"
- **B) Partial fulfillment:** Allow shipping partial set (with note)
- **C) Optional components:** Some components marked as optional in config

**Decision Needed:** Business rule for partial availability

---

### 6.4 Stock Reservation
**Question:** Should sets reserve component stock?

**Scenario:**
```
Stock:
  - SKU-HAT: 10
  - SKU-GLOVES: 10

Orders:
  - Order 1: SET-WINTER-KIT (needs 1x HAT, 1x GLOVES)
  - Order 2: SKU-HAT (needs 5x)
  - Order 3: SKU-GLOVES (needs 5x)
```

**Options:**
- **A) Priority-based:** Process in order priority (current behavior)
- **B) Reserve for sets:** Sets get first pick of component stock
- **C) Fair allocation:** Distribute evenly

**Decision Needed:** Stock allocation strategy

---

### 6.5 Import Source
**Question:** How will users provide set definitions?

**Options:**
- ✅ Manual entry in UI
- ✅ Import from CSV
- ⚠️ Import from Shopify API (fetch product variants)
- ⚠️ Import from Excel template

**Decision Needed:** Required import methods

---

### 6.6 Validation Rules
**Question:** What validation should we enforce?

**Current proposal:**
- ✅ Set SKU must be unique
- ✅ Set must have at least 1 component
- ✅ Component quantities must be positive integers
- ⚠️ Component SKUs must exist in stock? (or allow "future" components?)
- ⚠️ Prevent circular references? (Set A contains Set B, Set B contains Set A)

**Decision Needed:** Validation strictness level

---

## 7. Risks & Mitigation

### Risk 1: Performance with Large Orders
**Risk:** Expanding many sets could significantly increase DataFrame size

**Example:**
```
Before: 1000 orders with 100 sets (avg 5 components each)
After: 1000 - 100 + (100 * 5) = 1400 rows
Impact: +40% rows
```

**Mitigation:**
- ✅ Early testing with realistic data volumes
- ✅ Profile performance with 10k+ orders
- ⚠️ If needed: Add toggle to disable set expansion
- ⚠️ If needed: Optimize DataFrame operations (use vectorization)

**Severity:** Low (pandas handles 10k rows easily)

---

### Risk 2: Backward Compatibility
**Risk:** Existing sessions/reports might break

**Mitigation:**
- ✅ New columns (`Original_SKU`, `Is_Set_Component`) are optional
- ✅ If `set_decoders` is empty, system behaves exactly as before
- ✅ Existing configs auto-upgrade (field added if missing)
- ⚠️ Export format might change (need versioning?)

**Severity:** Low (additive changes only)

---

### Risk 3: User Error in Set Definitions
**Risk:** Users define invalid sets (wrong SKUs, wrong quantities)

**Example:**
```
SET-WINTER-KIT:
  - SKU-HAT (qty: 1)
  - SKU-GLOVESS (qty: 1)  ← Typo! SKU doesn't exist in stock
```

**Impact:** Orders marked as "Not Fulfillable" even though correct components available

**Mitigation:**
- ✅ UI validation: Warn if component SKU not in recent stock files
- ✅ Audit report: Show which set components were never matched
- ⚠️ Optional: Auto-suggest SKUs from stock file
- ⚠️ Test mode: Preview set expansion before saving

**Severity:** Medium

---

### Risk 4: Complex UI for Set Management
**Risk:** Managing sets with many components is tedious

**Mitigation:**
- ✅ CSV import/export for bulk editing
- ✅ Copy/paste functionality
- ⚠️ Templates for common set patterns
- ⚠️ Shopify integration (future)

**Severity:** Low (CSV import solves 90% of use cases)

---

## 8. Success Criteria

Implementation will be considered successful when:

✅ **Configuration:**
- [ ] Sets stored per client in `shopify_config.json`
- [ ] Sets persist across sessions
- [ ] Sets can be added/edited/deleted via UI
- [ ] Sets can be imported from CSV

✅ **Processing:**
- [ ] Orders with set SKUs automatically expanded to components
- [ ] Stock matching works correctly for expanded components
- [ ] Fulfillment simulation accounts for all components
- [ ] `Original_SKU` tracked for reporting

✅ **Reporting:**
- [ ] Reports clearly show which orders had sets
- [ ] Can identify which component is missing (if any)
- [ ] Warehouse can see both set and components
- [ ] Export formats compatible with existing tools

✅ **Quality:**
- [ ] Unit tests for set decoding logic (>90% coverage)
- [ ] Integration tests with real order/stock data
- [ ] Edge cases handled (empty sets, missing SKUs, etc.)
- [ ] Performance acceptable with 10k+ orders

✅ **Usability:**
- [ ] UI is intuitive (non-technical users can add sets)
- [ ] Clear error messages for invalid sets
- [ ] Help text explains how sets work
- [ ] CSV template provided

---

## 9. Estimated Effort Summary

| Phase | Task | Hours |
|-------|------|-------|
| **1** | Set Decoder Logic | 4-5 |
| **1** | Unit Tests | 2-3 |
| **2** | Config Management | 2-3 |
| **3** | Settings UI (Tab + Table) | 3-4 |
| **3** | Add/Edit Dialogs | 2-3 |
| **4** | Integration & Testing | 3-4 |
| **4** | Documentation | 1-2 |
| | **Total** | **17-24 hours** |

**Note:** Assumes developer familiar with codebase. First-time contributor may need +50% time.

---

## 10. Alternatives Considered

### Alternative 1: Manual CSV Preprocessing
**Idea:** Users manually expand sets in Excel before importing orders

**Pros:**
- ✅ No code changes needed
- ✅ Users have full control

**Cons:**
- ❌ Error-prone (manual copy-paste)
- ❌ Not scalable (10+ sets = too tedious)
- ❌ Can't update sets retroactively
- ❌ No audit trail

**Verdict:** ❌ Rejected (too manual)

---

### Alternative 2: Post-Processing Script
**Idea:** Separate script that expands sets after analysis

**Pros:**
- ✅ Minimal changes to core analysis

**Cons:**
- ❌ Two-step process (confusing)
- ❌ Stock calculations wrong (happens before expansion)
- ❌ Doesn't solve root problem

**Verdict:** ❌ Rejected (doesn't work)

---

### Alternative 3: Virtual Sets (No Expansion)
**Idea:** Keep sets as single rows, calculate stock on-the-fly

**Pros:**
- ✅ Smaller DataFrames
- ✅ Original SKU preserved

**Cons:**
- ❌ Complex fulfillment logic (must handle sets specially)
- ❌ Stock matching becomes complex
- ❌ Reporting becomes complex
- ❌ Hard to debug

**Verdict:** ❌ Rejected (too complex)

---

## 11. Next Steps

### Immediate Actions
1. **Get user approval** on architecture decisions (Sections 6.1-6.6)
2. **Confirm report format** preference (Section 6.2)
3. **Provide sample data** (orders with sets, stock with components)

### After Approval
1. Create feature branch: `feature/sets-decoding-system`
2. Implement Phase 1 (core decoding logic)
3. Write unit tests
4. Test with real data
5. Implement Phase 2 (config management)
6. Implement Phase 3 (UI)
7. Integration testing
8. Documentation
9. Pull request review

### Testing Checklist
- [ ] Simple set (3 components, all in stock)
- [ ] Set with missing component
- [ ] Set with insufficient stock for one component
- [ ] Multiple sets in same order
- [ ] Mix of sets and regular SKUs
- [ ] Set quantity > 1 (e.g., 3x SET-WINTER-KIT)
- [ ] Large order (100+ line items, 50+ sets)
- [ ] Empty set_decoders (backward compatibility)
- [ ] Invalid set definition (missing SKU, negative quantity)
- [ ] CSV import with 20+ sets

---

## Appendix A: Example Files

See companion files:
- `sets_config_example.json` - Example set definitions
- `sets_import_template.csv` - CSV template for bulk import
- `mock_ui_sets_tab.txt` - UI mockup

---

## Appendix B: Technical Glossary

**Set/Bundle:** A virtual SKU representing multiple component SKUs
**Component:** Individual SKU that is part of a set
**Set Decoder:** Configuration defining which components make up a set
**Expansion:** Process of converting set row to multiple component rows
**Early Expansion:** Decoding sets immediately after data cleaning
**Late Expansion:** Decoding sets during fulfillment simulation
**Original_SKU:** Column tracking the original set SKU after expansion

---

**End of Audit Report**

For questions or clarifications, please contact the development team.
