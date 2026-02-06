"""Setup local development environment for Shopify Tool.

This script creates a local mock of the file server structure
to enable development without access to the production server.

Uses ProfileManager as the single source of truth for config structures,
ensuring the mock environment always matches the production format.

Usage:
    python scripts/setup_dev_env.py [path]
    python scripts/setup_dev_env.py --with-session [path]
    python scripts/setup_dev_env.py --with-session --with-analysis [path]

    If no path provided, uses: D:\\Dev\\fulfillment-server-mock

Flags:
    --with-session    Create a pre-populated session with test CSV files
    --with-analysis   Also generate synthetic analysis results (implies --with-session)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path so we can import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from shopify_tool.profile_manager import ProfileManager


def _create_client_config(client_id: str, client_name: str) -> dict:
    """Create a complete client_config.json dict with ui_settings.

    Args:
        client_id: Client ID (e.g., "M")
        client_name: Display name (e.g., "Test Client M")

    Returns:
        Complete client_config dict matching production format
    """
    return {
        "client_id": client_id,
        "client_name": client_name,
        "created_at": datetime.now().isoformat(),
        "created_by": os.environ.get('COMPUTERNAME', 'DEV'),
        "active": True,
        "ui_settings": ProfileManager._get_default_ui_settings()
    }


def _create_shopify_config(client_id: str, client_name: str) -> dict:
    """Create a complete shopify_config.json dict with dev-specific additions.

    Uses ProfileManager._create_default_shopify_config as the base,
    then adds packing list and stock export configs useful for testing.

    Args:
        client_id: Client ID
        client_name: Display name

    Returns:
        Complete shopify_config dict matching production V2 format
    """
    config = ProfileManager._create_default_shopify_config(client_id, client_name)

    # Add dev-specific packing list configs for testing
    config["packing_list_configs"] = [
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
    ]

    # Add dev-specific stock export configs
    config["stock_export_configs"] = [
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

    return config


def _save_json(path: Path, data: dict):
    """Save dict as JSON file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def create_dev_structure(base_path: str, with_session: bool = False, with_analysis: bool = False):
    """Create local mock server structure.

    Args:
        base_path: Base directory for mock server structure
        with_session: If True, create a session with test CSV files
        with_analysis: If True, also generate synthetic analysis results
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
        "Clients/CLIENT_M/backups",
        "Clients/CLIENT_TEST",
        "Clients/CLIENT_TEST/backups",
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
        print(f"  + {dir_path}")

    print()

    # ========================================
    # CREATE CLIENT_M CONFIGURATION
    # ========================================
    print("Creating CLIENT_M configuration...")

    client_m_dir = base / "Clients/CLIENT_M"

    # client_config.json (with ui_settings + table_view)
    client_m_config = _create_client_config("M", "Test Client M")
    _save_json(client_m_dir / "client_config.json", client_m_config)
    print(f"  + client_config.json (V2 with ui_settings)")

    # shopify_config.json (V2 format from ProfileManager)
    shopify_m_config = _create_shopify_config("M", "Test Client M")
    _save_json(client_m_dir / "shopify_config.json", shopify_m_config)
    print(f"  + shopify_config.json (V2 column_mappings)")

    # Empty fulfillment history
    with open(client_m_dir / "fulfillment_history.csv", 'w', encoding='utf-8') as f:
        f.write("Order_Number,Date_Fulfilled\n")
    print(f"  + fulfillment_history.csv")

    print()

    # ========================================
    # CREATE CLIENT_TEST CONFIGURATION
    # ========================================
    print("Creating CLIENT_TEST configuration...")

    client_test_dir = base / "Clients/CLIENT_TEST"

    test_client_config = _create_client_config("TEST", "Test Client TEST")
    _save_json(client_test_dir / "client_config.json", test_client_config)

    test_shopify_config = _create_shopify_config("TEST", "Test Client TEST")
    _save_json(client_test_dir / "shopify_config.json", test_shopify_config)

    with open(client_test_dir / "fulfillment_history.csv", 'w', encoding='utf-8') as f:
        f.write("Order_Number,Date_Fulfilled\n")

    print(f"  + All CLIENT_TEST configs created (V2)")
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

    _save_json(base / "Stats/global_stats.json", global_stats)
    print(f"  + global_stats.json")
    print()

    # ========================================
    # CREATE SESSION WITH TEST DATA (optional)
    # ========================================
    if with_session or with_analysis:
        _create_test_session(base, with_analysis)

    # ========================================
    # ALSO CREATE LOCAL TEST DATA (backward compat)
    # ========================================
    print("Creating local test data (data/test_input/)...")
    try:
        from scripts.create_comprehensive_test_data import (
            create_comprehensive_orders,
            create_comprehensive_stock,
        )
        create_comprehensive_orders()
        create_comprehensive_stock()
    except ImportError:
        # Fallback if running from scripts/ directory
        try:
            from create_comprehensive_test_data import (
                create_comprehensive_orders,
                create_comprehensive_stock,
            )
            create_comprehensive_orders()
            create_comprehensive_stock()
        except ImportError:
            print("  (skipped - comprehensive test data script not found)")
    print()

    # ========================================
    # COMPLETION MESSAGE
    # ========================================
    print("=" * 60)
    print("DEV ENVIRONMENT SETUP COMPLETE!")
    print("=" * 60)
    print()
    print(f"Base path: {base.absolute()}")
    print()
    print("Next steps:")
    print("  1. Set environment variable:")
    print(f"     Windows CMD:  set FULFILLMENT_SERVER_PATH={base.absolute()}")
    print(f"     PowerShell:   $env:FULFILLMENT_SERVER_PATH='{base.absolute()}'")
    print()
    print("  2. Run the application:")
    print("     python gui_main.py")
    print()
    print("  Or use START_DEV.bat for automatic setup!")
    print()


def _create_test_session(base: Path, with_analysis: bool = False):
    """Create a pre-populated session with test CSV files.

    Args:
        base: Mock server base path
        with_analysis: If True, also generate synthetic analysis results
    """
    print("Creating test session for CLIENT_M...")

    # Generate session name
    today = datetime.now().strftime("%Y-%m-%d")
    session_name = f"{today}_1"
    session_path = base / "Sessions" / "CLIENT_M" / session_name

    # Session subdirectories (matching SessionManager.SESSION_SUBDIRS)
    subdirs = ["input", "analysis", "packing_lists", "stock_exports", "reference_labels", "barcodes"]
    for subdir in subdirs:
        (session_path / subdir).mkdir(parents=True, exist_ok=True)

    # Generate test CSVs directly into session input/
    try:
        from scripts.create_comprehensive_test_data import (
            create_comprehensive_orders,
            create_comprehensive_stock,
        )
    except ImportError:
        from create_comprehensive_test_data import (
            create_comprehensive_orders,
            create_comprehensive_stock,
        )

    input_dir = session_path / "input"
    orders_path = create_comprehensive_orders(input_dir / "orders.csv")
    stock_path = create_comprehensive_stock(input_dir / "stock.csv")

    # Create session_info.json
    session_info = {
        "created_by_tool": "shopify",
        "created_at": datetime.now().isoformat(),
        "client_id": "M",
        "session_name": session_name,
        "status": "active",
        "pc_name": os.environ.get('COMPUTERNAME', 'DEV'),
        "orders_file": "orders.csv",
        "stock_file": "stock.csv",
        "analysis_completed": False,
        "packing_lists_generated": [],
        "stock_exports_generated": [],
        "statistics": {
            "total_orders": 0,
            "total_items": 0,
            "packing_lists_count": 0,
            "packing_lists": []
        },
        "comments": "Auto-generated dev session",
        "last_modified": datetime.now().isoformat()
    }

    if with_analysis:
        _generate_mock_analysis(session_path, orders_path, stock_path, session_info)

    _save_json(session_path / "session_info.json", session_info)
    print(f"  + Session: {session_name}")
    print(f"  + Input files: orders.csv, stock.csv")
    if with_analysis:
        print(f"  + Analysis results generated")
    print()


def _generate_mock_analysis(session_path: Path, orders_path: Path, stock_path: Path, session_info: dict):
    """Generate synthetic analysis results for debugging post-analysis features.

    Creates DataFrame output files (pickle, xlsx, json) that the app can load
    without running the actual analysis pipeline.

    Args:
        session_path: Session directory path
        orders_path: Path to orders CSV
        stock_path: Path to stock CSV
        session_info: session_info dict to update with analysis results
    """
    import pandas as pd

    print("  Generating mock analysis results...")

    # Load test data
    orders_df = pd.read_csv(orders_path, encoding='utf-8-sig')
    stock_df = pd.read_csv(stock_path, sep=';', encoding='utf-8-sig')

    # Build stock lookup
    stock_lookup = dict(zip(stock_df['Артикул'], stock_df['Наличност']))

    # Build simplified analysis DataFrame
    rows = []
    stock_remaining = stock_lookup.copy()

    for _, row in orders_df.iterrows():
        sku = row.get('Lineitem sku', '')
        qty = int(row.get('Lineitem quantity', 1))
        available = stock_remaining.get(sku, 0)

        # Simple fulfillment check
        if available >= qty:
            status = "Fulfillable"
            stock_remaining[sku] = available - qty
            final_stock = stock_remaining[sku]
        else:
            status = "Not Fulfillable"
            final_stock = available

        # Determine courier from shipping method
        shipping_method = str(row.get('Shipping Method', ''))
        shipping_lower = shipping_method.lower()
        if 'dhl' in shipping_lower:
            provider = 'DHL'
        elif 'dpd' in shipping_lower:
            provider = 'DPD'
        elif 'speedy' in shipping_lower:
            provider = 'Speedy'
        elif 'postone' in shipping_lower:
            provider = 'PostOne'
        else:
            provider = shipping_method

        # Stock alert
        stock_val = stock_lookup.get(sku, 0)
        if stock_val == 0:
            stock_alert = "Out of Stock"
        elif stock_val <= 5:
            stock_alert = "Low Stock"
        else:
            stock_alert = ""

        rows.append({
            'Order_Number': row.get('Name', ''),
            'Order_Type': 'Multi' if orders_df[orders_df['Name'] == row.get('Name', '')].shape[0] > 1 else 'Single',
            'SKU': sku,
            'Has_SKU': bool(sku and sku not in ('07', 'Shipping protection')),
            'Product_Name': row.get('Lineitem name', ''),
            'Warehouse_Name': '',
            'Quantity': qty,
            'Total_Price': row.get('Total', 0),
            'Subtotal': row.get('Subtotal', 0),
            'Stock': stock_lookup.get(sku, 0),
            'Final_Stock': final_stock,
            'Source': row.get('Source', 'web'),
            'Stock_Alert': stock_alert,
            'Order_Fulfillment_Status': status,
            'Shipping_Provider': provider,
            'Destination_Country': row.get('Shipping Country', ''),
            'Shipping_Method': shipping_method,
            'Tags': row.get('Tags', ''),
            'Notes': row.get('Notes', ''),
            'System_note': '',
            'Status_Note': '',
            'Internal_Tags': '',
        })

    final_df = pd.DataFrame(rows)

    # Save analysis outputs
    analysis_dir = session_path / "analysis"

    final_df.to_pickle(analysis_dir / "current_state.pkl")
    final_df.to_excel(analysis_dir / "current_state.xlsx", index=False)
    final_df.to_excel(analysis_dir / "fulfillment_analysis.xlsx", index=False)

    # Stats JSON
    unique_orders = final_df['Order_Number'].nunique()
    fulfillable = final_df.groupby('Order_Number')['Order_Fulfillment_Status'].apply(
        lambda x: all(s == 'Fulfillable' for s in x)
    ).sum()

    stats = {
        "total_orders": unique_orders,
        "total_items": len(final_df),
        "fulfillable_orders": int(fulfillable),
        "not_fulfillable_orders": unique_orders - int(fulfillable),
        "generated_at": datetime.now().isoformat(),
        "is_mock": True
    }
    _save_json(analysis_dir / "analysis_stats.json", stats)

    # Analysis data JSON (packing tool integration format)
    orders_list = []
    for order_num, group in final_df.groupby('Order_Number'):
        first = group.iloc[0]
        items = [
            {
                "sku": r['SKU'],
                "product_name": r['Product_Name'],
                "quantity": int(r['Quantity'])
            }
            for _, r in group.iterrows()
        ]
        orders_list.append({
            "order_number": order_num,
            "courier": first['Shipping_Provider'],
            "status": first['Order_Fulfillment_Status'],
            "shipping_country": first['Destination_Country'],
            "tags": first['Tags'],
            "items": items
        })

    analysis_data = {
        "analyzed_at": datetime.now().isoformat(),
        "total_orders": unique_orders,
        "fulfillable_orders": int(fulfillable),
        "not_fulfillable_orders": unique_orders - int(fulfillable),
        "orders": orders_list
    }
    _save_json(analysis_dir / "analysis_data.json", analysis_data)

    # Update session_info
    session_info["analysis_completed"] = True
    session_info["statistics"] = {
        "total_orders": unique_orders,
        "total_items": len(final_df),
        "packing_lists_count": 0,
        "packing_lists": []
    }

    print(f"    Orders: {unique_orders}, Items: {len(final_df)}, "
          f"Fulfillable: {int(fulfillable)}, Not: {unique_orders - int(fulfillable)}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Setup local development environment for Shopify Tool"
    )
    parser.add_argument(
        'path',
        nargs='?',
        default=None,
        help="Base path for mock server (default: D:\\Dev\\fulfillment-server-mock)"
    )
    parser.add_argument(
        '--with-session',
        action='store_true',
        help="Create a pre-populated session with test CSV files"
    )
    parser.add_argument(
        '--with-analysis',
        action='store_true',
        help="Generate synthetic analysis results (implies --with-session)"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Determine base path
    if args.path:
        dev_path = args.path
    else:
        if os.name == 'nt':  # Windows
            dev_path = r"D:\Dev\fulfillment-server-mock"
        else:  # Mac/Linux
            dev_path = os.path.expanduser("~/Dev/fulfillment-server-mock")

    # --with-analysis implies --with-session
    with_session = args.with_session or args.with_analysis

    try:
        create_dev_structure(dev_path, with_session=with_session, with_analysis=args.with_analysis)
    except Exception as e:
        print(f"Error during setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
