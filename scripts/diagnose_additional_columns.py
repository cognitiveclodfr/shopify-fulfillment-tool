"""
Diagnostic script to check additional columns configuration.

Run this to diagnose why additional columns are not appearing.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shopify_tool.profile_manager import ProfileManager


def diagnose_client_config(server_path, client_id):
    """Diagnose additional columns configuration for a client."""
    print("\n" + "=" * 60)
    print(f"Diagnosing Additional Columns for {client_id}")
    print("=" * 60 + "\n")

    # Check if server path exists
    if not os.path.exists(server_path):
        print(f"ERROR: Server path does not exist: {server_path}")
        return False

    print(f"+ Server path: {server_path}")

    # Initialize ProfileManager
    pm = ProfileManager(server_path)

    # Check if client exists
    if not pm.client_exists(client_id):
        print(f"ERROR: Client {client_id} not found")
        # List available clients
        clients_dir = Path(server_path) / "Clients"
        if clients_dir.exists():
            available = [d.name for d in clients_dir.iterdir() if d.is_dir() and d.name.startswith("CLIENT_")]
            print(f"Available clients: {available}")
        return False

    print(f"+ Client exists: {client_id}\n")

    # Load client config
    client_config = pm.load_client_config(client_id)
    if not client_config:
        print("ERROR: Could not load client config")
        return False

    print("+ Client config loaded successfully\n")

    # Check ui_settings
    if "ui_settings" not in client_config:
        print("WARNING: No 'ui_settings' in client config")
        client_config["ui_settings"] = {}

    ui_settings = client_config.get("ui_settings", {})
    print(f"+ ui_settings keys: {list(ui_settings.keys())}\n")

    # Check table_view
    if "table_view" not in ui_settings:
        print("WARNING: No 'table_view' in ui_settings")
        ui_settings["table_view"] = {}

    table_view = ui_settings.get("table_view", {})
    print(f"+ table_view keys: {list(table_view.keys())}\n")

    # Check additional_columns
    if "additional_columns" not in table_view:
        print("WARNING: No 'additional_columns' in table_view")
        print("\nRECOMMENDATION:")
        print("1. Load a CSV file in the app")
        print("2. Open Column Configuration dialog")
        print("3. Click 'Scan Current CSV for Available Columns'")
        print("4. Check the columns you want")
        print("5. Click Apply")
        return False

    additional_columns = table_view.get("additional_columns", [])

    if not additional_columns:
        print("WARNING: additional_columns is empty")
        print("\nRECOMMENDATION: Same as above")
        return False

    print(f"+ Found {len(additional_columns)} additional columns configured\n")

    # Analyze columns
    enabled_cols = [col for col in additional_columns if col.get("enabled", False)]
    disabled_cols = [col for col in additional_columns if not col.get("enabled", False)]

    print(f"Enabled columns: {len(enabled_cols)}")
    for col in enabled_cols[:5]:  # Show first 5
        print(f"  + {col['csv_name']} -> {col['internal_name']}")
    if len(enabled_cols) > 5:
        print(f"  ... and {len(enabled_cols) - 5} more")

    print(f"\nDisabled columns: {len(disabled_cols)}")
    for col in disabled_cols[:5]:  # Show first 5
        print(f"  - {col['csv_name']} -> {col['internal_name']}")
    if len(disabled_cols) > 5:
        print(f"  ... and {len(disabled_cols) - 5} more")

    if not enabled_cols:
        print("\n" + "!" * 60)
        print("PROBLEM FOUND: No columns are enabled!")
        print("!" * 60)
        print("\nRECOMMENDATION:")
        print("1. Open Column Configuration dialog")
        print("2. Click 'Scan Current CSV for Available Columns'")
        print("3. CHECK the checkboxes for columns you want")
        print("4. Click Apply")
        print("\nOr enable them manually in:")
        config_path = pm.get_client_config_path(client_id)
        print(f"  {config_path}")
        print("\nChange \"enabled\": false to \"enabled\": true")
        return False

    print("\n" + "=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)
    print("\nConfiguration looks good!")
    print(f"+ {len(enabled_cols)} columns are enabled")
    print(f"+ {len(additional_columns)} columns are configured")
    print("\nNext steps:")
    print("1. Load CSV files in the app")
    print("2. Run analysis")
    print("3. Check logs for:")
    print("   'Loaded client config: X additional columns configured, Y enabled'")
    print("   'Renamed Y additional columns: [...]'")
    print("4. Check Analysis Results table for new columns")

    return True


if __name__ == "__main__":
    # Get server path from environment or use default
    server_path = os.getenv("FULFILLMENT_SERVER_PATH", "D:\\Dev\\fulfillment-server-mock")
    client_id = "ALMA"

    if len(sys.argv) > 1:
        client_id = sys.argv[1]

    try:
        success = diagnose_client_config(server_path, client_id)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
