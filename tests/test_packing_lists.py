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
