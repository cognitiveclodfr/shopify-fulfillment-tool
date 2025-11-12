# Column Mapping Audit Report

**Date:** 2025-11-12
**Repository:** cognitiveclodfr/shopify-fulfillment-tool
**Version:** 1.7
**Status:** 🔴 CRITICAL ISSUES FOUND

---

## Executive Summary

The current column mapping implementation has **critical design flaws** that prevent it from working as intended. While there is UI for configuring column mappings and validation logic to check for required columns, **the actual analysis code completely ignores these mappings and uses hardcoded column names**.

### Critical Finding

**The column mapping configuration in `shopify_config.json` is only used for validation, NOT for actual data processing. The analysis engine (`analysis.py`) has hardcoded column names that cannot be changed without modifying the source code.**

---

## 1. Current Implementation

### 1.1 Configuration Storage

**Location:** `\\server\share\0UFulfilment\Clients\CLIENT_{ID}\shopify_config.json`

**Module:** `shopify_tool/profile_manager.py:305-362`

**Structure:**
```json
{
  "client_id": "CLIENT_ID",
  "client_name": "Client Name",
  "created_at": "2025-11-12T10:00:00",

  "column_mappings": {
    "orders_required": [
      "Order_Number",
      "SKU",
      "Product_Name",
      "Quantity",
      "Shipping_Method"
    ],
    "stock_required": [
      "SKU",
      "Product_Name",
      "Available_Stock"
    ]
  }
}
```

**Features:**
- ✅ Stored on centralized file server for multi-PC access
- ✅ Per-client customization supported
- ✅ 60-second caching to reduce network round-trips
- ✅ Automatic backups (last 10 versions)
- ✅ File locking to prevent concurrent modification

---

### 1.2 File Loading and Validation

**Module:** `shopify_tool/core.py`

#### Pre-Load Validation (Quick Header Check)
**Function:** `validate_csv_headers()` (lines 128-166)
**Location:** Called from `gui/file_handler.py:127`

```python
def validate_csv_headers(file_path, required_columns, delimiter=","):
    """Validates CSV file contains required column headers."""
    headers = pd.read_csv(file_path, nrows=0, delimiter=delimiter).columns.tolist()
    missing_columns = [col for col in required_columns if col not in headers]

    if not missing_columns:
        return True, []
    else:
        return False, missing_columns
```

**UI Feedback:**
- ✓ Green checkmark if valid
- ✗ Red X with tooltip showing missing columns if invalid

#### Post-Load Validation (DataFrame Check)
**Function:** `_validate_dataframes()` (lines 95-125)
**Location:** Called from `core.run_full_analysis():157-161`

```python
def _validate_dataframes(orders_df, stock_df, config):
    """Validates that required columns are present in the dataframes."""
    errors = []
    column_mappings = config.get("column_mappings", {})
    required_orders_cols = column_mappings.get("orders_required", [])
    required_stock_cols = column_mappings.get("stock_required", [])

    for col in required_orders_cols:
        if col not in orders_df.columns:
            errors.append(f"Missing required column in Orders file: '{col}'")

    for col in required_stock_cols:
        if col not in stock_df.columns:
            errors.append(f"Missing required column in Stock file: '{col}'")

    return errors
```

---

### 1.3 UI for Mapping Configuration

**Module:** `gui/settings_window_pyside.py:804-913`

**Tab:** "Mappings"

#### UI Components

**Orders Required Columns** (lines 829-846):
```python
self.orders_required_text = QTextEdit()
self.orders_required_text.setPlaceholderText("Name\nLineitem sku\nLineitem quantity\nShipping Method")

# Load existing values
orders_required = self.config_data.get("column_mappings", {}).get("orders_required", [])
if orders_required:
    self.orders_required_text.setPlainText("\n".join(orders_required))
```

**Stock Required Columns** (lines 848-864):
```python
self.stock_required_text = QTextEdit()
self.stock_required_text.setPlaceholderText("Артикул\nНаличност")

# Load existing values
stock_required = self.config_data.get("column_mappings", {}).get("stock_required", [])
if stock_required:
    self.stock_required_text.setPlainText("\n".join(stock_required))
```

**Save Logic** (lines 1118-1143):
```python
def save_settings(self):
    # Parse orders required columns (one per line)
    orders_text = self.orders_required_text.toPlainText().strip()
    if orders_text:
        orders_columns = [line.strip() for line in orders_text.split('\n') if line.strip()]
        self.config_data["column_mappings"]["orders_required"] = orders_columns

    # Parse stock required columns (one per line)
    stock_text = self.stock_required_text.toPlainText().strip()
    if stock_text:
        stock_columns = [line.strip() for line in stock_text.split('\n') if line.strip()]
        self.config_data["column_mappings"]["stock_required"] = stock_columns
```

**Features:**
- ✅ User-friendly text area interface
- ✅ One column name per line
- ✅ Saves to server via ProfileManager
- ✅ Immediate feedback on save success/failure

---

### 1.4 Analysis Engine (THE PROBLEM)

**Module:** `shopify_tool/analysis.py:34-206`
**Function:** `run_analysis()`

#### 🔴 CRITICAL ISSUE: Hardcoded Column Names

**Lines 78-106 in analysis.py:**

```python
def run_analysis(stock_df, orders_df, history_df):
    # --- Data Cleaning ---
    orders_df["Name"] = orders_df["Name"].ffill()
    orders_df["Shipping Method"] = orders_df["Shipping Method"].ffill()
    orders_df["Shipping Country"] = orders_df["Shipping Country"].ffill()
    if "Total" in orders_df.columns:
        orders_df["Total"] = orders_df["Total"].ffill()

    columns_to_keep = [
        "Name",                # ← HARDCODED
        "Lineitem sku",        # ← HARDCODED
        "Lineitem quantity",   # ← HARDCODED
        "Shipping Method",     # ← HARDCODED
        "Shipping Country",    # ← HARDCODED
        "Tags",
        "Notes",
        "Total",
    ]

    # Filter for existing columns only
    columns_to_keep_existing = [col for col in columns_to_keep if col in orders_df.columns]
    orders_clean_df = orders_df[columns_to_keep_existing].copy()

    # Rename to internal standard names
    rename_map = {
        "Name": "Order_Number",           # ← HARDCODED
        "Lineitem sku": "SKU",            # ← HARDCODED
        "Lineitem quantity": "Quantity"   # ← HARDCODED
    }
    if "Total" in orders_clean_df.columns:
        rename_map["Total"] = "Total Price"

    orders_clean_df = orders_clean_df.rename(columns=rename_map)
    orders_clean_df = orders_clean_df.dropna(subset=["SKU"])

    # Stock DataFrame - HARDCODED CYRILLIC COLUMN NAMES
    stock_clean_df = stock_df[["Артикул", "Име", "Наличност"]].copy()  # ← HARDCODED
    stock_clean_df = stock_clean_df.rename(columns={
        "Артикул": "SKU",           # ← HARDCODED
        "Име": "Product_Name",      # ← HARDCODED
        "Наличност": "Stock"        # ← HARDCODED
    })
    stock_clean_df = stock_clean_df.dropna(subset=["SKU"])
    stock_clean_df = stock_clean_df.drop_duplicates(subset=["SKU"], keep="first")
```

**What This Means:**

❌ The analysis engine ONLY works with these specific column names:
- **Orders:** `Name`, `Lineitem sku`, `Lineitem quantity`, `Shipping Method`
- **Stock:** `Артикул`, `Име`, `Наличност`

❌ Even if you configure different column names in Settings, the analysis will **fail** because it can't find the hardcoded column names

❌ The `column_mappings` configuration is **completely ignored** during analysis

---

## 2. Required and Optional Columns

### 2.1 Orders Export

#### Required Columns (For Analysis to Work)

| Column Name (CSV) | Internal Name | Description | Used For |
|-------------------|---------------|-------------|----------|
| `Name` | `Order_Number` | Order identifier | Grouping line items, tracking fulfillment |
| `Lineitem sku` | `SKU` | Product SKU | Stock matching, fulfillment check |
| `Lineitem quantity` | `Quantity` | Quantity ordered | Stock deduction calculation |
| `Shipping Method` | `Shipping_Provider` | Shipping carrier/method | Courier mapping, report filtering |

**Note:** These column names are HARDCODED in `analysis.py:84-98` and cannot be changed without code modification.

#### Optional Columns (Used if Present)

| Column Name (CSV) | Internal Name | Description | Used For |
|-------------------|---------------|-------------|----------|
| `Shipping Country` | `Destination_Country` | Destination country | International filtering |
| `Tags` | `Tags` | Order tags from Shopify | Rule conditions, filtering |
| `Notes` | `Notes` | Order notes | Rule conditions |
| `Total` | `Total Price` | Order total amount | Rule conditions (e.g., high-value orders) |

**Note:** These are handled gracefully - analysis continues if missing, but functionality is limited.

---

### 2.2 Stock Export

#### Required Columns (For Analysis to Work)

| Column Name (CSV) | Internal Name | Description | Used For |
|-------------------|---------------|-------------|----------|
| `Артикул` | `SKU` | Product SKU (Cyrillic) | Matching with orders |
| `Име` | `Product_Name` | Product name (Cyrillic) | Display in reports |
| `Наличност` | `Stock` | Available quantity (Cyrillic) | Fulfillment simulation |

**Note:** These Cyrillic column names are HARDCODED in `analysis.py:104` and cannot be changed.

#### Optional Columns

None defined in current implementation.

---

### 2.3 Default Configuration vs Reality

#### What `shopify_config.json` Says (Default):

```json
"column_mappings": {
  "orders_required": [
    "Order_Number",     // ← WRONG! Should be "Name"
    "SKU",              // ← WRONG! Should be "Lineitem sku"
    "Product_Name",     // ← NOT EVEN USED in orders!
    "Quantity",         // ← WRONG! Should be "Lineitem quantity"
    "Shipping_Method"   // ← WRONG! Should be "Shipping Method"
  ],
  "stock_required": [
    "SKU",              // ← WRONG! Should be "Артикул"
    "Product_Name",     // ← WRONG! Should be "Име"
    "Available_Stock"   // ← WRONG! Should be "Наличност"
  ]
}
```

#### What Actually Works:

**Orders CSV must have:**
- `Name` (not `Order_Number`)
- `Lineitem sku` (not `SKU`)
- `Lineitem quantity` (not `Quantity`)
- `Shipping Method` (not `Shipping_Method`)

**Stock CSV must have:**
- `Артикул` (not `SKU`)
- `Име` (not `Product_Name`)
- `Наличност` (not `Available_Stock`)

---

## 3. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: User Selects Client                                 │
│  ↓                                                            │
│  Load shopify_config.json from server                        │
│  (Includes column_mappings configuration)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: User Selects CSV Files                              │
│  - Orders CSV (from Shopify export)                          │
│  - Stock CSV (from warehouse system)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Pre-Load Validation (file_handler.py:91-139)       │
│                                                               │
│  ✓ Uses column_mappings from config                          │
│  ✓ Reads only CSV headers (fast)                             │
│  ✓ Checks if required columns exist                          │
│  ✓ Shows ✓ or ✗ in UI                                        │
│                                                               │
│  🔴 PROBLEM: Validates wrong column names!                   │
│     Config says check for "Order_Number"                     │
│     but CSV has "Name" and analysis needs "Name"             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: User Clicks "Run Analysis"                          │
│  ↓                                                            │
│  core.run_full_analysis() (core.py:169)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Load CSV Files into DataFrames                      │
│  - orders_df = pd.read_csv(orders_file)                      │
│  - stock_df = pd.read_csv(stock_file, delimiter=";")         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 6: Post-Load Validation (core.py:95-125)              │
│                                                               │
│  ✓ Uses column_mappings from config                          │
│  ✓ Checks if required columns exist in DataFrames            │
│                                                               │
│  🔴 PROBLEM: Validates wrong column names again!             │
│     Will pass validation if CSV has "Order_Number"           │
│     but analysis will fail because it needs "Name"           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 7: Run Analysis (analysis.py:34)                       │
│                                                               │
│  ❌ HARDCODED COLUMN NAMES                                   │
│  ❌ Tries to access orders_df["Name"]                        │
│  ❌ Tries to access orders_df["Lineitem sku"]               │
│  ❌ Tries to access stock_df["Артикул"]                      │
│                                                               │
│  🔴 CRITICAL: If CSV doesn't have EXACT column names,        │
│               analysis crashes with KeyError!                 │
│                                                               │
│  ⚠️  column_mappings configuration is NEVER used here       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 8: Generate Reports                                    │
│  - Excel file with analysis results                          │
│  - Packing lists (if configured)                             │
│  - Stock exports (if configured)                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Issues Found

### 🔴 Issue #1: Column Mappings Not Used in Analysis Engine

**Severity:** CRITICAL
**Impact:** Makes the entire column mapping system non-functional

**Problem:**
The `analysis.py` module has hardcoded column names and completely ignores the `column_mappings` configuration from `shopify_config.json`.

**Evidence:**
- `analysis.py:78-106` directly references hardcoded column names
- No code path exists to pass column mappings to `run_analysis()`
- `core.run_full_analysis()` loads config but never passes mappings to analysis

**Example Failure Scenario:**
1. User configures mappings in Settings: `Order ID`, `Product SKU`, `Qty`
2. User's CSV has these exact column names
3. Validation passes (checks for configured names)
4. Analysis crashes with KeyError: `'Name'` not found

**Code Location:**
- `shopify_tool/analysis.py:78-106`

---

### 🔴 Issue #2: Default Configuration Contains Wrong Column Names

**Severity:** CRITICAL
**Impact:** Validation checks for wrong columns, users get false positives/negatives

**Problem:**
The default `column_mappings` in `profile_manager.py:320-332` specifies internal standardized column names (e.g., `Order_Number`, `SKU`) instead of actual CSV column names (e.g., `Name`, `Lineitem sku`).

**What's Wrong:**

Default config says:
```json
"orders_required": ["Order_Number", "SKU", "Product_Name", "Quantity", "Shipping_Method"]
```

But Shopify CSV exports have:
```json
["Name", "Lineitem sku", "Lineitem name", "Lineitem quantity", "Shipping Method"]
```

And analysis expects:
```python
["Name", "Lineitem sku", "Lineitem quantity", "Shipping Method"]
```

**Result:** Validation fails for valid Shopify exports!

**Code Location:**
- `shopify_tool/profile_manager.py:320-332`

---

### 🔴 Issue #3: Validation Without Mapping is Useless

**Severity:** HIGH
**Impact:** Confuses users, provides false sense of security

**Problem:**
The validation logic checks if CSV has required columns from config, but since analysis uses different hardcoded names, passing validation doesn't guarantee analysis will work.

**Scenario:**
```
CSV has:        ["Name", "Lineitem sku", "Lineitem quantity"]
Config checks:  ["Order_Number", "SKU", "Quantity"]
Validation:     ✗ FAIL (missing Order_Number, SKU, Quantity)
Analysis needs: ["Name", "Lineitem sku", "Lineitem quantity"]
Analysis would: ✓ WORK (all columns present)

User sees: ✗ Red X (file invalid)
Reality: File would work perfectly!
```

**Code Location:**
- `shopify_tool/core.py:128-166` (validate_csv_headers)
- `shopify_tool/core.py:95-125` (_validate_dataframes)

---

### 🔴 Issue #4: Hardcoded Cyrillic Column Names

**Severity:** CRITICAL
**Impact:** Only works with Bulgarian stock exports, cannot support other languages

**Problem:**
Stock analysis is hardcoded to expect Cyrillic column names: `Артикул`, `Име`, `Наличност`.

**Why This is Bad:**
- Cannot load stock exports from other countries/languages
- Cannot load stock exports from Shopify (which uses English)
- User's stated goal: "load exports not only from Shopify (different sources = different column names)"

**Code Location:**
- `shopify_tool/analysis.py:104`

---

### ⚠️ Issue #5: No UI Guidance on Actual Column Names

**Severity:** MEDIUM
**Impact:** Users don't know what column names to use

**Problem:**
The Settings UI shows placeholders like "Name\nLineitem sku" but doesn't explain:
- These are the ACTUAL column names from your CSV
- These are NOT the internal names used in the app
- Changing these only affects validation, not analysis

**User Experience:**
1. User sees default: `Order_Number`, `SKU`, `Quantity`
2. User's Shopify export has: `Name`, `Lineitem sku`, `Lineitem quantity`
3. User changes config to match their CSV
4. Validation now passes ✓
5. Analysis crashes 💥

**Code Location:**
- `gui/settings_window_pyside.py:821-827`

---

### ⚠️ Issue #6: Inconsistent Column Naming Throughout App

**Severity:** MEDIUM
**Impact:** Code confusion, maintenance difficulty

**Problem:**
Three different naming schemes coexist:
1. **CSV column names:** `Name`, `Lineitem sku`, `Артикул`
2. **Internal standardized names:** `Order_Number`, `SKU`, `Stock`
3. **Config validation names:** Mix of both (currently wrong)

**Examples:**

| Concept | CSV Name | Internal Name | Config (Wrong) |
|---------|----------|---------------|----------------|
| Order ID | `Name` | `Order_Number` | `Order_Number` |
| Product SKU | `Lineitem sku` | `SKU` | `SKU` |
| Stock SKU | `Артикул` | `SKU` | `SKU` |
| Quantity | `Lineitem quantity` | `Quantity` | `Quantity` |

---

### ⚠️ Issue #7: Column Mapping Saved But Never Read

**Severity:** LOW
**Impact:** Wasted effort, storage, and user time

**Problem:**
Users can spend time configuring column mappings in the Settings UI, which get saved to the server, but the saved mappings are never actually used for anything meaningful (only for validation which is broken anyway).

**Code Location:**
- `gui/settings_window_pyside.py:1118-1143` (saves config)
- No code reads these mappings for actual data transformation

---

## 5. Why This Design Exists

Based on code analysis, it appears the system was originally designed for:

1. **Single data source:** Bulgarian warehouse stock system (Cyrillic columns)
2. **Standard Shopify exports:** Always same English column names
3. **Fixed workflow:** Orders from Shopify, stock from warehouse

The `column_mappings` feature was likely added later to support client customization, but **the core analysis engine was never updated to actually use these mappings**.

---

## 6. How It Should Work (Design Intent)

### Intended Flow:

```
1. User configures column mappings:
   CSV Column Name → Internal Standard Name

   Example:
   "Order ID" → "Order_Number"
   "Item SKU" → "SKU"
   "Qty" → "Quantity"

2. Analysis engine receives mappings

3. Analysis engine dynamically renames columns:
   df.rename(columns=mappings, inplace=True)

4. Rest of analysis uses internal standard names

5. Reports use internal standard names
```

### Reality:

```
1. User configures column mappings ✓
2. Mappings saved to server ✓
3. Mappings used for validation ✓
4. Analysis engine ignores mappings ✗
5. Analysis crashes if columns don't match hardcoded names ✗
```

---

## 7. Impact on Stated Goals

From the issue description:

> "Планується завантажувати експорти не тільки від Shopify (різні джерела = різні назви колонок)"
>
> Translation: "It is planned to load exports not only from Shopify (different sources = different column names)"

**Current System Cannot Support This Goal** ❌

Why:
- Analysis engine only works with hardcoded Shopify column names
- Stock analysis only works with hardcoded Cyrillic columns
- No mechanism exists to map different column names to internal standard
- Even if you configure mappings, analysis ignores them

**To Support Multiple Data Sources, You Need:**
1. ✅ Configuration storage (already exists)
2. ✅ UI for mapping configuration (already exists)
3. ❌ Analysis engine that uses mappings (MISSING)
4. ❌ Dynamic column renaming based on mappings (MISSING)
5. ❌ Validation that checks actual CSV column names (currently broken)

---

## 8. Recommendations

### Priority 1: Fix Analysis Engine (CRITICAL)

**Task:** Refactor `analysis.py` to accept and use column mappings

**Changes Needed:**

1. **Update function signature:**
```python
def run_analysis(stock_df, orders_df, history_df, column_mappings):
    # Accept column_mappings parameter
```

2. **Add dynamic column mapping:**
```python
def run_analysis(stock_df, orders_df, history_df, column_mappings):
    # Get mappings
    orders_mappings = column_mappings.get("orders", {})
    stock_mappings = column_mappings.get("stock", {})

    # Rename columns to internal standard
    orders_df = orders_df.rename(columns=orders_mappings)
    stock_df = stock_df.rename(columns=stock_mappings)

    # Now use internal standard names
    orders_df["Order_Number"] = orders_df["Order_Number"].ffill()
    # ... rest of analysis
```

3. **Update core.py to pass mappings:**
```python
def run_full_analysis(..., config):
    column_mappings = config.get("column_mappings", {})

    final_df, summary_present, summary_missing, stats = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings
    )
```

**Effort:** ~4-6 hours
**Risk:** Medium (requires testing all analysis logic)

---

### Priority 2: Fix Configuration Structure (CRITICAL)

**Task:** Change `column_mappings` from validation list to mapping dictionary

**Current Structure (WRONG):**
```json
"column_mappings": {
  "orders_required": ["Order_Number", "SKU", "Quantity"],
  "stock_required": ["SKU", "Product_Name", "Available_Stock"]
}
```

**New Structure (CORRECT):**
```json
"column_mappings": {
  "orders": {
    "Name": "Order_Number",
    "Lineitem sku": "SKU",
    "Lineitem quantity": "Quantity",
    "Shipping Method": "Shipping_Method",
    "Lineitem name": "Product_Name"
  },
  "stock": {
    "Артикул": "SKU",
    "Име": "Product_Name",
    "Наличност": "Stock"
  }
}
```

**Benefits:**
- Clear mapping: CSV column → Internal name
- Supports any column names
- Easy to validate (check if CSV has keys)
- Easy to apply (df.rename(columns=mappings))

**Effort:** ~6-8 hours (includes UI changes)
**Risk:** Medium (requires config migration)

---

### Priority 3: Update Settings UI (HIGH)

**Task:** Redesign Mappings tab for clarity

**New UI Design:**

```
┌─ Orders CSV Column Mappings ───────────────────────────┐
│                                                         │
│  Map your CSV column names to internal standard names  │
│                                                         │
│  CSV Column Name          →  Internal Name             │
│  ┌─────────────────────┐     ┌──────────────────┐    │
│  │ Name                │  →  │ Order_Number     │    │
│  └─────────────────────┘     └──────────────────┘    │
│  ┌─────────────────────┐     ┌──────────────────┐    │
│  │ Lineitem sku        │  →  │ SKU              │    │
│  └─────────────────────┘     └──────────────────┘    │
│  ┌─────────────────────┐     ┌──────────────────┐    │
│  │ Lineitem quantity   │  →  │ Quantity         │    │
│  └─────────────────────┘     └──────────────────┘    │
│                                                         │
│  [+ Add Mapping]                                       │
│                                                         │
│  ⓘ Left side: Column name from your CSV file          │
│     Right side: Internal name (do not change)          │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- Clear left → right mapping
- Internal names in dropdown (fixed list)
- CSV names as text input (user defines)
- Add/remove mappings dynamically
- Validation: ensure all required internal names are mapped

**Effort:** ~4-6 hours
**Risk:** Low (UI only)

---

### Priority 4: Add Auto-Detection (NICE TO HAVE)

**Task:** Auto-detect column mappings from CSV

**Algorithm:**
```python
def auto_detect_mappings(csv_headers, internal_standard):
    mappings = {}

    for internal_name, patterns in COLUMN_PATTERNS.items():
        for csv_header in csv_headers:
            if any(pattern in csv_header.lower() for pattern in patterns):
                mappings[csv_header] = internal_name
                break

    return mappings

COLUMN_PATTERNS = {
    "Order_Number": ["order", "name", "#"],
    "SKU": ["sku", "артикул", "item", "product"],
    "Quantity": ["quantity", "qty", "quan", "наличност"],
    "Shipping_Method": ["shipping", "courier", "carrier", "method"],
}
```

**Benefits:**
- Better user experience
- Reduces configuration errors
- Supports common variations

**Effort:** ~2-3 hours
**Risk:** Low

---

## 9. Technical Debt

| Issue | Location | Lines of Code | Complexity |
|-------|----------|---------------|------------|
| Hardcoded column names | `analysis.py` | ~30 | Medium |
| Wrong default config | `profile_manager.py` | ~15 | Low |
| Validation logic | `core.py` | ~40 | Medium |
| UI for mappings | `settings_window_pyside.py` | ~100 | High |
| **Total** | **4 files** | **~185** | **Medium-High** |

---

## 10. Testing Requirements

After implementing fixes, test these scenarios:

### Test Case 1: Standard Shopify Export
- ✓ Load Shopify orders CSV (English columns)
- ✓ Load warehouse stock CSV (Cyrillic columns)
- ✓ Run analysis
- ✓ Verify results correct

### Test Case 2: Custom Column Names
- ✓ Configure mappings: `Order ID → Order_Number`, `Item SKU → SKU`
- ✓ Load CSV with custom column names
- ✓ Run analysis
- ✓ Verify results correct

### Test Case 3: Different Stock Source
- ✓ Configure stock mappings: `SKU → SKU`, `QTY → Stock`
- ✓ Load English stock CSV
- ✓ Run analysis
- ✓ Verify results correct

### Test Case 4: Missing Optional Columns
- ✓ Load CSV without `Total`, `Tags`, `Notes`
- ✓ Verify analysis completes (no crash)
- ✓ Verify optional features disabled gracefully

### Test Case 5: Validation
- ✓ Load CSV missing required column
- ✓ Verify validation fails with clear error
- ✓ Verify error message shows correct missing column name (CSV name, not internal name)

---

## 11. Migration Plan

If implementing new column mapping structure:

### Phase 1: Detection
```python
def detect_config_version(config):
    if "orders_required" in config.get("column_mappings", {}):
        return "v1"  # Old structure
    elif "orders" in config.get("column_mappings", {}):
        return "v2"  # New structure
    else:
        return "unknown"
```

### Phase 2: Migration
```python
def migrate_column_mappings_v1_to_v2(old_config):
    """Migrate from list-based to dict-based mappings."""

    # Default Shopify mappings
    SHOPIFY_DEFAULTS = {
        "Name": "Order_Number",
        "Lineitem sku": "SKU",
        "Lineitem quantity": "Quantity",
        "Shipping Method": "Shipping_Method",
        "Lineitem name": "Product_Name"
    }

    STOCK_DEFAULTS = {
        "Артикул": "SKU",
        "Име": "Product_Name",
        "Наличност": "Stock"
    }

    new_config = old_config.copy()
    new_config["column_mappings"] = {
        "orders": SHOPIFY_DEFAULTS,
        "stock": STOCK_DEFAULTS,
        "version": 2
    }

    return new_config
```

### Phase 3: Deployment
1. Update profile_manager.py to run migration on config load
2. Save migrated config back to server
3. Create backup before migration
4. Log migration success/failure

---

## 12. Conclusion

The current column mapping implementation is **fundamentally broken**. While the infrastructure exists (storage, UI, validation), the core analysis engine completely ignores the configured mappings and uses hardcoded column names.

**This must be fixed before the system can support multiple data sources.**

### Estimated Total Effort
- Priority 1 (Analysis Engine): 4-6 hours
- Priority 2 (Config Structure): 6-8 hours
- Priority 3 (Settings UI): 4-6 hours
- Testing: 3-4 hours
- **Total: 17-24 hours** (~3 working days)

### Risk Assessment
- **Technical Risk:** Medium (requires careful refactoring)
- **Breaking Changes:** Yes (config format changes)
- **Migration Complexity:** Medium (can be automated)
- **Testing Required:** High (affects core functionality)

---

**Auditor:** Claude (AI Assistant)
**Date:** 2025-11-12
**Version:** 1.0
