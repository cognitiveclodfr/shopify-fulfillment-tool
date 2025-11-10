# Shopify Fulfillment Tool

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6-green.svg)](https://www.qt.io/qt-for-python)
[![Architecture](https://img.shields.io/badge/architecture-server--based-orange.svg)](docs/ARCHITECTURE.md)

**Version:** 1.7
**Status:** Production Ready
**Architecture:** Server-Based Multi-Client System
**Last Updated:** 2025-11-10

---

## 📋 Overview

The Shopify Fulfillment Tool is a professional desktop application designed for **small to medium-sized businesses** running Shopify e-commerce operations. It streamlines warehouse order fulfillment through intelligent analysis, automation, and seamless integration with warehouse execution systems.

### What Makes This Tool Special?

✅ **Server-Based Architecture** - Multi-PC warehouse operations with centralized data
✅ **Multi-Client Support** - Manage multiple clients/brands from a single installation
✅ **Smart Prioritization** - Multi-item orders processed first to maximize complete shipments
✅ **Packing Tool Integration** - JSON exports ready for warehouse packing stations
✅ **Production Proven** - Used daily in warehouse operations with 99%+ reliability

### Target Users
- Warehouse managers and logistics coordinators
- Small/medium e-commerce fulfillment centers
- Multi-brand warehouse operations
- Shopify merchants with in-house fulfillment

---

## ✨ Key Features

### 📊 Intelligent Analysis Engine
- **Smart Prioritization**: Multi-item orders processed first to maximize complete shipments
- **Stock Simulation**: Calculate final stock levels before committing changes
- **History Tracking**: Automatic detection of repeat orders
- **Low Stock Alerts**: Configurable thresholds for inventory warnings
- **Exclude SKUs**: Filter out virtual items (shipping protection, gift cards, etc.)

### 🏢 Multi-Client Support
- **ProfileManager**: Manage multiple client configurations on centralized server
- **Client Switching**: Seamlessly switch between clients without restart
- **Isolated Sessions**: Each client has separate session history and statistics
- **Flexible Configuration**: Per-client automation rules, packing lists, and stock exports

### 📦 Session Management
- **Server-Based Sessions**: All data stored on network file server for multi-PC access
- **Dated Sessions**: Unique folders with format `YYYY-MM-DD_N`
- **Structured Storage**: Organized directories for inputs, analysis, reports, and exports
- **Session History**: Full audit trail of all fulfillment operations

### ⚙️ Powerful Automation
- **Rule Engine**: Create custom rules with conditions and actions
  - Match conditions: equals, contains, greater than, less than, regex, etc.
  - Actions: add tags, set priority, change status
  - Combine with ALL (AND) or ANY (OR) logic
- **Batch Operations**: Process multiple orders simultaneously
- **Configurable Filters**: Save reusable filters for packing lists and stock exports

### 📋 Report Generation
- **Packing Lists**:
  - Filtered by carrier, order type, or custom criteria
  - Professional formatting with order grouping
  - Print-ready A4 landscape layout
  - SKU exclusion support (e.g., "Shipping protection", "07")
  - Both XLSX and JSON formats for Packing Tool integration
- **Stock Exports**:
  - Aggregated by SKU
  - Compatible with courier systems
  - Multiple format support (.xls, .xlsx)
  - Cyrillic text support

### 🔗 Integration
- **Packing Tool Integration**: JSON exports with session metadata for warehouse execution
- **Unified Statistics**: Shared statistics across Shopify Tool and Packing Tool
- **Session Handoff**: Seamless workflow from analysis to packing

---

## 🏗️ Architecture

### Server-Based File Structure

The application uses a **centralized file server** for all data storage, enabling multi-PC warehouse operations:

```
\\Server\Share\0UFulfilment\
├── Clients/                          # Client-specific configurations
│   ├── CLIENT_M/
│   │   ├── client_config.json        # General client settings
│   │   ├── shopify_config.json       # Shopify-specific config (rules, packing lists, etc.)
│   │   ├── fulfillment_history.csv   # Historical fulfillment data
│   │   └── backups/                  # Automatic config backups (last 10)
│   └── CLIENT_{ID}/
│       └── ...
│
├── Sessions/                         # Session-based work folders
│   ├── CLIENT_M/
│   │   ├── 2025-11-05_1/            # Dated session folder
│   │   │   ├── session_info.json    # Session metadata
│   │   │   ├── input/               # Orders & stock CSV files
│   │   │   ├── analysis/            # Analysis results (XLSX + JSON)
│   │   │   ├── packing_lists/       # Generated packing lists (XLSX + JSON)
│   │   │   └── stock_exports/       # Stock writeoff exports (XLS)
│   │   └── 2025-11-05_2/
│   │       └── ...
│   └── CLIENT_{ID}/
│       └── ...
│
├── Stats/                            # Unified statistics
│   └── global_stats.json             # Cross-tool statistics database
│
└── Logs/                             # Centralized logging
    └── shopify_tool/                 # Application logs
```

### Core Components

- **ProfileManager** (`shopify_tool/profile_manager.py`): Manages client configurations with caching, file locking, and automatic backups
- **SessionManager** (`shopify_tool/session_manager.py`): Creates and manages work sessions on the file server
- **StatsManager** (`shared/stats_manager.py`): Unified statistics tracking for both Shopify and Packing tools
- **Analysis Engine** (`shopify_tool/analysis.py`): Core fulfillment simulation logic
- **Rule Engine** (`shopify_tool/rules.py`): Configurable automation rules

For detailed architecture information, see [ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 🚀 Installation

### Prerequisites

- **Python 3.8 or higher** (tested with Python 3.11)
- **Windows, macOS, or Linux**
- **Network access** to file server (for production) OR local dev environment setup

### Production Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/cognitiveclodfr/shopify-fulfillment-tool.git
   cd shopify-fulfillment-tool
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure server access**
   - The application will automatically connect to the production file server
   - Default path: `\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment`
   - Ensure network connectivity and proper permissions

5. **Run the application**
   ```bash
   python gui_main.py
   ```

### Development Environment Setup

For local development **without** access to the production server:

1. **Run the automated setup script**
   ```bash
   python scripts/setup_dev_env.py
   ```
   This will:
   - Create local mock server structure
   - Generate test client profiles (CLIENT_M, CLIENT_TEST)
   - Create comprehensive test data
   - Set up logging directories

2. **Set the environment variable**

   **Windows (CMD):**
   ```cmd
   set FULFILLMENT_SERVER_PATH=D:\Dev\fulfillment-server-mock
   python gui_main.py
   ```

   **Windows (PowerShell):**
   ```powershell
   $env:FULFILLMENT_SERVER_PATH='D:\Dev\fulfillment-server-mock'
   python gui_main.py
   ```

   **Linux/macOS:**
   ```bash
   export FULFILLMENT_SERVER_PATH=~/Dev/fulfillment-server-mock
   python gui_main.py
   ```

3. **Or use the convenience script** (Windows):
   ```cmd
   START_DEV.bat
   ```

The application **automatically detects** the environment:
- If `FULFILLMENT_SERVER_PATH` is set → Uses local dev directory
- If not set → Uses production network server

**No code changes needed!** See [README_DEV.md](README_DEV.md) for detailed dev setup instructions.

---

## 📖 Usage Workflow

### Basic Workflow (5 Steps)

#### 1. Select Client
- Launch the application
- Choose a client from the dropdown (e.g., "CLIENT_M")
- Client configuration loads automatically

#### 2. Create Session
- Click **"Create New Session"**
- A timestamped folder is created on the server: `Sessions/CLIENT_M/2025-11-10_1/`
- Session structure is automatically set up (input/, analysis/, packing_lists/, stock_exports/)

#### 3. Load Data Files
- **Load Orders File**: Select your Shopify orders export CSV
- **Load Stock File**: Select your current inventory CSV
- Files are validated and copied to the session's `input/` directory

#### 4. Run Analysis
- Click **"Run Analysis"**
- The tool will:
  - Clean and standardize data
  - Prioritize multi-item orders for complete fulfillment
  - Simulate stock allocation
  - Apply automation rules from your configuration
  - Calculate comprehensive statistics
  - Detect repeat customers
- Results appear in the data table with color coding:
  - 🟢 **Green**: Fulfillable orders
  - 🔴 **Red**: Not fulfillable (out of stock)
  - 🟡 **Yellow**: Repeat customer orders

#### 5. Generate Reports
- **Packing Lists**: Click "Create Packing List" and select from pre-configured lists
  - Filtered by courier (DHL, DPD, PostOne, Speedy, etc.)
  - Excludes virtual SKUs (e.g., "07", "Shipping protection")
  - Generates both XLSX (for printing) and JSON (for Packing Tool)
- **Stock Exports**: Click "Create Stock Export" for courier system integration
  - Aggregated quantities by SKU
  - XLS format for compatibility

### Advanced Features

#### Client Settings
Click **"Client Settings"** to configure:
- **Settings Tab**: General preferences, stock alert thresholds
- **Rules Tab**: Automation rules (conditions → actions)
- **Packing Lists Tab**: Configure filtered packing lists per courier/criteria
- **Stock Exports Tab**: Configure stock export formats
- **Mappings Tab**: CSV column mappings for different data sources

#### Interactive Data Table
- **Filtering**: Search/filter by any column (supports regex)
- **Sorting**: Click column headers to sort
- **Context Menu**: Right-click for quick actions
- **Manual Toggle**: Double-click to manually change order fulfillment status
- **Color Indicators**: Instant visual status

#### Statistics Panel
View real-time statistics:
- Total orders completed / not completed
- Total items to write off
- Per-courier breakdown
- Repeat order counts
- Low stock alerts

---

## ⚙️ Configuration

### Configuration Files

**All configurations are stored on the file server:**
- **Client Config**: `Clients/CLIENT_{ID}/client_config.json`
- **Shopify Config**: `Clients/CLIENT_{ID}/shopify_config.json`

**Old local configs** (`%APPDATA%/ShopifyFulfillmentTool/`) are **obsolete** after Phase 1 migration.

### Required CSV Columns

#### Orders File (`orders_export.csv`):
```
Name                - Order number
Lineitem sku        - Product SKU
Lineitem quantity   - Quantity ordered
Shipping Method     - Shipping method
Shipping Country    - Destination country
Tags                - Order tags
Notes               - Order notes
Total               - Order total (optional)
```

#### Stock File (`inventory.csv`):
```
Артикул            - Product SKU
Име                - Product name
Наличност          - Available quantity
```

**Note:** Cyrillic column headers are supported. Column mappings can be customized in Client Settings → Mappings tab.

### Exclude SKUs

Configure SKUs to exclude from packing lists (e.g., virtual items):
- `07` - Sample virtual SKU
- `Shipping protection` - Insurance add-on
- `Gift wrapping` - Service items

Set these in Client Settings → Packing Lists → Exclude SKUs field.

---

## 🧪 Testing

### Test Suite

The project includes comprehensive test coverage with **21 test files**:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_analysis.py

# Run with coverage report
pytest --cov=shopify_tool --cov=gui --cov-report=html
```

### Test Data Generation

Create comprehensive test data for development/testing:

```bash
# Generate complete test dataset (12 orders, 24 line items)
python scripts/create_comprehensive_test_data.py

# Generate simple test dataset
python scripts/create_test_data.py
```

Test data includes:
- Single and multi-item orders
- Multiple couriers (DHL, DPD, PostOne, Speedy)
- Stock competition scenarios
- Repeat customer detection
- Low stock situations
- International orders

See [docs/TEST_SCENARIOS.md](docs/TEST_SCENARIOS.md) for detailed test scenario documentation.

### Manual Testing Checklist

For manual verification after changes, use the comprehensive checklist:
- [docs/TESTING_CHECKLIST.md](docs/TESTING_CHECKLIST.md)

### Test Results

**Current Status:** ✅ 99%+ Pass Rate
- All core functionality tests passing
- Integration tests verified
- Multi-client scenarios validated
- Performance tests with 500+ order datasets

---

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

| Document | Description |
|----------|-------------|
| **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** | System design, server architecture, data flow, and design patterns |
| **[API.md](docs/API.md)** | Complete API reference for all classes and methods |
| **[FUNCTIONS.md](docs/FUNCTIONS.md)** | Detailed function catalog with examples |
| **[INTEGRATION.md](docs/INTEGRATION.md)** | Integration guide for Packing Tool and file server workflows |
| **[MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md)** | Phase 1 migration from local to server-based architecture |
| **[MIGRATION_CHECKLIST.md](docs/MIGRATION_CHECKLIST.md)** | Step-by-step migration verification checklist |
| **[TEST_SCENARIOS.md](docs/TEST_SCENARIOS.md)** | Comprehensive test data scenarios and expected results |
| **[TESTING_CHECKLIST.md](docs/TESTING_CHECKLIST.md)** | Manual testing procedures and validation steps |

---

## 🔗 Integration with Packing Tool

The Shopify Fulfillment Tool integrates seamlessly with the **Packing Tool** (warehouse execution system) through the shared file server:

### Workflow

```
┌────────────────────┐
│  Shopify Tool      │
│  1. Analyze orders │───┐
│  2. Generate lists │   │
└────────────────────┘   │
                         │ Session on
                         │ File Server
┌────────────────────┐   │
│  Packing Tool      │   │
│  1. Load session   │◄──┘
│  2. Pack orders    │
│  3. Track stats    │
└────────────────────┘
```

### Integration Features

- **JSON Exports**: Packing lists exported in JSON format for Packing Tool consumption
- **Session Metadata**: `session_info.json` tracks analysis status and available reports
- **Unified Statistics**: Both tools write to `Stats/global_stats.json`
- **Session Locking**: File locking prevents concurrent access conflicts

### JSON Format Example

```json
{
  "session_id": "2025-11-10_1",
  "created_at": "2025-11-10T10:30:00.123456",
  "total_orders": 150,
  "total_items": 450,
  "orders": [
    {
      "order_number": "12345",
      "order_type": "Multi",
      "items": [
        {
          "sku": "SKU-001",
          "product_name": "Product A",
          "quantity": 2
        }
      ],
      "courier": "DHL",
      "destination": "Bulgaria",
      "tags": ["Priority"]
    }
  ]
}
```

See [docs/INTEGRATION.md](docs/INTEGRATION.md) for detailed integration documentation.

---

## 🛠️ Technology Stack

### Core Technologies
- **Python 3.8+** - Programming language
- **PySide6 (Qt 6)** - Cross-platform GUI framework
- **pandas 2.3+** - Data manipulation and analysis
- **numpy 2.3+** - Numerical computations

### Data Processing
- **openpyxl 3.1+** - Modern Excel (.xlsx) file handling
- **xlsxwriter 3.2+** - Excel file creation with formatting
- **xlwt/xlrd/xlutils** - Legacy Excel (.xls) support

### Development Tools
- **pytest** - Testing framework
- **pytest-qt** - Qt testing utilities
- **pytest-mock** - Mocking support

---

## 🔧 Troubleshooting

### Common Issues

#### "ProfileManager failed to initialize"
**Cause:** Cannot connect to file server or `FULFILLMENT_SERVER_PATH` not set correctly

**Solution:**
- **Production:** Check network connectivity to `\\192.168.88.101\...`
- **Development:** Verify environment variable is set:
  ```bash
  # Windows
  echo %FULFILLMENT_SERVER_PATH%

  # Linux/macOS
  echo $FULFILLMENT_SERVER_PATH
  ```

#### "No clients found"
**Cause:** Client directories don't exist on server

**Solution:**
- **Development:** Run `python scripts/setup_dev_env.py`
- **Production:** Ensure `Clients/` directory exists with at least one `CLIENT_{ID}/` subdirectory

#### "Session creation failed"
**Cause:** Insufficient permissions or path issues

**Solution:**
- Check write permissions on file server
- Verify `Sessions/CLIENT_{ID}/` directory exists
- Check disk space on server

#### "Analysis fails with encoding error"
**Cause:** CSV file has incorrect encoding

**Solution:**
- Ensure CSV files are UTF-8 encoded
- Check for Cyrillic characters in product names
- Use Excel "Save As" → CSV UTF-8

#### "Packing list is empty"
**Cause:** Filters too restrictive or no fulfillable orders

**Solution:**
- Review filter conditions in Client Settings
- Check that analysis found fulfillable orders
- Verify courier names match exactly (case-sensitive)

### Debug Mode

Enable detailed logging:
1. Check logs at: `Logs/shopify_tool/` on file server
2. Look for recent log files with timestamps
3. Review error messages and stack traces

### Network Issues

If experiencing network timeouts:
- ProfileManager uses 60-second cache to minimize network calls
- File locking has automatic retry logic
- Check network stability and latency to file server

---

## 📊 Project Status

### Current Phase: Phase 1 Complete ✅

**Phase 1 - Unified Development (Server-Based Architecture)**
- ✅ ProfileManager: Multi-client support on file server
- ✅ SessionManager: Server-based session management
- ✅ StatsManager: Unified statistics tracking
- ✅ Integration: JSON exports for Packing Tool
- ✅ Testing: 99%+ pass rate with comprehensive test suite
- ✅ Documentation: Complete docs for architecture and integration

### Test Results Summary

| Category | Tests | Status |
|----------|-------|--------|
| Core Analysis | 85+ | ✅ Passing |
| File Operations | 30+ | ✅ Passing |
| Configuration | 25+ | ✅ Passing |
| Integration | 15+ | ✅ Passing |
| GUI Components | 20+ | ✅ Passing |

### Roadmap

**Phase 2 - Advanced Features** (Planned)
- Enhanced filtering and saved filter presets
- Advanced reporting templates
- Performance optimizations for large datasets
- Additional courier integrations

**Phase 3 - Analytics** (Planned)
- Fulfillment trend analysis
- Inventory forecasting
- Worker performance metrics
- Dashboard visualizations

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add AmazingFeature'`)
6. Push to the branch (`git push origin feature/AmazingFeature`)
7. Open a Pull Request

### Code Style
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write docstrings for all public functions/classes
- Ensure all tests pass before submitting PR

---

## 📄 License

This project is proprietary software developed for internal warehouse operations.

---

## 👥 Authors & Acknowledgments

**Development Team**
- Initial architecture and implementation
- Phase 1 migration to server-based system
- Integration with Packing Tool

**Built With**
- [PySide6](https://www.qt.io/qt-for-python) - Qt for Python GUI framework
- [pandas](https://pandas.pydata.org/) - Data analysis library
- [openpyxl](https://openpyxl.readthedocs.io/) - Excel file handling
- [pytest](https://pytest.org/) - Testing framework

---

## 📞 Support

For issues, questions, or feature requests:
- **GitHub Issues**: [cognitiveclodfr/shopify-fulfillment-tool/issues](https://github.com/cognitiveclodfr/shopify-fulfillment-tool/issues)
- **Documentation**: See `docs/` directory for detailed technical documentation

---

## 📈 Project Statistics

- **Lines of Code**: ~6,500+
- **Modules**: 23
- **Functions**: 90+
- **Classes**: 15+
- **Test Files**: 21
- **Documentation Files**: 8
- **Test Coverage**: 99%+

---

**Version**: 1.7
**Architecture**: Server-Based Multi-Client
**Status**: Production Ready ✅
**Last Updated**: 2025-11-10

For detailed technical documentation, see the [`docs/`](docs/) directory.
