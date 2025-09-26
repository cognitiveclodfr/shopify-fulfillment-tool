import sys
import os
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shopify_tool import stock_export


@pytest.fixture
def sample_analysis_df():
    """Provides a sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "Order_Fulfillment_Status": [
                "Fulfillable",
                "Fulfillable",
                "Fulfillable",
                "Not Fulfillable",
                "Fulfillable",
            ],
            "SKU": ["SKU-A", "SKU-B", "SKU-A", "SKU-C", "SKU-D"],
            "Quantity": [5, 3, 2, 10, 0],
            "Order_Type": ["Single", "Multi", "Single", "Single", "Multi"],
        }
    )


def test_create_stock_export_success(tmp_path, sample_analysis_df):
    """Tests the successful creation and content of a stock export file."""
    output_path = tmp_path / "stock_export_out.xls"

    stock_export.create_stock_export(sample_analysis_df, str(output_path))

    assert os.path.exists(output_path)

    # Read the output and validate its content
    result_df = pd.read_excel(output_path)

    # Expected data: SKU-A: 5+2=7, SKU-B: 3. SKU-C is not fulfillable, SKU-D has 0 quantity.
    expected_data = {"Артикул": ["SKU-A", "SKU-B"], "Наличност": [7, 3]}
    expected_df = pd.DataFrame(expected_data)

    pd.testing.assert_frame_equal(
        result_df.sort_values(by="Артикул").reset_index(drop=True),
        expected_df.sort_values(by="Артикул").reset_index(drop=True),
    )


def test_create_stock_export_with_filters(tmp_path, sample_analysis_df):
    """Tests that filters are correctly applied before generating a stock export."""
    output_path = tmp_path / "output.xls"
    filters = [{"field": "Order_Type", "operator": "==", "value": "Single"}]

    stock_export.create_stock_export(sample_analysis_df, str(output_path), filters=filters)

    assert os.path.exists(output_path)
    result_df = pd.read_excel(output_path)

    # Should only contain SKU-A from single orders
    expected_data = {"Артикул": ["SKU-A"], "Наличност": [7]}
    expected_df = pd.DataFrame(expected_data)

    pd.testing.assert_frame_equal(result_df, expected_df)


def test_create_stock_export_empty_after_filter(tmp_path, sample_analysis_df):
    """Tests that an empty file with headers is created if filtering results in an empty dataset."""
    output_path = tmp_path / "output.xls"
    filters = [{"field": "Order_Type", "operator": "==", "value": "NonExistent"}]

    stock_export.create_stock_export(sample_analysis_df, str(output_path), filters=filters)

    assert os.path.exists(output_path)
    result_df = pd.read_excel(output_path)
    assert result_df.empty
    assert list(result_df.columns) == ["Артикул", "Наличност"]


def test_create_stock_export_no_fulfillable_items(tmp_path):
    """Tests that an empty file is created when no items are fulfillable."""
    df = pd.DataFrame({"Order_Fulfillment_Status": ["Not Fulfillable"], "SKU": ["S1"], "Quantity": [1]})
    output_path = tmp_path / "output.xls"

    stock_export.create_stock_export(df, str(output_path))

    assert os.path.exists(output_path)
    result_df = pd.read_excel(output_path)
    assert result_df.empty
    assert list(result_df.columns) == ["Артикул", "Наличност"]


def test_create_stock_export_skips_invalid_filter(tmp_path, sample_analysis_df, caplog):
    """Tests that an invalid filter object is skipped without crashing."""
    output_path = tmp_path / "output.xls"
    # This filter is missing the 'value' key
    filters = [{"field": "Order_Type", "operator": "=="}]

    stock_export.create_stock_export(sample_analysis_df, str(output_path), filters=filters)

    assert "Skipping invalid filter" in caplog.text
    # The report should be created as if there were no filters
    assert os.path.exists(output_path)
    result_df = pd.read_excel(output_path)
    assert len(result_df) == 2 # SKU-A and SKU-B


def test_packaging_rules_are_applied(tmp_path):
    """
    Tests that packaging materials are correctly added to the stock export
    based on tags in the Status_Note column.
    """
    # 1. Create a sample DataFrame with tagged orders
    analysis_df = pd.DataFrame({
        "Order_Number": ["#1001", "#1002", "#1002", "#1003"],
        "Order_Fulfillment_Status": ["Fulfillable", "Fulfillable", "Fulfillable", "Fulfillable"],
        "SKU": ["SKU-A", "SKU-B", "SKU-C", "SKU-D"],
        "Quantity": [1, 2, 1, 3],
        "Status_Note": ["|BOX|", "|Double|", "|Double|", "|FRAGILE|BOX|"]
    })

    # 2. Define packaging rules
    packaging_rules = {
        "BOX": {"PACK-BOX-S": 1},
        "Double": {"PACK-BOX-M": 1, "PACK-TAPE": 1},
        "FRAGILE": {"PACK-BUBBLE": 2}
    }

    # 3. Generate the stock export
    output_path = tmp_path / "stock_export_with_packaging.xls"
    stock_export.create_stock_export(
        analysis_df, str(output_path), packaging_rules=packaging_rules
    )

    # 4. Read the output and validate its content
    assert os.path.exists(output_path)
    result_df = pd.read_excel(output_path)

    # 5. Define expected output
    # Original SKUs: SKU-A: 1, SKU-B: 2, SKU-C: 1, SKU-D: 3
    # Packaging SKUs:
    # Order #1001 (BOX): PACK-BOX-S: 1
    # Order #1002 (Double): PACK-BOX-M: 1, PACK-TAPE: 1
    # Order #1003 (FRAGILE, BOX): PACK-BUBBLE: 2, PACK-BOX-S: 1
    # Total Packaging: PACK-BOX-S: 2, PACK-BOX-M: 1, PACK-TAPE: 1, PACK-BUBBLE: 2
    expected_data = {
        "Артикул": ["SKU-A", "SKU-B", "SKU-C", "SKU-D", "PACK-BOX-S", "PACK-BOX-M", "PACK-TAPE", "PACK-BUBBLE"],
        "Наличност": [1, 2, 1, 3, 2, 1, 1, 2]
    }
    expected_df = pd.DataFrame(expected_data)

    # Sort both dataframes for consistent comparison
    result_df = result_df.sort_values(by="Артикул").reset_index(drop=True)
    expected_df = expected_df.sort_values(by="Артикул").reset_index(drop=True)

    pd.testing.assert_frame_equal(result_df, expected_df)
