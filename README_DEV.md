# Development Environment Setup

This guide explains how to set up a local development environment for the Shopify Fulfillment Tool without access to the production file server.

## Quick Start (Windows)

1. Run the setup script:
   ```cmd
   python scripts/setup_dev_env.py
   ```

2. Start development mode:
   ```cmd
   START_DEV.bat
   ```

That's it! The script will automatically:
- Create local mock server structure
- Generate test data files
- Set environment variable
- Launch the application

## Manual Setup

### Step 1: Create Dev Structure

```cmd
python scripts/setup_dev_env.py D:\Dev\fulfillment-server-mock
```

This creates a local directory structure that mimics the production server.

### Step 2: Create Test Data

```cmd
python scripts/create_test_data.py
```

This generates sample CSV files for testing.

### Step 3: Set Environment Variable

**Windows CMD:**
```cmd
set FULFILLMENT_SERVER_PATH=D:\Dev\fulfillment-server-mock
```

**PowerShell:**
```powershell
$env:FULFILLMENT_SERVER_PATH='D:\Dev\fulfillment-server-mock'
```

**Permanent (Windows):**
1. Right-click "This PC" → Properties → Advanced System Settings
2. Environment Variables → User Variables → New
3. Variable name: `FULFILLMENT_SERVER_PATH`
4. Variable value: `D:\Dev\fulfillment-server-mock`

**Linux/Mac:**
```bash
export FULFILLMENT_SERVER_PATH=~/Dev/fulfillment-server-mock
# Add to ~/.bashrc or ~/.zshrc for permanent
```

### Step 4: Test Setup

```cmd
python scripts/test_dev_env.py
```

### Step 5: Run Application

```cmd
python gui_main.py
```

## How It Works

The application automatically detects the environment:

1. **Development Mode:** If `FULFILLMENT_SERVER_PATH` is set, uses local directory
2. **Production Mode:** If not set, uses network server `\\192.168.88.101\...`

No code changes needed - it just works!

## Directory Structure

```
D:\Dev\fulfillment-server-mock\
├── Clients/
│   ├── CLIENT_M/
│   │   ├── client_config.json
│   │   ├── shopify_config.json
│   │   └── fulfillment_history.csv
│   └── CLIENT_TEST/
├── Sessions/
│   ├── CLIENT_M/
│   └── CLIENT_TEST/
├── Stats/
│   └── global_stats.json
└── Logs/
    └── shopify_tool/
```

## Test Data

Test files are created in `data/test_input/`:
- `test_orders.csv` - Sample orders (10 line items, 6 orders)
- `test_stock.csv` - Sample stock (8 SKUs)

You can modify these files or create your own test data.

## Troubleshooting

### "ProfileManager failed to initialize"
- Check that `FULFILLMENT_SERVER_PATH` is set correctly
- Run: `echo %FULFILLMENT_SERVER_PATH%` (Windows) or `echo $FULFILLMENT_SERVER_PATH` (Linux/Mac)

### "No clients found"
- Run setup script: `python scripts/setup_dev_env.py`
- Check that `Clients/` directory exists in your dev path

### "Test data not found"
- Run: `python scripts/create_test_data.py`

### Environment variable not persisting
- You need to set it permanently (see Step 3 above)
- Or use `START_DEV.bat` which sets it automatically

## Switching Between Dev and Production

**Development mode:**
```cmd
set FULFILLMENT_SERVER_PATH=D:\Dev\fulfillment-server-mock
python gui_main.py
```

**Production mode:**
```cmd
set FULFILLMENT_SERVER_PATH=
python gui_main.py
```

Or simply run from different computers (work PC = production, home PC = dev).

## Tips

- Keep test data in `data/test_input/` (gitignored)
- Commit dev scripts to help other developers
- Document any custom test scenarios
- Use separate clients (CLIENT_M, CLIENT_TEST) for different tests

## Next Steps

After setup:
1. Create a session
2. Load test CSV files
3. Run analysis
4. Test report generation
5. Verify everything works as expected

Happy coding! 🚀
