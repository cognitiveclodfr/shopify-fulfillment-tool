# Shopify Fulfillment Tool - User Guide

**Version:** 1.8.0
**Document Type:** End-User Documentation
**Last Updated:** November 17, 2025
**Audience:** Warehouse Staff, Managers

---

## 📑 Table of Contents

1. [Welcome & Introduction](#-welcome--introduction)
2. [Getting Started](#-getting-started)
3. [Core Features](#-core-features)
4. [Advanced Features](#-advanced-features)
5. [Settings & Configuration](#%EF%B8%8F-settings--configuration)
6. [Troubleshooting](#-troubleshooting)
7. [FAQ](#-faq)
8. [Glossary](#-glossary)
9. [Support & Contact](#-support--contact)

---

## 👋 Welcome & Introduction

### What is the Shopify Fulfillment Tool?

The **Shopify Fulfillment Tool** is a desktop application designed to streamline warehouse order fulfillment for Shopify/WooComerse/ANY e-commerce operations. It helps you:

✅ **Analyze** which orders can be fulfilled based on available stock
✅ **Prioritize** orders intelligently (multi-item orders first)
✅ **Generate** packing lists for warehouse staff, stock exports for warehouse sigh off
✅ **Track** repeat errors automatically
✅ **Automate** order tagging and categorization
✅ **Export** data for integration with the Packing Tool

### Who is this guide for?

This guide is written for:
- **Warehouse staff** - Daily users who process orders
- **Logistics coordinators** - Configure settings and generate reports
- **Managers** - Understand workflow and statistics

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **Time Savings** | Automate fulfillment analysis in seconds vs. manual hours |
| **Accuracy** | Eliminate stock counting errors with automated simulation |
| **Visibility** | Real-time view of what can be shipped today |
| **Integration** | Seamless connection with Packing Tool for warehouse execution |
| **Multi-Client** | Manage multiple clients/brands from one application |

### Document Structure

This guide follows your **typical workflow**:
1. First-time setup (one-time)
2. Daily operations (repeated workflow)
3. Advanced features (as needed)
4. Troubleshooting (when issues arise)

**💡 Tip:** If you're brand new, start with [Getting Started](#-getting-started) and the [Quick Start Guide](QUICK_START.md).

---

## 🚀 Getting Started

### System Requirements

**Minimum Requirements:**
- **Operating System:** Windows 10 or Windows 11
- **Processor:** Intel i3 or equivalent (2 GHz+)
- **RAM:** 4 GB minimum, 8 GB recommended
- **Storage:** 500 MB free space
- **Network:** Access to file server at `\\192.168.88.101\`

**Recommended for Large Datasets (10,000+ orders):**
- **RAM:** 16 GB
- **Processor:** Intel i5 or better
- **SSD:** For faster file operations

### Installation

**For IT Staff:**

1. **Install Python 3.9+** (if not already installed)
   - Download from [python.org](https://www.python.org/downloads/)
   - Check "Add Python to PATH" during installation

2. **Clone or copy the application files** to a local directory:
   ```
   C:\Applications\ShopifyFulfillmentTool\
   ```

3. **Install dependencies:**
   - Open Command Prompt (CMD)
   - Navigate to the application folder
   - Run: `pip install -r requirements.txt`

4. **Create desktop shortcut** (optional):
   - Right-click `gui_main.py`
   - Send to → Desktop (create shortcut)

**For End Users:**

Most users will find the application already installed and a shortcut on the desktop. Simply double-click the shortcut to launch.

### First Launch

When you first launch the application:

1. **Splash Screen** appears briefly (loading modules)
2. **Main Window** opens with the "Session Setup" tab active
3. **Client Dropdown** at the top shows available clients

**Visual Reference:**
```
[Screenshot placeholder: First launch - main window with client dropdown]
```

### Understanding the Interface

The application has **4 main tabs**:

| Tab | Purpose |
|-----|---------|
| **📋 Session Setup** | Create sessions, load files, run analysis |
| **📊 Analysis Results** | View results, edit data, generate reports |
| **🕒 Session Browser** | Browse past sessions and reload them |
| **ℹ️ Info** | View application logs and diagnostics and stats |

**Quick Tour:**

```
┌─────────────────────────────────────────────────────┐
│ [Client: CLIENT_M ▼]             [⚙️ Manage Clients]│
├─────────────────────────────────────────────────────┤
│ ┌─ Session Setup ─┐  Analysis Results  History  Info│
│ │                                                    │
│ │  📁 Load Orders CSV                                │
│ │  📁 Load Stock CSV                                 │
│ │  ▶️ Run Analysis                                   │
│ │                                                    │
│ │  Statistics Panel:                                 │
│ │  • Total Orders: 0                                 │
│ │  • Fulfillable: 0                                  │
│ │  • Not Fulfillable: 0                              │
│ └────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────┘
```

---

## 🎯 Core Features

### Feature 1: Session Management

#### What is a Session?

A **session** represents one run of order analysis. Think of it as a "work folder" containing:
- Input files (orders CSV, stock CSV)
- Analysis results
- Generated packing lists
- Export files

Sessions are stored on the **file server** and can be accessed from any computer in the warehouse.

#### Creating a New Session

**Steps:**

1. **Select your client** from the dropdown at the top
   - Example: "CLIENT_M - Main Client"

2. **Click "Create New Session"** button in the Session Setup tab

3. **Session created automatically** with a unique name:
   - Format: `2025-11-17_1` (date + sequence number)
   - If you create multiple sessions on the same day, the number increments: `2025-11-17_2`, `2025-11-17_3`, etc.

4. **Session structure created on server:**
   ```
   Sessions/CLIENT_M/2025-11-17_1/
   ├── session_info.json          # Session metadata
   ├── input/                     # Your uploaded CSV files
   ├── analysis/                  # Analysis results
   ├── packing_lists/             # Generated packing lists
   └── stock_exports/             # Stock export files
   ```

**Visual Reference:**
```
[Screenshot placeholder: Create New Session button and session folder structure]
```

**💡 Tip:** Sessions auto-save every 5 minutes. You don't need to manually save.

#### Loading an Existing Session

To continue working on a previous session:

1. Go to **🕒 Session Browser** tab

2. **Browse sessions** in the table:
   - Columns: Session ID, Date Created, Total Orders, Status

3. **Double-click** a session row to load it

4. **Analysis Results** tab opens with your previous work

**Session Status Indicators:**

| Status | Meaning |
|--------|---------|
| ✅ **Complete** | Analysis finished, packing lists generated |
| 🔄 **Active** | Analysis running or incomplete |
| 📝 **Abbadoned** | Session created but analysis not started |
| 🔒 **Locked** | Another user is currently working on this session |

**Visual Reference:**
```
[Screenshot placeholder: History tab showing session browser]
```

#### Session Locking

**Why sessions lock:**
- Prevents two people from editing the same session simultaneously
- Avoids data conflicts and lost work

**When you see a lock:**
1. Check who has the session open (shown in status)
2. Wait for them to finish
3. Or create a new session for your work

**Unlocking a session:**
- Sessions auto-unlock when you close the application
- If someone's computer crashed, IT can manually unlock

---

### Feature 2: Loading Data

#### Required Files

You need **two CSV files** to run an analysis:

1. **Orders File** - Export from Shopify with all pending orders
2. **Stock File** - Current inventory levels

#### Preparing Your CSV Files

**Orders File (`orders_export.csv`):**

Export from Shopify Admin → Orders → Export:
- File format: CSV
- Date range: Select pending orders only
- Include: All order details

**Required columns:**
- `Name` - Order number (e.g., #12345)
- `Lineitem sku` - Product SKU
- `Lineitem quantity` - Quantity ordered
- `Shipping Method` - Courier/shipping method
- `Shipping Country` - Destination

**Optional but recommended:**
- `Tags` - Order tags
- `Notes` - Order notes
- `Total` - Order total

**Stock File (`inventory.csv`):**

Export from your inventory system:
- File format: CSV
- Encoding: UTF-8 (important!)

**Required columns:**
- `SKU` or `Артикул` - Product code
- `Stock_Quantity` or `Наличност` - Available quantity

**Example:**
```csv
Артикул,Име,Наличност
SKU-001,Product A,50
SKU-002,Product B,120
SKU-003,Product C,0
```

**💡 Tips:**
- Column names are flexible (mappings can be configured)
- Cyrillic column names are supported
- Ensure no extra spaces in SKU codes
- Quantities should be integers (not decimals)

**Visual Reference:**
```
[Screenshot placeholder: Example CSV files open in Excel]
```

#### Loading Files into a Session

**Steps:**

1. **Click "📁 Load Orders"** button
   - File browser opens
   - Navigate to your orders CSV file
   - Click "Open"
   - File is validated and copied to session's `input/` folder
   - Success message appears: ✅ "Orders file loaded: 150 rows"

2. **Click "📁 Load Stock"** button
   - File browser opens
   - Navigate to your stock CSV file
   - Click "Open"
   - File is validated and copied to session's `input/` folder
   - Success message appears: ✅ "Stock file loaded: 300 SKUs"

**Validation Checks:**

The application automatically checks:
- ✅ File format is CSV (not Excel .xlsx)
- ✅ File encoding is readable (UTF-8 preferred)
- ✅ Required columns are present
- ✅ Data types are correct (quantities are numbers)
- ✅ No completely empty rows

**If validation fails:**
- ❌ Error message shows what's wrong
- 💡 Check [Troubleshooting](#-troubleshooting) section

**Visual Reference:**
```
[Screenshot placeholder: Load Orders and Load Stock buttons with success messages]
```

#### Supported File Formats

| Format | Supported | Notes |
|--------|-----------|-------|
| **CSV (.csv)** | ✅ Yes | Preferred format |
| **TXT (.txt)** | ✅ Yes | If tab or comma delimited |
| **Excel (.xlsx)** | ❌ No | Export to CSV first |
| **Excel (.xls)** | ❌ No | Export to CSV first |

**Converting Excel to CSV:**
1. Open file in Excel
2. File → Save As
3. Format: **CSV UTF-8 (Comma delimited)**
4. Save
5. Load into application

---

### Feature 3: Running Analysis

#### What Happens During Analysis?

When you click "▶️ Run Analysis", the application:

1. **Cleans data** - Removes extra spaces, standardizes text
2. **Validates** - Checks for missing SKUs, invalid quantities
3. **Prioritizes** - Sorts orders (multi-item orders first)
4. **Simulates stock allocation** - Calculates what can be fulfilled
5. **Applies rules** - Automatic tagging, status changes
6. **Detects repeats** - Identifies repeating orders
7. **Generates statistics** - Order counts, courier breakdown

**Time estimates:**
- 100 orders: **< 2 seconds**
- 1,000 orders: **< 5 seconds**
- 10,000 orders: **< 30 seconds**

#### Running Your First Analysis

**Steps:**

1. **Ensure files are loaded:**
   - ✅ Orders file loaded
   - ✅ Stock file loaded

2. **Click "▶️ Run Analysis"** button

3. **Progress bar** appears showing:
   - Current step (e.g., "Cleaning data...")
   - Percentage complete
   - Estimated time remaining

4. **Analysis completes:**
   - ✅ Success message
   - Results appear in **Analysis Results** tab (automatically switched)
   - Statistics panel updates with numbers

**Visual Reference:**
```
[Screenshot placeholder: Analysis running with progress bar]
```

#### Understanding Analysis Results

Results are displayed in a **data table** with these columns:

| Column | Description |
|--------|-------------|
| **Order_Number** | Unique order identifier |
| **SKU** | Product code |
| **Product_Name** | Product description |
| **Quantity** | Number of items ordered |
| **Courier** | Shipping method (DHL, PostOne, etc.) |
| **Status** | Fulfillable / Not Fulfillable |
| **Tags** | Auto-generated tags |
| **Location** | Warehouse location (if configured) |

**Color Coding:**

Rows are color-coded for quick identification:

- 🟢 **Green** - Order is fulfillable (all items in stock)
- 🔴 **Red** - Order is NOT fulfillable (out of stock)
- 🟡 **Yellow** - Repeat orders (orders was analysed before)

**Visual Reference:**
```
[Screenshot placeholder: Analysis results table with color-coded rows]
```

#### Statistics Panel

After analysis, the statistics panel shows:

**Overall Statistics:**
```
Total Orders: 150
  • Fulfillable: 120 
  • Not Fulfillable: 30 

Total Items to Write Off: 450
Total Items not to Write Off: 50
```

**By Courier:**
```
DHL: 60 orders (250 items)
PostOne: 40 orders (120 items)
Speedy: 30 orders (50 items)
```

**Repeat orders:**
```
Repeat Orders: 15
```

**Visual Reference:**
```
[Screenshot placeholder: Statistics panel with numbers]
```

---

### Feature 4: Rule Engine

#### What are Rules?

**Rules** automate order processing by applying actions when certain conditions are met.

**Example:**
```
IF shipping method is "DHL Express"
THEN add tag "Priority" and set priority to "High"
```

This happens **automatically during analysis** - no manual work needed!

#### Common Use Cases

| Use Case | Rule Configuration |
|----------|-------------------|
| **Fragile Items** | If Product Name contains "Glass" → Add tag "Fragile" |
| **Express Shipping** | If Shipping = "Express" → Set Priority = "High" |
| **Exclude Test Orders** | If Order Number contains "TEST" → Exclude from report |
| **High Value** | If Order Total > 500 → Add tag "Insure" |

#### Creating a Rule

**Steps:**

1. **Open Client Settings:**
   - Click **⚙️ Open Client Settings** button
   - Go to **"Rules"** tab

2. **Click "Add Rule"** button

3. **Configure rule:**

   **Rule Name:**
   ```
   "DHL Orders"
   ```

   **Condition:**
   ```
   Field: Shipping_Method
   Operator: equals
   Value: "DHL"
   ```

   **Action:**
   ```
   Type: ADD_TAG
   Value: "High"
   ```

4. **Save rule**

**Visual Reference:**
```
[Screenshot placeholder: Rule configuration dialog]
```

#### Available Conditions

| Operator | Description | Example |
|----------|-------------|---------|
| `equals` | Exact match | Courier equals "DHL" |
| `not_equals` | Not equal | Status not_equals "Cancelled" |
| `contains` | Text contains | Product_Name contains "Glass" |
| `not_contains` | Text doesn't contain | Notes not_contains "Hold" |
| `greater_than` | Numeric > | Total greater_than 100 |
| `less_than` | Numeric < | Quantity less_than 5 |
| `in_list` | Value in list | Courier in_list ["DHL", "DPD"] |

#### Available Actions

| Action | Description | Example |
|--------|-------------|---------|
| `ADD_TAG` | Add a tag to order | ADD_TAG = "Priority" |
| `SET_STATUS` | Change order status | SET_STATUS = "Hold" |
| `SET_PRIORITY` | Set priority level | SET_PRIORITY = "High" |
| `EXCLUDE_FROM_REPORT` | Hide from packing list | EXCLUDE_FROM_REPORT |

#### Rule Examples

**Example 1: Tag Fragile Items**
```yaml
Rule Name: "Fragile Products"
Condition: Product_Name contains "Glass"
Action: ADD_TAG = "⚠️ Fragile - Handle with Care"
```

**Example 2: Prioritize Express Shipping**
```yaml
Rule Name: "Express Priority"
Condition: Shipping contains "Express"
Actions:
  - ADD_TAG = "Express"
  - SET_PRIORITY = "High"
```

**Example 3: Exclude Virtual Products**
```yaml
Rule Name: "Exclude Shipping Protection"
Condition: SKU equals "SHIPPING-PROTECT"
Action: EXCLUDE_FROM_REPORT
```

**Example 4: Identify Packaging Type by SKU Prefix**
```yaml
Rule Name: "Box Items Only"
Level: order
Condition: has_sku starts with "01-"
Action: ADD_ORDER_TAG = "BOX_ONLY"

Rule Name: "Bag Items Only"
Level: order
Condition: has_sku starts with "02-FACE-"
Action: ADD_ORDER_TAG = "BAG_ONLY"

Rule Name: "Mixed Packaging"
Level: order
Match: ALL
Conditions:
  - has_sku starts with "01-"
  - has_sku starts with "02-"
Action: ADD_ORDER_TAG = "MIXED"
```

**Why use order-level rules with has_sku?**
- **Packaging Detection**: Identify what type of packaging is needed based on SKU patterns
- **Mixed Orders**: Detect orders that need multiple packaging types
- **Workflow Automation**: Route orders to appropriate packing stations
- **Inventory Planning**: Track which product types are selling together


#### Managing Rules

**Edit Rules:**
- Click on rule place
- Modify conditions or actions
- Save changes
- Run analysis again to apply

**Delete Rules:**
- Click **Delete** button
- Cannot be undone


**Visual Reference:**
```
[Screenshot placeholder: Rules management interface]
```

---

### Feature 5: Generating Packing Lists

#### What is a Packing List?

A **packing list** is a formatted report for warehouse staff showing:
- Which orders to pack
- Which items to pick
- Quantities needed

The packing list is **filtered** based on criteria like:
- Courier (DHL, PostOne, Speedy, etc.)
- Status (only fulfillable orders)
- Excluded SKUs (virtual items removed)

#### Generating a Basic Packing List

**Steps:**

1. **Complete analysis first:**
   - ✅ Analysis must be run
   - ✅ Results in Analysis Results tab

2. **Click "📄 Generate Packing List"** button

3. **Select packing list type:**
   - Pre-configured lists appear (e.g., "DHL Orders", "PostOne Orders")
   - Or choose "All Orders" for unfiltered

4. **Save location:**
   - Automaticly at server folder of session, in folder packing_lists

5. **Packing list generated:**
   - ✅ Excel file (.xlsx) created for printing
   - ✅ JSON file (.json) created automatically for Packing Tool
   - Success message shows file paths

**Visual Reference:**
```
[Screenshot placeholder: Generate Packing List button and file save dialog]
```

#### Pre-Configured Packing Lists

Most clients have pre-configured packing lists:

| Packing List | Filter | Excluded SKUs |
|--------------|--------|---------------|
| **DHL Orders** | Courier = DHL | 07, Shipping protection |
| **PostOne Orders** | Courier = PostOne | 07, Shipping protection |
| **Speedy Orders** | Courier = Speedy | 07 |
| **All Orders** | No filter | None |

**Setting up in Client Settings:**
1. Settings → Packing Lists tab
2. Click "Add Packing List"
3. Configure name, courier filter, excluded SKUs
4. Save

**Visual Reference:**
```
[Screenshot placeholder: Packing list configuration in settings]
```

#### Understanding Packing List Format

**Excel Output (for humans):**

```
┌────────────────────────────────────────────────────────┐
│ PACKING LIST - DHL Orders                              │
│ Generated: 2025-11-17 14:30                            │                 
├────────────────────────────────────────────────────────┤
│ Order_Number │ SKU      │ Product_Name  │ Qty │ Location│
├──────────────┼──────────┼───────────────┼─────┼─────────┤
│ 12345        │ SKU-001  │ Product A     │  2  │ A-01    │
│ 12345        │ SKU-002  │ Product B     │  1  │ A-05    │
│ 12346        │ SKU-001  │ Product A     │  3  │ A-01    │
│ ...          │ ...      │ ...           │ ... │ ...     │
└──────────────┴──────────┴───────────────┴─────┴─────────┘
```

**Features:**
- Header with summary statistics
- Grouped by order for easy picking
- Warehouse locations shown
- Clean formatting for printing

**JSON Output (for Packing Tool):**

```json
{
  "session_id": "SESSION_001",
  "created_at": "2025-11-17T10:30:00",
  "orders": [
    {
      "order_number": "ORD-001",
      "items": [
        {
          "sku": "SKU-A",
          "quantity": 2,
          "location": "A-01"
        }
      ]
    }
  ],
  "statistics": {...}
}
```

**Verification:**
- XLSX and JSON should have identical data
- Verify order counts match
- Check SKUs match

---

## ⚙️ Settings & Configuration

### Client Configuration

**Accessing Client Settings:**

1. Click **⚙️ Open Client Settings** button
2. Go to **"Client Configuration"** tab
3. View/edit client-specific settings

**Key Settings:**

**1. Client Information**
```
- Client ID: M
- Client Name: Main Client
```

**2. Column Mappings**

Map CSV headers to system fields:

| Your CSV Header | System Field |
|-----------------|--------------|
| Order No. | Order_Number |
| Article | SKU |
| Qty | Quantity |
| Shipping | Courier |

**Why needed?**
Different suppliers use different column names. Mappings ensure system reads data correctly.

**Adding Mapping:**
1. Click **"Add Mapping"**
2. Enter CSV header name
3. Select system field
4. Save

**3. Courier Mappings**

Map shipping method names to couriers:

| Shipping Method in CSV | Mapped Courier |
|------------------------|----------------|
| DHL Express | DHL |
| DHL Standard | DHL |
| Post Office | PostOne |
| Bulgarian Post | PostOne |

**Adding Courier Mapping:**
1. Click **"Add Courier Mapping"**
2. Enter shipping method text
3. Select courier from dropdown
4. Save

**4. Low Stock Thresholds**

Set alerts for low stock:
```
Default Threshold: 10 units
Per-SKU Thresholds:
  - SKU-A: 20 units
  - SKU-B: 5 units
```

**Visual Reference:**
```
[Screenshot placeholder: Client configuration]
```

---

### Rule Configuration

Already covered in [Feature 2: Rule Engine](#feature-2-rule-engine).

**Quick Reference:**

**Available Conditions:**
- `equals` - Exact match
- `not_equals` - Not equal
- `contains` - Text contains
- `not_contains` - Text doesn't contain
- `greater_than` - Numeric >
- `less_than` - Numeric <
- `in_list` - Value in list

**Available Actions:**
- `ADD_TAG` - Add tag to order
- `SET_STATUS` - Change status
- `SET_PRIORITY` - Set priority (High/Medium/Low)
- `EXCLUDE_FROM_REPORT` - Hide from packing list

**Rule Examples:**
```

Rule: "Fragile Items"
Condition: Product_Name contains "Glass"
Action: ADD_TAG = "Fragile - Handle with Care"

Rule: "Urgent Priority"
Condition: Shipping equals "Express"
Action: SET_PRIORITY = "High"

Rule: "Exclude Test Orders"
Condition: Order_Number contains "TEST"
Action: EXCLUDE_FROM_REPORT
```

---

---

## 🔧 Troubleshooting

### Problem 1: "File Server Not Accessible"

**Symptoms:**
- Error message: "Cannot connect to file server"
- Application slow to start
- Cannot save sessions

**Causes:**
- Network disconnected
- VPN not connected
- Server maintenance
- Incorrect permissions

**Solutions:**

**Solution 1: Check Network Connection**
```
1. Open File Explorer
2. Navigate to \\192.168.88.101\
3. Can you see folders? → Network OK
4. Cannot see folders? → Network issue
```

**Solution 2: Restart VPN**
```
1. Disconnect VPN
2. Wait 10 seconds
3. Reconnect VPN
4. Try application again
```

**Solution 3: Check Permissions**
```
1. Contact IT administrator
2. Verify you have read/write access
3. Check group memberships
```

**Solution 4: Use Local Mode (Temporary)**
```
1. Save files locally (Desktop/Documents)
2. Load from local location
3. Work offline
4. Sync to server when connection restored
```

---

### Problem 2: "CSV Parsing Error"

**Symptoms:**
- Error: "Failed to parse CSV file"
- Error: "Invalid delimiter detected"
- Columns misaligned

**Causes:**
- Wrong file encoding (not UTF-8)
- Corrupted file
- Excel formatting issues
- Special characters in data

**Solutions:**

**Solution 1: Check Encoding**
```
1. Open CSV in Notepad++
2. Menu: Encoding → Convert to UTF-8
3. Save file
4. Try loading again
```

**Solution 2: Re-export from Excel**
```
1. Open file in Excel
2. File → Save As
3. Format: CSV UTF-8 (Comma delimited)
4. Save
5. Try loading new file
```

**Solution 3: Check for Commas in Data**
```
1. Open CSV in Excel
2. Check product names, addresses
3. If they contain commas, data might be split
4. Use column mapping to fix
```

**Solution 4: Manual Delimiter**
```
1. In settings, disable auto-detect
2. Manually select delimiter:
   - Comma (,)
   - Semicolon (;)
   - Tab (\t)
3. Try loading again
```

---

### Problem 3: "Analysis Stuck / Not Completing"

**Symptoms:**
- Progress bar stuck at X%
- Application not responding
- Takes very long time

**Causes:**
- Very large dataset (>50,000 orders)
- Insufficient memory
- Complex rules
- Corrupted data

**Solutions:**

**Solution 1: Wait Longer**
```
For 10,000+ orders, analysis can take 1-2 minutes.
Check progress bar percentage - if moving slowly, just wait.
```

**Solution 2: Split Dataset**
```
1. Split orders CSV into smaller files
2. Process 5,000-10,000 orders at a time
3. Merge results if needed
```

**Solution 3: Simplify Rules**
```
1. Disable complex rules temporarily
2. Run analysis
3. Apply rules manually after
```

**Solution 4: Restart Application**
```
1. Force close application (Task Manager)
2. Restart
3. Try again with smaller dataset
```

**Solution 5: Check System Resources**
```
1. Open Task Manager
2. Check memory usage
3. Close other applications
4. Free up RAM
5. Try again
```

---

### Problem 4: "Repeated Order False Positives"

**Symptoms:**
- Orders tagged as "REPEATED" but they're new
- Same order number used for different orders

**Causes:**
- Order numbering reset
- Multiple channels using same numbers
- System migration

**Solutions:**

**Solution 1: Check History**
```
1. Go to History tab
2. Search for order number
3. Verify if actually duplicate
4. If not duplicate, continue
```

**Solution 2: Clear History (if reset occurred)**
```
1. Settings → History
2. Click "Clear History Before Date"
3. Select cutoff date
4. Confirm
```

**Solution 3: Ignore Tag**
```
1. REPEATED tag is informational only
2. Does not prevent fulfillment
3. Can be ignored if you've verified
```

**Solution 4: Use Different Order Prefixes**
```
For multiple channels:
- Shopify orders: SHOP-001
- Amazon orders: AMZ-001
- Direct orders: DIR-001
```

---

### Problem 5: "Stock Calculations Wrong"

**Symptoms:**
- Stock levels don't match expectations
- Orders marked unfulfillable when stock exists
- Negative stock values

**Causes:**
- Stock CSV missing SKUs
- Sets not configured correctly
- Multi-location stock not summed
- Data type issues (text instead of number)

**Solutions:**

**Solution 1: Verify Stock CSV**
```
1. Open stock CSV
2. Check all SKUs present
3. Check quantities are numbers (not text)
4. Check no negative values
5. Check decimal places (use integers)
```

**Solution 2: Check Sets Configuration**
```
1. If using sets, verify set definitions
2. Check component SKUs exist in stock
3. Check quantities in set definition
4. Disable sets temporarily to test
```

**Solution 3: Check Column Mapping**
```
1. Settings → Column Mappings
2. Verify "Stock_Quantity" mapped correctly
3. Verify "SKU" mapped correctly
4. Test with simple dataset
```

**Solution 4: Sum Multi-Location Stock**
```
If stock across multiple locations:
1. Pre-process CSV in Excel
2. Use SUMIF to sum by SKU
3. Create single stock quantity column
4. Load processed file
```

---

### Problem 6: "Packing List Missing Orders"

**Symptoms:**
- Some orders not in packing list
- Order count doesn't match

**Causes:**
- Status filter applied
- Orders excluded by rule
- SKU exclusion list
- Orders not fulfillable

**Solutions:**

**Solution 1: Check Filters**
```
When generating packing list:
1. Check status filter → Set to "All"
2. Check courier filter → Set to "All"
3. Check SKU exclusions → Clear list
4. Generate again
```

**Solution 2: Check Rules**
```
1. Settings → Rules
2. Check for EXCLUDE_FROM_REPORT actions
3. Disable rule temporarily
4. Run analysis again
5. Generate packing list
```

**Solution 3: Check Fulfillability**
```
1. Go to Analysis Results
2. Filter by order number
3. Check Status column
4. If "Not Fulfillable", check stock
5. If stock sufficient, check for errors
```

**Solution 4: Verify Analysis Completed**
```
1. Check statistics panel
2. Verify all orders processed
3. If partial analysis, run again
```

---

## ❓ FAQ

### General Questions

**Q: Can multiple users work simultaneously?**

A: Yes, but on different sessions. The system uses session locking to prevent conflicts. If someone is working on a session, you'll see a lock icon. Wait for them to finish or create a new session.

**Q: Are my changes saved automatically?**

A: Yes, sessions auto-save every 5 minutes. However, it's good practice to use "Save Session" button after major changes.

**Q: Can I undo changes?**

A: Yes, use the Undo/Redo buttons in the Analysis Results tab. Undo history is session-specific.

**Q: How long are sessions kept?**

A: Sessions are kept for 90 days by default. Older sessions are archived. Contact admin to restore archived sessions.

**Q: Can I export data to other formats?**

A: Currently supported formats:
- Excel (.xlsx, .xls)
- JSON (for Packing Tool)
- CSV (raw data export)

PDF export planned for future version.

---

### File Format Questions

**Q: What CSV format is required?**

A: The tool is flexible and supports most CSV formats. Required columns:
- Orders: `Order_Number`, `SKU`, `Quantity`
- Stock: `SKU`, `Stock_Quantity`

Other columns are optional but recommended (Product_Name, Courier, etc.)

**Q: Can I use semicolon (;) instead of comma?**

A: Yes, the tool auto-detects delimiters. Semicolon, comma, and tab are all supported.

**Q: Do I need to clean data before loading?**

A: Not usually. The tool handles:
- Extra spaces
- Mixed case
- Different date formats
- Unicode characters

However, corrupted files or wrong encoding will cause errors.

**Q: Can I load Excel files directly?**

A: Not currently. Export to CSV first from Excel:
1. File → Save As
2. Format: CSV UTF-8
3. Save

---

### Performance Questions

**Q: How many orders can I process?**

A: Tested up to 50,000 orders. Performance:
- 1,000 orders: ~2 seconds
- 10,000 orders: ~25 seconds
- 50,000 orders: ~2 minutes

Beyond 50,000, consider splitting into batches.

**Q: Why is my analysis slow?**

A: Several factors affect speed:
- Dataset size (more orders = longer time)
- Number of rules (complex rules slow down)
- Sets decoding (if enabled)
- System resources (RAM, CPU)

Tips to speed up:
- Disable unused rules
- Process in batches
- Close other applications
- Upgrade hardware if consistently slow

**Q: Can I cancel a running analysis?**

A: Yes, click the "Stop" button. Analysis will halt and you can try again with different settings.

---

### Rules & Configuration

**Q: How many rules can I create?**

A: No hard limit, but 50+ rules can slow analysis. Keep rules focused and disable unused ones.

**Q: Can rules modify stock levels?**

A: No, rules only affect tags, status, and priority. Stock levels are calculated based on orders and available stock.


**Q: What happens if multiple rules match?**

A: All matching rules apply. If rules conflict (e.g., both set priority), last rule wins.

---

### Integration Questions

**Q: How does integration with Packing Tool work?**

A: When you generate a packing list:
1. XLSX file created for humans
2. JSON file created automatically
3. Packing Tool reads JSON file
4. Data synced automatically

Both files contain identical data.

**Q: Can I integrate with other systems?**

A: JSON export can be used by any system. Documentation for JSON format available in technical docs.

**Q: Can I automate report generation?**

A: Not in GUI version. Command-line automation planned for future release. Currently requires manual steps.

---

### Error & Recovery

**Q: What if the application crashes?**

A: Sessions are auto-saved. When you restart:
1. Go to History tab
2. Find your session (check timestamp)
3. Load session
4. Continue where you left off

**Q: I deleted a session by accident. Can I recover?**

A: Sessions are soft-deleted (moved to trash). Contact admin to restore deleted sessions.

**Q: The analysis results look wrong. What should I do?**

A: Verification steps:
1. Check input files (are they correct?)
2. Check column mappings (mapped correctly?)
3. Check rules (any wrong conditions?)
4. Run analysis on small test dataset
5. Compare expected vs actual results
6. Contact support if still wrong

---

## 📚 Glossary

**Analysis Session**
: A single run of order analysis, including all data and results. Sessions are saved for future reference.

**Client**
: A business or warehouse you're processing orders for. Each client has separate configuration.

**Courier**
: Shipping company (DHL, PostOne, etc.). Used for filtering and routing.

**CSV (Comma-Separated Values)**
: Text file format for data. Rows represent records, columns separated by commas.

**Fulfillable**
: Order can be completed because all items are in stock.

**Not Fulfillable**
: Order cannot be completed because one or more items are out of stock.

**JSON (JavaScript Object Notation)**
: Machine-readable data format for system integration.

**Packing List**
: Report listing all items to pick and pack for orders. Given to warehouse staff.

**Priority**
: Importance level for order processing. High priority orders filled first.

**Rule Engine**
: System for automatically applying tags, status changes, etc. based on conditions.

**Session Lock**
: Prevents multiple users from editing the same session simultaneously.

**Sets / Bundles**
: Product packages containing multiple items. System expands to check component stock.

**SKU (Stock Keeping Unit)**
: Unique identifier for a product. Example: "PROD-001"

**Stock Simulation**
: Process of calculating what orders can be fulfilled with available stock.

**Tag**
: Label attached to order for categorization or identification.

**Vectorization**
: Technical optimization making analysis 10-50x faster on large datasets.

---

**Document Version:** 1.0
**Last Updated:** November 17, 2025
**For Version:** 1.8.0


---

