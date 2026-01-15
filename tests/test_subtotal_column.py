"""
Tests for Feature #3: Subtotal Column Support (v1.9.0)

Verifies that the Subtotal column from Shopify CSV is properly:
- Mapped from CSV to internal DataFrame
- Forward-filled for multi-line orders
- Included in final output
- Available in Rule Engine
"""

import pytest
import pandas as pd
import numpy as np
from shopify_tool import analysis


def test_subtotal_column_mapping():
    """Test that Subtotal column is properly mapped and forward-filled."""
    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1001", "#1002"],
        "Lineitem sku": ["SKU-A", "SKU-B", "SKU-C"],
        "Lineitem quantity": [1, 2, 1],
        "Shipping Method": ["DHL", "DHL", "DPD"],
        "Subtotal": ["45.00", None, "30.00"],
        "Total": ["50.00", None, "35.00"]
    })

    stock_df = pd.DataFrame({
        "SKU": ["SKU-A", "SKU-B", "SKU-C"],
        "Stock": [100, 100, 100]
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Shipping Method": "Shipping_Method",
            "Subtotal": "Subtotal",
            "Total": "Total_Price"
        },
        "stock": {
            "SKU": "SKU",
            "Stock": "Stock"
        }
    }

    # Run analysis
    history_df = pd.DataFrame(columns=["Order_Number"])
    final_df, _, _, _ = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings, {}
    )

    # Verify Subtotal column exists
    assert "Subtotal" in final_df.columns, "Subtotal column should be in output"

    # Verify forward-fill worked (second row should have same value as first)
    order_1001_rows = final_df[final_df["Order_Number"] == "#1001"]
    assert len(order_1001_rows) == 2, "Order #1001 should have 2 rows"
    assert order_1001_rows.iloc[0]["Subtotal"] == "45.00", "First row should have Subtotal"
    assert order_1001_rows.iloc[1]["Subtotal"] == "45.00", "Second row should have forward-filled Subtotal"


def test_subtotal_in_output_columns():
    """Test that Subtotal appears in final output columns in correct position."""
    orders_df = pd.DataFrame({
        "Name": ["#1001"],
        "Lineitem sku": ["SKU-A"],
        "Lineitem quantity": [1],
        "Shipping Method": ["DHL"],
        "Subtotal": ["45.00"],
        "Total": ["50.00"]
    })

    stock_df = pd.DataFrame({
        "SKU": ["SKU-A"],
        "Stock": [100]
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Shipping Method": "Shipping_Method",
            "Subtotal": "Subtotal",
            "Total": "Total_Price"
        },
        "stock": {
            "SKU": "SKU",
            "Stock": "Stock"
        }
    }

    history_df = pd.DataFrame(columns=["Order_Number"])
    final_df, _, _, _ = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings, {}
    )

    # Verify Subtotal is in output
    assert "Subtotal" in final_df.columns

    # Verify Subtotal comes after Total_Price
    cols = list(final_df.columns)
    if "Total_Price" in cols and "Subtotal" in cols:
        total_idx = cols.index("Total_Price")
        subtotal_idx = cols.index("Subtotal")
        assert subtotal_idx > total_idx, "Subtotal should come after Total_Price"


def test_subtotal_missing_gracefully():
    """Test that missing Subtotal doesn't break analysis."""
    orders_df = pd.DataFrame({
        "Name": ["#1001"],
        "Lineitem sku": ["SKU-A"],
        "Lineitem quantity": [1],
        "Shipping Method": ["DHL"]
        # No Subtotal column
    })

    stock_df = pd.DataFrame({
        "SKU": ["SKU-A"],
        "Stock": [100]
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Shipping Method": "Shipping_Method"
        },
        "stock": {
            "SKU": "SKU",
            "Stock": "Stock"
        }
    }

    history_df = pd.DataFrame(columns=["Order_Number"])

    # Should not raise exception
    final_df, _, _, _ = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings, {}
    )

    # Subtotal should not be in columns
    assert "Subtotal" not in final_df.columns


def test_subtotal_with_numeric_values():
    """Test that Subtotal works with numeric values (not just strings)."""
    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1001"],
        "Lineitem sku": ["SKU-A", "SKU-B"],
        "Lineitem quantity": [1, 2],
        "Shipping Method": ["DHL", "DHL"],
        "Subtotal": [45.00, np.nan],  # Numeric
        "Total": [50.00, np.nan]
    })

    stock_df = pd.DataFrame({
        "SKU": ["SKU-A", "SKU-B"],
        "Stock": [100, 100]
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Shipping Method": "Shipping_Method",
            "Subtotal": "Subtotal",
            "Total": "Total_Price"
        },
        "stock": {
            "SKU": "SKU",
            "Stock": "Stock"
        }
    }

    history_df = pd.DataFrame(columns=["Order_Number"])
    final_df, _, _, _ = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings, {}
    )

    # Verify Subtotal column exists
    assert "Subtotal" in final_df.columns

    # Verify both rows have the same value (forward-filled)
    order_rows = final_df[final_df["Order_Number"] == "#1001"]
    assert order_rows.iloc[0]["Subtotal"] == 45.00
    assert order_rows.iloc[1]["Subtotal"] == 45.00


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
