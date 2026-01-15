"""
Integration Test for v1.9.0 Phase 1 Features

Tests all 3 features working together:
- Feature #3: Subtotal Column Support
- Feature #2: Date-Based Repeat Detection
- Feature #1: Handle Orders Without SKU
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from shopify_tool import analysis


def test_all_v1_9_0_features_together():
    """Integration test for all Phase 1 features working together."""

    # Create test data with all features:
    # - Subtotal column
    # - NO_SKU rows (shipping fees)
    # - Multiple orders for repeat detection
    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1001", "#1001", "#1002", "#1002"],
        "Lineitem sku": ["HAT-001", "GLOVE-02", None, "HAT-001", None],
        "Lineitem quantity": [1, 2, 0, 1, 0],
        "Lineitem name": ["Red Hat", "Blue Gloves", "Shipping", "Red Hat", "Shipping"],
        "Shipping Method": ["DHL", "DHL", "DHL", "DPD", "DPD"],
        "Subtotal": ["45.00", None, None, "30.00", None],
        "Total": ["50.00", None, None, "35.00", None]
    })

    stock_df = pd.DataFrame({
        "SKU": ["HAT-001", "GLOVE-02"],
        "Stock": [100, 50]
    })

    # Create history with dates for repeat detection
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    history_df = pd.DataFrame({
        "Order_Number": ["#1001", "#1002"],
        "Execution_Date": [yesterday, week_ago]
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Lineitem name": "Product_Name",
            "Shipping Method": "Shipping_Method",
            "Subtotal": "Subtotal",
            "Total": "Total_Price"
        },
        "stock": {
            "SKU": "SKU",
            "Stock": "Stock"
        }
    }

    # Run full analysis with 1-day repeat window
    final_df, summary_present, summary_missing, stats = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings, {},
        repeat_window_days=1
    )

    # ===== Verify Feature #3: Subtotal column =====
    assert "Subtotal" in final_df.columns, "Subtotal column should be present"

    # Check forward-fill for order #1001
    order_1001 = final_df[final_df["Order_Number"] == "#1001"]
    assert len(order_1001) == 3, "Order #1001 should have 3 rows"
    # All rows should have same Subtotal (forward-filled)
    assert order_1001.iloc[0]["Subtotal"] == "45.00"
    assert order_1001.iloc[1]["Subtotal"] == "45.00"
    assert order_1001.iloc[2]["Subtotal"] == "45.00"

    # ===== Verify Feature #1: NO_SKU handling =====
    assert "Has_SKU" in final_df.columns, "Has_SKU column should be present"

    # Should have 5 rows total (not dropped)
    assert len(final_df) == 5, "All 5 rows should be kept (including NO_SKU)"

    # Find NO_SKU rows
    no_sku_rows = final_df[final_df["SKU"] == "NO_SKU"]
    assert len(no_sku_rows) == 2, "Should have 2 NO_SKU rows (shipping fees)"

    # NO_SKU rows should be marked as Not Fulfillable
    assert all(no_sku_rows["Order_Fulfillment_Status"] == "Not Fulfillable"), \
        "NO_SKU rows should be Not Fulfillable"

    # NO_SKU rows should have [NO_SKU] tag
    assert all(no_sku_rows["System_note"].str.contains("[NO_SKU]")), \
        "NO_SKU rows should have [NO_SKU] tag"

    # Real items should be Fulfillable
    real_items = final_df[final_df["SKU"] != "NO_SKU"]
    assert all(real_items["Order_Fulfillment_Status"] == "Fulfillable"), \
        "Real items should be Fulfillable"

    # ===== Verify Feature #2: Date-based repeat detection =====

    # Order #1001 was fulfilled yesterday (>= 1 day ago with 1-day window)
    order_1001_notes = order_1001["System_note"].unique()
    assert any("Repeat" in str(note) for note in order_1001_notes), \
        "#1001 should be marked as Repeat (>= 1 day ago)"

    # Order #1002 was fulfilled 7 days ago (>= 1 day ago, should be Repeat)
    order_1002 = final_df[final_df["Order_Number"] == "#1002"]
    order_1002_notes = order_1002["System_note"].unique()
    # Should have Repeat (>= 1 day ago)
    # Note: NO_SKU will have [NO_SKU], real items should have Repeat
    real_item_1002 = order_1002[order_1002["SKU"] != "NO_SKU"]
    assert any("Repeat" in str(note) for note in real_item_1002["System_note"]), \
        "#1002 should be marked as Repeat (>= 1 day ago)"


def test_v1_9_0_with_7_day_window():
    """Test that changing repeat window affects results correctly."""

    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1002"],
        "Lineitem sku": ["HAT-001", "GLOVE-02"],
        "Lineitem quantity": [1, 1],
        "Shipping Method": ["DHL", "DPD"],
        "Subtotal": ["45.00", "30.00"]
    })

    stock_df = pd.DataFrame({
        "SKU": ["HAT-001", "GLOVE-02"],
        "Stock": [100, 50]
    })

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    history_df = pd.DataFrame({
        "Order_Number": ["#1001", "#1002"],
        "Execution_Date": [yesterday, week_ago]
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Shipping Method": "Shipping_Method",
            "Subtotal": "Subtotal"
        },
        "stock": {
            "SKU": "SKU",
            "Stock": "Stock"
        }
    }

    # Test with 7-day window
    final_df_7d, _, _, _ = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings, {},
        repeat_window_days=7
    )

    # #1001 (yesterday, 1 day ago) should NOT be Repeat (< 7 days)
    # #1002 (week ago, 7 days ago) should be Repeat (>= 7 days)
    assert "Repeat" not in final_df_7d[final_df_7d["Order_Number"] == "#1001"].iloc[0]["System_note"], \
        "#1001 (1 day ago) should NOT be Repeat with 7-day window"
    assert "Repeat" in final_df_7d[final_df_7d["Order_Number"] == "#1002"].iloc[0]["System_note"], \
        "#1002 (7 days ago) should be Repeat with 7-day window"


def test_v1_9_0_backward_compatibility():
    """Test that all features are backward compatible with old data."""

    # Test with minimal data (no Subtotal, no Execution_Date, no NO_SKU)
    orders_df = pd.DataFrame({
        "Name": ["#1001"],
        "Lineitem sku": ["HAT-001"],
        "Lineitem quantity": [1],
        "Shipping Method": ["DHL"]
        # No Subtotal column
    })

    stock_df = pd.DataFrame({
        "SKU": ["HAT-001"],
        "Stock": [100]
    })

    # Old history format (no Execution_Date)
    history_df = pd.DataFrame({
        "Order_Number": []
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

    # Should not raise exception
    final_df, _, _, _ = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings, {},
        repeat_window_days=1
    )

    # Should complete successfully
    assert len(final_df) == 1
    assert final_df.iloc[0]["Order_Fulfillment_Status"] == "Fulfillable"

    # Subtotal should not be in columns (backward compatible)
    assert "Subtotal" not in final_df.columns


def test_v1_9_0_summary_reports_exclude_no_sku():
    """Test that summary reports correctly handle NO_SKU items."""

    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1001", "#1002"],
        "Lineitem sku": ["HAT-001", None, "GLOVE-02"],
        "Lineitem quantity": [2, 0, 3],
        "Lineitem name": ["Red Hat", "Shipping", "Blue Gloves"],
        "Shipping Method": ["DHL", "DHL", "DPD"]
    })

    stock_df = pd.DataFrame({
        "SKU": ["HAT-001", "GLOVE-02"],
        "Stock": [100, 50]
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

    final_df, summary_present, summary_missing, stats = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings, {}
    )

    # Summary should only include real items (not NO_SKU)
    assert "NO_SKU" not in summary_present["SKU"].values, \
        "Summary should not include NO_SKU items"

    # Should have 2 SKUs in summary (HAT-001, GLOVE-02)
    assert len(summary_present) == 2


def test_v1_9_0_stats_generation():
    """Test that statistics are correctly generated with new features."""

    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1001", "#1002", "#1002"],
        "Lineitem sku": ["HAT-001", None, "OUT-OF-STOCK", None],
        "Lineitem quantity": [1, 0, 1, 0],
        "Lineitem name": ["Red Hat", "Shipping", "Special Item", "Shipping"],
        "Shipping Method": ["DHL", "DHL", "DPD", "DPD"],
        "Subtotal": ["45.00", None, "100.00", None]
    })

    stock_df = pd.DataFrame({
        "SKU": ["HAT-001", "OUT-OF-STOCK"],
        "Stock": [10, 0]  # OUT-OF-STOCK has 0 stock
    })

    column_mappings = {
        "orders": {
            "Name": "Order_Number",
            "Lineitem sku": "SKU",
            "Lineitem quantity": "Quantity",
            "Lineitem name": "Product_Name",
            "Shipping Method": "Shipping_Method",
            "Subtotal": "Subtotal"
        },
        "stock": {
            "SKU": "SKU",
            "Stock": "Stock"
        }
    }

    history_df = pd.DataFrame(columns=["Order_Number"])

    final_df, _, _, stats = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings, {}
    )

    # Stats should be generated correctly
    assert "total_orders_completed" in stats
    assert "total_orders_not_completed" in stats

    # Both orders have NO_SKU items marked as "Not Fulfillable"
    # Stats count orders with ANY not fulfillable line
    # Since both #1001 and #1002 have NO_SKU items, both show up in not_completed
    # This is expected behavior - NO_SKU items affect order-level stats
    assert stats["total_orders_not_completed"] >= 1  # At least #1002 (out of stock)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
