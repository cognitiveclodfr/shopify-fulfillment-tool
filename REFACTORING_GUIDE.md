# Refactoring Guide - Shopify Fulfillment Tool

## Introduction

This guide provides step-by-step instructions for refactoring the Shopify Fulfillment Tool based on issues identified in `CRITICAL_ANALYSIS.md`. Follow the phases in order to minimize risk and maintain stability.

**Important**: Read `CRITICAL_ANALYSIS.md` first to understand the full context of each issue.

---

## Prerequisites

Before starting any refactoring:

1. ✅ **Ensure all tests pass**: `pytest tests/`
2. ✅ **Create a backup branch**: `git checkout -b backup-before-refactoring`
3. ✅ **Review CRITICAL_ANALYSIS.md** (especially sections 1-4)
4. ✅ **Add tests for current functionality** (if missing)
5. ✅ **Ensure code is committed**: Clean working directory

---

## Phase 1: Critical Fixes (2-3 weeks)

### Priority: HIGH - Do these first!

These fixes address data integrity issues and maintainability blockers.

---

### 1.1 Fix EXCLUDE_SKU Destructive Behavior

**Issue**: CRITICAL_ANALYSIS.md Section 1.2
**Severity**: High (data loss risk)
**Files**: `shopify_tool/rules.py`

#### Current Problem
```python
# DESTRUCTIVE - destroys original quantity!
df.loc[final_matches, "Quantity"] = 0
```

#### Solution
```python
# Add to RuleEngine._ensure_columns:
if "_excluded_skus" not in df.columns:
    df["_excluded_skus"] = ""
if "_original_quantity" not in df.columns:
    df["_original_quantity"] = df["Quantity"].copy()

# Replace EXCLUDE_SKU action:
elif action_type == "EXCLUDE_SKU":
    if "SKU" in df.columns:
        sku_to_exclude = value
        sku_matches = df["SKU"] == sku_to_exclude
        final_matches = matches & sku_matches

        # Mark as excluded (non-destructive)
        df.loc[final_matches, "_excluded_skus"] = sku_to_exclude

        # Add tag without duplicating
        current_notes = df.loc[final_matches, "Status_Note"].fillna("").astype(str)
        mask = ~current_notes.str.contains("SKU_EXCLUDED", regex=False)
        new_notes = current_notes.where(~mask, current_notes + ", SKU_EXCLUDED")
        df.loc[final_matches, "Status_Note"] = new_notes
```

#### Testing
1. Create test with excluded SKU
2. Verify original quantity preserved in `_original_quantity`
3. Verify SKU marked in `_excluded_skus`
4. Verify tag added without duplication
5. Test re-running rules doesn't double-modify

---

### 1.2 Implement Result Objects for Consistent Error Handling

**Issue**: CRITICAL_ANALYSIS.md Section 5.1
**Severity**: Medium (inconsistent API)
**Files**: `shopify_tool/core.py`, all backend modules

#### Create Result Class
```python
# shopify_tool/result.py
from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class Result:
    """Standard result object for all operations."""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[list] = None

    @classmethod
    def ok(cls, data=None, message=None):
        """Create successful result."""
        return cls(success=True, data=data, message=message)

    @classmethod
    def error(cls, message, errors=None):
        """Create error result."""
        return cls(success=False, message=message, errors=errors)

    def __bool__(self):
        """Allow if result: ... syntax."""
        return self.success
```

#### Refactor Functions
```python
# BEFORE:
def run_full_analysis(...):
    if errors:
        return False, "Validation failed", None, None
    return True, "Success", df, stats

# AFTER:
def run_full_analysis(...):
    if errors:
        return Result.error("Validation failed", errors=errors)
    return Result.ok(
        data={"dataframe": df, "stats": stats},
        message="Analysis complete"
    )

# Usage in GUI:
result = core.run_full_analysis(...)
if result:  # Truthy check uses __bool__
    self.analysis_results_df = result.data["dataframe"]
    self.analysis_stats = result.data["stats"]
else:
    QMessageBox.critical(self, "Error", result.message)
```

#### Migration Strategy
1. Create `Result` class
2. Add tests for `Result` class
3. Refactor one function at a time:
   - `validate_csv_headers` first (simple)
   - Then `run_full_analysis`
   - Then report functions
4. Update GUI handlers to use Result
5. Remove old tuple unpacking

---

### 1.3 Consolidate Operator Definitions

**Issue**: CRITICAL_ANALYSIS.md Section 1.1
**Severity**: Medium (maintenance burden)
**Files**: `shopify_tool/rules.py`, `gui/settings_window_pyside.py`

#### Create Operator Registry
```python
# shopify_tool/operators.py
from enum import Enum
from typing import Callable
import pandas as pd

class OperatorType(Enum):
    """Operator applicability."""
    TEXT = "text"
    NUMERIC = "numeric"
    GENERAL = "general"

class OperatorRegistry:
    """Centralized operator definitions."""

    # Define all operators once
    _OPERATORS = {
        "equals": {
            "function": lambda series, value: series == value,
            "types": [OperatorType.TEXT, OperatorType.NUMERIC],
            "pandas_query": "==",
            "display_name": "equals"
        },
        "contains": {
            "function": lambda series, value: series.str.contains(value, case=False, na=False),
            "types": [OperatorType.TEXT],
            "pandas_query": "contains",
            "display_name": "contains"
        },
        # ... add all operators
    }

    @classmethod
    def get_rule_operators(cls):
        """Get operators for rule engine."""
        return {k: v["function"] for k, v in cls._OPERATORS.items()}

    @classmethod
    def get_filter_operators(cls):
        """Get operators for report filters (pandas query)."""
        return {k: v["pandas_query"] for k, v in cls._OPERATORS.items()}

    @classmethod
    def get_operators_by_type(cls, op_type: OperatorType):
        """Get operators for a specific data type."""
        return [k for k, v in cls._OPERATORS.items() if op_type in v["types"]]
```

#### Refactor Rules Engine
```python
# shopify_tool/rules.py
from .operators import OperatorRegistry

OPERATOR_MAP = OperatorRegistry.get_rule_operators()

# No changes needed to _get_matching_rows - it uses OPERATOR_MAP
```

#### Refactor Settings Window
```python
# gui/settings_window_pyside.py
from shopify_tool.operators import OperatorRegistry, OperatorType

class SettingsWindow(QDialog):
    # REMOVE old constants
    # OPERATORS_BY_TYPE = {...}
    # FILTER_OPERATORS = [...]

    # USE registry instead
    def _get_operators_for_field(self, field, df):
        """Get appropriate operators based on field type."""
        if field in df.columns and pd.api.types.is_numeric_dtype(df[field]):
            return OperatorRegistry.get_operators_by_type(OperatorType.NUMERIC)
        else:
            return OperatorRegistry.get_operators_by_type(OperatorType.TEXT)
```

---

### 1.4 Fix Hardcoded Cyrillic Column Names

**Issue**: CRITICAL_ANALYSIS.md Section 4.1
**Severity**: High (not internationalized)
**Files**: `shopify_tool/analysis.py`, `shopify_tool/core.py`

#### Update core.py to Pass Column Mappings
```python
# shopify_tool/core.py
def run_full_analysis(stock_file_path, orders_file_path, output_dir_path, stock_delimiter, config):
    # ... existing code ...

    # Extract column mappings
    column_mappings = config.get("column_mappings", {})
    orders_cols = column_mappings.get("orders", {})
    stock_cols = column_mappings.get("stock", {})

    # Pass to analysis
    final_df, summary_present, summary_missing, stats = analysis.run_analysis(
        stock_df,
        orders_df,
        history_df,
        column_mappings={"orders": orders_cols, "stock": stock_cols}
    )
```

#### Update analysis.py to Use Mappings
```python
# shopify_tool/analysis.py
def run_analysis(stock_df, orders_df, history_df, column_mappings=None):
    """Run analysis with configurable column mappings."""

    # Default mappings for backward compatibility
    if column_mappings is None:
        column_mappings = {
            "orders": {
                "name": "Name",
                "sku": "Lineitem sku",
                "quantity": "Lineitem quantity"
            },
            "stock": {
                "sku": "Артикул",
                "name": "Име",
                "stock": "Наличност"
            }
        }

    # Use mappings
    orders_cols = column_mappings["orders"]
    stock_cols = column_mappings["stock"]

    # REPLACE hardcoded:
    # stock_clean_df = stock_df[["Артикул", "Име", "Наличност"]].copy()

    # WITH configurable:
    stock_clean_df = stock_df[[
        stock_cols["sku"],
        stock_cols.get("name", "Product_Name"),
        stock_cols["stock"]
    ]].copy()

    stock_clean_df = stock_clean_df.rename(columns={
        stock_cols["sku"]: "SKU",
        stock_cols.get("name", "Product_Name"): "Product_Name",
        stock_cols["stock"]: "Stock"
    })
```

#### Update config.json
```json
{
  "profiles": {
    "Default": {
      "column_mappings": {
        "orders": {
          "name": "Name",
          "sku": "Lineitem sku",
          "quantity": "Lineitem quantity"
        },
        "stock": {
          "sku": "Артикул",
          "name": "Име",
          "stock": "Наличност"
        }
      }
    }
  }
}
```

---

### 1.5 Add Rule Validation Before Execution

**Issue**: CRITICAL_ANALYSIS.md Section 1.3
**Severity**: Medium (runtime errors)
**Files**: `shopify_tool/rules.py`

#### Add Validation Method
```python
# shopify_tool/rules.py
class RuleEngine:
    def __init__(self, rules_config):
        self.rules = rules_config
        self.validate_rules()  # NEW

    def validate_rules(self):
        """Validates all rules before execution.

        Raises:
            ValueError: If any rule is invalid
        """
        errors = []

        for i, rule in enumerate(self.rules):
            # Validate rule name
            if not rule.get("name"):
                errors.append(f"Rule {i}: Missing 'name' field")

            # Validate conditions
            conditions = rule.get("conditions", [])
            if not conditions:
                errors.append(f"Rule '{rule.get('name')}': No conditions defined")

            for j, condition in enumerate(conditions):
                if not condition.get("field"):
                    errors.append(
                        f"Rule '{rule.get('name')}', Condition {j}: Missing 'field'"
                    )
                operator = condition.get("operator")
                if operator and operator not in OPERATOR_MAP:
                    errors.append(
                        f"Rule '{rule.get('name')}', Condition {j}: "
                        f"Invalid operator '{operator}'"
                    )
                if "value" not in condition:
                    errors.append(
                        f"Rule '{rule.get('name')}', Condition {j}: Missing 'value'"
                    )

            # Validate actions
            actions = rule.get("actions", [])
            if not actions:
                errors.append(f"Rule '{rule.get('name')}': No actions defined")

            valid_action_types = [
                "ADD_TAG", "SET_STATUS", "SET_PRIORITY",
                "EXCLUDE_FROM_REPORT", "EXCLUDE_SKU"
            ]
            for j, action in enumerate(actions):
                action_type = action.get("type", "").upper()
                if action_type not in valid_action_types:
                    errors.append(
                        f"Rule '{rule.get('name')}', Action {j}: "
                        f"Invalid action type '{action_type}'"
                    )
                if "value" not in action and action_type != "EXCLUDE_FROM_REPORT":
                    errors.append(
                        f"Rule '{rule.get('name')}', Action {j}: Missing 'value'"
                    )

        if errors:
            raise ValueError(
                "Rule validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )
```

---

## Phase 2: Code Quality Improvements (1-2 weeks)

### 2.1 Extract Settings Saving Methods

**Issue**: CRITICAL_ANALYSIS.md Section 2.1
**Severity**: High (97-line method)
**Files**: `gui/settings_window_pyside.py`

#### Refactor save_settings
```python
# gui/settings_window_pyside.py
def save_settings(self):
    """Saves all settings from UI back into config dictionary."""
    try:
        self._save_general_settings()
        self._save_paths()
        self._save_rules()
        self._save_packing_lists()
        self._save_stock_exports()
        self._save_mappings()
        self.accept()
    except ValueError as e:
        QMessageBox.critical(self, "Validation Error", str(e))
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

def _save_general_settings(self):
    """Saves general tab settings."""
    delimiter = self.stock_delimiter_edit.text()
    if len(delimiter) != 1:
        raise ValueError("Stock CSV delimiter must be a single character")
    self.config_data["settings"]["stock_csv_delimiter"] = delimiter

    threshold_text = self.low_stock_edit.text()
    if not threshold_text.isdigit() or int(threshold_text) < 0:
        raise ValueError("Low Stock Threshold must be a non-negative integer")
    self.config_data["settings"]["low_stock_threshold"] = int(threshold_text)

def _save_paths(self):
    """Saves path settings."""
    self.config_data["paths"]["templates"] = self.templates_path_edit.text()
    self.config_data["paths"]["output_dir_stock"] = self.stock_output_path_edit.text()

def _save_rules(self):
    """Saves rules tab settings."""
    rules_list = []
    for rule_w in self.rule_widgets:
        # ... existing rules saving logic
    self.config_data["rules"] = rules_list

# ... similar for other tabs
```

---

### 2.2 Replace JSON Deep Copy with copy.deepcopy

**Issue**: CRITICAL_ANALYSIS.md Section 2.3
**Severity**: Low (inefficient)
**Files**: `gui/settings_window_pyside.py`

```python
# BEFORE:
import json
self.config_data = json.loads(json.dumps(config))

# AFTER:
import copy
self.config_data = copy.deepcopy(config)
```

---

### 2.3 Add Type Hints to Public APIs

**Issue**: CRITICAL_ANALYSIS.md Section 6.1
**Severity**: Low (maintainability)
**Files**: All backend modules

```python
# Example for core.py
from typing import Dict, List, Tuple, Optional
import pandas as pd

def run_full_analysis(
    stock_file_path: Optional[str],
    orders_file_path: Optional[str],
    output_dir_path: str,
    stock_delimiter: str,
    config: Dict
) -> Tuple[bool, Optional[str], Optional[pd.DataFrame], Optional[Dict]]:
    """Orchestrates the entire fulfillment analysis process.

    Args:
        stock_file_path: Path to stock CSV, or None for testing
        orders_file_path: Path to orders CSV, or None for testing
        output_dir_path: Directory for output files
        stock_delimiter: Delimiter for stock CSV
        config: Application configuration dictionary

    Returns:
        Tuple of (success, message, dataframe, stats)
    """
    ...
```

---

## Phase 3: Architectural Refactoring (3-4 weeks)

### 3.1 Implement ProfileManager Service

**Issue**: CRITICAL_ANALYSIS.md Section 3.1
**Severity**: High (tight coupling)
**Files**: New `shopify_tool/profile_manager.py`, `gui/main_window_pyside.py`

#### Create ProfileManager Service
```python
# shopify_tool/profile_manager.py
import json
import copy
from typing import Dict, List, Optional

class ProfileManager:
    """Service for managing profile operations independently of UI."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Load configuration from file."""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_config(self) -> None:
        """Save configuration to file."""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get_profile(self, name: str) -> Optional[Dict]:
        """Get profile configuration by name."""
        return self.config.get("profiles", {}).get(name)

    def list_profiles(self) -> List[str]:
        """Get list of all profile names."""
        return sorted(self.config.get("profiles", {}).keys())

    def create_profile(self, name: str, base_profile_name: str = "Default") -> None:
        """Create a new profile.

        Args:
            name: Name for the new profile
            base_profile_name: Profile to copy from

        Raises:
            ValueError: If profile already exists
        """
        if name in self.config.get("profiles", {}):
            raise ValueError(f"Profile '{name}' already exists")

        base_config = self.config["profiles"].get(base_profile_name, {})
        self.config["profiles"][name] = copy.deepcopy(base_config)
        self.save_config()

    def rename_profile(self, old_name: str, new_name: str) -> None:
        """Rename an existing profile.

        Raises:
            ValueError: If old name doesn't exist or new name already exists
        """
        if old_name not in self.config.get("profiles", {}):
            raise ValueError(f"Profile '{old_name}' not found")

        if new_name in self.config["profiles"]:
            raise ValueError(f"Profile '{new_name}' already exists")

        self.config["profiles"][new_name] = self.config["profiles"].pop(old_name)

        if self.config.get("active_profile") == old_name:
            self.config["active_profile"] = new_name

        self.save_config()

    def delete_profile(self, name: str) -> None:
        """Delete a profile.

        Raises:
            ValueError: If trying to delete the last profile
        """
        if len(self.config.get("profiles", {})) <= 1:
            raise ValueError("Cannot delete the last profile")

        if name not in self.config["profiles"]:
            raise ValueError(f"Profile '{name}' not found")

        del self.config["profiles"][name]

        if self.config.get("active_profile") == name:
            self.config["active_profile"] = self.list_profiles()[0]

        self.save_config()
```

#### Update MainWindow
```python
# gui/main_window_pyside.py
from shopify_tool.profile_manager import ProfileManager

class MainWindow(QMainWindow):
    def __init__(self):
        # ... existing code ...

        # NEW: Use ProfileManager service
        self.profile_manager = ProfileManager(self.config_path)
        self.config = self.profile_manager.config

        # ... rest of init ...

    def create_profile(self, name, base_profile_name="Default"):
        """Creates a new profile using ProfileManager."""
        try:
            self.profile_manager.create_profile(name, base_profile_name)
            return True
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            return False

    # Similar updates for rename_profile, delete_profile
```

#### Update ProfileManagerDialog
```python
# gui/profile_manager_dialog.py
class ProfileManagerDialog(QDialog):
    def __init__(self, parent, profile_manager):
        super().__init__(parent)
        self.parent = parent
        self.profile_manager = profile_manager  # Service injection
        # ... rest of init ...

    def add_profile(self):
        """Handles 'Add New' button using ProfileManager."""
        new_name, ok = QInputDialog.getText(
            self, "Add Profile", "Enter new profile name:"
        )
        if ok and new_name:
            try:
                self.profile_manager.create_profile(new_name)
                self.populate_profiles()
                # Notify parent to switch
                self.parent.set_active_profile(new_name)
            except ValueError as e:
                QMessageBox.warning(self, "Error", str(e))
```

---

### 3.2 Extract Config Migration Logic

**Issue**: CRITICAL_ANALYSIS.md Section 3.2
**Severity**: Medium (complex __init__)
**Files**: New `shopify_tool/config_migrator.py`, `gui/main_window_pyside.py`

#### Create ConfigMigrator
```python
# shopify_tool/config_migrator.py
import shutil
import json

class ConfigMigrator:
    """Handles configuration file migrations between versions."""

    @staticmethod
    def needs_migration(config: dict) -> bool:
        """Check if config needs migration to profile-based structure."""
        return "profiles" not in config

    @staticmethod
    def migrate_to_profiles(old_config: dict) -> dict:
        """Migrate old flat config to profile-based structure."""
        return {
            "profiles": {"Default": old_config},
            "active_profile": "Default"
        }

    @staticmethod
    def create_backup(config_path: str) -> str:
        """Create a backup of the config file.

        Returns:
            Path to the backup file
        """
        backup_path = config_path + ".bak"
        shutil.copy(config_path, backup_path)
        return backup_path
```

#### Simplify MainWindow._init_and_load_config
```python
# gui/main_window_pyside.py
from shopify_tool.config_migrator import ConfigMigrator

def _init_and_load_config(self):
    """Initializes and loads the application configuration."""
    # 1. Ensure config exists
    if not os.path.exists(self.config_path):
        self._create_default_config()

    # 2. Load config
    with open(self.config_path, 'r', encoding='utf-8') as f:
        self.config = json.load(f)

    # 3. Migrate if needed
    if ConfigMigrator.needs_migration(self.config):
        self._handle_migration()

    # 4. Load active profile
    self._load_active_profile()

def _handle_migration(self):
    """Handle config migration with user confirmation."""
    reply = QMessageBox.question(
        self, "Migrate Configuration",
        "Your configuration needs to be updated...",
        QMessageBox.Yes | QMessageBox.No
    )

    if reply == QMessageBox.Yes:
        backup_path = ConfigMigrator.create_backup(self.config_path)
        self.config = ConfigMigrator.migrate_to_profiles(self.config)
        self._save_config()
        QMessageBox.information(
            self, "Migration Complete",
            f"Backup saved to:\n{backup_path}"
        )
    else:
        QMessageBox.critical(
            self, "Configuration Error",
            "Migration required to run."
        )
        QApplication.quit()
```

---

## Phase 4: Security and Polish (1 week)

### 4.1 Replace Pickle with Parquet + JSON

**Issue**: CRITICAL_ANALYSIS.md Section 7.1
**Severity**: Medium (security risk)
**Files**: `gui/main_window_pyside.py`

```python
# gui/main_window_pyside.py
def closeEvent(self, event):
    """Save session data using Parquet + JSON instead of pickle."""
    if not self.analysis_results_df.empty:
        try:
            session_dir = Path(self.session_file).parent
            session_dir.mkdir(parents=True, exist_ok=True)

            # Save DataFrame in Parquet format
            df_path = session_dir / "session_data.parquet"
            self.analysis_results_df.to_parquet(df_path)

            # Save metadata in JSON
            metadata = {
                "visible_columns": self.visible_columns,
                "dataframe_path": str(df_path),
                "timestamp": datetime.now().isoformat()
            }

            metadata_path = session_dir / "session_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            self.log_activity("Session", "Session data saved on exit.")
        except Exception as e:
            logging.error(f"Error saving session: {e}", exc_info=True)
    event.accept()

def load_session(self):
    """Load session data from Parquet + JSON."""
    metadata_path = Path(self.session_file).parent / "session_metadata.json"

    if metadata_path.exists():
        reply = QMessageBox.question(
            self, "Restore Session",
            "A previous session was found. Do you want to restore it?"
        )

        if reply == QMessageBox.Yes:
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)

                df_path = Path(metadata["dataframe_path"])
                self.analysis_results_df = pd.read_parquet(df_path)
                self.visible_columns = metadata.get("visible_columns", [])

                self.all_columns = [c for c in self.analysis_results_df.columns
                                    if c != "Order_Number"]
                self._update_all_views()
                self.log_activity("Session", "Restored previous session.")
            except Exception as e:
                QMessageBox.critical(self, "Load Error",
                                     f"Failed to load session: {e}")

        # Clean up session files
        try:
            metadata_path.unlink()
            Path(metadata["dataframe_path"]).unlink()
        except Exception as e:
            logging.error(f"Failed to remove session files: {e}")
```

---

## Testing Strategy

### For Each Phase

1. **Before Refactoring**:
   - Run full test suite: `pytest tests/ -v`
   - Document current behavior
   - Add missing tests for functionality being refactored

2. **During Refactoring**:
   - Write tests for new code BEFORE implementation (TDD)
   - Run tests after each change
   - Commit frequently with descriptive messages

3. **After Refactoring**:
   - Run full test suite again
   - Manual testing of affected features
   - Performance testing if applicable
   - Update documentation

### Test Coverage Goals

- Phase 1: 80% coverage of refactored code
- Phase 2: 70% coverage (focus on critical paths)
- Phase 3: 85% coverage (architectural changes need thorough testing)
- Phase 4: 90% coverage (security-critical changes)

---

## Rollback Plan

If issues arise during refactoring:

1. **Immediate Issues**: `git revert <commit-hash>`
2. **Major Problems**: `git reset --hard backup-before-refactoring`
3. **Partial Rollback**: Use git cherry-pick to selectively apply commits

Always test rollback before starting a phase!

---

## Documentation Updates

After each phase:

1. Update `TECHNICAL_DOCUMENTATION.md` with architectural changes
2. Update inline code comments
3. Update CRITICAL_ANALYSIS.md to mark issues as resolved
4. Create ADRs (Architecture Decision Records) for major decisions

---

## Conclusion

Follow this guide systematically. Don't skip phases or rush. The estimated 7-10 weeks accounts for:
- Careful implementation
- Thorough testing
- Documentation updates
- Code review time

Good luck with the refactoring! 🚀
