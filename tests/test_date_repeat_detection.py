"""
Tests for Feature #2: Date-Based Repeat Detection (v1.9.0)

Verifies that repeat detection:
- Filters history by configurable time window
- Only marks orders within the window as "Repeat"
- Falls back gracefully for old history without dates
- Handles invalid dates correctly
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from shopify_tool import analysis


def test_repeat_detection_with_1_day_window():
    """Test that only yesterday's orders are marked as repeat with 1-day window."""
    orders_df = pd.DataFrame({
        "Order_Number": ["#1001", "#1002", "#1003"],
        "SKU": ["SKU-A", "SKU-B", "SKU-C"]
    })

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    history_df = pd.DataFrame({
        "Order_Number": ["#1001", "#1002"],
        "Execution_Date": [yesterday, week_ago]
    })

    # Test with 1 day window
    result = analysis._detect_repeated_orders(orders_df, history_df, repeat_window_days=1)

    # Only #1001 should be marked as Repeat (within 1 day)
    assert (result == "Repeat").sum() == 1, "Only 1 order should be repeat"
    assert result.iloc[0] == "Repeat", "#1001 should be repeat"
    assert result.iloc[1] == "", "#1002 should NOT be repeat (>1 day ago)"
    assert result.iloc[2] == "", "#1003 should NOT be repeat (not in history)"


def test_repeat_detection_with_7_day_window():
    """Test that 7-day window includes week-old orders."""
    orders_df = pd.DataFrame({
        "Order_Number": ["#1001", "#1002", "#1003"],
        "SKU": ["SKU-A", "SKU-B", "SKU-C"]
    })

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    history_df = pd.DataFrame({
        "Order_Number": ["#1001", "#1002", "#1003"],
        "Execution_Date": [yesterday, week_ago, month_ago]
    })

    # Test with 7 day window
    result = analysis._detect_repeated_orders(orders_df, history_df, repeat_window_days=7)

    # #1001 and #1002 should be marked (within 7 days)
    assert (result == "Repeat").sum() == 2, "2 orders should be repeat"
    assert result.iloc[0] == "Repeat", "#1001 should be repeat"
    assert result.iloc[1] == "Repeat", "#1002 should be repeat"
    assert result.iloc[2] == "", "#1003 should NOT be repeat (>7 days)"


def test_repeat_detection_with_30_day_window():
    """Test that 30-day window includes month-old orders."""
    orders_df = pd.DataFrame({
        "Order_Number": ["#1001", "#1002", "#1003"],
        "SKU": ["SKU-A", "SKU-B", "SKU-C"]
    })

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    history_df = pd.DataFrame({
        "Order_Number": ["#1001", "#1002", "#1003"],
        "Execution_Date": [yesterday, week_ago, month_ago]
    })

    # Test with 30 day window
    result = analysis._detect_repeated_orders(orders_df, history_df, repeat_window_days=30)

    # All 3 should be marked (within 30 days)
    assert (result == "Repeat").sum() == 3, "All 3 orders should be repeat"
    assert result.iloc[0] == "Repeat"
    assert result.iloc[1] == "Repeat"
    assert result.iloc[2] == "Repeat"


def test_repeat_detection_backward_compatibility():
    """Test fallback when Execution_Date column is missing (old history format)."""
    orders_df = pd.DataFrame({
        "Order_Number": ["#1001", "#1002"],
        "SKU": ["SKU-A", "SKU-B"]
    })

    # Old history format (no Execution_Date column)
    history_df = pd.DataFrame({
        "Order_Number": ["#1001"]
    })

    # Should still work with full history fallback
    result = analysis._detect_repeated_orders(orders_df, history_df, repeat_window_days=1)

    # Should use full history (backward compatible)
    assert (result == "Repeat").sum() == 1
    assert result.iloc[0] == "Repeat", "#1001 should be repeat (fallback mode)"
    assert result.iloc[1] == "", "#1002 should NOT be repeat"


def test_repeat_detection_with_invalid_dates():
    """Test that invalid dates fall back to full history."""
    orders_df = pd.DataFrame({
        "Order_Number": ["#1001"],
        "SKU": ["SKU-A"]
    })

    history_df = pd.DataFrame({
        "Order_Number": ["#1001"],
        "Execution_Date": ["INVALID_DATE"]
    })

    # Should handle gracefully with fallback to full history
    result = analysis._detect_repeated_orders(orders_df, history_df, repeat_window_days=1)

    # Should use fallback (full history) due to invalid date
    assert (result == "Repeat").sum() == 1


def test_repeat_detection_with_empty_history():
    """Test that empty history returns no repeats."""
    orders_df = pd.DataFrame({
        "Order_Number": ["#1001", "#1002"],
        "SKU": ["SKU-A", "SKU-B"]
    })

    history_df = pd.DataFrame(columns=["Order_Number", "Execution_Date"])

    result = analysis._detect_repeated_orders(orders_df, history_df, repeat_window_days=1)

    # No repeats (empty history)
    assert (result == "Repeat").sum() == 0
    assert all(result == "")


def test_repeat_detection_with_mixed_date_formats():
    """Test that different valid date formats are handled."""
    orders_df = pd.DataFrame({
        "Order_Number": ["#1001", "#1002", "#1003"],
        "SKU": ["SKU-A", "SKU-B", "SKU-C"]
    })

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_alt = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    history_df = pd.DataFrame({
        "Order_Number": ["#1001", "#1002", "#1003"],
        "Execution_Date": [yesterday, yesterday_alt, week_ago]
    })

    # Test with 2 day window (should catch both yesterday formats)
    result = analysis._detect_repeated_orders(orders_df, history_df, repeat_window_days=2)

    # At least #1001 should be marked (valid ISO format)
    assert result.iloc[0] == "Repeat"


def test_repeat_detection_integration_with_run_analysis():
    """Test that repeat_window_days parameter works through run_analysis."""
    orders_df = pd.DataFrame({
        "Name": ["#1001", "#1002"],
        "Lineitem sku": ["SKU-A", "SKU-B"],
        "Lineitem quantity": [1, 1],
        "Shipping Method": ["DHL", "DHL"]
    })

    stock_df = pd.DataFrame({
        "SKU": ["SKU-A", "SKU-B"],
        "Stock": [100, 100]
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
            "Shipping Method": "Shipping_Method"
        },
        "stock": {
            "SKU": "SKU",
            "Stock": "Stock"
        }
    }

    # Test with 1 day window
    final_df, _, _, _ = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings, {},
        repeat_window_days=1
    )

    # Only #1001 should have "Repeat" in System_note
    order_1001 = final_df[final_df["Order_Number"] == "#1001"]
    order_1002 = final_df[final_df["Order_Number"] == "#1002"]

    assert "Repeat" in order_1001.iloc[0]["System_note"], "#1001 should be marked as Repeat"
    assert "Repeat" not in order_1002.iloc[0]["System_note"], "#1002 should NOT be marked as Repeat"

    # Test with 7 day window
    final_df_7d, _, _, _ = analysis.run_analysis(
        stock_df, orders_df, history_df, column_mappings, {},
        repeat_window_days=7
    )

    # Both should have "Repeat" in System_note
    order_1001_7d = final_df_7d[final_df_7d["Order_Number"] == "#1001"]
    order_1002_7d = final_df_7d[final_df_7d["Order_Number"] == "#1002"]

    assert "Repeat" in order_1001_7d.iloc[0]["System_note"]
    assert "Repeat" in order_1002_7d.iloc[0]["System_note"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
