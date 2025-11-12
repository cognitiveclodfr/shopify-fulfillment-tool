# Folder Loading Audit Report

**Date:** 2025-11-12
**Purpose:** Analyze current file loading system to add folder/multiple files support
**Repository:** cognitiveclodfr/shopify-fulfillment-tool

---

## 1. Current Architecture

### 1.1 UI Components

**Location:** `gui/main_window_pyside.py`

**File Selection Buttons:**
- **Orders:** Created in `UIManager.create_widgets()`, connected to `file_handler.select_orders_file()`
- **Stock:** Created in `UIManager.create_widgets()`, connected to `file_handler.select_stock_file()`
- **Type:** Single file only (uses `QFileDialog.getOpenFileName()`)

**Display Elements:**
```python
# File path labels - show filename only
self.orders_file_path_label  # Shows: os.path.basename(filepath)
self.stock_file_path_label   # Shows: os.path.basename(filepath)

# Status indicators
self.orders_file_status_label  # Shows: "✓" (green) or "✗" (red)
self.stock_file_status_label   # Shows: "✓" (green) or "✗" (red)
```

**Storage:**
```python
# MainWindow attributes (lines 67-68)
self.orders_file_path = None  # Single str path
self.stock_file_path = None   # Single str path
```

**Layout:**
- File selection section in left panel
- Each file type has: [Button] [Filename Label] [Status ✓/✗]
- No multi-file or folder selection UI elements

---

### 1.2 FileHandler Class

**File:** `gui/file_handler.py`

**Class Structure:**
```python
class FileHandler:
    def __init__(self, main_window):
        self.mw = main_window
        self.log = logging.getLogger(__name__)

    def select_orders_file(self):
        # Line 40: QFileDialog for SINGLE file
        filepath, _ = QFileDialog.getOpenFileName(
            self.mw,
            "Select Orders File",
            "",
            "CSV files (*.csv)"
        )
        # Returns: ONE file path

    def select_stock_file(self):
        # Line 110: QFileDialog for SINGLE file
        filepath, _ = QFileDialog.getOpenFileName(
            self.mw,
            "Select Stock File",
            "",
            "CSV files (*.csv);;All Files (*)"
        )
        # Returns: ONE file path
```

**Workflow for `select_orders_file()` (lines 32-101):**
1. **File Dialog:** Opens `QFileDialog.getOpenFileName()` → returns single filepath
2. **Store Path:** `self.mw.orders_file_path = filepath`
3. **Update UI:** `orders_file_path_label.setText(os.path.basename(filepath))`
4. **Auto-detect Delimiter:**
   - Calls `detect_csv_delimiter(filepath)` from `csv_utils.py`
   - Prompts user if detected differs from config
   - Offers to save new delimiter to config
5. **Validation:** Calls `validate_file("orders")`
6. **Ready Check:** Calls `check_files_ready()` to enable "Run Analysis" button

**Workflow for `select_stock_file()` (lines 103-201):**
- Similar to orders, but also **loads the CSV** to verify readability (line 185)
- Forces SKU columns to `str` dtype to prevent float conversion
- More robust error handling with QMessageBox

**Method: `validate_file(file_type)` (lines 203-278):**
```python
def validate_file(self, file_type):
    # Gets required columns from client config
    # Calls core.validate_csv_headers(path, required_cols, delimiter)
    # Updates status label: "✓" or "✗"
    # Sets tooltip with missing columns if invalid
```

**Method: `check_files_ready()` (lines 280-293):**
```python
def check_files_ready(self):
    orders_ok = self.mw.orders_file_path and self.mw.orders_file_status_label.text() == "✓"
    stock_ok = self.mw.stock_file_path and self.mw.stock_file_status_label.text() == "✓"
    if orders_ok and stock_ok:
        self.mw.run_analysis_button.setEnabled(True)
```

**Key Constraint:** All methods designed for SINGLE file path (str), not list of paths.

---

### 1.3 Core Analysis

**File:** `shopify_tool/core.py`

**Function Signature (lines 238-249):**
```python
def run_full_analysis(
    stock_file_path,      # Single file (str)
    orders_file_path,     # Single file (str)
    output_dir_path,
    stock_delimiter,
    orders_delimiter,
    config,
    client_id: Optional[str] = None,
    session_manager: Optional[Any] = None,
    profile_manager: Optional[Any] = None,
    session_path: Optional[str] = None
):
```

**Parameters:**
- `stock_file_path` (str): Path to **ONE** stock CSV file
- `orders_file_path` (str): Path to **ONE** orders CSV file
- **Does NOT accept:** `List[str]`, folder paths, or multiple files

**CSV Loading (lines 357-404):**
```python
# Line 359-360: Normalize UNC paths
stock_file_path = _normalize_unc_path(stock_file_path)
orders_file_path = _normalize_unc_path(orders_file_path)

# Line 362-363: Check file existence
if not os.path.exists(stock_file_path) or not os.path.exists(orders_file_path):
    return False, "One or both input files were not found.", None, None

# Line 367-368: Get dtype specs for SKU columns
stock_dtype = _get_sku_dtype_dict(column_mappings, "stock")
orders_dtype = _get_sku_dtype_dict(column_mappings, "orders")

# Line 373: Load SINGLE stock CSV
stock_df = pd.read_csv(
    stock_file_path,
    delimiter=stock_delimiter,
    encoding='utf-8-sig',
    dtype=stock_dtype
)

# Line 399: Load SINGLE orders CSV
orders_df = pd.read_csv(
    orders_file_path,
    delimiter=orders_delimiter,
    encoding='utf-8-sig',
    dtype=orders_dtype
)
```

**Result:** Two separate DataFrames loaded from single files each.

---

### 1.4 Validation System

**File:** `shopify_tool/core.py`

**Function: `validate_csv_headers()` (lines 196-226):**
```python
def validate_csv_headers(file_path, required_columns, delimiter=","):
    """Validates if a CSV file contains the required column headers.

    Args:
        file_path (str): Path to a SINGLE CSV file
        required_columns (list[str]): Required CSV column names
        delimiter (str): CSV delimiter

    Returns:
        tuple[bool, list[str]]: (is_valid, missing_columns)
    """
    headers = pd.read_csv(
        file_path,
        nrows=0,  # Only read headers
        delimiter=delimiter,
        encoding='utf-8-sig'
    ).columns.tolist()

    missing_columns = [col for col in required_columns if col not in headers]

    if not missing_columns:
        return True, []
    else:
        return False, missing_columns
```

**Capabilities:**
- ✅ Validates ONE file at a time
- ❌ Cannot validate multiple files
- ❌ Cannot check compatibility between files

---

### 1.5 Data Flow Diagram

**Current Flow:**

```
┌─────────────────────────────────────────┐
│ USER: Click "Select Orders File"        │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ FileHandler.select_orders_file()        │
│ - QFileDialog.getOpenFileName()         │
│ - User selects SINGLE file              │
│ - Returns: "/path/to/orders.csv"        │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Auto-detect Delimiter                   │
│ - detect_csv_delimiter(filepath)        │
│ - Prompt user if differs from config    │
│ - Result: delimiter = ","               │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Validation                              │
│ - validate_file("orders")               │
│ - core.validate_csv_headers()           │
│ - Check required columns exist          │
│ - Result: ✓ or ✗                       │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Store Path                              │
│ - self.mw.orders_file_path = filepath   │
│ - Update UI label with filename         │
│ - Update status indicator (✓/✗)        │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Check Ready                             │
│ - check_files_ready()                   │
│ - Both files selected and valid?        │
│ - Enable "Run Analysis" button          │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ USER: Click "Run Analysis"              │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ ActionsHandler.run_analysis()           │
│ - Create Worker thread                  │
│ - Pass: stock_file_path (str)           │
│ - Pass: orders_file_path (str)          │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ core.run_full_analysis()                │
│ - Load SINGLE orders CSV                │
│ - Load SINGLE stock CSV                 │
│ - Merge, analyze, export                │
└─────────────────────────────────────────┘
```

**Key Observations:**
- Single file path flows through entire pipeline
- No branching for multiple files
- No aggregation/merging capability before analysis

---

## 2. Data Flow: Where to Add Folder Loading

### Critical Intervention Points

**Option A: Early Merge (Recommended)**
```
User selects folder
    ↓
Scan folder for CSV files
    ↓
Validate ALL files
    ↓
MERGE into single DataFrame
    ↓
Continue with existing pipeline (no changes to core)
```

**Option B: Core-Level Merge**
```
User selects folder
    ↓
Pass list of file paths to core
    ↓
Modify core.run_full_analysis() to accept List[str]
    ↓
Core merges files internally
    ↓
Continue with analysis
```

**Recommendation:** **Option A** - Early merge keeps core.py unchanged and isolated.

---

## 3. What Needs to Change

### For Orders Folder Loading:

#### 3.1 UI Layer Changes

**Location:** `gui/main_window_pyside.py` or `gui/ui_manager.py`

**New UI Elements:**
```python
# Mode selector (Radio buttons or Combo box)
self.orders_mode_selector = QComboBox()
self.orders_mode_selector.addItems(["Single File", "Folder (Multiple Files)"])

# OR Radio buttons
self.orders_single_radio = QRadioButton("Single File")
self.orders_folder_radio = QRadioButton("Folder")

# File list preview (for folder mode)
self.orders_file_list_widget = QListWidget()  # Shows found CSV files
self.orders_file_count_label = QLabel()       # Shows "Found: 5 files, 1250 rows"

# Options
self.orders_recursive_checkbox = QCheckBox("Include subfolders")
self.orders_remove_duplicates_checkbox = QCheckBox("Remove duplicate orders")
```

**Button Behavior:**
```python
def on_orders_load_button_clicked(self):
    mode = self.orders_mode_selector.currentText()

    if mode == "Single File":
        self.file_handler.select_orders_file()  # Existing
    else:
        self.file_handler.select_orders_folder()  # NEW
```

---

#### 3.2 FileHandler Layer Changes

**Location:** `gui/file_handler.py`

**New Methods:**

```python
class FileHandler:

    def select_orders_folder(self):
        """Opens folder dialog and scans for CSV files."""
        folder_path = QFileDialog.getExistingDirectory(
            self.mw,
            "Select Orders Folder"
        )

        if not folder_path:
            return

        # Scan folder for CSV files
        csv_files = self.scan_folder_for_csv(
            folder_path,
            recursive=self.mw.orders_recursive_checkbox.isChecked()
        )

        if not csv_files:
            QMessageBox.warning(self.mw, "No Files", "No CSV files found in folder.")
            return

        # Validate all files
        valid, invalid, total_rows = self.validate_multiple_files(csv_files, "orders")

        # Show preview
        self.show_file_preview(csv_files, valid, invalid, total_rows)

        # Store file list (NEW: list instead of str)
        self.mw.orders_file_paths = csv_files  # List[str]
        self.mw.orders_file_path = None         # Clear single file path

        # Update UI
        self.mw.orders_file_path_label.setText(f"{len(csv_files)} files selected")
        self.check_files_ready()


    def scan_folder_for_csv(self, folder_path, recursive=False, pattern="*.csv"):
        """Scans folder for CSV files.

        Args:
            folder_path (str): Folder to scan
            recursive (bool): Include subfolders
            pattern (str): File pattern (default: "*.csv")

        Returns:
            List[str]: List of CSV file paths
        """
        from pathlib import Path

        folder = Path(folder_path)

        if recursive:
            csv_files = list(folder.rglob(pattern))
        else:
            csv_files = list(folder.glob(pattern))

        # Sort by name
        csv_files.sort(key=lambda p: p.name)

        # Convert to strings
        return [str(f) for f in csv_files]


    def validate_multiple_files(self, file_paths, file_type):
        """Validates multiple CSV files for compatibility.

        Args:
            file_paths (List[str]): List of file paths
            file_type (str): "orders" or "stock"

        Returns:
            tuple: (valid_files, invalid_files, total_rows)
        """
        valid_files = []
        invalid_files = []
        total_rows = 0

        config = self.mw.active_profile_config
        column_mappings = config.get("column_mappings", {})

        # Get required columns
        if file_type == "orders":
            REQUIRED = ["Order_Number", "SKU", "Quantity", "Shipping_Method"]
            mappings = column_mappings.get("orders", {})
            required_cols = [csv_col for csv_col, internal in mappings.items()
                            if internal in REQUIRED]
            delimiter = ","
        else:
            REQUIRED = ["SKU", "Stock"]
            mappings = column_mappings.get("stock", {})
            required_cols = [csv_col for csv_col, internal in mappings.items()
                            if internal in REQUIRED]
            delimiter = config.get("settings", {}).get("stock_csv_delimiter", ";")

        # Validate each file
        for filepath in file_paths:
            is_valid, missing_cols = core.validate_csv_headers(
                filepath,
                required_cols,
                delimiter
            )

            if is_valid:
                valid_files.append(filepath)
                # Count rows
                try:
                    df = pd.read_csv(filepath, delimiter=delimiter, encoding='utf-8-sig')
                    total_rows += len(df)
                except:
                    pass
            else:
                invalid_files.append((filepath, missing_cols))

        return valid_files, invalid_files, total_rows


    def show_file_preview(self, csv_files, valid, invalid, total_rows):
        """Shows preview dialog with list of files."""
        msg = f"Found {len(csv_files)} CSV files\n\n"
        msg += f"Valid: {len(valid)}\n"
        msg += f"Invalid: {len(invalid)}\n"
        msg += f"Total rows: {total_rows}\n\n"

        if invalid:
            msg += "Invalid files:\n"
            for filepath, missing in invalid:
                msg += f"  - {os.path.basename(filepath)}: missing {missing}\n"

        QMessageBox.information(self.mw, "Files Found", msg)
```

---

#### 3.3 Core Layer Changes

**Location:** `shopify_tool/core.py`

**Option A: Keep core unchanged, merge files in FileHandler**

**New Function: `merge_csv_files()` (can be in `csv_utils.py`):**

```python
def merge_csv_files(
    file_paths: List[str],
    delimiter: str,
    dtype_dict: Optional[Dict] = None,
    add_source_column: bool = True,
    remove_duplicates: bool = False,
    duplicate_keys: Optional[List[str]] = None
) -> pd.DataFrame:
    """Merges multiple CSV files into a single DataFrame.

    Args:
        file_paths: List of CSV file paths to merge
        delimiter: CSV delimiter
        dtype_dict: Column dtype specifications (e.g., {"SKU": str})
        add_source_column: Add _source_file column for tracking
        remove_duplicates: Remove duplicate rows after merge
        duplicate_keys: Columns to check for duplicates (default: all)

    Returns:
        pd.DataFrame: Merged DataFrame

    Example:
        >>> files = ["shop1_orders.csv", "shop2_orders.csv"]
        >>> merged_df = merge_csv_files(files, delimiter=",", dtype_dict={"Lineitem sku": str})
        >>> print(len(merged_df))
        450
    """
    if not file_paths:
        raise ValueError("No files provided for merging")

    dataframes = []

    for filepath in file_paths:
        try:
            df = pd.read_csv(
                filepath,
                delimiter=delimiter,
                encoding='utf-8-sig',
                dtype=dtype_dict
            )

            # Add source tracking
            if add_source_column:
                df['_source_file'] = os.path.basename(filepath)

            dataframes.append(df)
            logger.info(f"Loaded {len(df)} rows from {os.path.basename(filepath)}")

        except Exception as e:
            logger.error(f"Failed to load {filepath}: {e}")
            raise

    # Concatenate all DataFrames
    merged_df = pd.concat(dataframes, ignore_index=True)
    logger.info(f"Merged {len(dataframes)} files into {len(merged_df)} total rows")

    # Remove duplicates if requested
    if remove_duplicates:
        original_count = len(merged_df)

        if duplicate_keys:
            merged_df = merged_df.drop_duplicates(subset=duplicate_keys, keep='first')
        else:
            merged_df = merged_df.drop_duplicates(keep='first')

        removed = original_count - len(merged_df)
        logger.info(f"Removed {removed} duplicate rows")

    return merged_df
```

**Integration in FileHandler:**

```python
def select_orders_folder(self):
    # ... [scan and validate files as shown above] ...

    # Merge files immediately
    try:
        # Get dtype dict for SKU columns
        column_mappings = self.mw.active_profile_config.get("column_mappings", {})
        orders_dtype = core._get_sku_dtype_dict(column_mappings, "orders")

        # Merge all files
        merged_df = merge_csv_files(
            csv_files,
            delimiter=",",
            dtype_dict=orders_dtype,
            add_source_column=True,
            remove_duplicates=self.mw.orders_remove_duplicates_checkbox.isChecked(),
            duplicate_keys=["Name", "Lineitem sku"]  # Order_Number + SKU
        )

        # Save merged file to temp location
        temp_dir = self.mw.session_path or tempfile.gettempdir()
        merged_path = os.path.join(temp_dir, "merged_orders.csv")
        merged_df.to_csv(merged_path, index=False, encoding='utf-8-sig')

        # Store merged path as single file
        self.mw.orders_file_path = merged_path
        self.mw.orders_file_path_label.setText(f"{len(csv_files)} files merged")

        self.validate_file("orders")
        self.check_files_ready()

    except Exception as e:
        QMessageBox.critical(
            self.mw,
            "Merge Failed",
            f"Failed to merge CSV files:\n{str(e)}"
        )
```

**Result:** `core.run_full_analysis()` still receives a single file path (the merged temp file), so NO CHANGES to core needed!

---

**Option B: Modify core to accept List[str]**

```python
def run_full_analysis(
    stock_file_path: Union[str, List[str]],      # NEW: Can be list
    orders_file_path: Union[str, List[str]],     # NEW: Can be list
    output_dir_path,
    stock_delimiter,
    orders_delimiter,
    config,
    ...
):
    # ... [existing session setup] ...

    # 1. Load data
    logger.info("Step 1: Loading data files...")

    # Handle single file or list of files
    if isinstance(orders_file_path, list):
        # Multiple files - merge them
        orders_dtype = _get_sku_dtype_dict(config.get("column_mappings", {}), "orders")
        orders_df = merge_csv_files(
            orders_file_path,
            orders_delimiter,
            dtype_dict=orders_dtype
        )
    else:
        # Single file - existing logic
        orders_df = pd.read_csv(
            orders_file_path,
            delimiter=orders_delimiter,
            encoding='utf-8-sig',
            dtype=orders_dtype
        )

    # Same for stock_file_path
    # ... [rest of existing logic unchanged] ...
```

**Pros of Option B:**
- Core handles merging centrally
- No temp files needed

**Cons of Option B:**
- Changes core function signature (breaks compatibility)
- More complex error handling in core
- Harder to test

**Recommendation:** **Option A** (merge in FileHandler) is cleaner and safer.

---

### For Stock Folder Loading:

**Same structure as Orders**, but with stock-specific settings:
- Stock delimiter from config (typically ";")
- Different required columns: `["SKU", "Stock"]`
- Same merge logic

---

## 4. Technical Considerations

### 4.1 Memory Limitations

**Current Handling:**
- Single files loaded directly into memory via `pd.read_csv()`
- No streaming or chunking
- Typical file sizes: 100-5000 rows (manageable)

**For Folder Loading:**
- **Scenario:** 10 files × 500 rows = 5000 rows total → ~2-5 MB → **No problem**
- **Scenario:** 50 files × 2000 rows = 100,000 rows → ~50-100 MB → **Still OK**
- **Scenario:** 100+ files or files with >10,000 rows each → May hit memory limits

**Strategy:**
- **Limit:** Add warning if total rows > 50,000
- **Chunking:** Not needed for typical use case (small-medium CSV files)
- **Streaming:** Only if users regularly process 100k+ rows

**Recommendation:** Start without chunking, add warning for large file counts.

```python
if total_rows > 50000:
    reply = QMessageBox.question(
        self.mw,
        "Large Dataset",
        f"Warning: Merging {len(csv_files)} files with {total_rows} total rows.\n"
        f"This may take longer. Continue?",
        QMessageBox.Yes | QMessageBox.No
    )
    if reply == QMessageBox.No:
        return
```

---

### 4.2 File System Compatibility

**Current:**
- Works on Windows and Linux
- Handles UNC paths (network shares) via `_normalize_unc_path()`
- Uses `pathlib.Path` and `os.path`

**For Folder Loading:**
- ✅ `QFileDialog.getExistingDirectory()` works on all platforms
- ✅ `Path.glob()` and `Path.rglob()` work on all platforms
- ✅ No special handling needed for network paths (same as files)

---

### 4.3 CSV Structure Compatibility

**Challenge:** All files in folder must have same structure

**Solution: Pre-validation**
```python
def validate_multiple_files(self, file_paths, file_type):
    # 1. Validate all files have required columns
    # 2. Check all files have SAME delimiter
    # 3. Check all files have SAME column structure
    # 4. Warn if columns differ
```

**Example:**
```
File 1: ["Name", "Lineitem sku", "Lineitem quantity", "Shipping Method"]
File 2: ["Name", "Lineitem sku", "Lineitem quantity", "Shipping Method", "Tags"]
                                                                          ↑ Extra column

→ Still compatible (merge will add NaN for File 1)
→ Show warning: "Files have different column counts"
```

---

### 4.4 Duplicate Handling

**Scenarios:**

1. **Same Order appears in multiple files:**
   ```
   shop1_orders.csv: Order #1001, SKU-A, Qty: 2
   shop2_orders.csv: Order #1001, SKU-A, Qty: 2  ← Duplicate
   ```
   **Strategy:** Remove duplicates based on `(Order_Number, SKU)` → Keep first

2. **Same Order, different items:**
   ```
   shop1_orders.csv: Order #1001, SKU-A, Qty: 2
   shop2_orders.csv: Order #1001, SKU-B, Qty: 1  ← Different item, same order
   ```
   **Strategy:** Keep both (not duplicates)

3. **Same Order, different quantities:**
   ```
   shop1_orders.csv: Order #1001, SKU-A, Qty: 2
   shop2_orders.csv: Order #1001, SKU-A, Qty: 3  ← Different quantity
   ```
   **Strategy:**
   - Option A: Keep first
   - Option B: Keep last
   - Option C: Sum quantities → Qty: 5
   - **Recommendation:** Keep first + warn user

**Implementation:**
```python
# In merge_csv_files()
if remove_duplicates:
    # Define what makes a duplicate
    duplicate_keys = ["Order_Number", "SKU"]  # Internal column names

    # For CSV column names (before mapping):
    # duplicate_keys = ["Name", "Lineitem sku"]

    merged_df = merged_df.drop_duplicates(subset=duplicate_keys, keep='first')
```

---

### 4.5 Source Tracking

**Add `_source_file` column for debugging:**

```python
# In merge_csv_files()
df['_source_file'] = os.path.basename(filepath)
```

**Result DataFrame:**
```
Order_Number | SKU   | Quantity | _source_file
-------------|-------|----------|------------------
1001         | SKU-A | 2        | shop1_orders.csv
1002         | SKU-B | 1        | shop1_orders.csv
1003         | SKU-C | 3        | shop2_orders.csv
```

**Benefits:**
- Easy to trace which file caused issues
- Can filter by source in reports
- Helps debug data quality problems

**Optional:** Remove before final analysis if not needed.

---

## 5. Proposed Changes (High-Level)

### Phase 1: UI Changes (3-4 hours)

**Tasks:**
- [ ] Add mode selector (Single File / Folder) for Orders
- [ ] Add mode selector for Stock
- [ ] Add folder selection dialogs
- [ ] Add file list preview widget
- [ ] Add options: recursive scan, remove duplicates
- [ ] Update button click handlers to check mode

**Files to modify:**
- `gui/ui_manager.py` - Add new widgets
- `gui/main_window_pyside.py` - Update signal connections

---

### Phase 2: FileHandler Changes (4-5 hours)

**Tasks:**
- [ ] Create `select_orders_folder()` method
- [ ] Create `select_stock_folder()` method
- [ ] Create `scan_folder_for_csv()` utility
- [ ] Create `validate_multiple_files()` method
- [ ] Create `show_file_preview()` dialog
- [ ] Update `check_files_ready()` to handle folder mode

**Files to modify:**
- `gui/file_handler.py` - Add new methods

---

### Phase 3: Core Merge Logic (5-6 hours)

**Tasks:**
- [ ] Create `merge_csv_files()` function in `csv_utils.py`
- [ ] Implement duplicate detection
- [ ] Implement source tracking
- [ ] Add error handling for incompatible files
- [ ] Add progress logging
- [ ] Test with various file combinations

**Files to modify:**
- `shopify_tool/csv_utils.py` - Add merge function

**Files to create:**
- None (merge logic goes in existing csv_utils.py)

---

### Phase 4: Testing (3-4 hours)

**Test Cases:**
- [ ] Test with 2 files (basic merge)
- [ ] Test with 10 files
- [ ] Test with duplicates
- [ ] Test with different structures (extra columns)
- [ ] Test with recursive folder scan
- [ ] Test with invalid files mixed in
- [ ] Test memory usage with large datasets
- [ ] Test on Windows and Linux

**Files to create:**
- `tests/test_folder_loading.py`
- `tests/test_csv_merge.py`

---

## 6. Risk Assessment

### Low Risk

✅ **UI Changes**
- Additive only (no existing functionality removed)
- Easy to test visually
- Can be feature-flagged

✅ **File Scanning Logic**
- Standard library functions (`glob`, `rglob`)
- No complex logic
- Easy to unit test

---

### Medium Risk

⚠️ **Merging Logic**
- Must preserve data integrity
- Must handle edge cases (duplicates, different structures)
- Needs thorough testing

**Mitigation:**
- Add source tracking column
- Add comprehensive logging
- Show preview before merge
- Allow user to cancel

⚠️ **Validation with Multiple Files**
- Must check ALL files before proceeding
- Must handle partial failures

**Mitigation:**
- Show detailed error messages
- List invalid files separately
- Allow user to exclude problematic files

---

### High Risk

🔴 **Memory with Large File Counts**
- 100+ files or >100k rows could cause memory issues
- Pandas `concat()` creates copy in memory

**Mitigation:**
- Add row count warning (>50k rows)
- Add file count warning (>50 files)
- Consider streaming/chunking for v2

🔴 **Performance Degradation**
- Merging 50+ files could be slow
- UI might freeze during merge

**Mitigation:**
- Run merge in background thread (Worker)
- Show progress bar
- Add "Cancel" button

---

## 7. Estimated Effort

| Phase | Description | Estimated Time |
|-------|-------------|----------------|
| **Phase 1** | UI Changes | 3-4 hours |
| **Phase 2** | FileHandler | 4-5 hours |
| **Phase 3** | Core Merge | 5-6 hours |
| **Phase 4** | Testing | 3-4 hours |
| **Total** | | **15-19 hours** |

**Calendar Time:** 2-3 days (assuming focused work)

---

## 8. Questions for User

Before implementation, please clarify:

1. **Scope:** Should folder loading work for both Orders AND Stock? Or Orders only?

2. **Recursive Scan:** Should the tool scan subfolders by default? Or make it optional?

3. **Duplicate Handling:** When duplicate orders found (same Order_Number + SKU):
   - ❓ Remove duplicates (keep first) → **Recommended**
   - ❓ Keep all (user decides later)
   - ❓ Sum quantities for same SKU
   - ❓ Show warning and ask user

4. **Memory Limits:** Are there expected scenarios with >100 files or >100k total rows?
   - If yes, should we implement chunking/streaming from the start?
   - If no, we can add warnings and defer optimization

5. **Merged Data Storage:**
   - ❓ Save merged data to temp file (current recommendation)
   - ❓ Keep in memory only
   - ❓ Save permanently to session/input/ folder

6. **Source Tracking:**
   - ❓ Add `_source_file` column to analysis results?
   - ❓ Only use for validation, then remove?

7. **UI Preference:**
   - ❓ Radio buttons for mode selection (Single / Folder)?
   - ❓ Combo box?
   - ❓ Separate buttons ("Select File" vs "Select Folder")?

---

## 9. Code Locations Reference

### Files to Modify:

1. **`gui/ui_manager.py`**
   - Add folder selection UI widgets
   - Add mode selector
   - Add file list preview

2. **`gui/main_window_pyside.py`**
   - Update signal connections for new buttons
   - Add attributes for folder mode state

3. **`gui/file_handler.py`**
   - Add `select_orders_folder()`
   - Add `select_stock_folder()`
   - Add `scan_folder_for_csv()`
   - Add `validate_multiple_files()`
   - Add `show_file_preview()`
   - Update `check_files_ready()` logic

4. **`shopify_tool/csv_utils.py`**
   - Add `merge_csv_files()` function
   - Add duplicate detection helpers

### Files to Create:

5. **`tests/test_folder_loading.py`**
   - Test file scanning
   - Test validation of multiple files
   - Test UI interactions

6. **`tests/test_csv_merge.py`**
   - Test merging 2+ files
   - Test duplicate handling
   - Test source tracking
   - Test error cases

---

## 10. Next Steps

After audit approval:

1. ✅ **Finalize Requirements**
   - Get answers to questions in Section 8
   - Confirm UI design preference

2. **Create Detailed Implementation Plan**
   - Break down each phase into specific tasks
   - Define function signatures
   - Create test data samples

3. **Create UI Mockup**
   - Text-based or screenshot mockup
   - Show folder mode UI layout

4. **Implement Phase 1** (UI)
   - Start with UI changes
   - Get user feedback early
   - Iterate on design

5. **Implement Phases 2-3** (Logic)
   - FileHandler methods
   - Merge function
   - Integration

6. **Implement Phase 4** (Testing)
   - Write comprehensive tests
   - Test on real data
   - Performance testing

---

## 11. Additional Recommendations

### 11.1 Feature Flag

Add a settings option to enable/disable folder loading:

```python
# In config
"features": {
    "folder_loading_enabled": True  # Can disable if issues found
}
```

### 11.2 Progress Feedback

For large merges, show progress:

```python
progress_dialog = QProgressDialog("Merging files...", "Cancel", 0, len(csv_files))
for i, filepath in enumerate(csv_files):
    # Load file
    progress_dialog.setValue(i)
    if progress_dialog.wasCanceled():
        break
```

### 11.3 Merge Preview

Before running analysis, show merge summary:

```
Folder: Orders_2025-11-12/

Files found:
✓ shop1_orders.csv (150 rows)
✓ shop2_orders.csv (230 rows)
✓ shop3_orders.csv (95 rows)
─────────────────────────────
Total: 3 files, 475 rows

Duplicates found: 5 rows
Action: Remove duplicates (keep first)

[Continue] [Cancel]
```

### 11.4 File Name Patterns

Allow filtering by pattern:

```python
# Only load files matching pattern
pattern = "*_orders.csv"  # Only files ending with "_orders.csv"
csv_files = folder.glob(pattern)
```

### 11.5 Delimiter Auto-Detection Per File

Current code detects delimiter for single file. For folder mode:

```python
# Detect delimiter for each file
delimiters = {}
for filepath in csv_files:
    delimiter, method = detect_csv_delimiter(filepath)
    delimiters[filepath] = delimiter

# Check if all same
unique_delimiters = set(delimiters.values())
if len(unique_delimiters) > 1:
    # Files have different delimiters - warn user
    QMessageBox.warning(
        self.mw,
        "Mixed Delimiters",
        f"Files have different delimiters: {unique_delimiters}\n"
        f"Using comma for all files."
    )
```

---

## 12. Summary

### Current State

- ✅ Single file selection works perfectly
- ✅ Auto-detection of delimiters
- ✅ Validation of CSV headers
- ✅ SKU normalization handles edge cases
- ❌ No support for multiple files
- ❌ No support for folder selection
- ❌ No merging capability

### Proposed State

- ✅ Single file mode (existing, unchanged)
- ✅ Folder mode (new) for Orders and Stock
- ✅ Automatic merging of multiple CSV files
- ✅ Duplicate detection and removal
- ✅ Validation of all files before merge
- ✅ Source tracking for debugging
- ✅ Preview of files before processing
- ✅ Compatible with existing pipeline (no core changes needed)

### Implementation Strategy

**Recommended Approach: Option A (Early Merge)**
- Merge files in `FileHandler` before passing to core
- Create temp merged file
- Pass single file path to `core.run_full_analysis()`
- **No changes to core.py needed**

### Risk Level

- **UI Changes:** Low risk
- **File Scanning:** Low risk
- **Merging Logic:** Medium risk (needs testing)
- **Memory/Performance:** Medium-High risk (needs monitoring)

### Success Criteria

✅ User can select a folder with multiple CSV files
✅ System validates all files have compatible structure
✅ System merges files into single dataset
✅ Duplicates are handled correctly
✅ Analysis runs on merged data without errors
✅ User sees clear feedback (file count, row count, errors)
✅ Performance acceptable for 10-20 files
✅ Memory usage reasonable (<500 MB for typical use)

---

## Appendix A: UI Mockup (Text)

```
┌────────────────────────────────────────────────────────────┐
│ Shopify Fulfillment Tool                                   │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  📁 Orders File Loading                                    │
│  ┌──────────────────────────────────────────────────┐     │
│  │ Mode: [Single File ▼]                             │     │
│  │                                                    │     │
│  │ [Select File...]                                  │     │
│  │                                                    │     │
│  │ Selected: orders_export.csv                  ✓   │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
│  OR (when Folder mode selected):                           │
│                                                             │
│  📁 Orders File Loading                                    │
│  ┌──────────────────────────────────────────────────┐     │
│  │ Mode: [Folder (Multiple Files) ▼]                │     │
│  │                                                    │     │
│  │ [Select Folder...]                                │     │
│  │                                                    │     │
│  │ Selected: Orders_2025-11-12/                      │     │
│  │                                                    │     │
│  │ Files found:                                      │     │
│  │ ┌────────────────────────────────────────┐       │     │
│  │ │ ✓ shop1_orders.csv (150 rows)         │       │     │
│  │ │ ✓ shop2_orders.csv (230 rows)         │       │     │
│  │ │ ✓ shop3_orders.csv (95 rows)          │       │     │
│  │ └────────────────────────────────────────┘       │     │
│  │                                                    │     │
│  │ Total: 3 files, 475 rows               ✓         │     │
│  │                                                    │     │
│  │ Options:                                          │     │
│  │ ☑ Include subfolders                             │     │
│  │ ☑ Remove duplicate orders                        │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
│  [Run Analysis]                                            │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## Appendix B: Example Usage

### Scenario 1: Loading Single File (Existing)

```python
# User clicks "Select File"
# Dialog opens, user selects "orders.csv"
# Result:
mw.orders_file_path = "/path/to/orders.csv"
mw.orders_file_path_label.text = "orders.csv"
mw.orders_file_status_label.text = "✓"
```

### Scenario 2: Loading Folder (New)

```python
# User selects mode: "Folder"
# User clicks "Select Folder"
# Dialog opens, user selects "Orders_2025-11-12/"
# System scans folder:

csv_files = [
    "/path/to/Orders_2025-11-12/shop1_orders.csv",
    "/path/to/Orders_2025-11-12/shop2_orders.csv",
    "/path/to/Orders_2025-11-12/shop3_orders.csv"
]

# System validates all files (all valid)
# System merges files:

merged_df = pd.concat([df1, df2, df3], ignore_index=True)
# Result: 475 rows

# System saves to temp:
temp_path = "/tmp/session_xyz/merged_orders.csv"
merged_df.to_csv(temp_path)

# Store as single file path:
mw.orders_file_path = temp_path
mw.orders_file_path_label.text = "3 files merged (475 rows)"
mw.orders_file_status_label.text = "✓"

# Run analysis proceeds normally with merged file
```

---

**End of Audit Report**
