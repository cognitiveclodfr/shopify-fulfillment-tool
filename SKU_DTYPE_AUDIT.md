# SKU Data Type Audit Report

**Date:** 2025-11-12
**Issue:** Numeric SKUs displayed as "5170.0" instead of "5170", causing matching failures
**Severity:** 🔴 CRITICAL
**Status:** Audit Complete - Fix Required

---

## Executive Summary

**Root Cause:** Pandas auto-detects numeric SKUs as `float64` during CSV loading, which later becomes "5170.0" when converted to string, breaking SKU matching between orders and stock.

**Impact:**
- Stock matching failures → Wrong fulfillment status
- Orders marked "Not Fulfillable" when they should be "Fulfillable"
- Packing lists missing items
- Stock deductions not applied correctly

**Fix Required:** Force string dtype on CSV load + create centralized SKU normalization function

---

## 1. CSV Loading Locations

### 1.1 Orders CSV Loading

**Location:** `shopify_tool/core.py:359`

```python
orders_df = pd.read_csv(orders_file_path, delimiter=orders_delimiter, encoding='utf-8-sig')
```

- **CSV Column:** `"Lineitem sku"` → mapped to `"SKU"` (internal)
- **dtype parameter:** ❌ **NOT SPECIFIED**
- **Auto-detection:** If column contains only numbers (e.g., "5170", "5010"), pandas detects as `float64`
- **Result:** `5170` → `5170.0` (float)
- **Issue:** ✗ Later `.astype(str)` produces `"5170.0"` instead of `"5170"`

**Evidence from code:**
```python
# Column mapping (core.py:127-132)
orders_mappings = {
    "Name": "Order_Number",
    "Lineitem sku": "SKU",  # ← This column
    "Lineitem quantity": "Quantity",
    "Shipping Method": "Shipping_Method"
}
```

---

### 1.2 Stock CSV Loading

**Location:** `shopify_tool/core.py:333`

```python
stock_df = pd.read_csv(stock_file_path, delimiter=stock_delimiter, encoding='utf-8-sig')
```

- **CSV Column:** `"Артикул"` (Ukrainian for "SKU") → mapped to `"SKU"` (internal)
- **dtype parameter:** ❌ **NOT SPECIFIED**
- **Auto-detection:** Same issue - numeric SKUs become `float64`
- **Result:** `5170` → `5170.0` (float)
- **Issue:** ✗ Creates `"5170.0"` after string conversion

**Evidence from code:**
```python
# Column mapping (core.py:133-136)
stock_mappings = {
    "Артикул": "SKU",  # ← This column
    "Наличност": "Stock"
}
```

---

### 1.3 History CSV Loading

**Location:** `shopify_tool/core.py:415`

```python
history_df = pd.read_csv(history_path_str, encoding='utf-8-sig')
```

- **CSV Column:** `"SKU"` (direct, no mapping needed)
- **dtype parameter:** ❌ **NOT SPECIFIED**
- **Auto-detection:** Same float64 issue if history contains numeric SKUs
- **Result:** Potential matching issues with historical data
- **Issue:** ✗ May cause fulfillment history lookup failures

---

### 1.4 Stock Validation Loading (GUI)

**Location:** `gui/file_handler.py:178`

```python
stock_df = pd.read_csv(filepath, delimiter=delimiter, encoding='utf-8-sig')
```

- **Purpose:** Validate stock file before processing
- **dtype parameter:** ❌ **NOT SPECIFIED**
- **Issue:** ✗ Validation sees different data than actual processing

---

## 2. SKU Normalization

### 2.1 Current Implementation in `analysis.py`

**Orders Normalization - Location:** `shopify_tool/analysis.py:164`

```python
# CRITICAL: Normalize SKU to string for consistent merging
orders_clean_df["SKU"] = orders_clean_df["SKU"].astype(str).str.strip()
```

**Stock Normalization - Location:** `shopify_tool/analysis.py:180`

```python
# CRITICAL: Normalize SKU to string for consistent merging
stock_clean_df["SKU"] = stock_clean_df["SKU"].astype(str).str.strip()
```

**Problem Analysis:**
```
Scenario: Numeric SKU "5170" in CSV

1. CSV load without dtype: "5170" → pandas detects → 5170.0 (float64)
2. .astype(str):           5170.0 → "5170.0" (string with .0 suffix)
3. .str.strip():           "5170.0" → "5170.0" (no change, no trailing spaces)

Result: "5170.0" ≠ "5170" → MATCH FAILS
```

**Applied to:**
- ✓ Orders SKU
- ✓ Stock SKU
- ❌ History SKU (not normalized!)
- ❌ NOT applied before comparison (too late!)

---

### 2.2 Existing `normalize_sku` Function

**Location:** `shopify_tool/packing_lists.py:82-90`

```python
def normalize_sku(sku):
    """Normalize SKU: convert to string, remove leading zeros if numeric"""
    sku_str = str(sku).strip()
    try:
        # Try to convert to int to remove leading zeros: "07" -> 7 -> "7"
        return str(int(float(sku_str)))
    except (ValueError, TypeError):
        # Not a number, return as-is (handles alphanumeric SKUs)
        return sku_str
```

**Analysis:**
- ✓ **GOOD:** Converts `float` → `int` → `string` (removes .0 suffix)
- ✓ **GOOD:** `"5170.0"` → `int(5170.0)` → `5170` → `"5170"` ✓
- ✓ **GOOD:** Handles alphanumeric SKUs (ABC-123 stays ABC-123)
- ✓ **GOOD:** Removes leading zeros ("07" → "7")
- ❌ **BAD:** Only used in packing_lists.py, not in main analysis!
- ❌ **BAD:** Not applied at CSV load time
- ❌ **BAD:** Not used consistently across codebase

**Current Usage:**
- Used in: `packing_lists.py` for exclude SKU filtering
- NOT used in: `analysis.py` (main SKU matching!)
- NOT used in: `core.py` (CSV loading)
- NOT used in: History processing

**This function COULD solve the problem if applied everywhere!**

---

### 2.3 Normalization Gap Summary

| Location | Current Normalization | Issue |
|----------|----------------------|-------|
| Orders load | None | Auto-detection → float64 |
| Stock load | None | Auto-detection → float64 |
| History load | None | Auto-detection → float64 |
| Orders analysis | `.astype(str).str.strip()` | Produces "5170.0" |
| Stock analysis | `.astype(str).str.strip()` | Produces "5170.0" |
| Packing lists | `normalize_sku()` function | ✓ Works! But not used in analysis |

---

## 3. SKU Comparison Points

### 3.1 Stock Matching (Dictionary Lookup)

**Location:** `shopify_tool/analysis.py:191-200`

```python
live_stock = pd.Series(stock_clean_df.Stock.values, index=stock_clean_df.SKU).to_dict()
# Creates: {"5170.0": 100, "5010.0": 50, ...}

for order_number in prioritized_orders["Order_Number"]:
    order_items = orders_with_counts[orders_with_counts["Order_Number"] == order_number]
    for _, item in order_items.iterrows():
        sku, required_qty = item["SKU"], item["Quantity"]
        if required_qty > live_stock.get(sku, 0):  # ← LOOKUP FAILS HERE
            can_fulfill_order = False
```

**Problem:**
- Dictionary key: `"5170.0"` (from stock)
- Lookup key: `"5170"` (from orders - if originally string in Shopify CSV)
- Result: `live_stock.get("5170", 0)` returns `0` (not found!)
- Impact: Order marked as "Not Fulfillable" even though stock exists

**Current state:**
- Left: `orders_clean_df['SKU']` dtype = object (string, may have .0 suffix)
- Right: Dictionary keys from `stock_clean_df['SKU']` (may have .0 suffix)
- Normalized: ❌ NO - normalization happens before, but doesn't fix .0 issue

---

### 3.2 Merge Operations

**Location:** `shopify_tool/analysis.py:222,228,232`

```python
# Merge 1: Orders + Stock
final_df = pd.merge(orders_clean_df, stock_clean_df, on="SKU", how="left", suffixes=('', '_stock'))
# or
final_df = pd.merge(orders_clean_df, stock_clean_df, on="SKU", how="left")

# Merge 2: Add final stock levels
final_df = pd.merge(final_df, final_stock_levels, on="SKU", how="left")
```

**Problem:**
- If `orders_clean_df["SKU"]` has `"5170"` and `stock_clean_df["SKU"]` has `"5170.0"`:
  - Merge on "SKU" fails to match
  - Result: Stock column becomes NaN for that row
  - Order appears to have no stock available

**Impact:**
- Stock data not joined to orders
- Fulfillment status calculation broken
- Final_Stock values incorrect

---

### 3.3 Filtering Operations

**Location:** `shopify_tool/analysis.py:426,441,461`

```python
# Update stock
df.loc[df["SKU"] == sku, "Final_Stock"] += quantity

# Check current stock
current_stock = df.loc[df["SKU"] == sku, "Final_Stock"].iloc[0]

# Deduct stock
df.loc[df["SKU"] == sku, "Final_Stock"] -= needed_qty
```

**Problem:**
- If comparing `"5170"` == `"5170.0"`, condition is False
- No rows matched → `.iloc[0]` raises IndexError
- Stock updates silently fail

---

### 3.4 Exclude SKU Filtering

**Location:** `shopify_tool/packing_lists.py:100`

```python
sku_column_normalized = filtered_orders["SKU"].apply(normalize_sku)
exclude_skus_normalized = [normalize_sku(s) for s in exclude_skus]
mask = ~sku_column_normalized.isin(exclude_skus_normalized)
```

**Status:** ✓ **WORKING** - This is the ONLY place that uses proper normalization!

---

## 4. SKU Output Locations

### 4.1 Excel Exports

**Location:** `shopify_tool/core.py:482-484`

```python
final_df.to_excel(writer, sheet_name="fulfillment_analysis", index=False)
summary_present_df.to_excel(writer, sheet_name="Summary_Present", index=False)
summary_missing_df.to_excel(writer, sheet_name="Summary_Missing", index=False)
```

**Issue:** ✗ Excel shows "5170.0" in SKU columns (user-facing issue!)

---

### 4.2 History CSV

**Location:** `shopify_tool/core.py:556`

```python
updated_history.to_csv(history_path_str, index=False)
```

**Issue:**
- ✗ History file saved with "5170.0" format
- ✗ When loaded later, causes matching issues with new orders
- ✗ Compounds the problem over time

---

### 4.3 Packing Lists Excel

**Location:** `shopify_tool/packing_lists.py:147`

```python
print_list.to_excel(writer, sheet_name=sheet_name, index=False)
```

**Status:** ✓ Might work if normalize_sku is applied before export

---

### 4.4 Stock Export Excel

**Location:** `shopify_tool/stock_export.py:84`

```python
export_df.to_excel(writer, index=False, sheet_name="Sheet1")
```

**Issue:** ✗ Stock export shows "5170.0"

---

### 4.5 JSON API Data

**Location:** `shopify_tool/core.py:60`

```python
item_data = {
    "sku": str(row.get("SKU", "")),
    "product_name": str(row.get("Product_Name", "")),
    "quantity": int(row.get("Quantity", 0))
}
```

**Issue:** ✗ API returns `"sku": "5170.0"` to frontend

---

## 5. Root Cause Analysis

### Problem Flow Diagram

```
Step 1: CSV Loading (NO dtype specified)
┌─────────────────────────────────────────────┐
│ orders.csv contains: "5170"                 │
│ stock.csv contains:   5170  (no quotes)     │
└─────────────────────────────────────────────┘
                    ↓
         pandas.read_csv() auto-detection
                    ↓
┌─────────────────────────────────────────────┐
│ Orders: "5170" (string) → dtype object      │
│ Stock:   5170 (number) → dtype float64      │
│         Result: 5170.0                      │
└─────────────────────────────────────────────┘
                    ↓
Step 2: Normalization in analysis.py (.astype(str).str.strip())
                    ↓
┌─────────────────────────────────────────────┐
│ Orders: "5170" → str("5170") → "5170" ✓     │
│ Stock:  5170.0 → str(5170.0) → "5170.0" ✗   │
└─────────────────────────────────────────────┘
                    ↓
Step 3: SKU Comparison
                    ↓
┌─────────────────────────────────────────────┐
│ "5170" == "5170.0" → False                  │
│                                             │
│ Result: MATCH FAILS                         │
└─────────────────────────────────────────────┘
                    ↓
Step 4: Impact
┌─────────────────────────────────────────────┐
│ ✗ Merge on SKU fails                        │
│ ✗ Dictionary lookup fails                   │
│ ✗ Order marked "Not Fulfillable"            │
│ ✗ Stock not deducted                        │
│ ✗ Excel exports show "5170.0"               │
└─────────────────────────────────────────────┘
```

### Why This Happens

1. **Pandas Type Inference:**
   ```python
   # CSV contains numeric-looking data
   pd.read_csv("file.csv")  # No dtype specified
   # → Pandas sees: 5170, 5010, 5140
   # → Infers: "This looks like numbers, use float64"
   # → Result: 5170.0, 5010.0, 5140.0
   ```

2. **Float to String Conversion:**
   ```python
   pd.Series([5170.0]).astype(str)
   # → ["5170.0"]  (NOT "5170"!)
   ```

3. **String Comparison Fails:**
   ```python
   "5170" == "5170.0"  # False
   {"5170.0": 100}.get("5170", 0)  # Returns 0
   ```

---

## 6. Impact Assessment

### Severity: 🔴 CRITICAL

### Affected Features

- [x] **Stock matching** - Core functionality broken
- [x] **Fulfillment status** - Wrong status assigned
- [x] **Packing lists generation** - Missing items (partially mitigated by normalize_sku in packing_lists.py)
- [x] **Stock exports** - Shows incorrect SKU format
- [x] **Exclude SKU filtering** - Works (uses normalize_sku) ✓
- [x] **History checking** - Fails to match historical orders
- [x] **Excel reports** - User sees "5170.0" format
- [x] **JSON API** - Returns malformed SKUs to frontend

### User Impact

**Critical Issues:**
1. ✗ Orders that SHOULD be fulfillable marked as "Not Fulfillable"
2. ✗ Stock appears unavailable when it actually exists
3. ✗ Packing lists may be incomplete (though normalize_sku helps)
4. ✗ Stock deductions don't work correctly
5. ✗ Historical fulfillment data doesn't match current orders

**User Experience:**
- User uploads orders.csv and stock.csv
- Sees order with SKU "5170" has stock "5170.0"
- System says "Not Fulfillable" even though stock exists
- User manually fixes by editing CSV files (terrible UX!)

---

## 7. Evidence from Screenshot

Based on the reported issue:
- Orders show: "5170", "5010", "5140" (clean format)
- Stock shows: "5170.0", "5010.0", "5140.0" (float format)
- Fulfillment Status: "Not Fulfillable" (wrong!)
- Expected: Should match and mark as "Fulfillable"

This confirms the dtype auto-detection issue.

---

## 8. Recommendations

### ✅ Priority 1: Force String dtype on CSV Load (CRITICAL)

**Effort:** 2-3 hours

**Implementation:**
```python
# In core.py - orders loading
SKU_COLUMNS_ORDERS = ["Lineitem sku"]  # Add all potential SKU column names
dtype_orders = {col: str for col in SKU_COLUMNS_ORDERS}
orders_df = pd.read_csv(
    orders_file_path,
    delimiter=orders_delimiter,
    encoding='utf-8-sig',
    dtype=dtype_orders  # ← Force string
)

# In core.py - stock loading
SKU_COLUMNS_STOCK = ["Артикул"]
dtype_stock = {col: str for col in SKU_COLUMNS_STOCK}
stock_df = pd.read_csv(
    stock_file_path,
    delimiter=stock_delimiter,
    encoding='utf-8-sig',
    dtype=dtype_stock  # ← Force string
)

# In core.py - history loading
dtype_history = {"SKU": str}
history_df = pd.read_csv(
    history_path_str,
    encoding='utf-8-sig',
    dtype=dtype_history  # ← Force string
)
```

**Benefits:**
- Prevents float conversion at source
- "5170" stays as "5170", never becomes 5170.0
- Fixes root cause, not symptoms

**Considerations:**
- Column names come from mappings (dynamic)
- Need to extract mapped CSV columns, not internal names
- Handle both v1 and v2 config formats

---

### ✅ Priority 2: Centralize normalize_sku Function (HIGH)

**Effort:** 2-3 hours

**Implementation:**

1. **Move function to utils module:**
   ```python
   # In shopify_tool/utils.py (or create csv_utils.py)
   def normalize_sku(sku):
       """
       Normalize SKU to standard string format.

       Handles:
       - Float conversion artifacts (5170.0 → "5170")
       - Leading zeros for numeric SKUs ("07" → "7")
       - Whitespace (strips)
       - Alphanumeric SKUs (preserved as-is)
       - None/NaN values (returns empty string)

       Examples:
           5170.0 → "5170"
           "5170.0" → "5170"
           "5170" → "5170"
           " 5170 " → "5170"
           "ABC-123" → "ABC-123"
           "07" → "7"
           np.nan → ""
       """
       if pd.isna(sku):
           return ""

       sku_str = str(sku).strip()

       try:
           # Try to parse as number and back to remove .0 and leading zeros
           return str(int(float(sku_str)))
       except (ValueError, TypeError):
           # Not a number, return cleaned string
           return sku_str
   ```

2. **Import and use everywhere:**
   ```python
   # In analysis.py
   from shopify_tool.utils import normalize_sku

   # After loading and mapping
   orders_clean_df["SKU"] = orders_clean_df["SKU"].apply(normalize_sku)
   stock_clean_df["SKU"] = stock_clean_df["SKU"].apply(normalize_sku)

   # In core.py for history
   if not history_df.empty and 'SKU' in history_df.columns:
       history_df['SKU'] = history_df['SKU'].apply(normalize_sku)
   ```

**Benefits:**
- Single source of truth for SKU normalization
- Consistent behavior across codebase
- Easier to test and maintain
- Defensive: handles .0 suffix even if dtype is forced

---

### ✅ Priority 3: Apply Before All Comparisons (HIGH)

**Effort:** 2-3 hours

**Locations to update:**
1. ✓ `analysis.py:164` - Already has normalization (fix to use normalize_sku)
2. ✓ `analysis.py:180` - Already has normalization (fix to use normalize_sku)
3. ✓ `packing_lists.py:93` - Already uses normalize_sku ✓
4. ❌ `core.py:415` - History loading (add normalization)
5. ❌ `rules.py:261` - SKU comparison in rules (add normalization)

**Implementation:**
- Replace all `.astype(str).str.strip()` with `.apply(normalize_sku)`
- Add normalization after loading history
- Ensure normalized before merge/join/comparison

---

### ✅ Priority 4: Add Validation Warning (MEDIUM)

**Effort:** 1-2 hours

**Implementation:**
```python
# In file_handler.py or core.py validation
def validate_sku_format(df, column_name="SKU"):
    """Warn if SKU column contains float-like values"""
    if column_name in df.columns:
        # Check if any SKU has .0 suffix
        has_float_skus = df[column_name].astype(str).str.contains(r'\.0$', regex=True).any()

        if has_float_skus:
            logger.warning(
                f"Detected numeric SKUs with .0 suffix in {column_name} column. "
                f"This may indicate dtype auto-detection issue. "
                f"SKUs will be normalized automatically."
            )

            # Show examples
            float_skus = df[df[column_name].astype(str).str.contains(r'\.0$', regex=True)][column_name].head(5)
            logger.info(f"Example float SKUs: {float_skus.tolist()}")
```

**Benefits:**
- User visibility into data issues
- Easier debugging
- Builds trust (system acknowledges and handles the issue)

---

## 9. Testing Strategy

### Test Cases Required

| Test Case | Orders SKU | Stock SKU | Expected Match | Notes |
|-----------|-----------|-----------|----------------|-------|
| 1. Both string | "5170" | "5170" | ✓ YES | Baseline |
| 2. Mixed types | "5170" | 5170 | ✓ YES | Common case |
| 3. Float artifact | "5170" | "5170.0" | ✓ YES | Current bug |
| 4. Leading zeros | "07" | "7" | ✓ YES | normalize_sku handles |
| 5. Alphanumeric | "ABC-123" | "ABC-123" | ✓ YES | Must preserve |
| 6. With spaces | " 5170 " | "5170" | ✓ YES | Whitespace trim |
| 7. Empty/NaN | "" | "5170" | ✗ NO | Expected mismatch |
| 8. Case sensitive | "abc-123" | "ABC-123" | ? | Need to decide |

### Test Implementation

```python
# In tests/test_sku_normalization.py
def test_sku_matching_numeric():
    """Test that numeric SKUs match regardless of type"""
    orders = pd.DataFrame({"SKU": ["5170"]})
    stock = pd.DataFrame({"SKU": [5170]})

    # Apply normalization
    orders["SKU"] = orders["SKU"].apply(normalize_sku)
    stock["SKU"] = stock["SKU"].apply(normalize_sku)

    # Should match
    merged = pd.merge(orders, stock, on="SKU")
    assert len(merged) == 1

def test_sku_matching_float_artifact():
    """Test that float artifacts (5170.0) are normalized"""
    orders = pd.DataFrame({"SKU": ["5170"]})
    stock = pd.DataFrame({"SKU": ["5170.0"]})

    orders["SKU"] = orders["SKU"].apply(normalize_sku)
    stock["SKU"] = stock["SKU"].apply(normalize_sku)

    merged = pd.merge(orders, stock, on="SKU")
    assert len(merged) == 1
    assert merged["SKU"].iloc[0] == "5170"

def test_sku_dtype_force_on_load():
    """Test that forcing dtype=str prevents float conversion"""
    # Create CSV with numeric SKUs
    csv_content = "SKU,Stock\n5170,100\n5010,50"

    # Without dtype (broken)
    df_broken = pd.read_csv(io.StringIO(csv_content))
    assert df_broken["SKU"].dtype == np.float64
    assert df_broken["SKU"].iloc[0] == 5170.0

    # With dtype (fixed)
    df_fixed = pd.read_csv(io.StringIO(csv_content), dtype={"SKU": str})
    assert df_fixed["SKU"].dtype == object
    assert df_fixed["SKU"].iloc[0] == "5170"
```

---

## 10. Implementation Checklist

### Phase 1: Force String dtype (2-3 hours)

- [ ] Extract SKU column names from mappings
- [ ] Update `core.py:333` - Stock loading with dtype
- [ ] Update `core.py:359` - Orders loading with dtype
- [ ] Update `core.py:415` - History loading with dtype
- [ ] Update `file_handler.py:178` - Validation loading with dtype
- [ ] Handle dynamic column names from config
- [ ] Test with numeric SKU CSV files

### Phase 2: Centralize normalize_sku (2-3 hours)

- [ ] Create/update `shopify_tool/utils.py`
- [ ] Move normalize_sku function with full docstring
- [ ] Add unit tests for normalize_sku
- [ ] Update imports in `analysis.py`
- [ ] Update imports in `packing_lists.py`
- [ ] Replace `.astype(str).str.strip()` with `.apply(normalize_sku)`

### Phase 3: Apply Everywhere (2-3 hours)

- [ ] Update `analysis.py:164` - Orders SKU
- [ ] Update `analysis.py:180` - Stock SKU
- [ ] Add normalization for history SKU in core.py
- [ ] Update `rules.py` SKU comparisons
- [ ] Verify all merge/join operations
- [ ] Verify all filter operations

### Phase 4: Validation & Testing (1-2 hours)

- [ ] Add SKU format validation warning
- [ ] Create test cases for SKU matching
- [ ] Test with real CSV files (numeric SKUs)
- [ ] Test with alphanumeric SKUs
- [ ] Test Excel exports (verify no .0 suffix)
- [ ] Test JSON API output
- [ ] Integration test: full analysis run

### Phase 5: Documentation (30 min)

- [ ] Update README with SKU handling notes
- [ ] Add comments to code explaining dtype forcing
- [ ] Document normalize_sku function behavior
- [ ] Add migration notes for existing users

---

## 11. Estimated Total Effort

| Phase | Estimated Time |
|-------|----------------|
| Priority 1: Force dtype | 2-3 hours |
| Priority 2: Centralize normalize_sku | 2-3 hours |
| Priority 3: Apply everywhere | 2-3 hours |
| Priority 4: Validation | 1-2 hours |
| Testing | 1-2 hours |
| Documentation | 30 min |
| **TOTAL** | **8.5-13.5 hours** |

**Recommended Approach:** 1.5-2 days of focused work

---

## 12. Risks & Mitigations

### Risk 1: Breaking Alphanumeric SKUs

**Mitigation:**
- normalize_sku has try/except to preserve non-numeric SKUs
- Add comprehensive tests
- Test with real data before deployment

### Risk 2: Performance Impact

**Concern:** `.apply(normalize_sku)` on large DataFrames

**Mitigation:**
- Vectorized operations where possible
- Profile with real data (thousands of SKUs)
- Consider caching if needed

### Risk 3: Existing History Files

**Concern:** History CSV may have "5170.0" format

**Mitigation:**
- normalize_sku handles this automatically
- No data migration needed
- Old and new formats will match after normalization

### Risk 4: Config Column Name Mismatch

**Concern:** dtype dict needs exact CSV column names

**Mitigation:**
- Extract from column_mappings config
- Test with both v1 and v2 config formats
- Add validation

---

## 13. Conclusion

**Current State:** CRITICAL BUG - Numeric SKUs don't match, breaking core functionality

**Root Cause:** Pandas dtype auto-detection + incorrect string conversion

**Solution:** Two-pronged approach
1. **Preventive:** Force `dtype=str` on CSV load (stops float conversion at source)
2. **Defensive:** Apply `normalize_sku()` everywhere (handles legacy data and edge cases)

**Benefits:**
- ✓ SKU matching works for all formats
- ✓ Clean SKU display in exports (no .0 suffix)
- ✓ Correct fulfillment status
- ✓ Stock deductions work properly
- ✓ Consistent behavior across codebase
- ✓ Future-proof against similar issues

**Next Steps:** Proceed with implementation following the checklist above.

---

**Audit Completed By:** Claude (AI)
**Report Date:** 2025-11-12
**Status:** Ready for implementation ✓
