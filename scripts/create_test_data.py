"""Create test CSV files for development.

This script generates realistic test data for orders and stock
that can be used for testing without real business data.
"""

import pandas as pd
from pathlib import Path


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
    print(f"  ✓ Created: {output_path}")
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
    print(f"  ✓ Created: {output_path}")
    print(f"    SKUs: {len(df)}, Total stock: {df['Наличност'].sum()}")

    return output_path


def create_readme():
    """Create README for test data."""

    readme_content = """# Test Data Files

These files are automatically generated test data for development.

## Files:
- `test_orders.csv` - Sample Shopify orders export
- `test_stock.csv` - Sample warehouse stock inventory

## Usage:
1. Run analysis with these files in the Shopify Tool
2. Test packing list generation
3. Test stock export generation

## Regenerate:
To regenerate these files, run:
```
python scripts/create_test_data.py
```

## Notes:
- Order #1003 has "Priority" tag for testing rules
- Order #1005 has "Repeat" tag for testing repeat orders
- SKU "07" is included for testing exclude_skus functionality
- Stock levels vary to test low stock alerts
"""

    readme_path = Path("data/test_input/README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print(f"  ✓ Created: {readme_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("CREATING TEST DATA FILES")
    print("=" * 60)
    print()

    try:
        create_test_orders()
        create_test_stock()
        create_readme()

        print()
        print("=" * 60)
        print("✅ TEST DATA CREATED SUCCESSFULLY")
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
        print(f"❌ Error creating test data: {e}")
        import traceback
        traceback.print_exc()
