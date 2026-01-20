# Shopify Fulfillment Tool

![Version](https://img.shields.io/badge/version-1.9.2-blue)
![Status](https://img.shields.io/badge/status-stable-green)
![Tests](https://img.shields.io/badge/tests-60%2B%20passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![License](https://img.shields.io/badge/license-proprietary-red)

**Status:** ✅ Production Ready - Stable Release v1.9.2
**Version:** 1.9.2
**Architecture:** Server-Based Multi-Client System
**Last Updated:** 2026-01-17

---

## 🎉 What's New in v1.9.2

### Barcode Generator Integration (Feature #5)

**🏷️ Warehouse Barcode Labels**
- Generate Code-128 barcodes from analysis results
- 8 data fields: Sequential#, Items, Country, Tag, Order#, Courier, Date, Barcode
- 68mm × 38mm labels optimized for Citizen CL-E300 thermal printer
- PNG + PDF output formats with auto-open

**📋 Smart Organization**
- Filter by packing list configuration
- Per-packing-list subdirectories (DHL_Orders/, PostOne_Orders/)
- Sequential numbering consistent with Reference Labels
- Generation history with statistics

**⚠️ Breaking Change:** Destination_Country now populated for ALL couriers (previously DHL only)

### Tools Window (v1.9.1)

**📄 Reference Labels PDF Processor**
- Automated reference numbering for courier label PDFs
- 3-step matching: PostOne ID → Tracking → Name
- Automatic page sorting by reference number

---

*For detailed changes, see [CHANGELOG.md](CHANGELOG.md)*

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

### Core Functionality
- **Multi-Client Support**: Manage multiple clients with separate configurations
- **Session Management**: Server-based sessions with automatic state persistence
- **Order Analysis**: Intelligent fulfillment simulation with stock allocation
- **Rule Engine**: Flexible business rules for order processing and tagging
- **Sets Decoding**: Automatic expansion of product bundles into components
- **Manual Product Addition**: Add items on-the-fly with live recalculation

### Advanced Features
- **Repeated Orders Detection**: Automatic identification across sessions
- **Priority Management**: Multi-item orders prioritized for completion rate
- **Courier Mapping**: Flexible shipping method configuration
- **Stock Simulation**: Real-time stock availability checking
- **History Tracking**: Full audit trail of fulfillment operations
- **Undo/Redo System**: Session-based undo management

### Reports & Exports
- **Packing Lists**: Formatted Excel reports with multiple filter options
- **Stock Exports**: Multiple format support (.xlsx, .xls)
- **JSON Integration**: Seamless integration with Packing Tool
- **Analysis Reports**: Comprehensive fulfillment statistics
- **Custom Filters**: SKU exclusion, courier-specific reports

### Tools Window
- **Barcode Generator**: Generate Code-128 warehouse labels from analysis results
  - 68mm × 38mm labels for Citizen CL-E300 thermal printer
  - 8 data fields per label (sequential#, items, country, tag, etc.)
  - Filter by packing list configuration
  - PNG + PDF output with auto-open
  - Generation history and statistics

- **Reference Labels**: PDF processing for courier reference numbers
  - Automated reference numbering for PostOne labels
  - 3-step matching algorithm (ID → Tracking → Name)
  - Automatic page sorting by reference number

### User Interface
- **Modern Qt6 Interface**: Fast, responsive desktop application
- **Tabbed Workflow**: Session Setup, Analysis Results, History, Info
- **Smart Widgets**: Wheel-scroll-proof combo boxes for better UX
- **Real-time Updates**: Live statistics and progress tracking
- **Session Browser**: Easy navigation through historical sessions
- **Column Mapping**: Flexible CSV header adaptation

### Technical Excellence
- **Vectorized Operations**: High-performance pandas operations
- **Modular Architecture**: Clean separation of concerns
- **Comprehensive Logging**: Detailed debug information
- **Error Handling**: Specific exceptions with helpful messages
- **Type Hints**: Full type safety throughout codebase
- **Extensive Documentation**: Detailed docstrings on all functions

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

- **Python 3.9+** (required for type hints and modern features)
- **Windows 10/11** (primary platform, works on Windows Server)
- **Network Access** to file server: `\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\0UFulfilment\`

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

**Current Status:** ✅ 55/55 tests passing (100%)

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/test_core.py -v              # Core analysis
pytest tests/test_analysis.py -v          # Analysis engine
pytest tests/test_profile_manager.py -v   # Profile management
pytest tests/gui/ -v                      # GUI components

# Run with coverage
pytest tests/ --cov=shopify_tool --cov=gui --cov-report=html
```

### Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| Core Analysis | 17 | ~95% |
| Analysis Engine | 38 | ~90% |
| Profile Manager | 12 | ~85% |
| Session Manager | 15 | ~85% |
| GUI Components | 8 | ~70% |
| **Total** | **90+** | **~85%** |

### Testing Philosophy

- **Unit Tests**: Individual function testing
- **Integration Tests**: Module interaction testing
- **GUI Tests**: UI component testing with pytest-qt
- **Regression Tests**: Ensure refactoring doesn't break functionality

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

## ⚡ Performance

The tool is optimized for real-world warehouse operations:

### Benchmarks

| Dataset Size | Analysis Time | Memory Usage |
|--------------|---------------|--------------|
| 100 orders | <1 second | ~50 MB |
| 1,000 orders | <3 seconds | ~100 MB |
| 10,000 orders | <30 seconds | ~500 MB |

### Optimizations

- **Vectorized DataFrame Operations**: 10-50x faster than row iteration
- **Efficient Stock Simulation**: O(n) complexity for order processing
- **Smart Priority Sorting**: Multi-item orders processed first
- **Batch File Operations**: Reduced I/O overhead
- **Memory-Efficient**: Processes large datasets without memory issues

### Tested With

✅ Up to 10,000+ order lines
✅ Concurrent multi-user access
✅ Large CSV files (50+ MB)
✅ Complex rule sets (50+ rules)

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

**Issue: "File server not accessible"**
- Check network connectivity to `\\192.168.88.101`
- Verify you have read/write permissions
- Ensure VPN is connected if working remotely

**Issue: "CSV parsing error"**
- Check file encoding (should be UTF-8)
- Verify CSV has required columns (Order_Number, SKU, Quantity)
- Use automatic delimiter detection feature

**Issue: "Session already locked"**
- Another user may be working on the same session
- Check `.session.lock` file timestamp
- Wait or contact the other user

**Issue: Tests failing**
- Ensure all dependencies installed: `pip install -r requirements-dev.txt`
- Clear pytest cache: `pytest --cache-clear`
- Check Python version: `python --version` (should be 3.9+)

### Logging

Application logs are stored at:
- **Server:** `\\SERVER\SHARE\0UFulfilment\Logs\shopify_tool\`
- **Format:** `shopify_tool_YYYY-MM-DD.log`

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

For more help, check logs or contact support.

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

### Development Workflow

1. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**
   - Follow PEP 8 style guidelines
   - Add type hints to all functions
   - Write comprehensive docstrings (Google style)
   - Add unit tests for new functionality

3. **Run tests**
   ```bash
   pytest tests/ -v
   ruff check shopify_tool/ gui/
   ```

4. **Commit changes**
   ```bash
   git commit -m "feat: add your feature description"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Quality Standards

✅ **Type Hints**: All functions must have type hints
✅ **Docstrings**: Google-style docstrings required
✅ **Tests**: Maintain >85% test coverage
✅ **Linting**: Pass ruff checks
✅ **No Regressions**: All existing tests must pass

### Commit Message Format

Use conventional commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `refactor:` - Code refactoring
- `docs:` - Documentation updates
- `test:` - Test additions/updates
- `chore:` - Maintenance tasks

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

## 📊 Project Statistics

- **Lines of Code**: ~14,000+
- **Modules**: 30
- **Functions**: 350+
- **Classes**: 35+
- **Test Files**: 25
- **Documentation Files**: 10
- **Test Coverage**: ~85%

---

## 📝 Version History

**Current Version:** 1.8.0 (Stable)

Major releases:
- **v1.8.0** (2025-11-17): Performance & refactoring release
- **v1.7.1** (2025-11-10): Post-migration stable release
- **v1.7.0** (2025-11-04): Phase 1 unified server architecture
- **v1.6.x**: Legacy local storage architecture

For detailed changes, see [CHANGELOG.md](CHANGELOG.md)

---

## 📞 Support

For issues, questions, or feature requests:
- **Issues**: [GitHub Issues](https://github.com/cognitiveclodfr/shopify-fulfillment-tool/issues)
- **Documentation**: See `docs/` directory
- **Logs**: Check `Logs/shopify_tool/` on file server

---

## 📄 License

This project is proprietary software developed for internal warehouse operations.

---

**Built with ❤️ for efficient warehouse fulfillment operations**

**Last Updated:** 2025-11-17
**Version:** 1.8.0-stable
**Status:** Production Ready ✅
