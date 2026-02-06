"""Test script to verify additional columns save/load works correctly."""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shopify_tool.profile_manager import ProfileManager


def test_save_load_additional_columns():
    """Test that saving and loading additional columns config works."""
    server_path = os.getenv("FULFILLMENT_SERVER_PATH", "D:\\Dev\\fulfillment-server-mock")
    client_id = "ALMA"

    print("\n" + "=" * 60)
    print("Testing Additional Columns Save/Load")
    print("=" * 60 + "\n")

    pm = ProfileManager(server_path)

    # Step 1: Load current config
    print("Step 1: Load current config")
    client_config = pm.load_client_config(client_id)
    current_additional = client_config.get("ui_settings", {}).get("table_view", {}).get("additional_columns", [])
    print(f"+ Current config has {len(current_additional)} columns")
    enabled_before = [col for col in current_additional if col.get("enabled", False)]
    print(f"+ {len(enabled_before)} columns enabled:")
    for col in enabled_before:
        print(f"    - {col['csv_name']}")

    # Step 2: Simulate user changes
    print("\nStep 2: Simulate user changes (disable all, enable 2)")
    modified_config = []
    for col in current_additional:
        # Make a copy to avoid modifying original
        col_copy = col.copy()
        # Disable all first
        col_copy["enabled"] = False
        modified_config.append(col_copy)

    # Enable exactly 2 columns: Email and Phone
    for col in modified_config:
        if col["csv_name"] in ["Email", "Phone"]:
            col["enabled"] = True
            print(f"+ Enabled: {col['csv_name']}")

    # Step 3: Save modified config
    print("\nStep 3: Save modified config")
    client_config["ui_settings"]["table_view"]["additional_columns"] = modified_config
    success = pm.save_client_config(client_id, client_config)

    if not success:
        print("ERROR: Failed to save config")
        return False

    print("+ Config saved successfully")

    # Step 4: Reload from disk to verify
    print("\nStep 4: Reload from disk to verify")
    reloaded_config = pm.load_client_config(client_id)
    reloaded_additional = reloaded_config.get("ui_settings", {}).get("table_view", {}).get("additional_columns", [])
    enabled_after = [col for col in reloaded_additional if col.get("enabled", False)]

    print(f"+ Reloaded config has {len(reloaded_additional)} columns")
    print(f"+ {len(enabled_after)} columns enabled:")
    for col in enabled_after:
        print(f"    - {col['csv_name']}")

    # Step 5: Verify changes persisted
    print("\n" + "=" * 60)
    if len(enabled_after) == 2 and set(col['csv_name'] for col in enabled_after) == {"Email", "Phone"}:
        print("SUCCESS: Changes persisted correctly!")
        print("=" * 60)
        return True
    else:
        print("FAILED: Changes did not persist correctly")
        print(f"Expected: 2 enabled columns (Email, Phone)")
        print(f"Got: {len(enabled_after)} enabled columns: {[col['csv_name'] for col in enabled_after]}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    try:
        success = test_save_load_additional_columns()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
