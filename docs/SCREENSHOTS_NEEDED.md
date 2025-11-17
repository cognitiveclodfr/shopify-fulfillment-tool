# Screenshots Needed for User Guide

**Document:** USER_GUIDE.md
**Version:** 1.8.0
**Date:** November 17, 2025

---

## 📸 Screenshot Checklist

The User Guide contains **placeholder markers** for screenshots. This document lists all screenshots needed to complete the documentation.

**Format:** Replace `[Screenshot placeholder: Description]` with actual screenshot images.

---

## Screenshots by Section

### 1. Getting Started

#### Screenshot 1.1: First Launch
**Location:** Section "First Launch"
**Placeholder:** `[Screenshot placeholder: First launch - main window with client dropdown]`
**Description:**
- Show main window on first launch
- Highlight client dropdown at top
- Show Session Setup tab active
- Show empty session area

**Requirements:**
- Clean UI, no data loaded
- Client dropdown visible
- All 4 tabs visible (Session Setup, Analysis Results, History, Info)
- Window title showing application name and version

---

### 2. Session Management

#### Screenshot 2.1: Session Folder Structure
**Location:** Section "Creating a New Session"
**Placeholder:** `[Screenshot placeholder: Create New Session button and session folder structure]`
**Description:**
- Show File Explorer with session folder structure
- Path: `Sessions/CLIENT_M/2025-11-17_1/`
- Show subfolders: input/, analysis/, packing_lists/, stock_exports/
- Show session_info.json file

**Requirements:**
- Windows File Explorer view
- Tree view showing folder hierarchy
- Date-stamped session folder visible

#### Screenshot 2.2: History Tab
**Location:** Section "Loading an Existing Session"
**Placeholder:** `[Screenshot placeholder: History tab showing session browser]`
**Description:**
- Show History tab selected
- Table with multiple sessions listed
- Columns: Session ID, Date Created, Total Orders, Status
- Status indicators visible (✅ Complete, 🔄 In Progress, 🔒 Locked)

**Requirements:**
- At least 5-10 sample sessions
- Mix of different statuses
- Clear column headers

---

### 3. Loading Data

#### Screenshot 3.1: CSV File Examples
**Location:** Section "Preparing Your CSV Files"
**Placeholder:** `[Screenshot placeholder: Example CSV files open in Excel]`
**Description:**
- Split screen showing two Excel windows
- Left: Orders CSV with sample data
- Right: Stock CSV with sample data
- Show column headers clearly
- Show 10-15 rows of sample data

**Requirements:**
- Clear column headers
- Sample data that looks realistic
- Both files visible in same screenshot

#### Screenshot 3.2: Load Files Interface
**Location:** Section "Loading Files into a Session"
**Placeholder:** `[Screenshot placeholder: Load Orders and Load Stock buttons with success messages]`
**Description:**
- Show Session Setup tab
- Highlight "📁 Load Orders" button
- Highlight "📁 Load Stock" button
- Show success message: "✅ Orders file loaded: 150 rows"
- Show success message: "✅ Stock file loaded: 300 SKUs"

**Requirements:**
- Success messages visible
- Buttons clearly labeled
- File paths shown (if applicable)

---

### 4. Running Analysis

#### Screenshot 4.1: Analysis Progress
**Location:** Section "Running Your First Analysis"
**Placeholder:** `[Screenshot placeholder: Analysis running with progress bar]`
**Description:**
- Show progress bar at ~50%
- Show progress text: "Cleaning data..." or "Simulating stock allocation..."
- Show estimated time remaining
- Show percentage complete

**Requirements:**
- Progress bar prominent
- Status text visible
- Cancel button visible

#### Screenshot 4.2: Analysis Results Table
**Location:** Section "Understanding Analysis Results"
**Placeholder:** `[Screenshot placeholder: Analysis results table with color-coded rows]`
**Description:**
- Show Analysis Results tab with data table
- Show color-coded rows:
  - Green rows (fulfillable)
  - Red rows (not fulfillable)
  - Yellow rows (repeat customer)
- Show all columns: Order_Number, SKU, Product_Name, Quantity, Courier, Status, Tags, Priority, Location
- Show at least 20 rows with mix of colors

**Requirements:**
- Clear color differentiation
- All columns visible (may need to scroll or zoom out)
- Realistic sample data

#### Screenshot 4.3: Statistics Panel
**Location:** Section "Statistics Panel"
**Placeholder:** `[Screenshot placeholder: Statistics panel with numbers]`
**Description:**
- Show statistics panel (usually on right side)
- Show all statistics sections:
  - Total Orders: 150
  - Fulfillable: 120 (80%)
  - Not Fulfillable: 30 (20%)
  - By Courier breakdown
  - Repeat Customers count
  - Low Stock Alerts
- Show real numbers, not zeros

**Requirements:**
- All statistics visible
- Numbers realistic
- Low stock alerts section showing SKUs

---

### 5. Rule Engine

#### Screenshot 5.1: Rule Configuration Dialog
**Location:** Section "Creating a Rule"
**Placeholder:** `[Screenshot placeholder: Rule configuration dialog]`
**Description:**
- Show Settings window with Rules tab active
- Show "Add Rule" button
- Show rule configuration form:
  - Rule Name field
  - Condition section (Field, Operator, Value)
  - Action section (Type, Value)
  - Save button
- Show example rule configured: "COD Payment Orders"

**Requirements:**
- Clean dialog layout
- All fields visible
- Example rule partially filled in

#### Screenshot 5.2: Rules Management Interface
**Location:** Section "Managing Rules"
**Placeholder:** `[Screenshot placeholder: Rules management interface]`
**Description:**
- Show Settings window with Rules tab
- Show list of rules (5-10 rules)
- Show toggle switches for enable/disable
- Show Edit and Delete buttons
- Show drag handles for reordering
- Show Import/Export buttons

**Requirements:**
- Multiple rules visible
- Some enabled, some disabled (different states)
- All action buttons visible

---

### 6. Generating Packing Lists

#### Screenshot 6.1: Generate Packing List
**Location:** Section "Generating a Basic Packing List"
**Placeholder:** `[Screenshot placeholder: Generate Packing List button and file save dialog]`
**Description:**
- Show "📄 Generate Packing List" button
- Show packing list type selector dropdown
- Show file save dialog
- Show default filename
- Show both .xlsx and .json files

**Requirements:**
- Button prominent
- Dropdown menu showing options (DHL Orders, PostOne Orders, All Orders)
- Save dialog showing file types

#### Screenshot 6.2: Packing List Configuration
**Location:** Section "Pre-Configured Packing Lists"
**Placeholder:** `[Screenshot placeholder: Packing list configuration in settings]`
**Description:**
- Show Settings window with Packing Lists tab
- Show list of configured packing lists
- Show configuration fields:
  - Packing List Name
  - Courier Filter
  - Excluded SKUs list
- Show Add/Edit/Delete buttons

**Requirements:**
- Multiple packing lists configured
- Configuration form visible
- Excluded SKUs list showing examples (07, Shipping protection)

---

### 7. Settings & Configuration

#### Screenshot 7.1: Client Configuration
**Location:** Section "Client Configuration"
**Placeholder:** `[Screenshot placeholder: Client configuration]`
**Description:**
- Show Settings window with Client Configuration tab
- Show all configuration sections:
  - Client Information (ID, Name, Default Courier)
  - Column Mappings table
  - Courier Mappings table
  - Low Stock Thresholds
- Show Add buttons for mappings

**Requirements:**
- All sections visible (may need scrolling or multiple screenshots)
- Tables showing sample mappings
- Add buttons prominent

#### Screenshot 7.2: Application Settings
**Location:** Section "Application Settings"
**Placeholder:** `[Screenshot placeholder: Application settings]`
**Description:**
- Show Settings window with Application Settings tab
- Show all settings categories:
  - Display Settings
  - Performance Settings
  - File Locations
  - Network Settings
  - Advanced Settings
- Show Save and Reset to Defaults buttons

**Requirements:**
- Clean settings layout
- All categories visible
- Example values filled in

---

## Screenshot Specifications

### Technical Requirements

**Resolution:**
- Minimum: 1920x1080
- Recommended: Higher for clarity

**Format:**
- PNG (preferred for screenshots)
- JPG acceptable for photos

**File Naming Convention:**
```
screenshot_<section>_<number>_<description>.png

Examples:
screenshot_session_01_main_window.png
screenshot_analysis_01_progress_bar.png
screenshot_rules_01_configuration.png
```

**Storage Location:**
```
docs/images/
```

### Content Requirements

**General:**
- Clean UI, no personal data
- Use sample/dummy data only
- Remove any sensitive information
- Ensure high contrast for readability

**Sample Data Guidelines:**
- Order numbers: Use format ORD-001, ORD-002, etc.
- SKUs: Use format SKU-A, SKU-B, SKU-001, etc.
- Product names: Generic names (Product A, Product B)
- Customer names: Use "Sample Customer", "Test User", etc.
- Addresses: Use fictional addresses
- Prices: Use round numbers ($10, $25, $50)

**UI State:**
- Application maximized (not windowed)
- No overlapping windows
- No desktop clutter
- Clean taskbar

---

## Integration Instructions

Once screenshots are captured:

1. **Save to:** `docs/images/` folder

2. **Update USER_GUIDE.md:**
   - Replace `[Screenshot placeholder: Description]` with:
     ```markdown
     ![Description](images/screenshot_name.png)
     ```

3. **Example replacement:**
   ```markdown
   # Before:
   [Screenshot placeholder: Main window with client dropdown]

   # After:
   ![Main window with client dropdown](images/screenshot_session_01_main_window.png)
   ```

4. **Verify links:**
   - Check all image links work
   - Check images display correctly in markdown viewer

---

## Priority Levels

### High Priority (Core Workflow)
- ✅ Screenshot 4.2: Analysis Results Table (color-coded rows)
- ✅ Screenshot 3.2: Load Files Interface
- ✅ Screenshot 4.1: Analysis Progress
- ✅ Screenshot 4.3: Statistics Panel

### Medium Priority (Important Features)
- ✅ Screenshot 2.2: History Tab
- ✅ Screenshot 5.1: Rule Configuration
- ✅ Screenshot 6.1: Generate Packing List
- ✅ Screenshot 7.1: Client Configuration

### Low Priority (Reference)
- ✅ Screenshot 1.1: First Launch
- ✅ Screenshot 2.1: Session Folder Structure
- ✅ Screenshot 3.1: CSV File Examples
- ✅ Screenshot 5.2: Rules Management
- ✅ Screenshot 6.2: Packing List Configuration
- ✅ Screenshot 7.2: Application Settings

---

## Status Tracking

| Screenshot | Status | Date | Notes |
|------------|--------|------|-------|
| 1.1 First Launch | ⏳ Pending | - | - |
| 2.1 Session Folder | ⏳ Pending | - | - |
| 2.2 History Tab | ⏳ Pending | - | - |
| 3.1 CSV Examples | ⏳ Pending | - | - |
| 3.2 Load Files | ⏳ Pending | - | - |
| 4.1 Analysis Progress | ⏳ Pending | - | - |
| 4.2 Results Table | ⏳ Pending | - | HIGH PRIORITY |
| 4.3 Statistics Panel | ⏳ Pending | - | HIGH PRIORITY |
| 5.1 Rule Config | ⏳ Pending | - | - |
| 5.2 Rules Management | ⏳ Pending | - | - |
| 6.1 Generate Packing List | ⏳ Pending | - | - |
| 6.2 Packing List Config | ⏳ Pending | - | - |
| 7.1 Client Config | ⏳ Pending | - | - |
| 7.2 App Settings | ⏳ Pending | - | - |

**Legend:**
- ⏳ Pending - Not yet captured
- 📸 In Progress - Being captured
- ✅ Complete - Captured and integrated
- ❌ Blocked - Cannot capture (waiting on something)

---

## Next Steps

1. **Capture screenshots** following this guide
2. **Save to** `docs/images/` folder
3. **Update** USER_GUIDE.md with image links
4. **Verify** all images display correctly
5. **Commit** changes to repository

---

**Total Screenshots Needed:** 14
**Estimated Time:** 2-3 hours (including setup and cleanup)

---

**Document Version:** 1.0
**Last Updated:** November 17, 2025
