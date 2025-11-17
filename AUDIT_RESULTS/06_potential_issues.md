# Potential Bugs and Code Smells

## Summary

**Total Issues Found:** 98

- 🔴 **CRITICAL:** 1
- 🔴 **HIGH:** 91
- 🟡 **MEDIUM:** 6
- 🟢 **LOW:** 0

## 🔴 CRITICAL Issues

These issues require immediate attention.

### Bare Except (1 occurrences)

- `unknown:187` - Bare except: clause (catches all exceptions including KeyboardInterrupt)

## 🔴 HIGH Priority Issues

### Broad Except (91 occurrences)

- `unknown:138` - Catching broad Exception type - consider specific exceptions
- `unknown:275` - Catching broad Exception type - consider specific exceptions
- `unknown:319` - Catching broad Exception type - consider specific exceptions
- `unknown:358` - Catching broad Exception type - consider specific exceptions
- `unknown:443` - Catching broad Exception type - consider specific exceptions
- `unknown:498` - Catching broad Exception type - consider specific exceptions
- `unknown:86` - Catching broad Exception type - consider specific exceptions
- `unknown:110` - Catching broad Exception type - consider specific exceptions
- `unknown:65` - Catching broad Exception type - consider specific exceptions
- `unknown:167` - Catching broad Exception type - consider specific exceptions
- `unknown:230` - Catching broad Exception type - consider specific exceptions
- `unknown:298` - Catching broad Exception type - consider specific exceptions
- `unknown:589` - Catching broad Exception type - consider specific exceptions
- `unknown:643` - Catching broad Exception type - consider specific exceptions
- `unknown:874` - Catching broad Exception type - consider specific exceptions
- ... and 76 more

## 🟡 MEDIUM Priority Issues

### Nested Try (5 occurrences)

**Count:** 5

- `unknown:857` - Deeply nested try-except blocks (depth: 3)
- `unknown:895` - Deeply nested try-except blocks (depth: 3)
- `unknown:561` - Deeply nested try-except blocks (depth: 3)
- `unknown:504` - Deeply nested try-except blocks (depth: 3)
- `unknown:156` - Deeply nested try-except blocks (depth: 4)

### Too Many Params (1 occurrences)

**Count:** 1

- `unknown:238` - Function run_full_analysis() has 10 parameters (>7)

## Circular Import Detection

✅ No obvious circular imports detected


## Recommendations by Priority

### 🔴 Critical (Immediate Action Required)

1. **Fix all bare except: clauses** - They catch system exits and keyboard interrupts
2. **Remove eval/exec calls** - Major security vulnerability
3. **Review exception handling** - Use specific exception types

### 🔴 High Priority

1. **Fix mutable default arguments** - Can cause subtle bugs
2. **Narrow exception catching** - Replace broad Exception with specific types
3. **Review circular imports** - Can cause import-time errors

### 🟡 Medium Priority

1. **Refactor functions with too many parameters** - Use config objects or dataclasses
2. **Simplify nested try-except blocks** - Improve code readability
3. **Review deep nesting** - Consider flattening control flow
