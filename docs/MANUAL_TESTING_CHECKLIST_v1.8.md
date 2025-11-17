# Manual Testing Checklist - v1.8.0

**Purpose:** Comprehensive manual testing before stable release
**Tester:** [Name]
**Date:** [Date]
**Version:** 1.8.0

---

## ✅ Pre-Testing Setup

- [ ] Fresh installation from repository
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] All automated tests passing: `pytest tests/ -v`
- [ ] Test data prepared (orders CSV, stock CSV)
- [ ] Network access to file server available

---

## 📋 Core Functionality Tests

### Session Management

- [ ] **Create New Session**
  - Select client → Create new session → Session created successfully
  - Verify session folder created on server
  - Verify session_info.json created

- [ ] **Load Existing Session**
  - Browse sessions → Select session → Data loads correctly
  - Verify analysis results displayed
  - Verify statistics shown

- [ ] **Switch Between Clients**
  - Switch client → Previous client data cleared
  - New client data loaded correctly
  - No data leakage between clients

### File Loading

- [ ] **Load Orders CSV**
  - Select orders file → File loads successfully
  - Delimiter auto-detected correctly
  - Column mapping works if headers don't match
  - Progress indicator shows during load

- [ ] **Load Stock CSV**
  - Select stock file → File loads successfully
  - Delimiter auto-detected correctly
  - SKU types preserved (no "5170.0" → "5170" issues)

- [ ] **Folder Loading (Batch)**
  - Select folder with multiple CSVs → All files loaded
  - Merged correctly
  - Progress shows for each file

### Analysis Execution

- [ ] **Run Basic Analysis**
  - Load files → Run analysis → Results displayed
  - Statistics calculated correctly
  - Fulfillable/not fulfillable marked correctly

- [ ] **Analysis with Sets**
  - Enable sets → Load orders with sets → Sets decoded
  - Expanded products shown
  - Stock calculated correctly for components

- [ ] **Analysis with Rules**
  - Configure rules → Run analysis → Rules applied
  - Tags added correctly
  - Status/priority set correctly
  - Conditions matched properly

- [ ] **Repeated Orders Detection**
  - Load orders with repeats → Analysis runs
  - Repeated orders tagged correctly
  - History checked

### Performance Testing

- [ ] **Small Dataset (100 orders)**
  - Load → Analyze → Completes in <1 second
  - No lag or freezing

- [ ] **Medium Dataset (1000 orders)**
  - Load → Analyze → Completes in <3 seconds
  - UI remains responsive

- [ ] **Large Dataset (5000+ orders)**
  - Load → Analyze → Completes in <15 seconds
  - Memory usage acceptable
  - No crashes

---

## 🎨 UI/UX Tests

### ComboBox Wheel Scroll Prevention (NEW in v1.8)

- [ ] **Settings Window - Rules**
  - Hover over condition dropdown → Scroll wheel
  - ✅ Value does NOT change
  - Click dropdown → Select item → Value changes

- [ ] **Report Selection Dialog**
  - Hover over courier filter → Scroll wheel
  - ✅ Filter does NOT change
  - Click → Select → Filter changes

- [ ] **Column Mapping**
  - Hover over mapping dropdown → Scroll wheel
  - ✅ Mapping does NOT change

- [ ] **Keyboard Navigation**
  - Tab through dropdowns → Focus works
  - Arrow keys when focused → Value changes (OK)

### General UI

- [ ] **Window Resizing**
  - Resize window → Layout adapts correctly
  - No overlapping widgets
  - Scrollbars appear when needed

- [ ] **Tab Navigation**
  - Switch between tabs → Data persists
  - UI updates correctly
  - No lag

- [ ] **Progress Indicators**
  - Long operations show progress
  - Can cancel operations
  - UI doesn't freeze

---

## 📊 Reports Generation

### Packing Lists

- [ ] **Basic Packing List**
  - Generate → Excel file created
  - Formatting correct (borders, colors)
  - Data accurate

- [ ] **Filtered Packing List**
  - Apply filters (courier, status) → Generate
  - Only filtered data included
  - SKU exclusions work

- [ ] **Multiple Packing Lists**
  - Generate multiple → Each saved separately
  - JSON files created for Packing Tool
  - XLSX and JSON match

### Stock Exports

- [ ] **Basic Stock Export**
  - Generate → File created
  - Stock calculations correct
  - Format matches template

- [ ] **Multiple Formats**
  - Generate .xlsx → Works
  - Generate .xls → Works
  - Data identical

---

## 🛠️ Settings & Configuration

### Client Configuration

- [ ] **Edit Client Config**
  - Open settings → Modify config → Save
  - Changes persist
  - Reload shows changes

- [ ] **Column Mappings**
  - Add mapping → Save → Apply to new file
  - Mapping works correctly

- [ ] **Courier Mappings**
  - Add courier → Save → Apply in analysis
  - Shipping methods mapped correctly

### Rules Engine

- [ ] **Create New Rule**
  - Add rule → Set conditions → Set actions → Save
  - Rule saved correctly

- [ ] **Edit Existing Rule**
  - Modify rule → Save → Apply
  - Changes work

- [ ] **Delete Rule**
  - Delete rule → Confirm → Rule removed
  - Doesn't apply anymore

- [ ] **Rule Conditions (ALL vs ANY)**
  - Test ALL matching → Works correctly
  - Test ANY matching → Works correctly

- [ ] **Rule Actions**
  - ADD_TAG → Tag added
  - SET_STATUS → Status changed
  - SET_PRIORITY → Priority set
  - EXCLUDE_FROM_REPORT → Not in reports

---

## 🔧 Error Handling

### File Errors

- [ ] **Missing File**
  - Load non-existent file → Clear error message
  - Message shows file path
  - No crash

- [ ] **Corrupted CSV**
  - Load invalid CSV → Error caught
  - Message explains issue
  - No crash

- [ ] **Wrong Encoding**
  - Load non-UTF-8 file → Error shown
  - Suggests encoding issue
  - No crash

### Network Errors

- [ ] **Server Disconnect**
  - Disconnect from server → Error detected
  - Clear error message
  - Can retry

- [ ] **Permission Denied**
  - Try to save without permissions → Error shown
  - Message actionable

### Data Errors

- [ ] **Missing Columns**
  - Load CSV missing required column → Error shown
  - Lists missing columns
  - No crash

- [ ] **Invalid Data Types**
  - Non-numeric in quantity → Error or handled
  - Message clear

---

## 🔄 Integration Tests

### Packing Tool Integration

- [ ] **Generate JSON for Packing Tool**
  - Generate packing list → JSON created
  - Packing Tool can load it
  - Data matches XLSX

- [ ] **Session Sharing**
  - Create session in Shopify Tool
  - Open in Packing Tool → Session found
  - Data loads correctly

---

## 📝 Documentation Tests

- [ ] **README Accurate**
  - Follow installation steps → Works
  - Features listed match actual features

- [ ] **User Guide Clear**
  - New user can follow guide
  - Screenshots up-to-date
  - Instructions clear

---

## 🎯 Acceptance Criteria

### Must Pass (Blocking Issues)

- [ ] All core functionality works
- [ ] No data loss
- [ ] No crashes on normal operations
- [ ] Performance acceptable (<30s for 10k orders)
- [ ] Critical errors handled gracefully

### Should Pass (Minor Issues)

- [ ] UI polish complete
- [ ] All error messages helpful
- [ ] Documentation accurate
- [ ] No known bugs

### Nice to Have

- [ ] Very fast performance
- [ ] Perfect UI/UX
- [ ] Comprehensive error recovery

---

## 🐛 Issues Found

| # | Severity | Description | Status |
|---|----------|-------------|--------|
| 1 |          |             |        |
| 2 |          |             |        |
| 3 |          |             |        |

**Severity Levels:**
- 🔴 **CRITICAL**: Blocks release
- 🟡 **HIGH**: Should fix before release
- 🟢 **MEDIUM**: Can fix in patch
- ⚪ **LOW**: Future improvement

---

## ✅ Sign-Off

- [ ] All tests completed
- [ ] All blocking issues resolved
- [ ] Ready for release

**Tester Name:** _______________
**Date:** _______________
**Signature:** _______________
