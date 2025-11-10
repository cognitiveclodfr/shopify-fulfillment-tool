"""Setup local development environment for Shopify Tool.

This script creates a local mock of the file server structure
to enable development without access to the production server.

Usage:
    python scripts/setup_dev_env.py [path]

    If no path provided, uses: D:\Dev\fulfillment-server-mock
"""

import os
import json
from pathlib import Path
from datetime import datetime
import sys


def create_dev_structure(base_path: str):
    """Create local mock server structure.

    Args:
        base_path: Base directory for mock server structure
    """

    base = Path(base_path)
    print("=" * 60)
    print("SHOPIFY TOOL - DEV ENVIRONMENT SETUP")
    print("=" * 60)
    print(f"\nCreating dev environment at: {base}")
    print()

    # ========================================
    # CREATE DIRECTORY STRUCTURE
    # ========================================
    dirs = [
        "Clients/CLIENT_M",
        "Clients/CLIENT_TEST",
        "Sessions/CLIENT_M",
        "Sessions/CLIENT_TEST",
        "Stats",
        "Logs/shopify_tool",
        "Logs/packing_tool"
    ]

    print("Creating directories...")
    for dir_path in dirs:
        full_path = base / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {dir_path}")

    print()

    # ========================================
    # CREATE CLIENT_M CONFIGURATION
    # ========================================
    print("Creating CLIENT_M configuration...")

    client_m_config = {
        "client_id": "M",
        "client_name": "Test Client M",
        "created_at": datetime.now().isoformat(),
        "active": True
    }

    shopify_m_config = {
        "settings": {
            "stock_csv_delimiter": ";",
            "low_stock_threshold": 10
        },
        "column_mappings": {
            "orders_required": [
                "Name",
                "Lineitem sku",
                "Lineitem quantity",
                "Shipping Method",
                "Shipping Country",
                "Tags",
                "Notes"
            ],
            "stock_required": [
                "Артикул",
                "Име",
                "Наличност"
            ]
        },
        "courier_mappings": {
            "dhl": "DHL",
            "dpd": "DPD",
            "speedy": "PostOne",
            "postone": "PostOne",
            "econt": "Econt"
        },
        "rules": [],
        "packing_list_configs": [
            {
                "name": "DHL Orders",
                "output_filename": "DHL_Orders.xlsx",
                "filters": [
                    {
                        "field": "Shipping_Provider",
                        "operator": "==",
                        "value": "DHL"
                    }
                ],
                "exclude_skus": ["07", "Shipping protection"]
            },
            {
                "name": "PostOne Orders",
                "output_filename": "PostOne_Orders.xlsx",
                "filters": [
                    {
                        "field": "Shipping_Provider",
                        "operator": "==",
                        "value": "PostOne"
                    }
                ],
                "exclude_skus": ["07"]
            }
        ],
        "stock_export_configs": [
            {
                "name": "Stock Export ALL",
                "output_filename": "stock_export_all.xls",
                "filters": []
            },
            {
                "name": "Stock Export DHL Only",
                "output_filename": "stock_export_dhl.xls",
                "filters": [
                    {
                        "field": "Shipping_Provider",
                        "operator": "==",
                        "value": "DHL"
                    }
                ]
            }
        ]
    }

    client_m_dir = base / "Clients/CLIENT_M"

    # Save client_config.json
    with open(client_m_dir / "client_config.json", 'w', encoding='utf-8') as f:
        json.dump(client_m_config, f, indent=2, ensure_ascii=False)
    print(f"  ✓ client_config.json")

    # Save shopify_config.json
    with open(client_m_dir / "shopify_config.json", 'w', encoding='utf-8') as f:
        json.dump(shopify_m_config, f, indent=2, ensure_ascii=False)
    print(f"  ✓ shopify_config.json")

    # Create empty history
    with open(client_m_dir / "fulfillment_history.csv", 'w', encoding='utf-8') as f:
        f.write("Order_Number,Date_Fulfilled\n")
    print(f"  ✓ fulfillment_history.csv")

    print()

    # ========================================
    # CREATE CLIENT_TEST CONFIGURATION
    # ========================================
    print("Creating CLIENT_TEST configuration...")

    test_config = client_m_config.copy()
    test_config["client_id"] = "TEST"
    test_config["client_name"] = "Test Client TEST"

    client_test_dir = base / "Clients/CLIENT_TEST"

    with open(client_test_dir / "client_config.json", 'w', encoding='utf-8') as f:
        json.dump(test_config, f, indent=2, ensure_ascii=False)

    with open(client_test_dir / "shopify_config.json", 'w', encoding='utf-8') as f:
        json.dump(shopify_m_config, f, indent=2, ensure_ascii=False)

    with open(client_test_dir / "fulfillment_history.csv", 'w', encoding='utf-8') as f:
        f.write("Order_Number,Date_Fulfilled\n")

    print(f"  ✓ All CLIENT_TEST configs created")
    print()

    # ========================================
    # CREATE GLOBAL STATS
    # ========================================
    print("Creating global stats...")

    global_stats = {
        "total_analyses": 0,
        "total_orders_analyzed": 0,
        "total_items_analyzed": 0,
        "clients": {},
        "last_updated": datetime.now().isoformat()
    }

    stats_file = base / "Stats/global_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(global_stats, f, indent=2, ensure_ascii=False)
    print(f"  ✓ global_stats.json")

    print()

    # ========================================
    # COMPLETION MESSAGE
    # ========================================
    print("=" * 60)
    print("✅ DEV ENVIRONMENT SETUP COMPLETE!")
    print("=" * 60)
    print()
    print(f"Base path: {base.absolute()}")
    print()
    print("Next steps:")
    print("  1. Set environment variable:")
    print(f"     Windows CMD:  set FULFILLMENT_SERVER_PATH={base.absolute()}")
    print(f"     PowerShell:   $env:FULFILLMENT_SERVER_PATH='{base.absolute()}'")
    print()
    print("  2. Create test data:")
    print("     python scripts/create_test_data.py")
    print()
    print("  3. Run the application:")
    print("     python gui_main.py")
    print()
    print("  Or use START_DEV.bat for automatic setup!")
    print()


if __name__ == "__main__":
    # Get base path from arguments or use default
    if len(sys.argv) > 1:
        dev_path = sys.argv[1]
    else:
        # Default dev path
        if os.name == 'nt':  # Windows
            dev_path = r"D:\Dev\fulfillment-server-mock"
        else:  # Mac/Linux
            dev_path = os.path.expanduser("~/Dev/fulfillment-server-mock")

    try:
        create_dev_structure(dev_path)
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
