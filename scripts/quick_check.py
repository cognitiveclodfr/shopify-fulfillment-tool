"""Quick check of current configuration and what will be loaded."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shopify_tool.profile_manager import ProfileManager

server_path = os.getenv("FULFILLMENT_SERVER_PATH", "D:\\Dev\\fulfillment-server-mock")
client_id = "ALMA"

pm = ProfileManager(server_path)
client_config = pm.load_client_config(client_id)

additional_columns = client_config.get("ui_settings", {}).get("table_view", {}).get("additional_columns", [])

print("\n" + "=" * 60)
print("QUICK CHECK: What will be loaded in analysis")
print("=" * 60)

enabled = [col for col in additional_columns if col.get("enabled", False)]
disabled = [col for col in additional_columns if not col.get("enabled", False)]

print(f"\nTotal configured: {len(additional_columns)}")
print(f"Enabled: {len(enabled)}")
print(f"Disabled: {len(disabled)}")

if enabled:
    print(f"\nEnabled columns (will appear in analysis):")
    for col in enabled:
        print(f"  + {col['csv_name']} -> {col['internal_name']}")
else:
    print("\nWARNING: No columns enabled!")

if len(enabled) > 10:
    print(f"\n⚠️  WARNING: You have {len(enabled)} columns enabled!")
    print("   This is a lot and may cause performance issues.")
    print("   Consider disabling some columns.")

print("\n" + "=" * 60)
