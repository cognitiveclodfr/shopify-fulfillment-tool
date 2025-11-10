# Test Scenarios - Comprehensive Test Data

This document describes all test scenarios included in the comprehensive test data and their expected results.

## 📊 Test Data Overview

**Orders:** 12 orders, 24 line items
**Time Range:** 2025-11-05 to 2025-11-07
**Couriers:** DHL, DPD, PostOne, Speedy
**Countries:** Bulgaria (BG), Germany (DE), United Kingdom (GB)

---

## 🎯 SCENARIO 1: Single-Item Orders (Fulfillable)

### Order #1001 - Standard Single DHL
- **SKU:** 01-DM-0379-110-L (Python Camo Denim L)
- **Quantity:** 1
- **Courier:** DHL
- **Stock:** 200 available
- **Expected Result:** ✅ FULFILLABLE
- **Notes:** High stock, no competition

### Order #1002 - Single DPD with Discount
- **SKU:** 01-DM-0239-003-M (Flare Repaired Denim)
- **Quantity:** 1
- **Courier:** DPD
- **Stock:** 50 available
- **Expected Result:** ✅ FULFILLABLE
- **Notes:** Has discount code "SAVE10"

### Order #1003 - Single PostOne (Competing)
- **SKU:** 01-DM-0339-006-M (Eyelet Flare Denim)
- **Quantity:** 2
- **Courier:** PostOne
- **Stock:** 4 available (CRITICAL)
- **Competes With:** Order #1005 (wants 3 of same SKU)
- **Expected Result:** ⚠️ DEPENDS ON PRIORITY
  - If processed before #1005: ✅ FULFILLABLE
  - If processed after #1005: ❌ NOT FULFILLABLE (insufficient stock)

---

## 🎯 SCENARIO 2: Multi-Item Orders (Priority Processing)

### Order #1004 - Multi DHL VIP Priority ⭐
- **Items:**
  - 01-DM-0379-110-L × 1 (Stock: 200)
  - 01-DM-03-Diamond-L × 1 (Stock: 100)
  - 03-SK-0230-001-OS × 1 (Stock: 150)
- **Courier:** DHL
- **Tags:** Priority, VIP
- **Expected Result:** ✅ FULFILLABLE (Process FIRST - multi-item priority)
- **Notes:** Should be processed before single-item orders due to multi-item prioritization

### Order #1005 - Multi Speedy (Stock Competition)
- **Items:**
  - 01-DM-0339-006-M × 3 (Stock: 4 - INSUFFICIENT!)
  - 01-DM-0334-001-M × 1 (Stock: 10)
- **Courier:** Speedy
- **Competes With:** Order #1003 for same SKU
- **Expected Result:** ❌ PARTIALLY FULFILLABLE or NOT FULFILLABLE
  - Multi-item priority means it should be checked first
  - Needs 3 units but stock has only 4
  - If Order #1003 already took 2, only 2 remain
  - **Likely:** ❌ NOT FULFILLABLE (cannot complete multi-item order)

---

## 🎯 SCENARIO 3: Not Fulfillable Orders

### Order #1006 - Insufficient Stock (Single)
- **SKU:** 01-HD-0341-104-S (Limited Edition Hoodie)
- **Quantity:** 5
- **Stock:** 2 available
- **Expected Result:** ❌ NOT FULFILLABLE
- **Notes:** Wants 5, only 2 in stock

---

## 🎯 SCENARIO 4: International Orders

### Order #1007 - International Germany
- **SKU:** 01-DM-0342-104-L
- **Quantity:** 1
- **Courier:** DHL International
- **Country:** Germany (DE)
- **Stock:** 45 available
- **Expected Result:** ✅ FULFILLABLE
- **Notes:** Has customs notes, VAT included

---

## 🎯 SCENARIO 5: Repeat Customer

### Order #1008 - Repeat Customer
- **SKU:** 01-PT-0269-066-M
- **Quantity:** 1
- **Courier:** DHL
- **Email:** customer1@example.com (same as Order #1001)
- **Expected Result:** ✅ FULFILLABLE + Tag "Repeat"
- **Notes:** Should be automatically tagged as repeat order by system

---

## 🎯 SCENARIO 6: Exclude SKUs

### Order #1009 - Contains Fee SKU "07"
- **Items:**
  - 01-DM-0379-110-L × 1 (Stock: 200)
  - 07 × 1 (Fee SKU)
- **Courier:** DPD
- **Expected Result:** ✅ FULFILLABLE
- **Packing List Behavior:**
  - If exclude_skus includes "07": Should show only main product
  - If no exclusion: Should show both items
- **Stock Export:** Should aggregate both SKUs

### Order #1010 - Contains Shipping Protection
- **Items:**
  - 03-SK-0321-074-S/M × 2 (Stock: 60)
  - Shipping protection × 1 (Service SKU)
- **Courier:** PostOne
- **Expected Result:** ✅ FULFILLABLE
- **Packing List Behavior:** Similar to #1009 with "Shipping protection" exclusion

---

## 🎯 SCENARIO 7: Edge Cases

### Order #1011 - Very Low Stock Competition
- **Items:**
  - 01-HD-0341-104-S × 1 (Stock: 2 - competes with #1006)
  - 01-DM-0380-001-M × 1 (Stock: 8)
- **Courier:** DHL
- **Expected Result:** ❌ PARTIALLY FULFILLABLE
  - Hoodie: ❌ NOT FULFILLABLE (if #1006 checked first, no stock)
  - Denim: ✅ FULFILLABLE (stock available)
  - **Overall:** ❌ NOT FULFILLABLE (multi-item order incomplete)

### Order #1012 - High Priority International
- **Items:**
  - 01-DM-03-Diamond-S × 1 (Stock: 80)
  - 01-TE-0350-105-L × 1 (Stock: 35)
- **Courier:** DHL Express International
- **Country:** United Kingdom (GB)
- **Tags:** Priority, International, Express
- **Expected Result:** ✅ FULFILLABLE
- **Notes:** High priority + international + express shipping

---

## 📈 Expected Analysis Results

### Summary Statistics

| Metric | Expected Value | Notes |
|--------|---------------|-------|
| Total Orders | 12 | - |
| Total Line Items | 24 | - |
| Fulfillable Orders | ~7-8 | Depends on processing order |
| Not Fulfillable Orders | ~4-5 | Due to stock competition |
| Multi-Item Orders | 5 | Should be prioritized |
| Single-Item Orders | 7 | Processed after multi |
| International Orders | 2 | #1007 (DE), #1012 (GB) |
| Repeat Orders | 1 | #1008 (same email as #1001) |
| Priority Tagged | 2 | #1004, #1012 |

### Stock Competition Critical Points

**SKU: 01-DM-0339-006-M (Eyelet Flare Denim)**
- Stock: 4 units
- Demand: 2 (#1003) + 3 (#1005) = 5 units
- **Result:** One order will NOT be fulfilled

**SKU: 01-HD-0341-104-S (Limited Edition Hoodie)**
- Stock: 2 units
- Demand: 5 (#1006) + 1 (#1011) = 6 units
- **Result:** Both orders will NOT be fulfilled

### Courier Distribution

| Courier | Orders | Expected Fulfillable |
|---------|--------|---------------------|
| DHL | 6 | 4-5 |
| DPD | 2 | 2 |
| PostOne | 2 | 1-2 |
| Speedy | 1 | 0 |

---

## 🧪 Testing Processing Order

The analysis engine should process in this order:

1. **Multi-item orders first** (maximize completions)
   - #1004 ✅ Priority VIP
   - #1012 ✅ Priority International
   - #1005 ❌ (Stock conflict)
   - #1009 ✅ (Has fee SKU)
   - #1010 ✅ (Has protection)
   - #1011 ❌ (Stock conflict)

2. **Single-item orders second**
   - #1001 ✅
   - #1002 ✅
   - #1003 ⚠️ (Depends on #1005)
   - #1006 ❌ (Insufficient stock)
   - #1007 ✅ International
   - #1008 ✅ Repeat

---

## ✅ Validation Checklist

Use this checklist when testing with comprehensive data:

### Analysis Phase
- [ ] 12 orders loaded correctly
- [ ] 24 line items detected
- [ ] Multi-item orders processed before single-item
- [ ] Stock simulation shows correct "Not Fulfillable" orders
- [ ] Low stock alerts triggered for critical SKUs
- [ ] Repeat customer detected (#1008)
- [ ] International orders flagged (#1007, #1012)

### Packing Lists
- [ ] DHL packing list contains correct orders
- [ ] Exclude SKU "07" works (if configured)
- [ ] Exclude "Shipping protection" works (if configured)
- [ ] Destination countries shown correctly
- [ ] Quantities accurate
- [ ] JSON files generated for Packing Tool

### Stock Exports
- [ ] SKUs aggregated correctly
- [ ] Quantities summed by SKU
- [ ] Format correct (Артикул, Наличност)
- [ ] Exclude SKUs handled properly

### Statistics
- [ ] Total orders count correct
- [ ] Fulfillable vs Not Fulfillable split accurate
- [ ] Items to write off calculated correctly
- [ ] Courier breakdown correct
- [ ] Low stock warnings shown

---

## 🔍 Known Issues to Watch For

1. **Stock Competition:** Orders #1003 and #1005 compete for SKU 01-DM-0339-006-M
   - Only 4 available, need 5 total
   - Multi-item priority means #1005 should be checked first
   - But #1005 needs 3 and will fail (multi can't be partial)
   - So #1003 (needs 2) might succeed

2. **Low Stock Critical:** SKU 01-HD-0341-104-S
   - Only 2 in stock
   - Orders want 6 total
   - Both orders should fail

3. **Exclude SKUs:** Make sure "07" and "Shipping protection" are in exclude list
   - Check packing list configuration
   - Verify they don't appear in warehouse packing lists

---

## 🎯 Success Criteria

The test data is working correctly if:

✅ Multi-item orders are processed before single-item
✅ Stock competition is handled correctly (some orders fail)
✅ Repeat customers are detected
✅ International orders are flagged
✅ Exclude SKUs work in packing lists
✅ Stock exports show aggregated quantities
✅ Priority tags are respected
✅ Low stock warnings appear

---

**Last Updated:** 2025-11-07
**Data Version:** 1.0
**Compatible With:** Shopify Tool v1.7+, Packing Tool v2.0+
