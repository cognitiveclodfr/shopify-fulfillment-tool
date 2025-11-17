# Quick Start Guide - Shopify Fulfillment Tool

**Version 1.8.0** | 5-Minute Setup

---

## 🚀 First Time Setup

### Step 1: Launch Application
Double-click `gui_main.py` or application shortcut

### Step 2: Select Client
Top dropdown → Select your client (e.g., "M - Main Client")

### Step 3: Load Files
1. Click **"📁 Load Orders"** → Select orders CSV
2. Click **"📁 Load Stock"** → Select stock CSV

### Step 4: Run Analysis
Click **"▶️ Run Analysis"** → Wait 5-30 seconds

### Step 5: Generate Report
Click **"📄 Generate Packing List"** → Choose location → Done!

---

## ⚡ Daily Workflow

```
┌─────────────────────────────────────────┐
│ 1. Export orders + stock from Shopify  │
│    ↓                                    │
│ 2. Load into Fulfillment Tool          │
│    ↓                                    │
│ 3. Run Analysis                         │
│    ↓                                    │
│ 4. Review Results                       │
│    ↓                                    │
│ 5. Generate Packing List                │
│    ↓                                    │
│ 6. Print & Process Orders               │
└─────────────────────────────────────────┘
```

**Time:** 5-10 minutes per day

---

## 📋 Required CSV Columns

**Orders File:**
- `Order_Number` - Unique order ID
- `SKU` - Product code
- `Quantity` - Number of items

**Stock File:**
- `SKU` - Product code
- `Stock_Quantity` - Units available

*Other columns optional*

---

## 🔴🟢🟡 Color Indicators

After analysis, rows are color-coded:

- **🟢 Green** - Order is fulfillable (all items in stock)
- **🔴 Red** - Order is NOT fulfillable (out of stock)
- **🟡 Yellow** - Repeat customer (ordered before)

---

## 📊 Understanding Statistics

After analysis completes, check the statistics panel:

```
Total Orders: 150
  • Fulfillable: 120 (80%)
  • Not Fulfillable: 30 (20%)

By Courier:
  • DHL: 60 orders
  • PostOne: 40 orders
  • Speedy: 30 orders

Repeat Customers: 15
Low Stock Alerts: 5 SKUs
```

---

## 🆘 Common Issues

| Problem | Quick Fix |
|---------|-----------|
| **File won't load** | Check file is CSV (not XLS) |
| **"Server not found"** | Check VPN connection |
| **Analysis stuck** | Wait or split into smaller batches |
| **Results look wrong** | Check column mappings in Settings |
| **Missing orders in packing list** | Check filters and excluded SKUs |

---

## ⚙️ Key Settings

**Access Settings:** Click **⚙️ Settings** button (top-right)

**Important Tabs:**
- **Rules** - Automate order tagging and categorization
- **Packing Lists** - Configure courier-specific reports
- **Column Mappings** - Map CSV headers to system fields
- **Courier Mappings** - Map shipping methods to couriers

---

## 📁 File Requirements

**Orders CSV Format:**
```csv
Name,Lineitem sku,Lineitem quantity,Shipping Method
12345,SKU-001,2,DHL Express
12346,SKU-002,1,PostOne Standard
```

**Stock CSV Format:**
```csv
SKU,Product_Name,Stock_Quantity
SKU-001,Product A,50
SKU-002,Product B,120
```

**💡 Tip:** Use UTF-8 encoding for best compatibility

---

## 🎯 Quick Tips

**Performance:**
- 1,000 orders → ~5 seconds
- 10,000 orders → ~30 seconds
- For 50,000+ orders, split into batches

**Best Practices:**
- Run analysis daily for fresh data
- Review low stock alerts
- Check repeat customer orders for special handling
- Use rules to automate repetitive tasks

**Shortcuts:**
- Double-click session in History to reload
- Right-click data table for quick actions
- Use search/filter to find specific orders

---

## 📖 Need More Help?

**Full Documentation:**
- **User Guide:** `docs/USER_GUIDE.md` - Comprehensive feature guide
- **Technical Docs:** `docs/` folder - API and architecture
- **Troubleshooting:** See USER_GUIDE.md Section 6

**Support:**
- IT Department / Warehouse Manager
- Logs: `Logs/shopify_tool/` on server
- GitHub Issues: Report bugs and feature requests

---

## 📅 Session Management

**Creating Sessions:**
- Sessions auto-named by date: `2025-11-17_1`
- Multiple sessions per day increment: `2025-11-17_2`, etc.
- Sessions auto-save every 5 minutes

**Loading Past Sessions:**
1. Go to **🕒 History** tab
2. Find session by date
3. Double-click to load

**Session Status:**
- ✅ **Complete** - Analysis finished
- 🔄 **In Progress** - Analysis running
- 🔒 **Locked** - Another user working

---

## 🔧 Advanced Features (Optional)

**Rule Engine:**
- Automatically tag orders based on conditions
- Example: Tag "COD" if payment method is Cash on Delivery
- Configure in Settings → Rules

**Sets/Bundles:**
- Define product bundles (e.g., Gift Set = Item A + Item B)
- System automatically expands and checks component stock

**Manual Product Addition:**
- Add items to orders on-the-fly
- Live recalculation of stock impact

**Multiple Export Formats:**
- Excel (.xlsx) for printing
- JSON for Packing Tool integration
- XLS for legacy systems

---

## ✅ Quick Checklist

Before running analysis, ensure:
- [ ] Client selected from dropdown
- [ ] Orders CSV loaded successfully
- [ ] Stock CSV loaded successfully
- [ ] No error messages displayed

After analysis:
- [ ] Check statistics for fulfillment %
- [ ] Review low stock alerts
- [ ] Verify repeat customer orders
- [ ] Generate packing list for each courier

---

## 🎉 You're Ready!

**Next Steps:**
1. Load your first order and stock files
2. Run analysis
3. Review results
4. Generate packing list
5. Start processing orders!

**Pro Tip:** Save this guide as a bookmark for quick reference.

---

**That's it! You're ready to process orders.** 🎉

For detailed explanations, see the [Full User Guide](USER_GUIDE.md).

---

**Version:** 1.8.0
**Last Updated:** November 17, 2025
