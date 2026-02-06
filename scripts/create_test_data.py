"""Create test CSV files for development.

This script generates realistic test data for orders and stock
that can be used for testing without real business data.

Usage:
    python scripts/create_test_data.py
    python scripts/create_test_data.py --server-path D:\\Dev\\fulfillment-server-mock
"""

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd


def create_test_orders():
    """Create realistic test orders CSV."""

    print("Creating test orders CSV...")

    orders_data = {
        "Name": [
            "#1001", "#1001", "#1002",
            "#1003", "#1003", "#1003",
            "#1004", "#1005", "#1005",
            "#1006"
        ],
        "Lineitem sku": [
            "SKU-001", "SKU-002", "SKU-003",
            "SKU-001", "SKU-004", "SKU-005",
            "SKU-006", "SKU-001", "SKU-007",
            "07"  # This should be excluded
        ],
        "Lineitem quantity": [
            2, 1, 1,
            3, 2, 1,
            1, 1, 2,
            1
        ],
        "Shipping Method": [
            "dhl", "dhl", "dpd",
            "speedy", "speedy", "speedy",
            "dhl", "postone", "postone",
            "dhl"
        ],
        "Shipping Country": [
            "BG", "BG", "BG",
            "BG", "BG", "BG",
            "DE", "BG", "BG",
            "BG"
        ],
        "Tags": [
            "", "", "",
            "Priority", "Priority", "Priority",
            "", "Repeat", "Repeat",
            ""
        ],
        "Notes": [
            "", "", "",
            "Rush order", "Rush order", "Rush order",
            "International", "", "",
            ""
        ],
        "Total": [
            50.00, 50.00, 25.00,
            75.00, 75.00, 75.00,
            30.00, 15.00, 15.00,
            5.00
        ]
    }

    df = pd.DataFrame(orders_data)
    output_path = Path("data/test_input/test_orders.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"  + Created: {output_path}")
    print(f"    Orders: {df['Name'].nunique()}, Line items: {len(df)}")

    return output_path


def create_test_stock():
    """Create realistic test stock CSV."""

    print("Creating test stock CSV...")

    stock_data = {
        "Артикул": [
            "SKU-001", "SKU-002", "SKU-003",
            "SKU-004", "SKU-005", "SKU-006",
            "SKU-007", "07"
        ],
        "Име": [
            "Product A - Bestseller",
            "Product B - Medium Stock",
            "Product C - Low Stock",
            "Product D - Very Low Stock",
            "Product E - Critical Stock",
            "Product F - New Item",
            "Product G - Popular",
            "Shipping Protection"
        ],
        "Наличност": [
            100, 50, 25,
            10, 5, 15,
            30, 999
        ]
    }

    df = pd.DataFrame(stock_data)
    output_path = Path("data/test_input/test_stock.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False, sep=";", encoding='utf-8')
    print(f"  + Created: {output_path}")
    print(f"    SKUs: {len(df)}, Total stock: {df['Наличност'].sum()}")

    return output_path


def copy_to_server(orders_path: Path, stock_path: Path, server_path: str):
    """Copy test data into mock server's latest session input directory.

    Args:
        orders_path: Path to generated orders CSV
        stock_path: Path to generated stock CSV
        server_path: Mock server base path
    """
    server = Path(server_path)
    sessions_dir = server / "Sessions" / "CLIENT_M"

    if not sessions_dir.exists():
        print(f"  (skipped server copy - {sessions_dir} does not exist)")
        return

    # Find latest session
    session_dirs = sorted(
        [d for d in sessions_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True
    )

    if not session_dirs:
        print(f"  (skipped server copy - no sessions found in {sessions_dir})")
        return

    latest_session = session_dirs[0]
    input_dir = latest_session / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(orders_path, input_dir / "orders.csv")
    shutil.copy2(stock_path, input_dir / "stock.csv")
    print(f"  + Copied to: {input_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create test CSV files for development")
    parser.add_argument(
        '--server-path',
        default=None,
        help="Mock server path - also copy test data into latest session's input/"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("CREATING TEST DATA FILES")
    print("=" * 60)
    print()

    try:
        orders_path = create_test_orders()
        stock_path = create_test_stock()

        if args.server_path:
            print()
            print("Copying to mock server...")
            copy_to_server(orders_path, stock_path, args.server_path)

        print()
        print("=" * 60)
        print("TEST DATA CREATED SUCCESSFULLY")
        print("=" * 60)
        print()
        print("Files created in: data/test_input/")
        print()
        print("You can now:")
        print("  1. Load test_orders.csv as Orders file")
        print("  2. Load test_stock.csv as Stock file")
        print("  3. Run analysis to test the workflow")
        print()

    except Exception as e:
        print(f"Error creating test data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
