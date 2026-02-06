"""
Reset additional columns configuration to recommended defaults.

This script will:
1. Load current configuration
2. Disable ALL additional columns
3. Enable only a small set of useful columns (Email, Phone, Financial Status)
4. Save the updated configuration
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shopify_tool.profile_manager import ProfileManager


# Recommended columns to enable by default
RECOMMENDED_COLUMNS = [
    "Email",
    "Phone",
    "Financial Status",
    "Fulfillment Status",
    "Paid at",
]


def reset_additional_columns(server_path, client_id):
    """Reset additional columns to recommended defaults."""
    print("\n" + "=" * 60)
    print(f"Resetting Additional Columns for {client_id}")
    print("=" * 60 + "\n")

    # Initialize ProfileManager
    pm = ProfileManager(server_path)

    # Load client config
    client_config = pm.load_client_config(client_id)
    if not client_config:
        print("ERROR: Could not load client config")
        return False

    # Get additional columns
    additional_columns = client_config.get("ui_settings", {}).get("table_view", {}).get("additional_columns", [])

    if not additional_columns:
        print("No additional columns configured yet")
        return True

    print(f"Current: {len(additional_columns)} columns configured")
    enabled_count = sum(1 for col in additional_columns if col.get("enabled", False))
    print(f"  {enabled_count} enabled")
    print(f"  {len(additional_columns) - enabled_count} disabled\n")

    # Disable all columns first
    for col in additional_columns:
        col["enabled"] = False

    # Enable only recommended columns
    enabled_recommended = []
    for col in additional_columns:
        if col["csv_name"] in RECOMMENDED_COLUMNS:
            col["enabled"] = True
            enabled_recommended.append(col["csv_name"])

    print(f"After reset: {len(additional_columns)} columns configured")
    print(f"  {len(enabled_recommended)} enabled (recommended)")
    print(f"  {len(additional_columns) - len(enabled_recommended)} disabled\n")

    if enabled_recommended:
        print("Enabled columns:")
        for name in enabled_recommended:
            print(f"  + {name}")
    else:
        print("WARNING: None of the recommended columns found in configuration")
        print("You may need to scan CSV again to discover columns")

    # Save config
    if "ui_settings" not in client_config:
        client_config["ui_settings"] = {}
    if "table_view" not in client_config["ui_settings"]:
        client_config["ui_settings"]["table_view"] = {}

    client_config["ui_settings"]["table_view"]["additional_columns"] = additional_columns

    success = pm.save_client_config(client_id, client_config)
    if not success:
        print("\nERROR: Failed to save configuration")
        return False

    print("\n" + "=" * 60)
    print("RESET COMPLETE")
    print("=" * 60)
    print("\nConfiguration saved successfully!")
    print(f"\nNext steps:")
    print("1. Restart the app (or reload client)")
    print("2. Load CSV files")
    print("3. Run analysis")
    print("4. Check that only recommended columns appear in results")
    print("\nTo customize:")
    print("- Open Column Configuration dialog")
    print("- Scan Current CSV")
    print("- Enable/disable columns as needed")
    print("- Click Apply")

    return True


if __name__ == "__main__":
    # Get server path from environment or use default
    server_path = os.getenv("FULFILLMENT_SERVER_PATH", "D:\\Dev\\fulfillment-server-mock")
    client_id = "ALMA"

    if len(sys.argv) > 1:
        client_id = sys.argv[1]

    try:
        success = reset_additional_columns(server_path, client_id)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
