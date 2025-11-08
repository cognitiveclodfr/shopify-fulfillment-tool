"""Test that development environment is properly configured.

This script verifies:
1. Environment variable is set
2. Directory structure exists
3. ProfileManager can initialize
4. Client configs can be loaded
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
        print("  ❌ FULFILLMENT_SERVER_PATH environment variable is not set!")
        print()
        print("  Set it with:")
        print("    Windows: set FULFILLMENT_SERVER_PATH=D:\\Dev\\fulfillment-server-mock")
        print("    Linux:   export FULFILLMENT_SERVER_PATH=/home/user/Dev/fulfillment-server-mock")
        print()
        all_passed = False
    else:
        print(f"  ✓ FULFILLMENT_SERVER_PATH = {server_path}")

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
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/ (missing)")
            all_dirs_exist = False

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
        print(f"  ✓ ProfileManager initialized")
        print(f"    Base path: {pm.base_path}")
        print(f"    Dev mode: {pm._is_dev_environment()}")

    except Exception as e:
        print(f"  ❌ ProfileManager initialization failed: {e}")
        all_passed = False
        print()
        return False

    print()

    # ========================================
    # TEST 4: List Clients
    # ========================================
    print("Test 4: Client listing...")

    try:
        clients = pm.list_clients()

        if clients:
            print(f"  ✓ Found {len(clients)} client(s): {', '.join(clients)}")
        else:
            print(f"  ⚠ No clients found (expected CLIENT_M, CLIENT_TEST)")
            print(f"    Run setup script to create default clients:")
            print(f"      python scripts/setup_dev_env.py")
            all_passed = False

    except Exception as e:
        print(f"  ❌ Failed to list clients: {e}")
        all_passed = False

    print()

    # ========================================
    # TEST 5: Load Client Config
    # ========================================
    if clients:
        print("Test 5: Loading client configuration...")

        test_client = clients[0]

        try:
            config = pm.load_client_config(test_client)
            print(f"  ✓ Loaded client_config.json for {test_client}")
            print(f"    Client name: {config.get('client_name', 'N/A')}")

            shopify_config = pm.load_shopify_config(test_client)
            print(f"  ✓ Loaded shopify_config.json for {test_client}")

            packing_lists = shopify_config.get('packing_list_configs', [])
            print(f"    Packing lists: {len(packing_lists)}")

        except Exception as e:
            print(f"  ❌ Failed to load configs: {e}")
            all_passed = False

        print()

    # ========================================
    # TEST 6: Test Data Files
    # ========================================
    print("Test 6: Test data files...")

    test_orders = Path("data/test_input/test_orders.csv")
    test_stock = Path("data/test_input/test_stock.csv")

    if test_orders.exists():
        print(f"  ✓ test_orders.csv")
    else:
        print(f"  ⚠ test_orders.csv (missing)")
        print(f"    Run: python scripts/create_test_data.py")

    if test_stock.exists():
        print(f"  ✓ test_stock.csv")
    else:
        print(f"  ⚠ test_stock.csv (missing)")
        print(f"    Run: python scripts/create_test_data.py")

    print()

    # ========================================
    # SUMMARY
    # ========================================
    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Dev environment is ready!")
        print("=" * 60)
        print()
        print("You can now:")
        print("  1. Run the application: python gui_main.py")
        print("  2. Or use: START_DEV.bat")
        print()
        return True
    else:
        print("❌ SOME TESTS FAILED - Please fix issues above")
        print("=" * 60)
        print()
        return False


if __name__ == "__main__":
    success = test_dev_environment()
    sys.exit(0 if success else 1)
