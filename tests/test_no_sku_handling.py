"""
Tests for Feature #1: Handle Orders Without SKU (v1.9.0)

Verifies that orders without SKU:
- Are kept in the analysis (not dropped)
- Are tagged with "NO_SKU" placeholder
- Have Has_SKU field set correctly
- Don't participate in stock simulation
- Are marked as Not Fulfillable
- Are available in Rule Engine
"""

import pytest
import pandas as pd
from shopify_tool import analysis


def test_orders_without_sku_are_kept():
    """Test that orders without SKU are tagged but not dropped."""
    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1001", "#1002"],
        "Lineitem sku": ["HAT-001", None, "GLOVE-02"],
        "Lineitem quantity": [1, 0, 2],
        "Lineitem name": ["Red Hat", "Shipping Fee", "Blue Gloves"],
        "Shipping Method": ["DHL", "DHL", "DPD"]
    })

    stock_df = pd.DataFrame({
        "SKU": ["HAT-001", "GLOVE-02"],
        "Stock": [10, 20]
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Lineitem name": "Product_Name",
            "Shipping Method": "Shipping_Method"
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

    # Should have 3 rows (not dropped)
    assert len(final_df) == 3, "All 3 rows should be kept"

    # Has_SKU column should exist
    assert "Has_SKU" in final_df.columns, "Has_SKU column should exist"

    # Second row should be marked as NO_SKU
    second_row = final_df.iloc[1]
    assert second_row["Has_SKU"] == False, "Second row should have Has_SKU=False"
    assert second_row["SKU"] == "NO_SKU", "Second row should have SKU=NO_SKU"


def test_no_sku_items_marked_not_fulfillable():
    """Test that NO_SKU items are marked as Not Fulfillable in final DF."""
    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1001"],
        "Lineitem sku": ["HAT-001", None],
        "Lineitem quantity": [1, 0],
        "Lineitem name": ["Red Hat", "Shipping"],
        "Shipping Method": ["DHL", "DHL"]
    })

    stock_df = pd.DataFrame({
        "SKU": ["HAT-001"],
        "Stock": [10]
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Lineitem name": "Product_Name",
            "Shipping Method": "Shipping_Method"
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

    # Find NO_SKU row
    no_sku_row = final_df[final_df["SKU"] == "NO_SKU"].iloc[0]

    # Verify it's marked as Not Fulfillable
    assert no_sku_row["Order_Fulfillment_Status"] == "Not Fulfillable", \
        "NO_SKU items should be Not Fulfillable"

    # Verify [NO_SKU] tag in System_note
    assert "[NO_SKU]" in no_sku_row["System_note"], \
        "NO_SKU items should have [NO_SKU] tag in System_note"


def test_no_sku_items_dont_block_order_fulfillment():
    """Test that NO_SKU items don't prevent order fulfillment."""
    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1001"],
        "Lineitem sku": ["HAT-001", None],
        "Lineitem quantity": [1, 0],
        "Lineitem name": ["Red Hat", "Shipping"],
        "Shipping Method": ["DHL", "DHL"]
    })

    stock_df = pd.DataFrame({
        "SKU": ["HAT-001"],
        "Stock": [10]
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Lineitem name": "Product_Name",
            "Shipping Method": "Shipping_Method"
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

    # The actual SKU item should be Fulfillable
    hat_row = final_df[final_df["SKU"] == "HAT-001"].iloc[0]
    assert hat_row["Order_Fulfillment_Status"] == "Fulfillable", \
        "Regular item should be Fulfillable (NO_SKU doesn't block it)"


def test_no_sku_with_descriptive_product_name():
    """Test that NO_SKU items get descriptive product name."""
    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1001"],
        "Lineitem sku": ["HAT-001", None],
        "Lineitem quantity": [1, 0],
        "Lineitem name": ["Red Hat", None],  # Missing product name
        "Shipping Method": ["DHL", "DHL"]
    })

    stock_df = pd.DataFrame({
        "SKU": ["HAT-001"],
        "Stock": [10]
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Lineitem name": "Product_Name",
            "Shipping Method": "Shipping_Method"
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

    # Find NO_SKU row
    no_sku_row = final_df[final_df["SKU"] == "NO_SKU"].iloc[0]

    # Should have descriptive product name
    assert "No SKU" in no_sku_row["Product_Name"], \
        "NO_SKU items should have descriptive product name"


def test_multiple_no_sku_items():
    """Test handling multiple NO_SKU items in same order."""
    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1001", "#1001", "#1001"],
        "Lineitem sku": ["HAT-001", None, None, "GLOVE-02"],
        "Lineitem quantity": [1, 0, 0, 1],
        "Lineitem name": ["Red Hat", "Shipping", "Discount", "Blue Gloves"],
        "Shipping Method": ["DHL", "DHL", "DHL", "DHL"]
    })

    stock_df = pd.DataFrame({
        "SKU": ["HAT-001", "GLOVE-02"],
        "Stock": [10, 10]
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Lineitem name": "Product_Name",
            "Shipping Method": "Shipping_Method"
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

    # Should have 4 rows
    assert len(final_df) == 4, "All 4 rows should be kept"

    # Find NO_SKU rows
    no_sku_rows = final_df[final_df["SKU"] == "NO_SKU"]
    assert len(no_sku_rows) == 2, "Should have 2 NO_SKU rows"

    # Both should be marked as Not Fulfillable
    assert all(no_sku_rows["Order_Fulfillment_Status"] == "Not Fulfillable")

    # Real items should be Fulfillable
    real_items = final_df[final_df["SKU"] != "NO_SKU"]
    assert all(real_items["Order_Fulfillment_Status"] == "Fulfillable")


def test_no_sku_doesnt_affect_stock_simulation():
    """Test that NO_SKU items don't consume stock."""
    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1001", "#1002"],
        "Lineitem sku": ["HAT-001", None, "HAT-001"],
        "Lineitem quantity": [5, 0, 5],
        "Lineitem name": ["Red Hat", "Shipping", "Red Hat"],
        "Shipping Method": ["DHL", "DHL", "DHL"]
    })

    stock_df = pd.DataFrame({
        "SKU": ["HAT-001"],
        "Stock": [10]  # Only 10 available
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Lineitem name": "Product_Name",
            "Shipping Method": "Shipping_Method"
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

    # Both orders should be Fulfillable (10 stock = 5 + 5, NO_SKU doesn't consume)
    hat_rows = final_df[final_df["SKU"] == "HAT-001"]
    assert all(hat_rows["Order_Fulfillment_Status"] == "Fulfillable"), \
        "Both HAT orders should be fulfillable (NO_SKU doesn't consume stock)"


def test_no_sku_with_set_expansion():
    """Test that NO_SKU items are skipped during set expansion."""
    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1001"],
        "Lineitem sku": ["SET-001", None],
        "Lineitem quantity": [1, 0],
        "Lineitem name": ["Gift Set", "Shipping"],
        "Shipping Method": ["DHL", "DHL"]
    })

    stock_df = pd.DataFrame({
        "SKU": ["HAT-001", "GLOVE-02"],
        "Stock": [10, 10]
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Lineitem name": "Product_Name",
            "Shipping Method": "Shipping_Method"
        },
        "stock": {
            "SKU": "SKU",
            "Stock": "Stock"
        },
        "set_decoders": {
            "SET-001": [
                {"sku": "HAT-001", "quantity": 1},
                {"sku": "GLOVE-02", "quantity": 1}
            ]
        }
    }

    history_df = pd.DataFrame(columns=["Order_Number"])

    final_df, _, _, _ = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings, {}
    )

    # Set should be expanded (2 components)
    # NO_SKU should remain as 1 row
    # Total: 3 rows (HAT-001, GLOVE-02, NO_SKU)
    assert len(final_df) == 3, "Should have 3 rows (2 set components + NO_SKU)"

    # Verify NO_SKU row exists
    no_sku_rows = final_df[final_df["SKU"] == "NO_SKU"]
    assert len(no_sku_rows) == 1, "Should have 1 NO_SKU row"


def test_has_sku_field_in_output():
    """Test that Has_SKU field appears in final output."""
    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1001"],
        "Lineitem sku": ["HAT-001", None],
        "Lineitem quantity": [1, 0],
        "Shipping Method": ["DHL", "DHL"]
    })

    stock_df = pd.DataFrame({
        "SKU": ["HAT-001"],
        "Stock": [10]
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

    final_df, _, _, _ = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings, {}
    )

    # Has_SKU should be in output columns
    assert "Has_SKU" in final_df.columns, "Has_SKU should be in output"

    # Verify values are correct
    hat_row = final_df[final_df["SKU"] == "HAT-001"].iloc[0]
    no_sku_row = final_df[final_df["SKU"] == "NO_SKU"].iloc[0]

    assert hat_row["Has_SKU"] == True, "HAT-001 should have Has_SKU=True"
    assert no_sku_row["Has_SKU"] == False, "NO_SKU should have Has_SKU=False"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
