# Performance Issues Analysis

## Summary

**Total Performance Issues Found:** 131

- 🔴 **CRITICAL:** 0
- 🔴 **HIGH:** 27
- 🟡 **MEDIUM:** 96
- 🟢 **LOW:** 8

## 🔴 HIGH Priority Performance Issues

### Df Iterrows (13 occurrences)

**Problem:** `DataFrame.iterrows()` is very slow for large DataFrames

**Solution:** Use vectorized operations or `.apply()` method

**Example:**
```python
# Bad
for idx, row in df.iterrows():
    df.at[idx, 'new_col'] = row['col1'] + row['col2']

# Good
df['new_col'] = df['col1'] + df['col2']
```

**Occurrences:**
- `shopify_tool/analysis.py:266` - Using DataFrame.iterrows() - consider vectorized operations instead
- `shopify_tool/analysis.py:274` - Using DataFrame.iterrows() - consider vectorized operations instead
- `shopify_tool/analysis.py:359` - Using DataFrame.iterrows() - consider vectorized operations instead
- `shopify_tool/stock_export.py:99` - Using DataFrame.iterrows() - consider vectorized operations instead
- `shopify_tool/core.py:93` - Using DataFrame.iterrows() - consider vectorized operations instead
- `shopify_tool/set_decoder.py:62` - Using DataFrame.iterrows() - consider vectorized operations instead
- `shopify_tool/set_decoder.py:210` - Using DataFrame.iterrows() - consider vectorized operations instead
- `gui/actions_handler.py:448` - Using DataFrame.iterrows() - consider vectorized operations instead
- `gui/actions_handler.py:915` - Using DataFrame.iterrows() - consider vectorized operations instead
- `gui/actions_handler.py:927` - Using DataFrame.iterrows() - consider vectorized operations instead
- `gui/actions_handler.py:1072` - Using DataFrame.iterrows() - consider vectorized operations instead
- `gui/actions_handler.py:1081` - Using DataFrame.iterrows() - consider vectorized operations instead
- `gui/actions_handler.py:1104` - Using DataFrame.iterrows() - consider vectorized operations instead

### Io In Loop (13 occurrences)

**Problem:** File I/O operations in loops are very slow

**Solution:** Batch operations or collect data first, then write once

**Occurrences:**
- `shopify_tool/stock_export.py:96` - File I/O operation (write) inside loop - consider batching
- `shopify_tool/stock_export.py:101` - File I/O operation (write) inside loop - consider batching
- `shopify_tool/packing_lists.py:168` - File I/O operation (write) inside loop - consider batching
- `shopify_tool/packing_lists.py:199` - File I/O operation (write) inside loop - consider batching
- `shared/stats_manager.py:211` - File open() inside loop - consider batching operations
- `shared/stats_manager.py:214` - File I/O operation (read) inside loop - consider batching
- `shared/stats_manager.py:261` - File open() inside loop - consider batching operations
- `shared/stats_manager.py:265` - File I/O operation (dump) inside loop - consider batching
- `shared/stats_manager.py:288` - File open() inside loop - consider batching operations
- `shared/stats_manager.py:289` - File I/O operation (dump) inside loop - consider batching
- `shared/stats_manager.py:292` - File open() inside loop - consider batching operations
- `shared/stats_manager.py:296` - File I/O operation (read) inside loop - consider batching
- `shared/stats_manager.py:323` - File I/O operation (dump) inside loop - consider batching

### Nested Loops (1 occurrences)

**Problem:** Nested loops can have exponential time complexity

**Solution:** Consider using dictionaries/sets for lookups, or vectorized operations

**Occurrences:**
- `shopify_tool/rules.py:182` - Deeply nested loops (depth: 3) - potential O(n^3) complexity

## 🟡 MEDIUM Priority Performance Issues

### Append In Loop (42 occurrences)

**Files with most occurrences:**
- `gui/settings_window_pyside.py`: 10 occurrences
- `shopify_tool/core.py`: 5 occurrences
- `shopify_tool/set_decoder.py`: 5 occurrences
- `shopify_tool/rules.py`: 4 occurrences
- `gui/file_handler.py`: 4 occurrences
- `shopify_tool/session_manager.py`: 3 occurrences
- `shopify_tool/analysis.py`: 2 occurrences
- `gui/actions_handler.py`: 2 occurrences
- `gui/report_selection_dialog.py`: 2 occurrences
- `shopify_tool/stock_export.py`: 1 occurrences

### Large Data Op (39 occurrences)

**Note:** These operations can be memory-intensive with large datasets

**Files with most occurrences:**
- `shopify_tool/analysis.py`: 13 occurrences
- `gui/actions_handler.py`: 9 occurrences
- `shopify_tool/set_decoder.py`: 4 occurrences
- `shopify_tool/undo_manager.py`: 3 occurrences
- `shopify_tool/rules.py`: 2 occurrences
- `shared/stats_manager.py`: 2 occurrences
- `shopify_tool/stock_export.py`: 1 occurrences
- `shopify_tool/core.py`: 1 occurrences
- `shopify_tool/csv_utils.py`: 1 occurrences
- `shopify_tool/packing_lists.py`: 1 occurrences

### String Concat In Loop (15 occurrences)

**Problem:** String concatenation in loops creates many intermediate objects

**Solution:** Use `''.join(list)` or accumulate in a list

**Files with most occurrences:**
- `shopify_tool/packing_lists.py`: 5 occurrences
- `shared/stats_manager.py`: 3 occurrences
- `shopify_tool/core.py`: 2 occurrences
- `shopify_tool/stock_export.py`: 1 occurrences
- `shopify_tool/profile_manager.py`: 1 occurrences
- `shopify_tool/rules.py`: 1 occurrences
- `gui/tag_delegate.py`: 1 occurrences
- `gui/settings_window_pyside.py`: 1 occurrences

## 🟢 LOW Priority Performance Notes

### Large Data Op: 8 occurrences


## Performance Optimization Recommendations

### 🔴 Immediate Actions

1. **Replace DataFrame.iterrows()** with vectorized operations
2. **Move file I/O outside of loops** - batch read/write operations
3. **Optimize nested loops** - use dictionaries for O(1) lookups

### 🟡 Recommended Improvements

1. **Review DataFrame operations** - ensure they're necessary
2. **Check string building in loops** - use join() where appropriate
3. **Consider chunking for large files** - reduce memory usage

### General Best Practices

1. **Profile before optimizing** - use cProfile or line_profiler to find bottlenecks
2. **Use vectorized operations** - NumPy/Pandas operations are much faster than Python loops
3. **Batch I/O operations** - minimize disk access
4. **Consider caching** - for expensive repeated calculations
5. **Monitor memory usage** - especially with large DataFrames

## Summary Table

| Issue Type | Count | Severity | Est. Impact |
|------------|-------|----------|-------------|
| Df Iterrows | 13 | 🔴 HIGH | High |
| Io In Loop | 13 | 🔴 HIGH | High |
| Nested Loops | 1 | 🔴 HIGH | High |
| Large Data Op | 47 | 🟡 MEDIUM | Medium |
| Append In Loop | 42 | 🟡 MEDIUM | Medium |
| String Concat In Loop | 15 | 🟡 MEDIUM | Medium |
