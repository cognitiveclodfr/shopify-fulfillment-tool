import sys
import os
import json
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shopify_tool import packing_lists


def test_create_packing_list_minimal(tmp_path):
    """Tests the basic creation of a packing list with minimal data."""
    # Build a small DataFrame that matches the analysis_df shape
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Fulfillable"],
            "Order_Number": ["A1", "A1"],
            "SKU": ["S1", "S2"],
            "Product_Name": ["P1", "P2"],
            "Quantity": [1, 2],
            "Shipping_Provider": ["DHL", "DHL"],
            "Destination_Country": ["BG", ""],
        }
    )

    out_file = tmp_path / "packing_test.xlsx"
    packing_lists.create_packing_list(df, str(out_file), report_name="TestReport", filters=None)
    assert out_file.exists()


def test_create_packing_list_with_not_equals_filter(tmp_path):
    """
    Tests that a packing list can be correctly filtered with a '!=' operator.
    """
    # Build a DataFrame with different shipping providers
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Fulfillable", "Fulfillable", "Fulfillable", "Not Fulfillable"],
            "Order_Number": ["A1", "A2", "A3", "A4", "A5"],
            "SKU": ["S1", "S2", "S3", "S4", "S5"],
            "Product_Name": ["P1", "P2", "P3", "P4", "P5"],
            "Quantity": [1, 1, 1, 1, 1],
            "Shipping_Provider": ["DHL", "PostOne", "DPD", "DHL", "DHL"],
            "Destination_Country": ["BG", "US", "DE", "FR", "CA"],
        }
    )

    out_file = tmp_path / "packing_test_ne.xlsx"

    # Define a filter to exclude DHL
    filters = [{"field": "Shipping_Provider", "operator": "!=", "value": "DHL"}]

    packing_lists.create_packing_list(df, str(out_file), report_name="TestReportNE", filters=filters)

    assert out_file.exists()

    # Read the generated Excel file and verify its contents
    result_df = pd.read_excel(out_file)

    # The output should only contain the 'PostOne' and 'DPD' orders
    assert len(result_df) == 2
    assert "A2" in result_df["Order_Number"].values
    assert "A3" in result_df["Order_Number"].values
    assert "A1" not in result_df["Order_Number"].values
    assert "A4" not in result_df["Order_Number"].values
    assert "A5" not in result_df["Order_Number"].values  # Should be excluded due to status


def test_create_packing_list_with_exclude_skus(tmp_path):
    """
    Tests that exclude_skus parameter correctly excludes specified SKUs from packing list.
    """
    # Build a DataFrame with multiple SKUs
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Fulfillable", "Fulfillable", "Fulfillable"],
            "Order_Number": ["A1", "A1", "A2", "A2"],
            "SKU": ["SKU-001", "SKU-002", "SKU-001", "SKU-003"],
            "Product_Name": ["Product 1", "Product 2", "Product 1", "Product 3"],
            "Quantity": [1, 2, 1, 1],
            "Shipping_Provider": ["DHL", "DHL", "DHL", "DHL"],
            "Destination_Country": ["BG", "", "BG", ""],
        }
    )

    out_file = tmp_path / "packing_test_exclude.xlsx"

    # Exclude SKU-002 from the packing list
    exclude_skus = ["SKU-002"]

    packing_lists.create_packing_list(
        df, str(out_file), report_name="TestExclude", filters=None, exclude_skus=exclude_skus
    )

    assert out_file.exists()

    # Read the generated Excel file and verify its contents
    result_df = pd.read_excel(out_file)

    # SKU-002 should be excluded, leaving 3 items
    assert len(result_df) == 3
    assert "SKU-001" in result_df["SKU"].values
    assert "SKU-003" in result_df["SKU"].values
    assert "SKU-002" not in result_df["SKU"].values


def test_create_packing_list_with_multiple_exclude_skus(tmp_path):
    """
    Tests that multiple SKUs can be excluded at once.
    """
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable"] * 5,
            "Order_Number": ["A1", "A1", "A1", "A2", "A2"],
            "SKU": ["SKU-001", "SKU-002", "SKU-003", "SKU-004", "SKU-005"],
            "Product_Name": ["P1", "P2", "P3", "P4", "P5"],
            "Quantity": [1, 1, 1, 1, 1],
            "Shipping_Provider": ["DHL"] * 5,
            "Destination_Country": ["BG", "", "", "US", ""],
        }
    )

    out_file = tmp_path / "packing_test_multi_exclude.xlsx"

    # Exclude multiple SKUs
    exclude_skus = ["SKU-002", "SKU-004"]

    packing_lists.create_packing_list(
        df, str(out_file), report_name="TestMultiExclude", filters=None, exclude_skus=exclude_skus
    )

    assert out_file.exists()

    result_df = pd.read_excel(out_file)

    # Should have 3 items left (SKU-001, SKU-003, SKU-005)
    assert len(result_df) == 3
    assert "SKU-001" in result_df["SKU"].values
    assert "SKU-003" in result_df["SKU"].values
    assert "SKU-005" in result_df["SKU"].values
    assert "SKU-002" not in result_df["SKU"].values
    assert "SKU-004" not in result_df["SKU"].values


def test_create_packing_list_with_filters_and_exclude_skus(tmp_path):
    """
    Tests that filters and exclude_skus work together correctly.
    """
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable"] * 4 + ["Not Fulfillable"],
            "Order_Number": ["A1", "A1", "A2", "A2", "A3"],
            "SKU": ["SKU-001", "SKU-002", "SKU-001", "SKU-003", "SKU-004"],
            "Product_Name": ["P1", "P2", "P1", "P3", "P4"],
            "Quantity": [1, 1, 1, 1, 1],
            "Shipping_Provider": ["DHL", "DHL", "PostOne", "PostOne", "DHL"],
            "Destination_Country": ["BG", "", "US", "", "FR"],
        }
    )

    out_file = tmp_path / "packing_test_combined.xlsx"

    # Filter to only DHL and exclude SKU-002
    filters = [{"field": "Shipping_Provider", "operator": "==", "value": "DHL"}]
    exclude_skus = ["SKU-002"]

    packing_lists.create_packing_list(
        df, str(out_file), report_name="TestCombined", filters=filters, exclude_skus=exclude_skus
    )

    assert out_file.exists()

    result_df = pd.read_excel(out_file)

    # Should have only SKU-001 from order A1 (DHL + Fulfillable + not excluded)
    # A3 is not Fulfillable so excluded
    assert len(result_df) == 1
    assert result_df["SKU"].iloc[0] == "SKU-001"
    assert result_df["Order_Number"].iloc[0] == "A1"


def test_exclude_skus_with_numeric_types(tmp_path):
    """
    Tests that exclude_skus works correctly when SKU is stored as int/float in DataFrame.
    This is critical for cases like SKU "07" which might be stored as int 7.
    """
    # Create DataFrame with NUMERIC SKUs (as they might be stored in Excel/CSV)
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable"] * 5,
            "Order_Number": ["A1", "A1", "A2", "A2", "A2"],
            "SKU": [7, 123, 456, 7, 789],  # SKU as integers, including duplicate
            "Product_Name": ["Virtual Product", "Real Product 1", "Real Product 2", "Virtual Product", "Real Product 3"],
            "Quantity": [1, 2, 1, 1, 3],
            "Shipping_Provider": ["DHL"] * 5,
            "Destination_Country": ["BG", "", "US", "", "FR"],
        }
    )

    out_file = tmp_path / "packing_test_numeric_exclude.xlsx"

    # Exclude SKU "07" (passed as string, but stored as int 7 in DataFrame)
    exclude_skus = ["07", "789"]  # Also test excluding "789"

    packing_lists.create_packing_list(
        df, str(out_file), report_name="TestNumericExclude", filters=None, exclude_skus=exclude_skus
    )

    assert out_file.exists()

    result_df = pd.read_excel(out_file)

    # Should exclude all items with SKU 7 (even though we passed "07") and 789
    # Should keep only SKU 123 and 456
    assert len(result_df) == 2
    assert 123 in result_df["SKU"].values or "123" in result_df["SKU"].values
    assert 456 in result_df["SKU"].values or "456" in result_df["SKU"].values
    # Ensure 7 and 789 are NOT in results
    assert 7 not in result_df["SKU"].values and "7" not in result_df["SKU"].values and "07" not in result_df["SKU"].values
    assert 789 not in result_df["SKU"].values and "789" not in result_df["SKU"].values


# ============================================================================
# Tests for Configurable Fulfillment Status Filter
# ============================================================================


def test_fulfillment_filter_default_behavior(tmp_path):
    """Test backward compatibility - default filters to Fulfillable only."""
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Not Fulfillable", "Fulfillable"],
            "Order_Number": ["A1", "A2", "A3"],
            "SKU": ["S1", "S2", "S3"],
            "Product_Name": ["P1", "P2", "P3"],
            "Quantity": [1, 1, 1],
            "Shipping_Provider": ["DHL", "DHL", "DHL"],
            "Destination_Country": ["BG", "US", "DE"],
        }
    )

    out_file = tmp_path / "test_default.xlsx"

    # No config provided - should default to Fulfillable
    packing_lists.create_packing_list(df, str(out_file), report_name="TestDefault")

    assert out_file.exists()
    result_df = pd.read_excel(out_file)

    # Should only contain Fulfillable orders (A1 and A3)
    assert len(result_df) == 2
    assert "A1" in result_df["Order_Number"].values
    assert "A3" in result_df["Order_Number"].values
    assert "A2" not in result_df["Order_Number"].values


def test_fulfillment_filter_explicit_fulfillable(tmp_path):
    """Test explicit Fulfillable filter in config."""
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Not Fulfillable", "Fulfillable"],
            "Order_Number": ["A1", "A2", "A3"],
            "SKU": ["S1", "S2", "S3"],
            "Product_Name": ["P1", "P2", "P3"],
            "Quantity": [1, 1, 1],
            "Shipping_Provider": ["DHL", "DHL", "DHL"],
            "Destination_Country": ["BG", "US", "DE"],
        }
    )

    out_file = tmp_path / "test_explicit_fulfillable.xlsx"

    config = {"fulfillment_status_filter": {"enabled": True, "status": "Fulfillable"}}

    packing_lists.create_packing_list(df, str(out_file), report_name="TestExplicit", config=config)

    assert out_file.exists()
    result_df = pd.read_excel(out_file)

    # Should only contain Fulfillable orders
    assert len(result_df) == 2
    assert "A1" in result_df["Order_Number"].values
    assert "A3" in result_df["Order_Number"].values


def test_fulfillment_filter_not_fulfillable(tmp_path):
    """Test filtering for NOT Fulfillable orders."""
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Not Fulfillable", "Fulfillable", "Not Fulfillable"],
            "Order_Number": ["A1", "A2", "A3", "A4"],
            "SKU": ["S1", "S2", "S3", "S4"],
            "Product_Name": ["P1", "P2", "P3", "P4"],
            "Quantity": [1, 1, 1, 1],
            "Shipping_Provider": ["DHL", "DHL", "DHL", "DHL"],
            "Destination_Country": ["BG", "US", "DE", "FR"],
        }
    )

    out_file = tmp_path / "test_not_fulfillable.xlsx"

    config = {"fulfillment_status_filter": {"enabled": True, "status": "Not Fulfillable"}}

    packing_lists.create_packing_list(df, str(out_file), report_name="TestNotFulfillable", config=config)

    assert out_file.exists()
    result_df = pd.read_excel(out_file)

    # Should only contain Not Fulfillable orders (A2 and A4)
    assert len(result_df) == 2
    assert "A2" in result_df["Order_Number"].values
    assert "A4" in result_df["Order_Number"].values
    assert "A1" not in result_df["Order_Number"].values
    assert "A3" not in result_df["Order_Number"].values


def test_fulfillment_filter_disabled(tmp_path):
    """Test disabled filter - should include ALL orders."""
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Not Fulfillable", "Fulfillable"],
            "Order_Number": ["A1", "A2", "A3"],
            "SKU": ["S1", "S2", "S3"],
            "Product_Name": ["P1", "P2", "P3"],
            "Quantity": [1, 1, 1],
            "Shipping_Provider": ["DHL", "DHL", "DHL"],
            "Destination_Country": ["BG", "US", "DE"],
        }
    )

    out_file = tmp_path / "test_disabled.xlsx"

    config = {"fulfillment_status_filter": {"enabled": False}}

    packing_lists.create_packing_list(df, str(out_file), report_name="TestDisabled", config=config)

    assert out_file.exists()
    result_df = pd.read_excel(out_file)

    # Should contain ALL orders
    assert len(result_df) == 3
    assert "A1" in result_df["Order_Number"].values
    assert "A2" in result_df["Order_Number"].values
    assert "A3" in result_df["Order_Number"].values


def test_fulfillment_filter_multiple_statuses(tmp_path):
    """Test filtering for multiple statuses (OR logic)."""
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Not Fulfillable", "Partial", "Fulfillable"],
            "Order_Number": ["A1", "A2", "A3", "A4"],
            "SKU": ["S1", "S2", "S3", "S4"],
            "Product_Name": ["P1", "P2", "P3", "P4"],
            "Quantity": [1, 1, 1, 1],
            "Shipping_Provider": ["DHL", "DHL", "DHL", "DHL"],
            "Destination_Country": ["BG", "US", "DE", "FR"],
        }
    )

    out_file = tmp_path / "test_multiple.xlsx"

    config = {"fulfillment_status_filter": {"enabled": True, "status": ["Fulfillable", "Partial"]}}

    packing_lists.create_packing_list(df, str(out_file), report_name="TestMultiple", config=config)

    assert out_file.exists()
    result_df = pd.read_excel(out_file)

    # Should contain Fulfillable and Partial orders (A1, A3, A4)
    assert len(result_df) == 3
    assert "A1" in result_df["Order_Number"].values
    assert "A3" in result_df["Order_Number"].values
    assert "A4" in result_df["Order_Number"].values
    assert "A2" not in result_df["Order_Number"].values


def test_fulfillment_filter_with_additional_filters(tmp_path):
    """Test fulfillment filter combined with other filters."""
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Not Fulfillable", "Fulfillable", "Fulfillable"],
            "Order_Number": ["A1", "A2", "A3", "A4"],
            "SKU": ["S1", "S2", "S3", "S4"],
            "Product_Name": ["P1", "P2", "P3", "P4"],
            "Quantity": [1, 1, 1, 1],
            "Shipping_Provider": ["DHL", "DHL", "PostOne", "DHL"],
            "Destination_Country": ["BG", "US", "DE", "FR"],
        }
    )

    out_file = tmp_path / "test_combined_filters.xlsx"

    config = {"fulfillment_status_filter": {"enabled": True, "status": "Fulfillable"}}
    filters = [{"field": "Shipping_Provider", "operator": "==", "value": "DHL"}]

    packing_lists.create_packing_list(df, str(out_file), report_name="TestCombined", filters=filters, config=config)

    assert out_file.exists()
    result_df = pd.read_excel(out_file)

    # Should only contain Fulfillable + DHL orders (A1 and A4)
    assert len(result_df) == 2
    assert "A1" in result_df["Order_Number"].values
    assert "A4" in result_df["Order_Number"].values
    assert "A2" not in result_df["Order_Number"].values  # Not Fulfillable
    assert "A3" not in result_df["Order_Number"].values  # PostOne


def test_build_fulfillment_filter_helper():
    """Test the _build_fulfillment_filter helper function directly."""
    # Test default behavior (empty config)
    assert packing_lists._build_fulfillment_filter({}) == ["Order_Fulfillment_Status == 'Fulfillable'"]

    # Test explicit Fulfillable
    config = {"fulfillment_status_filter": {"enabled": True, "status": "Fulfillable"}}
    assert packing_lists._build_fulfillment_filter(config) == ["Order_Fulfillment_Status == 'Fulfillable'"]

    # Test Not Fulfillable
    config = {"fulfillment_status_filter": {"enabled": True, "status": "Not Fulfillable"}}
    assert packing_lists._build_fulfillment_filter(config) == ["Order_Fulfillment_Status == 'Not Fulfillable'"]

    # Test disabled filter
    config = {"fulfillment_status_filter": {"enabled": False}}
    assert packing_lists._build_fulfillment_filter(config) == []

    # Test multiple statuses
    config = {"fulfillment_status_filter": {"enabled": True, "status": ["Fulfillable", "Partial"]}}
    assert packing_lists._build_fulfillment_filter(config) == ["Order_Fulfillment_Status in ['Fulfillable', 'Partial']"]
