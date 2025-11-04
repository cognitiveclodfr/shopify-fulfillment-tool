# Shopify Fulfillment Tool

A professional desktop application for streamlining Shopify order fulfillment operations. Built with Python and PySide6, this tool helps warehouse managers and logistics personnel efficiently process orders, manage inventory, and generate reports.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6-green.svg)](https://www.qt.io/qt-for-python)

## 🎯 What Does It Do?

The Shopify Fulfillment Tool automates the complex process of order fulfillment by:

1. **Analyzing** orders against available stock
2. **Prioritizing** multi-item orders to maximize complete shipments
3. **Simulating** stock allocation before actual fulfillment
4. **Applying** custom automation rules for tagging and prioritization
5. **Generating** professional packing lists and stock exports
6. **Tracking** fulfillment history to identify repeat customers

## ✨ Key Features

### 📊 Intelligent Analysis Engine
- **Smart Prioritization**: Multi-item orders processed first to maximize complete shipments
- **Stock Simulation**: Calculate final stock levels before committing changes
- **History Tracking**: Automatic detection of repeat orders
- **Low Stock Alerts**: Configurable thresholds for inventory warnings

### 🎨 Interactive User Interface
- **Color-Coded Status**:
  - 🟢 Green: Fulfillable orders
  - 🔴 Red: Not fulfillable orders
  - 🟡 Yellow: Repeat customer orders
- **Advanced Filtering**: Search by any column with regex support
- **Context Menu Actions**: Quick access to common operations
- **Real-Time Updates**: Instant UI refresh after data changes

### ⚙️ Powerful Automation
- **Rule Engine**: Create custom rules with conditions and actions
  - Match conditions: equals, contains, greater than, etc.
  - Actions: add tags, set priority, change status
  - Combine with ALL (AND) or ANY (OR) logic
- **Profile System**: Multiple configuration profiles for different workflows
- **Batch Operations**: Process multiple orders simultaneously

### 📋 Report Generation
- **Packing Lists**:
  - Filtered by carrier, order type, or custom criteria
  - Professional formatting with order grouping
  - Print-ready A4 landscape layout
  - SKU exclusion support
- **Stock Exports**:
  - Aggregated by SKU
  - Compatible with courier systems
  - Multiple format support (.xls, .xlsx)
- **Custom Reports**: Build ad-hoc reports with selected columns and filters

### 💾 Session Management
- **Dated Sessions**: Unique folders for each work session
- **Auto-Save**: Session data preserved between application runs
- **History Persistence**: Fulfillment history stored securely

## 📸 Screenshots

### Main Window
The main interface showing order analysis with color-coded statuses, filtering options, and statistics.

### Settings & Rules
Configure automation rules, packing list templates, and stock export formats.

## 🚀 Quick Start

### Prerequisites
- **Python 3.9 or higher**
- **Windows, macOS, or Linux**

### Installation

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

4. **Run the application**
   ```bash
   python gui_main.py
   ```

## 📖 Usage Workflow

### 1. Create a Session
Click **"Create New Session"** to generate a dated folder for your outputs.

### 2. Load Data Files
- **Load Orders File**: Select your Shopify orders export CSV
- **Load Stock File**: Select your current inventory CSV
- Both files are validated before loading

### 3. Run Analysis
Click **"Run Analysis"** to process orders. The tool will:
- Clean and standardize data
- Prioritize multi-item orders
- Simulate stock allocation
- Apply automation rules
- Calculate statistics

### 4. Review Results
- Browse the **Analysis Data** tab with color-coded rows
- Filter and sort by any column
- Double-click to toggle order status
- Right-click for context menu options

### 5. Generate Reports
- **Packing Lists**: Select pre-configured lists or use Report Builder
- **Stock Exports**: Generate courier-specific stock files
- **Custom Reports**: Create one-off reports with custom columns

### 6. Statistics
View comprehensive statistics including:
- Total orders completed/not completed
- Items to write off
- Per-courier breakdown
- Repeat order counts

## 🔧 Configuration

### Configuration File Location
- **Windows**: `%APPDATA%/ShopifyFulfillmentTool/config.json`
- **Linux/macOS**: `~/.local/share/ShopifyFulfillmentTool/config.json`

### Profile System
Create multiple profiles for different warehouses or workflows:
- Click **"Manage..."** next to the profile selector
- Add, rename, or delete profiles
- Each profile has independent settings

### Required CSV Columns

**Orders File (orders_export.csv)**:
- `Name` - Order number
- `Lineitem sku` - Product SKU
- `Lineitem quantity` - Quantity ordered
- `Shipping Method` - Shipping method
- `Shipping Country` - Destination country
- `Tags` - Order tags
- `Notes` - Order notes
- `Total` - Order total (optional)

**Stock File (inventory.csv)**:
- `Артикул` - Product SKU
- `Име` - Product name
- `Наличност` - Available quantity

## 🏗️ Project Structure

```
shopify-fulfillment-tool/
├── shopify_tool/           # Backend business logic
│   ├── core.py            # Main orchestration
│   ├── analysis.py        # Fulfillment simulation
│   ├── rules.py           # Rule engine
│   ├── packing_lists.py   # Packing list generation
│   ├── stock_export.py    # Stock export generation
│   ├── utils.py           # Utility functions
│   └── logger_config.py   # Logging setup
│
├── gui/                    # Frontend UI components
│   ├── main_window_pyside.py       # Main window
│   ├── settings_window_pyside.py   # Settings dialog
│   ├── actions_handler.py          # Action handlers
│   ├── ui_manager.py               # UI management
│   ├── file_handler.py             # File operations
│   └── ...                         # Other UI components
│
├── tests/                  # Test suite
├── data/                   # Templates and data
│   ├── templates/          # Excel templates
│   ├── input/             # Sample input files
│   └── output/            # Generated reports
│
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md    # System architecture
│   ├── API.md            # API reference
│   └── FUNCTIONS.md      # Function catalog
│
├── gui_main.py            # Application entry point
├── config.json            # Default configuration
└── requirements.txt       # Dependencies
```

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design, data flow, and architecture patterns
- **[API.md](docs/API.md)** - Complete API reference for all classes and methods
- **[FUNCTIONS.md](docs/FUNCTIONS.md)** - Detailed function catalog with examples

## 🔨 Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run tests with coverage
pytest --cov=shopify_tool --cov=gui

```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_analysis.py

# Run tests in verbose mode
pytest -v

# Run tests with output
pytest -s
```

### Building Executable

```bash
# Build standalone executable with PyInstaller
pyinstaller --onefile --windowed \
  --add-data "config.json;." \
  --add-data "data/templates;data/templates" \
  --name "ShopifyFulfillmentTool" \
  gui_main.py
```

The executable will be created in `dist/ShopifyFulfillmentTool.exe`.

## 🧪 Testing

The project includes comprehensive test coverage:

- **Unit Tests**: Individual function testing
- **Integration Tests**: Module interaction testing
- **GUI Tests**: UI component testing with pytest-qt
- **Mock Tests**: External dependency mocking

Test files mirror the source structure in the `tests/` directory.

## 🛠️ Technology Stack

### Core Technologies
- **Python 3.9+** - Programming language
- **PySide6** - Qt 6 bindings for GUI
- **pandas** - Data manipulation and analysis
- **numpy** - Numerical computations

### Data Processing
- **openpyxl** - Modern Excel (.xlsx) file handling
- **xlsxwriter** - Excel file creation with formatting
- **xlwt/xlrd** - Legacy Excel (.xls) support

### Development Tools
- **pytest** - Testing framework
- **pytest-qt** - Qt testing utilities
- **pytest-mock** - Mocking support
- **PyInstaller** - Executable packaging

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Code Style
- Follow PEP 8 guidelines
- Use Google-style docstrings
- Ensure all tests pass


## 🐛 Bug Reports & Feature Requests

Please use the [GitHub Issues](https://github.com/cognitiveclodfr/shopify-fulfillment-tool/issues) page to report bugs or request features.

## 👥 Authors

- **Development Team** - *Initial work*

## 🙏 Acknowledgments

- Built with [PySide6](https://www.qt.io/qt-for-python) for cross-platform GUI
- Data processing powered by [pandas](https://pandas.pydata.org/)
- Excel generation using [openpyxl](https://openpyxl.readthedocs.io/) and [xlsxwriter](https://xlsxwriter.readthedocs.io/)

## 📊 Project Statistics

- **Lines of Code**: ~5,640
- **Modules**: 21
- **Functions**: 80+
- **Classes**: 13
- **Test Coverage**: Comprehensive

---

**Version**: 1.0
**Last Updated**: 2025-11-04
**Status**: Production Ready

For detailed technical documentation, see the `docs/` directory.
