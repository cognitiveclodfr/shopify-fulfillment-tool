"""Test that development environment is properly configured.

This script verifies:
1. Environment variable is set
2. Directory structure exists (including backups/)
3. ProfileManager can initialize
4. Client configs can be loaded
5. Shopify config is V2 format with all required fields
6. Client config has ui_settings with table_view
7. Test data files exist
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_dev_environment():
    """Run all dev environment tests."""

    print("=" * 60)
    print("TESTING DEVELOPMENT ENVIRONMENT")
    print("=" * 60)
    print()

    all_passed = True

    # ========================================
    # TEST 1: Environment Variable
    # ========================================
    print("Test 1: Environment variable...")
    server_path = os.environ.get('FULFILLMENT_SERVER_PATH')

    if not server_path:
        print("  FAIL: FULFILLMENT_SERVER_PATH environment variable is not set!")
        print()
        print("  Set it with:")
        print("    Windows: set FULFILLMENT_SERVER_PATH=D:\\Dev\\fulfillment-server-mock")
        print("    Linux:   export FULFILLMENT_SERVER_PATH=/home/user/Dev/fulfillment-server-mock")
        print()
        all_passed = False
    else:
        print(f"  OK: FULFILLMENT_SERVER_PATH = {server_path}")

    print()

    if not server_path:
        return False

    # ========================================
    # TEST 2: Directory Structure
    # ========================================
    print("Test 2: Directory structure...")

    base = Path(server_path)
    required_dirs = [
        "Clients",
        "Sessions",
        "Stats",
        "Logs"
    ]

    all_dirs_exist = True
    for dir_name in required_dirs:
        dir_path = base / dir_name
        if dir_path.exists():
            print(f"  OK: {dir_name}/")
        else:
            print(f"  FAIL: {dir_name}/ (missing)")
            all_dirs_exist = False

    # Check backups directories
    for client_dir in (base / "Clients").iterdir() if (base / "Clients").exists() else []:
        if client_dir.is_dir() and client_dir.name.startswith("CLIENT_"):
            backups = client_dir / "backups"
            if backups.exists():
                print(f"  OK: {client_dir.name}/backups/")
            else:
                print(f"  WARN: {client_dir.name}/backups/ (missing)")

    if not all_dirs_exist:
        print()
        print("  Run setup script to create structure:")
        print("    python scripts/setup_dev_env.py")
        all_passed = False

    print()

    # ========================================
    # TEST 3: ProfileManager
    # ========================================
    print("Test 3: ProfileManager initialization...")

    try:
        from shopify_tool.profile_manager import ProfileManager

        pm = ProfileManager()
        print(f"  OK: ProfileManager initialized")
        print(f"    Base path: {pm.base_path}")
        print(f"    Dev mode: {pm._is_dev_environment()}")

    except Exception as e:
        print(f"  FAIL: ProfileManager initialization failed: {e}")
        all_passed = False
        print()
        return False

    print()

    # ========================================
    # TEST 4: List Clients
    # ========================================
    print("Test 4: Client listing...")

    clients = []
    try:
        clients = pm.list_clients()

        if clients:
            print(f"  OK: Found {len(clients)} client(s): {', '.join(clients)}")
        else:
            print(f"  WARN: No clients found (expected CLIENT_M, CLIENT_TEST)")
            print(f"    Run setup script to create default clients:")
            print(f"      python scripts/setup_dev_env.py")
            all_passed = False

    except Exception as e:
        print(f"  FAIL: Failed to list clients: {e}")
        all_passed = False

    print()

    # ========================================
    # TEST 5: Load Client Config + ui_settings
    # ========================================
    if clients:
        print("Test 5: Loading client configuration...")

        test_client = clients[0]

        try:
            config = pm.load_client_config(test_client)
            print(f"  OK: Loaded client_config.json for {test_client}")
            print(f"    Client name: {config.get('client_name', 'N/A')}")

            # Check ui_settings
            ui_settings = config.get("ui_settings")
            if ui_settings:
                print(f"  OK: ui_settings present")
                if "table_view" in ui_settings:
                    print(f"  OK: table_view present in ui_settings")
                else:
                    print(f"  WARN: table_view missing (will be auto-migrated)")
            else:
                print(f"  WARN: ui_settings missing (will be auto-migrated)")

        except Exception as e:
            print(f"  FAIL: Failed to load client config: {e}")
            all_passed = False

        print()

    # ========================================
    # TEST 6: Shopify Config V2 Format
    # ========================================
    if clients:
        print("Test 6: Shopify config V2 format...")

        test_client = clients[0]

        try:
            shopify_config = pm.load_shopify_config(test_client)
            print(f"  OK: Loaded shopify_config.json for {test_client}")

            # Check column_mappings version
            col_mappings = shopify_config.get('column_mappings', {})
            version = col_mappings.get('version')
            if version and version >= 2:
                print(f"  OK: column_mappings version = {version}")
            else:
                print(f"  WARN: column_mappings version = {version} (expected >= 2)")

            # Check required V2 fields
            required_fields = ['tag_categories', 'set_decoders', 'order_rules', 'packaging_rules']
            for field in required_fields:
                if field in shopify_config:
                    print(f"  OK: {field} present")
                else:
                    print(f"  WARN: {field} missing")

            # Check settings
            settings = shopify_config.get('settings', {})
            required_settings = ['stock_csv_delimiter', 'orders_csv_delimiter', 'low_stock_threshold']
            for setting in required_settings:
                if setting in settings:
                    print(f"  OK: settings.{setting} = {settings[setting]}")
                else:
                    print(f"  WARN: settings.{setting} missing")

            packing_lists = shopify_config.get('packing_list_configs', [])
            print(f"  OK: Packing lists: {len(packing_lists)}")

        except Exception as e:
            print(f"  FAIL: Failed to load shopify config: {e}")
            all_passed = False

        print()

    # ========================================
    # TEST 7: Test Data Files
    # ========================================
    print("Test 7: Test data files...")

    test_files = [
        ("data/test_input/test_orders.csv", "Basic test orders"),
        ("data/test_input/test_stock.csv", "Basic test stock"),
        ("data/test_input/comprehensive_orders.csv", "Comprehensive orders"),
        ("data/test_input/comprehensive_stock.csv", "Comprehensive stock"),
    ]

    for filepath, desc in test_files:
        if Path(filepath).exists():
            print(f"  OK: {filepath}")
        else:
            print(f"  WARN: {filepath} (missing - run: python scripts/create_test_data.py)")

    print()

    # ========================================
    # TEST 8: Session with test data
    # ========================================
    print("Test 8: Pre-populated sessions...")

    sessions_dir = base / "Sessions" / "CLIENT_M"
    if sessions_dir.exists():
        session_dirs = sorted(
            [d for d in sessions_dir.iterdir() if d.is_dir()],
            key=lambda d: d.name,
            reverse=True
        )
        if session_dirs:
            latest = session_dirs[0]
            print(f"  OK: Latest session: {latest.name}")

            input_dir = latest / "input"
            if input_dir.exists() and list(input_dir.glob("*.csv")):
                csv_files = [f.name for f in input_dir.glob("*.csv")]
                print(f"  OK: Input files: {', '.join(csv_files)}")
            else:
                print(f"  WARN: No CSV files in session input/")

            analysis_dir = latest / "analysis"
            if analysis_dir.exists() and (analysis_dir / "current_state.pkl").exists():
                print(f"  OK: Analysis results present")
            else:
                print(f"  INFO: No analysis results (run with --with-analysis to generate)")
        else:
            print(f"  INFO: No sessions found (run with --with-session to create)")
    else:
        print(f"  INFO: No sessions directory for CLIENT_M")

    print()

    # ========================================
    # SUMMARY
    # ========================================
    print("=" * 60)
    if all_passed:
        print("ALL TESTS PASSED - Dev environment is ready!")
        print("=" * 60)
        print()
        print("You can now:")
        print("  1. Run the application: python gui_main.py")
        print("  2. Or use: START_DEV.bat")
        print()
        return True
    else:
        print("SOME TESTS FAILED - Please fix issues above")
        print("=" * 60)
        print()
        return False


if __name__ == "__main__":
    success = test_dev_environment()
    sys.exit(0 if success else 1)
