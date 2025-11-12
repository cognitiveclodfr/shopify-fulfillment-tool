# Delimiter Detection Audit Report

**Date:** 2025-11-12
**Repository:** cognitiveclodfr/shopify-fulfillment-tool
**Branch:** claude/audit-delimiter-detection-011CV3kEkfsB86cDiqUve8Zz
**Auditor:** Claude Code

---

## Executive Summary

The Shopify Fulfillment Tool currently uses **hardcoded and partially configurable delimiters** for CSV file processing. Stock files support configurable delimiters (default `;`) stored in client settings, while Orders files use hardcoded comma delimiters. **Critical findings**: no automatic delimiter detection, no encoding specification in read operations, and inconsistent error handling. This creates potential failures when CSV formats don't match expectations, especially for international users with different regional CSV standards.

---

## 1. Current Implementation

### 1.1 Orders CSV Loading

**Location:** `shopify_tool/core.py:331`
**Method:** Hardcoded comma delimiter
**Delimiter:** Hardcoded `,` (no parameter specified = pandas default)
**Encoding:** Not specified (uses pandas default)

**Code snippet:**
```python
# shopify_tool/core.py:331
orders_df = pd.read_csv(orders_file_path)
```

**Additional validation location:** `gui/file_handler.py:118`
```python
# gui/file_handler.py:118
delimiter = ","
```

**Analysis:**
- Orders files assume Shopify export format (comma-separated)
- No parameter passed to `pd.read_csv()` means pandas uses default `,` delimiter
- No flexibility for different formats
- No encoding specified - may fail with non-ASCII characters

---

### 1.2 Stock CSV Loading

**Location:** `shopify_tool/core.py:329`
**Method:** Configurable via client settings
**Delimiter:** Retrieved from config, defaults to `;`
**Encoding:** Not specified (uses pandas default)

**Code snippet:**
```python
# shopify_tool/core.py:329
stock_df = pd.read_csv(stock_file_path, delimiter=stock_delimiter)

# shopify_tool/core.py:207
def run_full_analysis(
    stock_file_path,
    orders_file_path,
    output_dir_path,
    stock_delimiter,  # ← passed as parameter
    config,
    ...
)
```

**Configuration retrieval locations:**
1. **GUI Actions Handler:** `gui/actions_handler.py:115`
   ```python
   stock_delimiter = self.mw.active_profile_config.get("settings", {}).get("stock_delimiter", ";")
   ```

2. **File Handler (validation):** `gui/file_handler.py:69`
   ```python
   delimiter = config.get("settings", {}).get("stock_csv_delimiter", ";")
   ```

3. **Settings Window:** `gui/settings_window_pyside.py:183-184`
   ```python
   self.stock_delimiter_edit = QLineEdit(
       self.config_data.get("settings", {}).get("stock_csv_delimiter", ";")
   )
   ```

**Analysis:**
- Stock delimiter is configurable but uses different config keys in different places:
  - `stock_delimiter` (actions_handler)
  - `stock_csv_delimiter` (file_handler, settings)
- Default is `;` (semicolon)
- User can change via Settings UI
- Still no encoding specified

---

### 1.3 CSV Header Validation

**Location:** `shopify_tool/core.py:161-200`
**Method:** Pre-load header check with specified delimiter
**Delimiter:** Passed as parameter (default `,`)

**Code snippet:**
```python
def validate_csv_headers(file_path, required_columns, delimiter=","):
    """Validates CSV file contains required column headers.

    Args:
        file_path (str): Path to CSV file
        required_columns (list[str]): Required CSV column names
        delimiter (str, optional): Delimiter used in CSV. Defaults to ",".

    Returns:
        tuple[bool, list[str]]: (is_valid, missing_columns)
    """
    try:
        headers = pd.read_csv(file_path, nrows=0, delimiter=delimiter).columns.tolist()
        missing_columns = [col for col in required_columns if col not in headers]

        if not missing_columns:
            return True, []
        else:
            return False, missing_columns

    except FileNotFoundError:
        return False, [f"File not found at path: {file_path}"]
    except pd.errors.ParserError as e:
        return False, [f"Could not parse file. Error: {e}"]
    except Exception as e:
        return False, [f"An unexpected error occurred: {e}"]
```

**Analysis:**
- Good: Has error handling with try/except
- Good: Returns clear error messages
- Problem: If wrong delimiter used, ParserError may not clearly indicate delimiter issue
- Problem: No encoding specified

---

### 1.4 Configuration Storage

**Config Structure (Profile Manager):** `shopify_tool/profile_manager.py:436-439`

```python
"settings": {
    "low_stock_threshold": 5,
    "stock_delimiter": ";"
}
```

**Default Values:**
- **Orders delimiter:** Not stored in config (always `,`)
- **Stock delimiter:** Stored as `stock_delimiter` or `stock_csv_delimiter`
- **Default stock delimiter:** `;` (semicolon)

**Configuration Inconsistencies:**
| Location | Config Key | Default | Notes |
|----------|-----------|---------|-------|
| `profile_manager.py:438` | `stock_delimiter` | `;` | Template default |
| `settings_window_pyside.py:184` | `stock_csv_delimiter` | `;` | UI settings |
| `file_handler.py:69` | `stock_csv_delimiter` | `;` | File validation |
| `actions_handler.py:115` | `stock_delimiter` | `;` | Analysis execution |

**Issue:** Two different keys used (`stock_delimiter` vs `stock_csv_delimiter`)

---

## 2. Issues Found

### 🔴 Issue #1: Hardcoded Orders Delimiter

**Severity:** HIGH
**Location:** `shopify_tool/core.py:331`, `gui/file_handler.py:118`
**Description:** Orders CSV files always use comma delimiter with no option to change

**Impact:**
- Users cannot process orders files with semicolon or other delimiters
- International users with different regional CSV formats (e.g., European Excel exports with `;`) cannot use the tool without manual file conversion
- No flexibility for different Shopify export settings

**Example:**
```python
# shopify_tool/core.py:331
orders_df = pd.read_csv(orders_file_path)  # Always uses comma
```

**Symptoms when wrong delimiter:**
- Only 1 column loaded instead of multiple columns
- Column names contain delimiter characters
- KeyError when looking for expected columns
- Confusing error messages for users

---

### 🔴 Issue #2: No Encoding Specification

**Severity:** HIGH
**Location:** All `pd.read_csv()` calls
**Description:** No encoding parameter specified when reading CSV files

**Impact:**
- May fail with non-ASCII characters (Cyrillic, special symbols)
- Different behavior on Windows vs Linux (system default encodings differ)
- Potential UnicodeDecodeError for Bulgarian product names or descriptions
- Silent data corruption possible

**Example:**
```python
# Current (all locations):
orders_df = pd.read_csv(orders_file_path)  # encoding not specified
stock_df = pd.read_csv(stock_file_path, delimiter=stock_delimiter)  # encoding not specified

# Should be:
orders_df = pd.read_csv(orders_file_path, encoding='utf-8-sig')
stock_df = pd.read_csv(stock_file_path, delimiter=stock_delimiter, encoding='utf-8-sig')
```

**Note:** Write operations DO specify encoding (`utf-8` or `utf-8-sig`), but reads don't!

---

### 🔴 Issue #3: No Automatic Delimiter Detection

**Severity:** MEDIUM
**Location:** Entire codebase
**Description:** System does not attempt to auto-detect delimiter, relying entirely on configuration or hardcoded values

**Impact:**
- Users must manually configure correct delimiter
- Trial-and-error required if delimiter is unknown
- Poor user experience for non-technical users
- Easy to get wrong and hard to diagnose

**Best practices NOT implemented:**
1. **Pandas auto-detection:** `pd.read_csv(file, sep=None, engine='python')`
2. **csv.Sniffer:** Standard library delimiter detection
3. **Manual heuristics:** Count delimiter occurrences in first line

**Example of what's missing:**
```python
# Option 1: Pandas auto-detection
df = pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8-sig')

# Option 2: csv.Sniffer
import csv
with open(file_path, 'r', encoding='utf-8-sig') as f:
    sample = f.read(1024)
    delimiter = csv.Sniffer().sniff(sample).delimiter

# Option 3: Manual detection
def detect_delimiter(file_path):
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        first_line = f.readline()
        counts = {',': first_line.count(','), ';': first_line.count(';'), '\t': first_line.count('\t')}
        return max(counts, key=counts.get)
```

---

### 🟡 Issue #4: Inconsistent Configuration Keys

**Severity:** MEDIUM
**Location:** Multiple files
**Description:** Stock delimiter uses different config keys in different parts of codebase

**Locations:**
- `stock_delimiter` in `profile_manager.py:438` and `actions_handler.py:115`
- `stock_csv_delimiter` in `settings_window_pyside.py:184` and `file_handler.py:69`

**Impact:**
- Confusion when debugging
- Potential for misconfiguration
- Code maintenance difficulty
- May cause settings not to persist correctly

**Recommendation:** Standardize on single key name throughout codebase

---

### 🟡 Issue #5: Incomplete Error Handling

**Severity:** MEDIUM
**Location:** `shopify_tool/core.py:329-331`
**Description:** Main CSV loading in `run_full_analysis()` lacks try/except blocks

**Code:**
```python
# shopify_tool/core.py:329-331
stock_df = pd.read_csv(stock_file_path, delimiter=stock_delimiter)
logger.info(f"Reading orders file from normalized path: {orders_file_path}")
orders_df = pd.read_csv(orders_file_path)
```

**Impact:**
- Unhandled exceptions crash the entire analysis
- No user-friendly error messages
- Difficult to diagnose delimiter-related issues

**Note:** File handler DOES have try/except (file_handler.py:72-85), but core analysis doesn't

---

### 🟡 Issue #6: No Preview/Verification Before Analysis

**Severity:** LOW
**Location:** User workflow
**Description:** No visual confirmation that CSV was parsed correctly before running analysis

**Impact:**
- User doesn't see if delimiter is wrong until analysis fails
- No opportunity to fix delimiter setting before processing
- Wasted time running analysis with wrong settings

**Recommendation:** Add CSV preview with first few rows after file selection

---

### 🟡 Issue #7: No Orders Delimiter Configuration

**Severity:** MEDIUM
**Location:** Configuration system
**Description:** Orders delimiter is hardcoded with no UI option to change it

**Impact:**
- Stock delimiter is configurable via Settings, but orders delimiter is not
- Inconsistent user experience
- Users may expect to configure orders delimiter when they see stock delimiter setting

**Current Settings UI:**
- ✓ Stock CSV Delimiter: [;]
- ✗ Orders CSV Delimiter: (not available)

---

## 3. All pandas.read_csv() Calls

| File | Line | Context | Delimiter | Encoding | Error Handling | Issues |
|------|------|---------|-----------|----------|----------------|--------|
| `gui/file_handler.py` | 73 | Stock file validation | From config (param) | ❌ Not specified | ✓ Try/except | ⚠️ No encoding |
| `shopify_tool/core.py` | 185 | CSV header validation | Param (default `,`) | ❌ Not specified | ✓ Try/except | ⚠️ No encoding |
| `shopify_tool/core.py` | 329 | Stock data loading | Param from config | ❌ Not specified | ❌ No try/except | ❌ No encoding, no error handling |
| `shopify_tool/core.py` | 331 | Orders data loading | ❌ Hardcoded `,` | ❌ Not specified | ❌ No try/except | ❌ Hardcoded delimiter, no encoding, no error handling |
| `shopify_tool/core.py` | 366 | History loading | Default `,` | ❌ Not specified | ✓ Try/except (FileNotFoundError only) | ⚠️ No encoding, incomplete error handling |
| `tests/test_core.py` | 275 | Test history loading | Default `,` | ❌ Not specified | ❌ No try/except | ⚠️ Test code |
| `tests/integration/test_migration.py` | 298 | Test orders loading | Default `,` | ❌ Not specified | ❌ No try/except | ⚠️ Test code |
| `tests/integration/test_migration.py` | 301 | Test stock loading | `;` hardcoded | ❌ Not specified | ❌ No try/except | ⚠️ Test code |

**Summary Statistics:**
- **Total read_csv calls:** 8 (3 production, 5 tests)
- **With encoding specified:** 0 (0%)
- **With error handling:** 3 (37.5%)
- **With hardcoded delimiter:** 2 (25%)
- **With configurable delimiter:** 1 (12.5%)

---

## 4. Test Results

### Test Scenario 1: Standard Shopify CSV (comma delimiter)

**Test File:** `test_comma.csv`
```csv
Name,Lineitem sku,Lineitem quantity,Shipping Method
ORDER-001,SKU-001,2,Standard
ORDER-002,SKU-002,1,Express
```

**Expected Behavior:**
- ✓ Loads correctly with default settings
- ✓ Should detect 4 columns
- ✓ Should parse 2 data rows

**Actual Behavior (based on code analysis):**
- ✓ Will load correctly (orders use comma by default)
- ✓ Headers will be correctly identified
- ⚠️ May fail if file contains non-ASCII characters (no encoding specified)

---

### Test Scenario 2: Stock CSV with semicolon

**Test File:** `test_semicolon.csv`
```csv
Артикул;Име;Наличност
SKU-001;Product A;10
SKU-002;Product B;5
```

**Expected Behavior:**
- ✓ Loads correctly with stock_delimiter=";"
- ✓ Should detect 3 columns
- ✓ Should parse 2 data rows
- ✓ Should handle Cyrillic characters

**Actual Behavior (based on code analysis):**
- ✓ Will load correctly if `stock_delimiter=";"` (default)
- ❌ **Will likely fail** with Cyrillic headers due to encoding issue
- ⚠️ Error message won't clearly indicate encoding vs delimiter problem

---

### Test Scenario 3: CSV with tab delimiter

**Test File:** `test_tab.csv`
```csv
Name	SKU	Qty	Method
ORDER-001	SKU-001	2	Standard
ORDER-002	SKU-002	1	Express
```

**Expected Behavior:**
- With auto-detection: Should load correctly
- Without auto-detection: Will fail

**Actual Behavior (based on code analysis):**
- ❌ **Orders:** Will fail (expects comma, gets tab)
- ❌ **Stock:** Will fail unless user manually sets delimiter to `\t` in settings
- ❌ No auto-detection available
- ❌ User has no way to specify tab delimiter in current UI (would need to type `\t`)

---

### Test Scenario 4: CSV with wrong delimiter

**Test:** Load comma CSV with semicolon delimiter setting

**Expected Behavior:**
- Should fail gracefully with clear error message
- Should suggest checking delimiter setting

**Actual Behavior (based on code analysis):**

**For Stock file (file_handler.py:72-85):**
- ✓ Has try/except block
- ✓ Shows error dialog with delimiter hint
- ✓ Error message includes: "Make sure the delimiter is set correctly"
- ✓ Good user experience

**For Orders file (core.py:331):**
- ❌ No try/except block
- ❌ Will crash with unhandled ParserError
- ❌ Error message won't mention delimiter
- ❌ Poor user experience

**Example of what happens:**
```python
# If file has semicolons but code expects commas:
# Result: Single column with all data as one string
df.columns: ['Name;Lineitem sku;Lineitem quantity;Shipping Method']
df.shape: (2, 1)  # ← Only 1 column instead of 4!

# Subsequent code expecting separate columns will fail with KeyError
```

---

## 5. Comparison with Best Practices

| Practice | Used? | Implementation Status | Notes |
|----------|-------|----------------------|-------|
| **Pandas auto-detection** (`sep=None`) | ❌ No | Not implemented | Most reliable method, built-in pandas feature |
| **csv.Sniffer** | ❌ No | Not implemented | Standard library, good fallback option |
| **Manual detection** (count delimiters) | ❌ No | Not implemented | Simple implementation, covers 90% of cases |
| **Encoding specification** | ❌ No | Not implemented | Critical for international users |
| **Error handling** | ⚠️ Partial | Inconsistent | Good in file_handler, missing in core |
| **User configuration** | ⚠️ Partial | Stock only | Only stock delimiter configurable |
| **Preview before processing** | ❌ No | Not implemented | Would improve UX significantly |
| **Delimiter validation** | ⚠️ Indirect | Through parsing | Could be more explicit |

**Best Practice Examples:**

### 1. Pandas Auto-Detection
```python
def load_csv_auto(file_path):
    """Load CSV with automatic delimiter detection."""
    return pd.read_csv(
        file_path,
        sep=None,           # Auto-detect delimiter
        engine='python',    # Required for sep=None
        encoding='utf-8-sig'  # Handle UTF-8 with BOM
    )
```

### 2. csv.Sniffer
```python
import csv

def detect_delimiter(file_path):
    """Detect delimiter using standard library."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        sample = f.read(1024)
        sniffer = csv.Sniffer()
        return sniffer.sniff(sample).delimiter
```

### 3. Manual Detection with Fallback
```python
def detect_delimiter_robust(file_path):
    """Robust delimiter detection with fallback."""
    try:
        # Try csv.Sniffer first
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            sample = f.read(1024)
            return csv.Sniffer().sniff(sample).delimiter
    except:
        # Fallback: count common delimiters
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            first_line = f.readline()
            counts = {
                ',': first_line.count(','),
                ';': first_line.count(';'),
                '\t': first_line.count('\t'),
                '|': first_line.count('|')
            }
            # Return delimiter with most occurrences
            return max(counts, key=counts.get) if max(counts.values()) > 0 else ','
```

### 4. Full Implementation Example
```python
def load_csv_smart(file_path, config_delimiter=None, encoding='utf-8-sig'):
    """
    Smart CSV loading with delimiter detection and error handling.

    Priority:
    1. Use config_delimiter if provided and works
    2. Try auto-detection
    3. Try common delimiters
    4. Fail with helpful error message
    """
    delimiters_to_try = []

    # Add config delimiter first if provided
    if config_delimiter:
        delimiters_to_try.append(('config', config_delimiter))

    # Try auto-detection
    try:
        df = pd.read_csv(file_path, sep=None, engine='python', encoding=encoding, nrows=5)
        return df, 'auto-detected'
    except:
        pass

    # Try common delimiters
    delimiters_to_try.extend([
        ('comma', ','),
        ('semicolon', ';'),
        ('tab', '\t'),
        ('pipe', '|')
    ])

    for name, delim in delimiters_to_try:
        try:
            df = pd.read_csv(file_path, delimiter=delim, encoding=encoding, nrows=5)
            # Check if parsing was successful (more than 1 column)
            if len(df.columns) > 1:
                return df, f'{name} ({delim})'
        except:
            continue

    raise ValueError(
        f"Could not parse CSV file: {file_path}\n"
        f"Tried delimiters: {[d[1] for d in delimiters_to_try]}\n"
        f"Please check file format and encoding."
    )
```

---

## 6. Recommendations

### Priority 1: Add Encoding Parameter to All read_csv Calls
**Effort:** 1 hour
**Impact:** HIGH
**Breaking Changes:** No

**Description:**
Add `encoding='utf-8-sig'` to all `pd.read_csv()` calls. This fixes critical issue with Cyrillic characters and international users.

**Changes Required:**
```python
# shopify_tool/core.py:329
stock_df = pd.read_csv(stock_file_path, delimiter=stock_delimiter, encoding='utf-8-sig')

# shopify_tool/core.py:331
orders_df = pd.read_csv(orders_file_path, encoding='utf-8-sig')

# shopify_tool/core.py:185
headers = pd.read_csv(file_path, nrows=0, delimiter=delimiter, encoding='utf-8-sig').columns.tolist()

# shopify_tool/core.py:366
history_df = pd.read_csv(history_path_str, encoding='utf-8-sig')

# gui/file_handler.py:73
stock_df = pd.read_csv(filepath, delimiter=delimiter, encoding='utf-8-sig')
```

**Testing:** Verify with files containing Cyrillic characters

---

### Priority 2: Implement Automatic Delimiter Detection
**Effort:** 4-6 hours
**Impact:** HIGH
**Breaking Changes:** No (enhancement)

**Description:**
Add automatic delimiter detection for both orders and stock files. Use pandas `sep=None` as primary method with fallback to csv.Sniffer.

**Implementation Plan:**

1. **Create utility function** (new file: `shopify_tool/csv_utils.py`):
```python
def detect_csv_delimiter(file_path, encoding='utf-8-sig'):
    """
    Automatically detect CSV delimiter.

    Args:
        file_path: Path to CSV file
        encoding: File encoding (default: utf-8-sig)

    Returns:
        tuple: (delimiter, detection_method)
    """
    # Method 1: Pandas auto-detection
    try:
        df = pd.read_csv(file_path, sep=None, engine='python',
                        encoding=encoding, nrows=2)
        if len(df.columns) > 1:
            # Infer delimiter from what pandas detected
            with open(file_path, 'r', encoding=encoding) as f:
                first_line = f.readline()
                for delim in [',', ';', '\t', '|']:
                    if first_line.count(delim) >= len(df.columns) - 1:
                        return delim, 'pandas'
    except Exception as e:
        logging.debug(f"Pandas auto-detection failed: {e}")

    # Method 2: csv.Sniffer
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            sample = f.read(2048)
            delimiter = csv.Sniffer().sniff(sample).delimiter
            return delimiter, 'sniffer'
    except Exception as e:
        logging.debug(f"csv.Sniffer failed: {e}")

    # Method 3: Manual counting
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            first_line = f.readline()
            counts = {
                ',': first_line.count(','),
                ';': first_line.count(';'),
                '\t': first_line.count('\t'),
                '|': first_line.count('|')
            }
            if max(counts.values()) > 0:
                delimiter = max(counts, key=counts.get)
                return delimiter, 'counting'
    except Exception as e:
        logging.debug(f"Manual counting failed: {e}")

    # Fallback: return comma
    return ',', 'default'
```

2. **Update file_handler.py** to detect delimiter when file selected:
```python
def select_stock_file(self):
    filepath, _ = QFileDialog.getOpenFileName(...)
    if not filepath:
        return

    # Auto-detect delimiter
    from shopify_tool.csv_utils import detect_csv_delimiter
    detected_delimiter, method = detect_csv_delimiter(filepath)

    self.log.info(f"Detected delimiter '{detected_delimiter}' using {method}")

    # Get configured delimiter
    config_delimiter = self.mw.active_profile_config.get("settings", {}).get("stock_csv_delimiter", ";")

    # If detected differs from config, offer to update
    if detected_delimiter != config_delimiter:
        result = QMessageBox.question(
            self.mw,
            "Delimiter Detected",
            f"Detected delimiter: '{detected_delimiter}'\n"
            f"Configured delimiter: '{config_delimiter}'\n\n"
            f"Use detected delimiter?",
            QMessageBox.Yes | QMessageBox.No
        )
        if result == QMessageBox.Yes:
            delimiter = detected_delimiter
            # Update config
            self.mw.active_profile_config["settings"]["stock_csv_delimiter"] = delimiter
        else:
            delimiter = config_delimiter
    else:
        delimiter = detected_delimiter

    # Continue with loading...
```

3. **Update core.py** to use detected delimiter if available:
```python
def run_full_analysis(...):
    # If delimiter not provided or is default, try to detect
    if stock_delimiter == ";":
        detected, _ = detect_csv_delimiter(stock_file_path)
        if detected != ";":
            logger.info(f"Using detected delimiter '{detected}' instead of default ';'")
            stock_delimiter = detected
```

**Testing:**
- Test with comma-separated files
- Test with semicolon-separated files
- Test with tab-separated files
- Test with mixed/unusual delimiters

---

### Priority 3: Add Error Handling to Core CSV Loading
**Effort:** 2 hours
**Impact:** MEDIUM
**Breaking Changes:** No

**Description:**
Add try/except blocks around CSV loading in `run_full_analysis()` to gracefully handle parsing errors.

**Implementation:**
```python
# shopify_tool/core.py:329-331
try:
    logger.info(f"Reading stock file from normalized path: {stock_file_path}")
    stock_df = pd.read_csv(stock_file_path, delimiter=stock_delimiter, encoding='utf-8-sig')
    logger.info(f"Stock data loaded: {len(stock_df)} rows, {len(stock_df.columns)} columns")
except pd.errors.ParserError as e:
    error_msg = (
        f"Failed to parse stock file. The file may have incorrect delimiter.\n"
        f"Current delimiter: '{stock_delimiter}'\n"
        f"Error: {str(e)}"
    )
    logger.error(error_msg)
    return False, error_msg, None, None
except Exception as e:
    error_msg = f"Failed to load stock file: {str(e)}"
    logger.error(error_msg)
    return False, error_msg, None, None

try:
    logger.info(f"Reading orders file from normalized path: {orders_file_path}")
    orders_df = pd.read_csv(orders_file_path, encoding='utf-8-sig')
    logger.info(f"Orders data loaded: {len(orders_df)} rows, {len(orders_df.columns)} columns")
except pd.errors.ParserError as e:
    error_msg = (
        f"Failed to parse orders file. The file may have incorrect delimiter.\n"
        f"Expected delimiter: ',' (comma)\n"
        f"Error: {str(e)}"
    )
    logger.error(error_msg)
    return False, error_msg, None, None
except Exception as e:
    error_msg = f"Failed to load orders file: {str(e)}"
    logger.error(error_msg)
    return False, error_msg, None, None
```

---

### Priority 4: Standardize Configuration Key
**Effort:** 1-2 hours
**Impact:** MEDIUM
**Breaking Changes:** Yes (requires migration)

**Description:**
Standardize on single config key for stock delimiter throughout codebase.

**Recommendation:** Use `stock_csv_delimiter` (more descriptive)

**Changes Required:**
1. Update `profile_manager.py:438`: `"stock_delimiter"` → `"stock_csv_delimiter"`
2. Update `actions_handler.py:115`: `"stock_delimiter"` → `"stock_csv_delimiter"`
3. Add migration code to handle old configs:
```python
def migrate_config(config):
    """Migrate old config format to new."""
    settings = config.get("settings", {})

    # Migrate stock_delimiter → stock_csv_delimiter
    if "stock_delimiter" in settings and "stock_csv_delimiter" not in settings:
        settings["stock_csv_delimiter"] = settings["stock_delimiter"]
        del settings["stock_delimiter"]
        logging.info("Migrated stock_delimiter to stock_csv_delimiter")

    return config
```

**Testing:** Verify existing configs still work after migration

---

### Priority 5: Add Orders Delimiter Configuration
**Effort:** 3-4 hours
**Impact:** MEDIUM
**Breaking Changes:** No (enhancement)

**Description:**
Add configuration option for orders delimiter in Settings UI, matching stock delimiter setting.

**Implementation:**

1. **Update Settings UI** (`gui/settings_window_pyside.py`):
```python
# Add orders delimiter field after stock delimiter
orders_delimiter_label = QLabel("Orders CSV Delimiter:")
self.orders_delimiter_edit = QLineEdit(
    self.config_data.get("settings", {}).get("orders_csv_delimiter", ",")
)
self.orders_delimiter_edit.setMaximumWidth(100)
self.orders_delimiter_edit.setToolTip(
    "Character used to separate columns in orders CSV file.\n\n"
    "Common values:\n"
    "  • Comma (,) - standard Shopify exports\n"
    "  • Semicolon (;) - European Excel exports\n\n"
    "Make sure this matches your orders CSV file format."
)
settings_layout.addRow(orders_delimiter_label, self.orders_delimiter_edit)
```

2. **Update save method**:
```python
self.config_data["settings"]["orders_csv_delimiter"] = self.orders_delimiter_edit.text()
```

3. **Update file_handler.py**:
```python
# line 118
delimiter = client_config.get("settings", {}).get("orders_csv_delimiter", ",")
```

4. **Update core.py**:
```python
def run_full_analysis(
    stock_file_path,
    orders_file_path,
    output_dir_path,
    stock_delimiter,
    orders_delimiter,  # ← new parameter
    config,
    ...
):
    ...
    orders_df = pd.read_csv(orders_file_path, delimiter=orders_delimiter, encoding='utf-8-sig')
```

5. **Update actions_handler.py**:
```python
stock_delimiter = self.mw.active_profile_config.get("settings", {}).get("stock_csv_delimiter", ";")
orders_delimiter = self.mw.active_profile_config.get("settings", {}).get("orders_csv_delimiter", ",")

worker = Worker(
    core.run_full_analysis,
    self.mw.stock_file_path,
    self.mw.orders_file_path,
    None,
    stock_delimiter,
    orders_delimiter,  # ← pass to core
    ...
)
```

**Testing:** Verify both delimiters can be configured independently

---

### Priority 6: Add CSV Preview Feature
**Effort:** 6-8 hours
**Impact:** LOW (UX enhancement)
**Breaking Changes:** No

**Description:**
Add preview dialog showing first few rows of CSV after file selection to verify correct parsing.

**Implementation:**

1. **Create preview dialog** (new file: `gui/csv_preview_dialog.py`):
```python
class CSVPreviewDialog(QDialog):
    """Dialog to preview CSV file with detected delimiter."""

    def __init__(self, file_path, delimiter, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CSV Preview")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        # Info label
        info = QLabel(f"File: {os.path.basename(file_path)}\nDelimiter: '{delimiter}'")
        layout.addWidget(info)

        # Table view
        table = QTableWidget()
        df = pd.read_csv(file_path, delimiter=delimiter, encoding='utf-8-sig', nrows=10)

        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns)

        for i, row in df.iterrows():
            for j, value in enumerate(row):
                table.setItem(i, j, QTableWidgetItem(str(value)))

        layout.addWidget(table)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
```

2. **Integrate into file_handler.py**:
```python
def select_stock_file(self):
    filepath, _ = QFileDialog.getOpenFileName(...)
    if not filepath:
        return

    # Detect delimiter
    delimiter, method = detect_csv_delimiter(filepath)

    # Show preview
    preview = CSVPreviewDialog(filepath, delimiter, self.mw)
    if preview.exec_() != QDialog.Accepted:
        return  # User cancelled

    # Continue with validation...
```

**Testing:** Test with various CSV formats and sizes

---

### Priority 7: Add Comprehensive Tests
**Effort:** 4-6 hours
**Impact:** MEDIUM
**Breaking Changes:** No

**Description:**
Add unit tests for delimiter detection and CSV loading with various formats.

**Test Cases:**
1. Test comma-separated CSV
2. Test semicolon-separated CSV
3. Test tab-separated CSV
4. Test CSV with Cyrillic characters
5. Test CSV with wrong delimiter (should fail gracefully)
6. Test auto-detection with various formats
7. Test encoding handling (UTF-8, UTF-8-BOM, Windows-1251)

---

## 7. Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER SELECTS CSV FILE                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              AUTOMATIC DELIMITER DETECTION                       │
│  1. Try pandas sep=None (preferred)                             │
│  2. Fallback to csv.Sniffer                                     │
│  3. Fallback to manual counting                                 │
│  4. Use configured default                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│          CHECK AGAINST CONFIGURED DELIMITER                      │
│  - If matches config: proceed                                   │
│  - If differs: prompt user to confirm                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              [OPTIONAL] SHOW CSV PREVIEW                         │
│  - Display first 10 rows in table                               │
│  - Show detected delimiter                                      │
│  - Allow user to override if wrong                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               LOAD CSV WITH CORRECT SETTINGS                     │
│  - Use detected/confirmed delimiter                             │
│  - Always specify encoding='utf-8-sig'                          │
│  - Wrap in try/except for error handling                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  VALIDATE HEADERS                                │
│  - Check required columns present                               │
│  - Provide clear error messages                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              PROCEED WITH ANALYSIS                               │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principles:**
1. **Automatic first**: Try to detect delimiter automatically
2. **User confirmation**: Prompt if detection differs from config
3. **Visual feedback**: Show preview so user can verify
4. **Graceful degradation**: Multiple fallback methods
5. **Clear errors**: Helpful messages when parsing fails

---

## 8. Breaking Changes

### Minimal Breaking Changes Approach (Recommended)

**Priority 1-3 (Encoding, Detection, Error Handling):**
- ✓ **Backward compatible** - No API changes
- ✓ Existing code continues to work
- ✓ Configs remain valid
- ✓ Only adds safety and robustness

**Priority 4 (Config Key Standardization):**
- ⚠️ **Requires migration** - Config key changes
- ⚠️ Need migration function to update old configs
- ✓ Can be made backward compatible with migration code
- ✓ Transparent to end users

**Priority 5 (Orders Delimiter Config):**
- ✓ **Backward compatible** - New optional field
- ✓ Defaults to current behavior (`,`)
- ✓ Existing configs work without changes

**Priority 6-7 (Preview & Tests):**
- ✓ **Backward compatible** - Pure additions
- ✓ No impact on existing functionality

### Migration Strategy

1. **Phase 1: Safety improvements (Priority 1-3)**
   - Add encoding parameters
   - Add auto-detection
   - Add error handling
   - **No breaking changes**
   - Can be deployed immediately

2. **Phase 2: Config improvements (Priority 4-5)**
   - Standardize config keys
   - Add orders delimiter config
   - **Include migration function**
   - Test with existing client configs
   - Deploy with version bump

3. **Phase 3: UX enhancements (Priority 6-7)**
   - Add preview feature
   - Add comprehensive tests
   - **No breaking changes**
   - Can be deployed incrementally

---

## 9. Migration Plan

### For Priority 4 (Config Key Standardization)

**Migration Function:**
```python
def migrate_delimiter_config(config: dict, config_version: str) -> dict:
    """
    Migrate delimiter configuration from v1 to v2 format.

    Changes:
    - Rename 'stock_delimiter' → 'stock_csv_delimiter'
    - Add 'orders_csv_delimiter' with default ','

    Args:
        config: Client configuration dictionary
        config_version: Current config version

    Returns:
        Migrated configuration dictionary
    """
    if config_version >= "2.1":
        return config  # Already migrated

    settings = config.get("settings", {})

    # Migrate stock_delimiter → stock_csv_delimiter
    if "stock_delimiter" in settings:
        if "stock_csv_delimiter" not in settings:
            settings["stock_csv_delimiter"] = settings["stock_delimiter"]
        del settings["stock_delimiter"]
        logging.info("Migrated 'stock_delimiter' to 'stock_csv_delimiter'")

    # Add orders_csv_delimiter if missing
    if "orders_csv_delimiter" not in settings:
        settings["orders_csv_delimiter"] = ","
        logging.info("Added default 'orders_csv_delimiter': ','")

    # Update version
    config["config_version"] = "2.1"

    return config
```

**Integration:**
```python
# In profile_manager.py load_client_config()
def load_client_config(self, client_id: str) -> Optional[Dict]:
    config = self._load_config_file(config_path)

    # Check if migration needed
    current_version = config.get("config_version", "1.0")
    if current_version < "2.1":
        config = migrate_delimiter_config(config, current_version)
        # Save migrated config
        self.save_client_config(client_id, config)

    return config
```

**Testing Migration:**
1. Create test configs with old format
2. Load through migration function
3. Verify new keys present
4. Verify old keys removed
5. Verify existing functionality unchanged

---

### User Communication

**For existing users after update:**

```
--- Shopify Fulfillment Tool Update ---

Improvements to CSV File Handling:

✓ Better support for international characters (Cyrillic, etc.)
✓ Automatic delimiter detection - tool now detects , ; or tab automatically
✓ Improved error messages when CSV files can't be loaded
✓ New setting: Orders CSV delimiter (in addition to Stock CSV delimiter)

No action required - your existing configurations have been automatically updated.

If you experience any issues with CSV loading, please check:
1. Settings > CSV Delimiters (both orders and stock)
2. File encoding (should be UTF-8)

Report issues: [GitHub link]
```

---

## 10. Estimated Effort

| Priority | Task | Effort (hours) | Complexity | Dependencies |
|----------|------|----------------|------------|--------------|
| 1 | Add encoding parameters | 1 | Low | None |
| 2 | Implement auto-detection | 4-6 | Medium | Priority 1 |
| 3 | Add error handling | 2 | Low | None |
| 4 | Standardize config keys | 1-2 | Medium | None |
| 5 | Add orders delimiter config | 3-4 | Medium | Priority 4 |
| 6 | Add CSV preview | 6-8 | High | Priority 2 |
| 7 | Add comprehensive tests | 4-6 | Medium | All above |

**Total Effort:**
- **Minimum (Essential fixes only):** 7-8 hours (Priorities 1-3)
- **Recommended (Include config improvements):** 11-14 hours (Priorities 1-5)
- **Complete (All enhancements):** 21-28 hours (All priorities)

**Suggested Implementation Schedule:**

**Week 1: Critical Fixes (Priorities 1-3)**
- Day 1: Add encoding parameters (1h) + testing (1h)
- Day 2-3: Implement auto-detection (6h) + testing (2h)
- Day 4: Add error handling (2h) + testing (1h)
- Day 5: Integration testing and bug fixes (3h)
- **Total:** 16 hours (2 days of work)

**Week 2: Configuration Improvements (Priorities 4-5)**
- Day 1: Standardize config keys (2h) + migration code (2h)
- Day 2: Add orders delimiter config (4h)
- Day 3: Testing and validation (4h)
- **Total:** 12 hours (1.5 days of work)

**Week 3: UX Enhancements (Priorities 6-7)**
- Day 1-2: CSV preview feature (8h)
- Day 3: Comprehensive tests (6h)
- Day 4: Documentation and final testing (4h)
- **Total:** 18 hours (2.5 days of work)

**Overall Project:** 46 hours (~6 days of development work)

---

## 11. Code Locations Reference

### Files Requiring Changes

**High Priority Changes:**

1. **shopify_tool/core.py**
   - Lines 185, 329, 331, 366: Add `encoding='utf-8-sig'`
   - Lines 329-331: Add try/except error handling
   - Line 207: Add `orders_delimiter` parameter
   - Line 331: Use `orders_delimiter` parameter

2. **gui/file_handler.py**
   - Line 73: Add `encoding='utf-8-sig'`
   - Lines 47-89: Add auto-detection logic
   - Line 118: Make orders delimiter configurable

3. **gui/actions_handler.py**
   - Line 115: Standardize config key to `stock_csv_delimiter`
   - Add: Retrieve `orders_delimiter` from config
   - Line 122: Pass `orders_delimiter` to core

4. **gui/settings_window_pyside.py**
   - Lines 181-197: Keep stock delimiter settings
   - Add: Orders delimiter settings (new UI controls)
   - Line 969: Save both delimiters

5. **shopify_tool/profile_manager.py**
   - Line 438: Change `stock_delimiter` → `stock_csv_delimiter`
   - Add: `orders_csv_delimiter` default
   - Add: Migration function for config updates

**New Files to Create:**

1. **shopify_tool/csv_utils.py** (new)
   - `detect_csv_delimiter()` function
   - Helper utilities for CSV handling

2. **gui/csv_preview_dialog.py** (new, Priority 6)
   - CSV preview UI dialog

3. **tests/test_csv_utils.py** (new, Priority 7)
   - Unit tests for delimiter detection

4. **tests/test_delimiter_integration.py** (new, Priority 7)
   - Integration tests for CSV loading

---

## 12. Additional Notes

### Known Issues Not Covered by This Audit

This audit focused specifically on delimiter detection. Related issues that may need separate attention:

1. **Column mapping system** - Not evaluated in this audit
2. **Data validation logic** - Only CSV parsing evaluated
3. **Performance with large files** - Not tested
4. **Memory usage** - Not evaluated
5. **Unicode normalization** - May need attention beyond encoding

### Comparison: Write vs Read Operations

**Interesting finding:** Write operations consistently use `encoding='utf-8-sig'`:
- `scripts/create_comprehensive_test_data.py:829`
- `scripts/create_test_data.py:110`
- All JSON file operations

**But read operations (CSV) do NOT specify encoding!**

This inconsistency suggests developers were aware of encoding issues but only addressed it for write operations.

---

## 13. Testing Checklist

Before deploying changes, verify:

### Delimiter Detection
- [ ] Comma-separated CSV loads correctly
- [ ] Semicolon-separated CSV loads correctly
- [ ] Tab-separated CSV loads correctly
- [ ] Pipe-separated CSV loads correctly
- [ ] Mixed delimiters handled gracefully (error)
- [ ] Auto-detection works for all above

### Encoding Handling
- [ ] UTF-8 files load correctly
- [ ] UTF-8-BOM files load correctly
- [ ] Files with Cyrillic characters load correctly
- [ ] Files with special characters (€, £, etc.) load correctly
- [ ] Windows-generated files load correctly
- [ ] Linux-generated files load correctly

### Error Handling
- [ ] Wrong delimiter shows helpful error
- [ ] Corrupted file shows helpful error
- [ ] Missing file shows helpful error
- [ ] Empty file handled gracefully
- [ ] File with only headers handled correctly

### Configuration
- [ ] Stock delimiter can be configured
- [ ] Orders delimiter can be configured
- [ ] Settings persist correctly
- [ ] Old configs migrate automatically
- [ ] Default values work for new installs

### Integration
- [ ] Full analysis works with various CSV formats
- [ ] History file loads correctly
- [ ] Export files have correct format
- [ ] No regression in existing functionality

---

## 14. Conclusion

The current delimiter detection system has **significant gaps** that impact usability, especially for international users:

**Critical Issues:**
1. ❌ No encoding specification → Cyrillic characters may fail
2. ❌ Hardcoded orders delimiter → No flexibility
3. ❌ No auto-detection → Poor UX, easy to misconfigure

**Good Aspects:**
1. ✓ Stock delimiter is configurable
2. ✓ Some error handling exists (file_handler)
3. ✓ Clear UI for stock delimiter setting

**Recommended Action:**
Implement **Priorities 1-3 immediately** (encoding + auto-detection + error handling) as these are critical fixes that improve reliability without breaking changes. Total effort: ~7-8 hours.

Priorities 4-5 can follow in next release for better UX and consistency.

**Risk Assessment:**
- **Priority 1-3 changes:** Low risk, high reward
- **Priority 4-5 changes:** Medium risk (config migration), high reward
- **Priority 6-7 changes:** Low risk, medium reward

---

**End of Audit Report**

Generated: 2025-11-12
Report Version: 1.0
