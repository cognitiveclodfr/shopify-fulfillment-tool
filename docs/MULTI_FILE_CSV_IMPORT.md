# Multi-File CSV Import Feature

## Overview

This feature adds the ability to load and merge multiple CSV files from a folder, making it easier to process large batches of orders from different sources or time periods.

## Features

### 1. **Single File vs Folder Selection**
- Radio button toggle to choose between:
  - **Single File**: Load one CSV file (original behavior)
  - **Multiple Files (Folder)**: Load all CSV files from a folder

### 2. **Automatic CSV Merging**
- Loads all `.csv` files from the selected folder
- Validates that all files have compatible structure
- Merges them into a single dataset
- Displays summary information (files count, total orders)

### 3. **Duplicate Detection & Removal**
- Automatically detects duplicate orders across files
- Removes duplicates based on Order_Number
- Shows warning with count of duplicates removed
- Keeps the first occurrence of each order

### 4. **Auto-Detection Features**

#### Delimiter Detection
The system automatically detects CSV delimiters:
- Comma (`,`)
- Semicolon (`;`)
- Tab (`\t`)
- Pipe (`|`)

No need to manually configure the delimiter for each file!

#### Export Format Detection
Automatically recognizes different export formats:
- **Shopify Export**: Detects by "Name" column
- **WooCommerce Export**: Detects by "Order ID" column

Columns are automatically normalized to standard names:
- Shopify "Name" → "Order_Number"
- WooCommerce "Order ID" → "Order_Number"
- "Lineitem sku" → "SKU"
- "Lineitem name" → "Product_Name"
- "Lineitem quantity" → "Quantity"
- "Shipping Method" → "Shipping_Method"

### 5. **Validation & Error Handling**
- **Structure Validation**: Ensures all files have the same columns
- **Empty File Detection**: Warns about empty CSV files
- **Missing Files**: Clear error messages for file access issues
- **Format Mismatch**: Alerts if files have incompatible structures

## Usage

### Loading Single File
1. Select "Single File" radio button (default)
2. Click "📄 Load Orders File"
3. Choose your CSV file
4. File is loaded with auto-detection

### Loading Multiple Files
1. Select "Multiple Files (Folder)" radio button
2. Click "📁 Load Orders Folder"
3. Choose folder containing CSV files
4. Review the summary popup showing:
   - Number of files found
   - Total orders loaded
   - Duplicates removed (if any)
   - Detected format (Shopify/WooCommerce)

## Summary Display

After loading a folder, you'll see a summary like:

```
✓ Successfully loaded 3 file(s)
  Total orders: 247
  ⚠ Duplicates removed: 2
  Detected format: SHOPIFY

Warnings (1):
  • Found 2 duplicate orders across different files
```

## Technical Details

### New Module: `csv_loader.py`
Located in `shopify_tool/csv_loader.py`, this module provides:

**Main Functions:**
- `load_single_csv(file_path)` - Load a single CSV file
- `load_orders_from_folder(folder_path)` - Load and merge multiple CSV files
- `detect_csv_delimiter(file_path)` - Auto-detect delimiter
- `detect_export_format(df)` - Detect Shopify vs WooCommerce
- `normalize_columns(df, format)` - Normalize column names
- `remove_duplicates(df)` - Remove duplicate orders

**Result Object:**
`CSVLoadResult` contains:
- `success` (bool) - Whether loading succeeded
- `dataframe` (pd.DataFrame) - The loaded/merged data
- `files_processed` (int) - Number of files loaded
- `total_orders` (int) - Total unique orders
- `duplicates_removed` (int) - Count of duplicates
- `warnings` (list) - Warning messages
- `errors` (list) - Error messages
- `detected_format` (str) - "shopify" or "woocommerce"

### Integration Points

**UI Components (ui_manager.py):**
- Radio buttons for mode selection
- Separate buttons for file/folder selection
- Enhanced status display with folder information

**File Handler (file_handler.py):**
- `select_orders_file()` - Enhanced with csv_loader
- `select_orders_folder()` - New method for folder selection
- Auto-detection and validation

## Benefits

1. **Time Saving**: Load multiple exports at once instead of manually merging
2. **Error Prevention**: Automatic validation prevents mismatched data
3. **Duplicate Management**: Automatically handles duplicate orders
4. **Format Flexibility**: Works with both Shopify and WooCommerce exports
5. **User Friendly**: Clear summaries and warnings

## Testing

Comprehensive test suite in `tests/test_csv_loader.py`:
- 31 unit tests covering all functionality
- Tests for delimiter detection
- Tests for format detection
- Tests for duplicate removal
- Tests for structure validation
- Tests for error handling

All tests passing ✓

## Example Scenarios

### Scenario 1: Monthly Exports
You have exports from each week of the month:
- `week1_orders.csv`
- `week2_orders.csv`
- `week3_orders.csv`
- `week4_orders.csv`

**Solution**: Put all in one folder, select "Multiple Files (Folder)" mode, load the folder. All orders are merged, duplicates removed.

### Scenario 2: Mixed Sources
You have orders from different platforms:
- `shopify_export.csv` (Shopify format)
- `woocommerce_export.csv` (WooCommerce format)

**Challenge**: Different column names ("Name" vs "Order ID")

**Solution**: The system detects each format automatically and normalizes column names, allowing seamless merging.

### Scenario 3: Delimiter Confusion
Your warehouse sends CSV with semicolon delimiter (`;`), but Shopify exports use comma (`,`).

**Solution**: Auto-detection handles both delimiters automatically - no manual configuration needed!

## Future Enhancements

Potential improvements for future versions:
- Support for Excel (.xlsx) files
- Custom column mapping UI
- Save merged CSV for future use
- Order preview before loading
- Advanced filtering options

---

**Version**: 2.0
**Author**: Shopify Fulfillment Tool Team
**Date**: 2025-01-11
