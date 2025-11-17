# Dependency Analysis

## 1. Declared Dependencies

### Production Requirements (requirements.txt)

| Package | Version Constraint |
|---------|-------------------|
| `numpy` | `>=2.3.0` |
| `openpyxl` | `>=3.0.0` |
| `pandas` | `>=2.3.0` |
| `pyside6` | `>=6.5.0` |
| `python-dateutil` | `>=2.8.0` |
| `pytz` | `>=2025.1` |
| `six` | `>=1.17.0` |
| `typing_extensions` | `>=4.0.0` |
| `tzdata` | `>=2025.1` |
| `xlrd` | `>=2.0.0` |
| `xlsxwriter` | `>=3.0.0` |
| `xlutils` | `>=2.0.0` |
| `xlwt` | `>=1.3.0` |

### Development Requirements (requirements-dev.txt)

| Package | Version Constraint |
|---------|-------------------|
| `altgraph` | `>=0.17.0` |
| `iniconfig` | `>=2.0.0` |
| `packaging` | `>=24.0` |
| `pluggy` | `>=1.0.0` |
| `pyinstaller` | `>=6.0.0` |
| `pyinstaller-hooks-contrib` | `>=2025.0` |
| `pytest` | `>=8.0.0` |
| `pytest-cov` | `>=4.0.0` |
| `pytest-mock` | `>=3.10.0` |
| `pytest-qt` | `>=4.0.0` |
| `ruff` | `>=0.1.0` |

## 2. Actual Imports Used in Code

**Total unique imports:** 37

### Standard Library Imports

**Count:** 18

Modules used: `collections`, `csv`, `datetime`, `functools`, `json`, `logging`, `os`, `pathlib`, `pickle`, `platform`, `re`, `shutil`, `subprocess`, `sys`, `tempfile`, `time`, `traceback`, `typing`


### Third-Party Library Imports

**Count:** 16

- `PySide6`
- `contextlib`
- `csv_utils`
- `customtkinter`
- `fcntl`
- `logger_config`
- `msvcrt`
- `numpy`
- `pandas`
- `pandas_model`
- `rules`
- `set_decoder`
- `stats_manager`
- `tkinter`
- `utils`
- `xlwt`

### Internal Package Imports

**Count:** 3

- `gui`
- `shared`
- `shopify_tool`

## 3. Dependency Verification

### ⚠️ Packages Used But Not in requirements.txt

- `PySide6` (imported in code but not declared)
- `contextlib` (imported in code but not declared)
- `csv_utils` (imported in code but not declared)
- `customtkinter` (imported in code but not declared)
- `fcntl` (imported in code but not declared)
- `logger_config` (imported in code but not declared)
- `msvcrt` (imported in code but not declared)
- `pandas_model` (imported in code but not declared)
- `rules` (imported in code but not declared)
- `set_decoder` (imported in code but not declared)
- `stats_manager` (imported in code but not declared)
- `tkinter` (imported in code but not declared)
- `utils` (imported in code but not declared)

**Recommendation:** 🔴 Add these packages to requirements.txt
**Priority:** HIGH

### ⚠️ Packages in requirements.txt Potentially Not Used

**Note:** This may include packages used only at runtime or indirectly.

- `openpyxl` (declared but not directly imported)
- `pyside6` (declared but not directly imported)
- `python-dateutil` (declared but not directly imported)
- `pytz` (declared but not directly imported)
- `six` (declared but not directly imported)
- `typing_extensions` (declared but not directly imported)
- `tzdata` (declared but not directly imported)
- `xlrd` (declared but not directly imported)
- `xlsxwriter` (declared but not directly imported)
- `xlutils` (declared but not directly imported)

**Recommendation:** 🟡 Verify if these packages are actually needed
**Priority:** MEDIUM

## 4. Dependency Usage by Module

### Core Business Logic (`shopify_tool/`)

Third-party dependencies: csv_utils, fcntl, logger_config, msvcrt, numpy, pandas, rules, set_decoder, utils, xlwt

### GUI Layer (`gui/`)

Third-party dependencies: PySide6, customtkinter, pandas, pandas_model, tkinter

### Shared Utilities (`shared/`)

Third-party dependencies: contextlib, fcntl, msvcrt, stats_manager

## 5. Version Constraint Analysis

### Flexible Versions (>=)

**Count:** 13

Packages: `pandas`, `numpy`, `python-dateutil`, `pytz`, `tzdata`, `openpyxl`, `xlsxwriter`, `xlrd`, `xlwt`, `xlutils`, `pyside6`, `six`, `typing_extensions`

✅ **Good:** Allows minor and patch updates

### Pinned Versions (==)

**Count:** 0

### Range Constraints

**Count:** 0

## 6. Security & Maintenance

### Version Update Strategy

✅ **Status:** GOOD - Mostly using flexible version constraints (>=)

**Benefit:** Allows receiving security patches and bug fixes


### Recommendations for Dependency Management

1. **Regular Updates:** Run `pip list --outdated` to check for updates
2. **Security Scanning:** Use `pip-audit` or `safety` to check for vulnerabilities
3. **Lock File:** Consider using `pip-compile` to generate a lock file for reproducible builds
4. **Virtual Environment:** Always use virtual environments to isolate dependencies
5. **Minimal Dependencies:** Periodically review and remove unused packages

## Summary

| Metric | Value | Status |
|--------|-------|--------|
| Declared Dependencies | 13 | - |
| Dev Dependencies | 11 | - |
| Third-Party Imports | 16 | - |
| Missing from requirements.txt | 13 | 🔴 ACTION NEEDED |
| Potentially Unused | 10 | 🟡 REVIEW |
| Flexible Version Constraints | 13 | ✅ GOOD |
| Pinned Versions | 0 | ✅ GOOD |

## Priority Actions

### 🔴 HIGH PRIORITY

1. Add missing packages to requirements.txt:
   - `PySide6`
   - `contextlib`
   - `csv_utils`
   - `customtkinter`
   - `fcntl`
   - `logger_config`
   - `msvcrt`
   - `pandas_model`
   - `rules`
   - `set_decoder`
   - `stats_manager`
   - `tkinter`
   - `utils`

### 🟡 MEDIUM PRIORITY

1. Review potentially unused packages:
   - `openpyxl` - check if really needed
   - `pyside6` - check if really needed
   - `python-dateutil` - check if really needed
   - `pytz` - check if really needed
   - `six` - check if really needed
   - `typing_extensions` - check if really needed
   - `tzdata` - check if really needed
   - `xlrd` - check if really needed
   - `xlsxwriter` - check if really needed
   - `xlutils` - check if really needed

### 🟢 LOW PRIORITY

1. Set up automated dependency scanning
2. Create a dependency update schedule
3. Document dependency purposes in requirements.txt
