# Shopify Tool - Profile System Analysis

## Executive Summary

This document provides a detailed analysis of how the current profile system works in the Shopify Fulfillment Tool, prepared for integration with the ClientManager module. The profile system enables users to maintain separate configurations for different warehouses or workflows.

**Last Updated:** 2025-11-04

---

## Current Architecture

### Config Location

**Path Resolution:**
- **Windows:** `%APPDATA%/ShopifyFulfillmentTool/config.json`
- **Linux/Mac:** `~/ShopifyFulfillmentTool/config.json`

**Function:** `shopify_tool.utils.get_persistent_data_path(filename)`
- Location: `shopify_tool/utils.py:8`
- Uses `os.getenv("APPDATA")` on Windows, `os.path.expanduser("~")` on other platforms
- Creates directory if it doesn't exist
- Falls back to current directory (`.`) if unable to create AppData directory

**Initialization:**
- Config path set in: `gui/main_window_pyside.py:130`
  ```python
  self.config_path = get_persistent_data_path("config.json")
  ```

---

## Profile Selection

### UI Components

**Dropdown Widget:**
- Component: `QComboBox` named `self.profile_combo`
- Created by: `UIManager.create_widgets()` in `gui/ui_manager.py`
- Signal: `currentTextChanged` connected to `MainWindow.set_active_profile()`
- Location: Main window toolbar, top section

**Manage Profiles Button:**
- Component: `QPushButton` named `self.manage_profiles_btn`
- Signal: `clicked` connected to `MainWindow.open_profile_manager()`
- Opens: `ProfileManagerDialog` for CRUD operations

### Active Profile Variables

**In MainWindow:**
- `self.active_profile_name` (str): Name of currently active profile
- `self.active_profile_config` (dict): Reference to the active profile's configuration dictionary
- `self.config` (dict): The entire config object containing all profiles

**Initialization Flow:**
1. `MainWindow.__init__()` calls `self._init_and_load_config()`
2. Config loaded from disk via `json.load()`
3. Active profile name read from `config["active_profile"]`
4. Active profile config set to `config["profiles"][active_profile_name]`
5. Profile combo populated via `self.update_profile_combo()`

---

## Profile Data Flow

### 1. Load Configuration
**Method:** `MainWindow._init_and_load_config()`
- **Location:** `gui/main_window_pyside.py:166`
- **Purpose:** Initialize and load application configuration
- **Steps:**
  1. Check if `config.json` exists; if not, create from default template
  2. Load JSON from disk
  3. **Migration:** If `"profiles"` key missing, migrate old flat config to profile structure
  4. Set `self.active_profile_name` from `config["active_profile"]`
  5. Load active profile: `self.active_profile_config = self.config["profiles"][self.active_profile_name]`

**Migration Logic (Line 200-234):**
- Detects old format (no "profiles" key)
- Prompts user for confirmation
- Creates backup at `config.json.bak`
- Wraps existing config in `{"profiles": {"Default": old_config}, "active_profile": "Default"}`

### 2. Get Active Profile
**Method:** Direct attribute access
- **Variable:** `self.active_profile_name`
- **Config Reference:** `self.active_profile_config`
- **Usage:** Throughout the codebase when reading settings

**Example from ActionsHandler (line 124):**
```python
base_output_dir = self.mw.active_profile_config["paths"].get("output_dir_stock", "data/output")
```

### 3. Switch Profile
**Method:** `MainWindow.set_active_profile(profile_name)`
- **Location:** `gui/main_window_pyside.py:330`
- **Trigger:** User selects different profile from dropdown
- **Steps:**
  1. Validate profile exists in `self.config["profiles"]`
  2. Update `self.active_profile_name`
  3. Update `self.active_profile_config` reference
  4. Update `self.config["active_profile"]` for persistence
  5. Call `self._save_config()` to persist change
  6. **Reset data:** Clear `analysis_results_df` and `analysis_stats`
  7. Refresh UI via `self._update_all_views()`
  8. Update combo box via `self.update_profile_combo()`

**Important:** Switching profiles clears all analysis data (line 345-346)

### 4. Save Profile Configuration
**Method:** `MainWindow._save_config()`
- **Location:** `gui/main_window_pyside.py:251`
- **Purpose:** Write entire config object to disk
- **Format:** JSON with 2-space indentation, UTF-8 encoding
- **Error Handling:** Logs error and shows critical message box on failure

**Called by:**
- Profile switching
- Profile creation/rename/delete
- Settings window save (updates active profile's config)

### 5. Update Profile in Settings
**Flow:** `ActionsHandler.open_settings_window()`
- **Location:** `gui/actions_handler.py:204`
- **Steps:**
  1. Create `SettingsWindow` with deep copy of `active_profile_config`
  2. User edits settings (rules, paths, etc.)
  3. On save (dialog.exec() returns True):
     - Update: `self.mw.config["profiles"][self.mw.active_profile_name] = dialog.config_data`
     - Persist: `self.mw._save_config()`
     - Refresh: `self.mw.active_profile_config = dialog.config_data`

**Deep Copy Mechanism (SettingsWindow line 110):**
```python
self.config_data = json.loads(json.dumps(config))
```
- Isolates changes until user clicks "Save"
- Prevents accidental modification of active config

---

## Profile Configuration Structure

### Complete Schema

```json
{
  "active_profile": "Default",
  "profiles": {
    "Default": {
      "paths": {
        "input": {
          "stock_file": "data/input/EXCEL.csv",
          "orders_file": "data/input/orders_export.csv"
        },
        "output": {
          "analysis_file": "data/output/fulfillment_analysis.xlsx"
        },
        "templates": "data/templates/",
        "output_dir_stock": "data/output/"
      },
      "settings": {
        "stock_csv_delimiter": ";",
        "low_stock_threshold": 10
      },
      "column_mappings": {
        "orders": {
          "name": "Name",
          "sku": "Lineitem sku",
          "quantity": "Lineitem quantity",
          "shipping_provider": "Shipping Provider"
        },
        "stock": {
          "sku": "Артикул",
          "stock": "Наличност"
        },
        "orders_required": ["Name", "Lineitem sku", "Lineitem quantity"],
        "stock_required": ["Артикул", "Наличност"]
      },
      "courier_mappings": {
        "DHL Express": "DHL",
        "Deutsche Post": "DPD"
      },
      "rules": [
        {
          "name": "Auto-tag Low Stock",
          "match": "ALL",
          "conditions": [
            {
              "field": "Stock_Available",
              "operator": "is less than",
              "value": "5"
            }
          ],
          "actions": [
            {
              "type": "ADD_TAG",
              "value": "LOW_STOCK"
            }
          ]
        }
      ],
      "packing_lists": [
        {
          "name": "All Fulfillable Orders",
          "output_filename": "packing_list_ALL.xlsx",
          "filters": [],
          "exclude_skus": ["07", "Shipping protection"]
        }
      ],
      "stock_exports": [
        {
          "name": "Stock Export (ALL)",
          "template": "dropALL.xls",
          "filters": []
        }
      ]
    },
    "Warehouse-B": {
      "...": "Same structure as Default"
    }
  }
}
```

### Key Observations

1. **Top-level keys:**
   - `active_profile`: String, name of currently active profile
   - `profiles`: Dictionary mapping profile names to profile configs

2. **Profile-specific keys:**
   - `paths`: Input/output directories and templates location
   - `settings`: Delimiters, thresholds, general preferences
   - `column_mappings`: CSV column name mappings for orders/stock
   - `courier_mappings`: Standardization of courier names
   - `rules`: Automation rules for tagging/filtering
   - `packing_lists`: Pre-configured report definitions
   - `stock_exports`: Pre-configured export templates

3. **Default Structure:**
   - Located at: `config.json` (project root, used as template)
   - Loaded when no user config exists
   - Wrapped in profile structure during first-time initialization

---

## Files That Use Profiles

### 1. `gui/main_window_pyside.py` (Primary Profile Manager)

**Profile Management Methods:**

| Method | Line | Purpose |
|--------|------|---------|
| `_init_and_load_config()` | 166 | Load config, handle migration, set active profile |
| `_save_config()` | 251 | Persist entire config object to JSON file |
| `update_profile_combo()` | 321 | Refresh profile dropdown with current profiles |
| `set_active_profile(profile_name)` | 330 | Switch to different profile, clear data, save |
| `open_profile_manager()` | 354 | Open ProfileManagerDialog |
| `create_profile(name, base_profile_name)` | 360 | Create new profile by copying existing |
| `rename_profile(old_name, new_name)` | 374 | Rename profile, update active if needed |
| `delete_profile(name)` | 391 | Delete profile, switch if currently active |

**Direct Config Usage:**
- Line 130: `self.config_path = get_persistent_data_path("config.json")`
- Line 131: `self.active_profile_name = None`
- Line 132: `self.active_profile_config = {}`
- Line 237: Load active profile from `self.config["active_profile"]`
- Line 248: Get active config: `self.active_profile_config = self.config["profiles"][self.active_profile_name]`

### 2. `gui/actions_handler.py` (Profile Consumer)

**Methods Using active_profile_config:**

| Method | Line | What it reads |
|--------|------|---------------|
| `create_new_session()` | 124 | `active_profile_config["paths"]["output_dir_stock"]` |
| `run_analysis()` | 155 | `active_profile_config["settings"]["stock_csv_delimiter"]` |
| `run_analysis()` | 162 | Entire `active_profile_config` passed to backend |
| `open_settings_window()` | 210 | Entire `active_profile_config` passed to dialog |
| `open_report_selection_dialog()` | 229 | `active_profile_config.get(report_type, [])` |

**Profile Modification:**
- Line 213: `self.mw.config["profiles"][self.mw.active_profile_name] = dialog.config_data`
- Saves updated profile config after settings dialog closes

### 3. `gui/settings_window_pyside.py` (Profile Editor)

**Initialization:**
- Line 97: `__init__(self, parent, config, analysis_df=None)`
- Line 110: Deep copy via `json.loads(json.dumps(config))`
- **Receives:** Active profile config only (not entire config object)
- **Returns:** Modified config via `self.config_data` attribute

**What it edits:**
- General settings (delimiter, threshold, paths)
- Rules (conditions, actions)
- Packing lists (filters, exclude SKUs)
- Stock exports (template, filters)
- Column mappings (orders/stock CSV columns)
- Courier mappings (name standardization)

**Save Method (line 736):**
- Iterates through all widget groups
- Rebuilds config structure from UI state
- Calls `self.accept()` on success (dialog.exec() returns True)

### 4. `gui/profile_manager_dialog.py` (Profile CRUD UI)

**Purpose:** Dedicated dialog for managing profile lifecycle

**Methods:**

| Method | Line | What it does |
|--------|------|--------------|
| `populate_profiles()` | 58 | Read `parent.config["profiles"]` and fill list widget |
| `add_profile()` | 66 | Call `parent.create_profile(new_name, base_profile)` |
| `rename_profile()` | 81 | Call `parent.rename_profile(old_name, new_name)` |
| `delete_profile()` | 99 | Call `parent.delete_profile(name)` |

**Direct Parent Access:**
- Line 61: `self.parent.config.get("profiles", {})`
- Line 75: `self.parent.active_profile_name`
- All methods delegate to MainWindow for actual operations

### 5. `gui/file_handler.py` (Indirect Config Usage)

**Validation Method (line 61):**
- Line 76: `required_cols = self.mw.config.get("column_mappings", {}).get("orders_required", [])`
- Line 81: `required_cols = self.mw.config.get("column_mappings", {}).get("stock_required", [])`
- Line 82: `delimiter = self.mw.config.get("settings", {}).get("stock_csv_delimiter", ";")`

**Note:** Uses `self.mw.config` directly, NOT `self.mw.active_profile_config`
- **Potential Bug:** Should be using `active_profile_config` for profile-specific settings
- Currently works because it reaches into the global config (may access wrong data if profiles differ)

### 6. Backend Files (Consumers Only)

**Files receiving profile config:**
- `shopify_tool/core.py`: Receives full profile config in `run_full_analysis()`
- `shopify_tool/rules.py`: Uses rules from profile config
- `shopify_tool/reports.py`: Uses packing_lists/stock_exports definitions

**Pattern:** Backend is profile-agnostic; config passed as parameter

---

## Integration Points for ClientManager

### 1. Changes Needed

#### A. Replace Direct config.json Access

**Current State:**
- Config loaded/saved directly via JSON file I/O
- Path: `get_persistent_data_path("config.json")`

**Required Changes:**
- Replace `json.load()` / `json.dump()` with ClientManager API calls
- Maintain backward compatibility during transition

**Affected Methods:**
- `MainWindow._init_and_load_config()` (line 166)
- `MainWindow._save_config()` (line 251)

#### B. Centralize Profile Management

**Current State:**
- Profile CRUD operations scattered across MainWindow
- Direct dictionary manipulation of `self.config["profiles"]`

**Required Changes:**
- Move profile operations to ClientManager
- Use ClientManager methods: `get_client()`, `save_client()`, `list_clients()`, `delete_client()`
- Update MainWindow to call ClientManager instead of direct config access

**Affected Methods:**
- `create_profile()` → `ClientManager.save_client()`
- `rename_profile()` → `ClientManager.rename_client()`
- `delete_profile()` → `ClientManager.delete_client()`
- `set_active_profile()` → Update to use ClientManager

#### C. Update active_profile_config References

**Current Pattern:**
```python
setting = self.mw.active_profile_config["paths"]["output_dir_stock"]
```

**New Pattern (with ClientManager):**
```python
client_config = client_manager.get_client(self.mw.active_profile_name)
setting = client_config["paths"]["output_dir_stock"]
```

**OR maintain cached reference:**
```python
# MainWindow initialization
self.active_profile_config = client_manager.get_client(self.active_profile_name)

# Usage remains the same
setting = self.mw.active_profile_config["paths"]["output_dir_stock"]
```

**Affected Files:**
- `gui/actions_handler.py`: 5 references to `active_profile_config`
- `gui/main_window_pyside.py`: Direct access to `self.active_profile_config`
- `gui/settings_window_pyside.py`: Receives config as parameter (minimal change)

#### D. Fix file_handler.py Bug

**Current Issue:**
- Line 76, 81, 82: Uses `self.mw.config` instead of `self.mw.active_profile_config`
- May read wrong column mappings if profiles differ

**Fix:**
```python
# Before
required_cols = self.mw.config.get("column_mappings", {}).get("orders_required", [])

# After
required_cols = self.mw.active_profile_config.get("column_mappings", {}).get("orders_required", [])
```

#### E. Migration Strategy

**Option 1: Gradual Migration**
1. Add ClientManager alongside existing JSON I/O
2. Read from JSON, write to both JSON and ClientManager
3. Eventually switch to read-only from ClientManager
4. Remove JSON I/O code

**Option 2: Direct Replacement**
1. Import ClientManager
2. Replace all `_save_config()` calls with `client_manager.save_client()`
3. Replace all config reads with `client_manager.get_client()`
4. Update profile CRUD methods

**Recommended:** Option 1 for safer transition

### 2. Risk Areas

#### High Risk

**A. Migration Path for Existing Users**
- **Issue:** Users have existing `config.json` files with multiple profiles
- **Risk:** Data loss if migration fails; user frustration if configs not preserved
- **Mitigation:**
  - Implement auto-migration on first ClientManager init
  - Detect existing `config.json`, import all profiles
  - Create backup before migration
  - Provide rollback mechanism

**B. Session Persistence**
- **Issue:** Session data (`session_data.pkl`) uses pickle, tied to config location
- **Risk:** Network share locking issues with file-based persistence
- **Current File:** `get_persistent_data_path("session_data.pkl")`
- **Related:** See `CRITICAL_ANALYSIS.md Section 7.1` for pickle security concerns
- **Mitigation:**
  - Consider moving session data to ClientManager storage
  - OR use separate, profile-specific session files

**C. Active Profile Switching**
- **Issue:** Switching profiles clears all analysis data (line 345-346)
- **Risk:** Users lose work if they switch profiles accidentally
- **Mitigation:**
  - Add confirmation dialog before clearing data
  - Consider per-profile session caching

#### Medium Risk

**D. Settings Window Deep Copy**
- **Issue:** Uses `json.loads(json.dumps(config))` for deep copy (line 110)
- **Risk:** Inefficient for large configs; doesn't work if ClientManager uses non-JSON-serializable objects
- **Mitigation:**
  - Use `copy.deepcopy()` instead
  - OR have ClientManager provide immutable config snapshots

**E. Profile Combo State**
- **Issue:** Combo box updates trigger `set_active_profile()` signal
- **Risk:** Unintended profile switches during UI refresh
- **Current Mitigation:** Uses `blockSignals(True/False)` (line 323-328)
- **Ensure:** ClientManager integration maintains signal blocking

**F. file_handler.py Config Access**
- **Issue:** Directly accesses `self.mw.config` instead of `active_profile_config`
- **Risk:** May validate against wrong profile's column mappings
- **Impact:** File validation could fail/succeed incorrectly
- **Fix:** Update to use `active_profile_config` (see Section 1.D above)

#### Low Risk

**G. Default Config Template**
- **Issue:** Root `config.json` used as default template (line 178)
- **Risk:** If ClientManager changes structure, default may be incompatible
- **Mitigation:**
  - Bundle default config within ClientManager
  - OR maintain separate `default_profile.json` template

**H. Concurrent Access**
- **Issue:** Current system doesn't handle concurrent access (multiple instances)
- **Risk:** Two instances could overwrite each other's changes
- **Mitigation:** ClientManager should implement file locking or detect conflicts

---

## Profile-Related Signals and Events

### Signals

**MainWindow:**
- `profile_combo.currentTextChanged` → `set_active_profile()` (line 282)

**ActionsHandler:**
- `data_changed` signal → `_update_all_views()` (line 103, emitted after profile operations)

**ProfileManagerDialog:**
- No custom signals; uses dialog acceptance pattern

### Event Flow: Profile Switch

1. User selects profile from dropdown
2. `currentTextChanged` signal emitted
3. `MainWindow.set_active_profile(profile_name)` called
4. Validation: Check profile exists
5. Update `active_profile_name`, `active_profile_config`, `config["active_profile"]`
6. **Call `_save_config()`** (persists switch immediately)
7. Clear `analysis_results_df` and `analysis_stats` (line 345-346)
8. Call `_update_all_views()` (refresh UI)
9. Call `update_profile_combo()` (refresh dropdown)

### Event Flow: Profile Create

1. User clicks "Manage Profiles" button
2. `ProfileManagerDialog` opens
3. User clicks "Add New..." button
4. `add_profile()` method called
5. Prompts for new profile name
6. Calls `parent.create_profile(new_name, base_profile_name)`
7. **MainWindow.create_profile():**
   - Deep copy base profile: `json.loads(json.dumps(base_config))`
   - Add to `self.config["profiles"][name]`
   - Call `_save_config()` (persist)
   - Call `set_active_profile(new_name)` (switch to new profile)
8. Dialog calls `populate_profiles()` (refresh list)

---

## Testing Considerations

### Unit Tests Needed

1. **Profile Loading:**
   - Load config with multiple profiles
   - Load config with missing active_profile
   - Load config with invalid active_profile reference
   - Migration from old format to profile format

2. **Profile Switching:**
   - Switch between profiles
   - Data clearing on switch
   - Config persistence after switch

3. **Profile CRUD:**
   - Create profile from base
   - Rename profile (including active profile)
   - Delete profile (switch if active)
   - Cannot delete last profile

4. **Config Save/Load:**
   - Save config to disk
   - Load config from disk
   - Handle file I/O errors
   - JSON encoding/decoding errors

### Integration Tests Needed

1. **Settings Update:**
   - Open settings, modify, save
   - Verify profile config updated
   - Verify config persisted to disk

2. **Profile Manager Dialog:**
   - Create, rename, delete operations
   - UI refresh after operations
   - Combo box updates

3. **Multi-Profile Workflow:**
   - Create two profiles with different settings
   - Switch between them
   - Run analysis with each
   - Verify settings isolation

### Edge Cases

1. **Empty Profiles:**
   - What if `config["profiles"]` is empty?
   - Currently: Critical error, app quits (line 242-244)

2. **Duplicate Profile Names:**
   - Create profile with existing name
   - Currently: Shows warning, returns False (line 363)

3. **Rename to Existing Name:**
   - Currently: Shows warning, returns False (line 379)

4. **Delete Active Profile:**
   - Currently: Switches to first remaining profile (line 404)

5. **Network Share Issues:**
   - Config stored on network share with locking issues
   - Currently: No special handling; may fail silently or show error

---

## Recommendations for ClientManager Integration

### Critical

1. **Implement Migration Tool**
   - Auto-detect existing `config.json`
   - Import all profiles to ClientManager format
   - Create backup before migration
   - Provide migration status/progress to user

2. **Fix file_handler.py Bug**
   - Update to use `active_profile_config` instead of `config`
   - Test with multiple profiles having different column mappings

3. **Add Confirmation Before Data Loss**
   - Profile switching currently clears analysis data without warning
   - Add "You have unsaved analysis results. Switch profile anyway?" dialog

### High Priority

4. **Centralize Profile Operations**
   - Move all profile CRUD to ClientManager API
   - Remove direct dictionary manipulation from MainWindow
   - Update ProfileManagerDialog to use ClientManager

5. **Replace JSON Deep Copy**
   - Change `json.loads(json.dumps(config))` to `copy.deepcopy(config)`
   - More efficient, works with non-JSON types

6. **Session Data Integration**
   - Consider storing session data in ClientManager
   - OR use profile-specific session files
   - Address pickle security issue (see CRITICAL_ANALYSIS.md)

### Medium Priority

7. **Config Validation**
   - Validate config structure after load
   - Ensure all required keys exist
   - Provide defaults for missing optional keys

8. **Concurrent Access Handling**
   - Detect if another instance modified config
   - Prompt user to reload or overwrite
   - OR implement file locking

9. **Profile Import/Export**
   - Allow users to export profiles as JSON
   - Import profiles from JSON (for sharing/backup)

### Low Priority

10. **Profile Metadata**
    - Add creation date, last modified date to profiles
    - Track profile usage statistics
    - Allow profile descriptions/notes

11. **UI Improvements**
    - Show warning icon if profile has validation issues
    - Preview profile settings in ProfileManagerDialog
    - Keyboard shortcuts for profile switching

---

## Appendix: Code References

### Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `shopify_tool/utils.py` | 8-40 | `get_persistent_data_path()` function |
| `gui/main_window_pyside.py` | 121-615 | MainWindow class, profile management |
| `gui/actions_handler.py` | 82-394 | ActionsHandler class, uses active profile config |
| `gui/settings_window_pyside.py` | 55-834 | SettingsWindow class, edits profile config |
| `gui/profile_manager_dialog.py` | 13-123 | ProfileManagerDialog class, CRUD UI |
| `gui/file_handler.py` | 8-117 | FileHandler class, validation (has bug) |
| `config.json` | 1-136 | Default profile template |

### Key Variables

| Variable | Type | Location | Purpose |
|----------|------|----------|---------|
| `config_path` | str | MainWindow | Full path to config.json |
| `config` | dict | MainWindow | Entire config object (all profiles) |
| `active_profile_name` | str | MainWindow | Name of current profile |
| `active_profile_config` | dict | MainWindow | Reference to current profile's config |
| `profile_combo` | QComboBox | MainWindow | UI dropdown for profile selection |

### Key Methods

| Method | Location | Line | Purpose |
|--------|----------|------|---------|
| `get_persistent_data_path()` | utils.py | 8 | Resolve config.json path |
| `_init_and_load_config()` | main_window_pyside.py | 166 | Initialize config system |
| `_save_config()` | main_window_pyside.py | 251 | Persist config to disk |
| `set_active_profile()` | main_window_pyside.py | 330 | Switch active profile |
| `create_profile()` | main_window_pyside.py | 360 | Create new profile |
| `rename_profile()` | main_window_pyside.py | 374 | Rename profile |
| `delete_profile()` | main_window_pyside.py | 391 | Delete profile |

---

## Conclusion

The current profile system is well-structured but tightly coupled to JSON file I/O. Integration with ClientManager will require:

1. **API Replacement:** Swap JSON I/O with ClientManager method calls
2. **Migration Path:** Import existing configs on first run
3. **Bug Fixes:** Correct file_handler.py config access
4. **UX Improvements:** Add confirmations before data loss
5. **Testing:** Comprehensive tests for migration and multi-profile workflows

The profile system is used extensively throughout the GUI layer but is isolated from the backend, making it a good candidate for centralized management via ClientManager.

**Next Steps:**
1. Review ClientManager API design
2. Create migration plan
3. Update file_handler.py bug
4. Implement ClientManager integration
5. Test thoroughly with multiple profiles
