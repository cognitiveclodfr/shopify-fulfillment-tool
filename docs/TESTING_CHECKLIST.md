# Manual Testing Checklist - Post-Migration Verification

Use this checklist to verify all functionality works correctly after Phase 1 migration.

**Tester:** _____________
**Date:** _____________
**Environment:** [ ] Dev  [ ] Production
**Test Data:** [ ] Comprehensive  [ ] Custom

---

## 🚀 SETUP

### Prerequisites
- [ ] Dev environment setup complete (`scripts/setup_dev_env.py` executed)
- [ ] Test data generated (`scripts/create_comprehensive_test_data.py` executed)
- [ ] Environment variable set (`FULFILLMENT_SERVER_PATH`)
- [ ] Application starts without errors

### Files Ready
- [ ] `comprehensive_orders.csv` in `data/test_input/`
- [ ] `comprehensive_stock.csv` in `data/test_input/`
- [ ] Dev server structure exists at `FULFILLMENT_SERVER_PATH`

---

## 📋 PHASE 1: BASIC FUNCTIONALITY

### 1.1 Client Profile Management

**Test:** Create and switch between clients

- [ ] **1.1.1** Open application
- [ ] **1.1.2** Client selector shows available clients (CLIENT_M, CLIENT_TEST)
- [ ] **1.1.3** Select CLIENT_M → No errors
- [ ] **1.1.4** UI updates with client name
- [ ] **1.1.5** Switch to CLIENT_TEST → No errors
- [ ] **1.1.6** Switch back to CLIENT_M → No errors
- [ ] **1.1.7** No DataFrame validation errors during switching

**Expected:** Smooth client switching without errors
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 1.2 Session Management

**Test:** Create new session

- [ ] **1.2.1** Click "Create New Session"
- [ ] **1.2.2** Session created with format `YYYY-MM-DD_N`
- [ ] **1.2.3** Session directory created on server
- [ ] **1.2.4** Subdirectories created: input/, analysis/, packing_lists/, stock_exports/
- [ ] **1.2.5** session_info.json created with correct metadata
- [ ] **1.2.6** File loading buttons enabled

**Expected:** New session folder structure created on server
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 1.3 File Loading

**Test:** Load CSV files

- [ ] **1.3.1** Click "Load Orders File"
- [ ] **1.3.2** Select `comprehensive_orders.csv`
- [ ] **1.3.3** File validation succeeds
- [ ] **1.3.4** File copied to session/input/
- [ ] **1.3.5** Orders file path displayed in UI
- [ ] **1.3.6** Click "Load Stock File"
- [ ] **1.3.7** Select `comprehensive_stock.csv`
- [ ] **1.3.8** File validation succeeds
- [ ] **1.3.9** File copied to session/input/
- [ ] **1.3.10** Stock file path displayed in UI
- [ ] **1.3.11** "Run Analysis" button enabled

**Expected:** Both files loaded and copied to session
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

## 📊 PHASE 2: ANALYSIS EXECUTION

### 2.1 Run Analysis

**Test:** Execute fulfillment analysis

- [ ] **2.1.1** Click "Run Analysis"
- [ ] **2.1.2** Progress indicator shows
- [ ] **2.1.3** Analysis completes without errors
- [ ] **2.1.4** Success message displays
- [ ] **2.1.5** Analysis results appear in data table
- [ ] **2.1.6** Statistics panel updates

**Expected:** Analysis runs successfully
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 2.2 Analysis Results

**Test:** Verify analysis results accuracy

- [ ] **2.2.1** Total orders: 12
- [ ] **2.2.2** Total line items: 24
- [ ] **2.2.3** Fulfillable orders: ~7-8 (check TEST_SCENARIOS.md)
- [ ] **2.2.4** Not fulfillable orders: ~4-5
- [ ] **2.2.5** Order #1008 tagged as "Repeat"
- [ ] **2.2.6** Color coding correct:
  - [ ] Green rows (Fulfillable)
  - [ ] Red rows (Not Fulfillable)
  - [ ] Yellow rows (Repeat orders)

**Expected:** Results match expected values from TEST_SCENARIOS.md
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 2.3 Analysis Files

**Test:** Verify analysis output files

- [ ] **2.3.1** File created: `session/analysis/analysis_report.xlsx`
- [ ] **2.3.2** File created: `session/analysis/analysis_data.json`
- [ ] **2.3.3** Excel file opens without errors
- [ ] **2.3.4** Excel contains all expected columns
- [ ] **2.3.5** JSON file is valid JSON format
- [ ] **2.3.6** JSON contains orders array

**Expected:** Both analysis output files created correctly
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

## ⚙️ PHASE 3: SETTINGS WINDOW

### 3.1 Open Settings

**Test:** Settings window functionality

- [ ] **3.1.1** Click "Client Settings" button
- [ ] **3.1.2** Settings window opens without errors
- [ ] **3.1.3** All tabs present: Settings, Rules, Packing Lists, Stock Exports, Mappings
- [ ] **3.1.4** Existing configurations loaded (if any)

**Expected:** Settings window opens and loads configurations
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 3.2 Configure Packing List

**Test:** Create packing list configuration

- [ ] **3.2.1** Go to "Packing Lists" tab
- [ ] **3.2.2** Click "Add Packing List"
- [ ] **3.2.3** Set name: "Test DHL Orders"
- [ ] **3.2.4** Set filename: "Test_DHL.xlsx"
- [ ] **3.2.5** Add filter: Shipping_Provider == DHL
- [ ] **3.2.6** Set exclude SKUs: "07, Shipping protection"
- [ ] **3.2.7** Click "Save"
- [ ] **3.2.8** No errors on save
- [ ] **3.2.9** Close Settings

**Expected:** Packing list configuration saved
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 3.3 Settings Persistence

**Test:** Verify configuration persists

- [ ] **3.3.1** Open Settings again
- [ ] **3.3.2** Go to "Packing Lists" tab
- [ ] **3.3.3** "Test DHL Orders" configuration visible
- [ ] **3.3.4** All settings intact (name, filename, filters, excludes)
- [ ] **3.3.5** Close Settings

**Expected:** Configuration loaded correctly on reopen
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 3.4 Configure Stock Export

**Test:** Create stock export configuration

- [ ] **3.4.1** Open Settings
- [ ] **3.4.2** Go to "Stock Exports" tab
- [ ] **3.4.3** Click "Add Stock Export"
- [ ] **3.4.4** Set name: "Test Export ALL"
- [ ] **3.4.5** Set filename: "test_export.xls"
- [ ] **3.4.6** No filters (leave empty for ALL)
- [ ] **3.4.7** Click "Save"
- [ ] **3.4.8** Close and reopen Settings
- [ ] **3.4.9** Verify configuration persists

**Expected:** Stock export configuration saved and persists
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

## 📄 PHASE 4: REPORT GENERATION

### 4.1 Generate Packing List

**Test:** Create packing list from configuration

- [ ] **4.1.1** Ensure analysis has been run
- [ ] **4.1.2** Click "Create Packing List" button
- [ ] **4.1.3** Dialog shows available packing lists
- [ ] **4.1.4** "Test DHL Orders" appears in list
- [ ] **4.1.5** Select "Test DHL Orders"
- [ ] **4.1.6** Click Generate
- [ ] **4.1.7** No errors during generation
- [ ] **4.1.8** Success message displays

**Expected:** Packing list generation succeeds
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 4.2 Verify Packing List Format

**Test:** Check packing list output format

- [ ] **4.2.1** Navigate to `session/packing_lists/`
- [ ] **4.2.2** File `Test_DHL.xlsx` exists
- [ ] **4.2.3** File `Test_DHL.json` exists
- [ ] **4.2.4** Open XLSX file
- [ ] **4.2.5** Format matches expected (6 columns):
  - [ ] Destination_Country
  - [ ] Order_Number
  - [ ] SKU
  - [ ] Product_Name (or filename in header)
  - [ ] Quantity
  - [ ] Shipping_Provider (or timestamp in header)
- [ ] **4.2.6** Header contains timestamp
- [ ] **4.2.7** Header contains filename
- [ ] **4.2.8** Rows are formatted (borders, grouping by order)
- [ ] **4.2.9** SKU "07" excluded (if in config)
- [ ] **4.2.10** "Shipping protection" excluded (if in config)
- [ ] **4.2.11** Only DHL orders present
- [ ] **4.2.12** Open JSON file
- [ ] **4.2.13** Valid JSON structure
- [ ] **4.2.14** Contains orders array

**Expected:** Packing list formatted correctly, ready for warehouse
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 4.3 Generate Stock Export

**Test:** Create stock export

- [ ] **4.3.1** Click "Create Stock Export" button
- [ ] **4.3.2** Dialog shows available stock exports
- [ ] **4.3.3** "Test Export ALL" appears in list
- [ ] **4.3.4** Select "Test Export ALL"
- [ ] **4.3.5** Click Generate
- [ ] **4.3.6** No errors during generation
- [ ] **4.3.7** Success message displays

**Expected:** Stock export generation succeeds
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 4.4 Verify Stock Export Format

**Test:** Check stock export output format

- [ ] **4.4.1** Navigate to `session/stock_exports/`
- [ ] **4.4.2** File exists with format `test_export_{date}.xls`
- [ ] **4.4.3** Open XLS file
- [ ] **4.4.4** Contains exactly 2 columns:
  - [ ] Артикул
  - [ ] Наличност
- [ ] **4.4.5** Data is aggregated by SKU (no duplicates)
- [ ] **4.4.6** Quantities are summed correctly
- [ ] **4.4.7** All fulfillable SKUs present
- [ ] **4.4.8** Format ready for warehouse system import

**Expected:** Stock export aggregated correctly, proper format
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

## 📈 PHASE 5: STATISTICS & HISTORY

### 5.1 Statistics Recording

**Test:** Verify statistics are recorded on server

- [ ] **5.1.1** After analysis, check `Stats/global_stats.json`
- [ ] **5.1.2** File exists on server
- [ ] **5.1.3** File is valid JSON
- [ ] **5.1.4** Contains updated statistics:
  - [ ] total_analyses incremented
  - [ ] total_orders_analyzed updated
  - [ ] total_items_analyzed updated
  - [ ] client statistics updated
- [ ] **5.1.5** Timestamp updated to recent time

**Expected:** Statistics recorded correctly on server
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 5.2 Fulfillment History

**Test:** Verify history is saved on server

- [ ] **5.2.1** Check `Clients/CLIENT_M/fulfillment_history.csv`
- [ ] **5.2.2** File exists on server (not in %APPDATA%)
- [ ] **5.2.3** Contains headers: Order_Number, Date_Fulfilled
- [ ] **5.2.4** Repeat orders are recorded
- [ ] **5.2.5** Run analysis again
- [ ] **5.2.6** History file updated with new data

**Expected:** History saved on server, not locally
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

## 🔄 PHASE 6: WORKFLOW INTEGRATION

### 6.1 Load Existing Session

**Test:** Open previously created session

- [ ] **6.1.1** Restart application
- [ ] **6.1.2** Select CLIENT_M
- [ ] **6.1.3** Session browser shows previous session
- [ ] **6.1.4** Select previous session
- [ ] **6.1.5** Analysis data loads correctly
- [ ] **6.1.6** Data table populates
- [ ] **6.1.7** Statistics display correctly
- [ ] **6.1.8** Can generate reports from loaded session

**Expected:** Previous session loads correctly
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 6.2 Packing Tool Integration Prep

**Test:** Verify files ready for Packing Tool

- [ ] **6.2.1** Check `session/packing_lists/Test_DHL.json`
- [ ] **6.2.2** JSON structure matches Packing Tool format:
  - [ ] session_id
  - [ ] created_at
  - [ ] total_orders
  - [ ] total_items
  - [ ] orders array with:
    - [ ] order_number
    - [ ] order_type
    - [ ] items array (sku, product_name, quantity)
    - [ ] courier
    - [ ] destination
    - [ ] tags
- [ ] **6.2.3** All fields populated correctly
- [ ] **6.2.4** Ready for Packing Tool import

**Expected:** JSON files properly formatted for Packing Tool
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

## 🧪 PHASE 7: EDGE CASES

### 7.1 Empty Analysis

**Test:** Handle no fulfillable orders

- [ ] **7.1.1** Create session with only out-of-stock items
- [ ] **7.1.2** Run analysis
- [ ] **7.1.3** Application handles gracefully
- [ ] **7.1.4** Appropriate message shown
- [ ] **7.1.5** Can still generate reports (empty)

**Expected:** Graceful handling of edge case
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 7.2 Large Dataset

**Test:** Performance with many orders

- [ ] **7.2.1** Create CSV with 500+ orders
- [ ] **7.2.2** Load and analyze
- [ ] **7.2.3** Analysis completes in < 30 seconds
- [ ] **7.2.4** UI remains responsive
- [ ] **7.2.5** Reports generate correctly

**Expected:** Good performance with large datasets
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

### 7.3 Special Characters

**Test:** Handle Cyrillic and special characters

- [ ] **7.3.1** Test with Cyrillic product names
- [ ] **7.3.2** Verify display in UI
- [ ] **7.3.3** Verify in Excel reports
- [ ] **7.3.4** Verify in JSON files
- [ ] **7.3.5** No encoding errors

**Expected:** Proper UTF-8 handling throughout
**Result:** [ ] PASS  [ ] FAIL
**Notes:** ___________________________

---

## 🏁 FINAL VALIDATION

### Summary

**Total Tests:** ___ / ___
**Passed:** ___
**Failed:** ___
**Pass Rate:** ___%

### Critical Issues Found

1. ___________________________
2. ___________________________
3. ___________________________

### Non-Critical Issues

1. ___________________________
2. ___________________________
3. ___________________________

### Sign-Off

- [ ] All critical functionality working
- [ ] No blocking bugs found
- [ ] Ready for Phase 2 development

**Tester Signature:** _______________
**Date:** _______________

---

## 📝 NOTES SECTION

Additional observations:

_______________________________________________
_______________________________________________
_______________________________________________
_______________________________________________

---

**Checklist Version:** 1.0
**Last Updated:** 2025-11-07
**Compatible With:** Shopify Tool v1.7+
