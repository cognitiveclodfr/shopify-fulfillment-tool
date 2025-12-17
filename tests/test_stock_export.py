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


# ============================================================================
# Tests for Configurable Fulfillment Status Filter
# ============================================================================


def test_stock_export_fulfillment_filter_default_behavior(tmp_path):
    """Test backward compatibility - default filters to Fulfillable only."""
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Not Fulfillable", "Fulfillable"],
            "SKU": ["SKU-A", "SKU-B", "SKU-A"],
            "Quantity": [5, 10, 3],
        }
    )

    output_path = tmp_path / "test_default.xls"

    # No config provided - should default to Fulfillable
    stock_export.create_stock_export(df, str(output_path))

    assert os.path.exists(output_path)
    result_df = pd.read_excel(output_path)

    # Should only contain Fulfillable orders (SKU-A with total quantity 8)
    assert len(result_df) == 1
    assert result_df.iloc[0]["Артикул"] == "SKU-A"
    assert result_df.iloc[0]["Наличност"] == 8


def test_stock_export_fulfillment_filter_explicit_fulfillable(tmp_path):
    """Test explicit Fulfillable filter in config."""
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Not Fulfillable", "Fulfillable"],
            "SKU": ["SKU-A", "SKU-B", "SKU-A"],
            "Quantity": [5, 10, 3],
        }
    )

    output_path = tmp_path / "test_explicit.xls"

    config = {"fulfillment_status_filter": {"enabled": True, "status": "Fulfillable"}}

    stock_export.create_stock_export(df, str(output_path), config=config)

    assert os.path.exists(output_path)
    result_df = pd.read_excel(output_path)

    # Should only contain Fulfillable orders
    assert len(result_df) == 1
    assert result_df.iloc[0]["Артикул"] == "SKU-A"
    assert result_df.iloc[0]["Наличност"] == 8


def test_stock_export_fulfillment_filter_not_fulfillable(tmp_path):
    """Test filtering for NOT Fulfillable orders."""
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Not Fulfillable", "Not Fulfillable"],
            "SKU": ["SKU-A", "SKU-B", "SKU-B"],
            "Quantity": [5, 10, 3],
        }
    )

    output_path = tmp_path / "test_not_fulfillable.xls"

    config = {"fulfillment_status_filter": {"enabled": True, "status": "Not Fulfillable"}}

    stock_export.create_stock_export(df, str(output_path), config=config)

    assert os.path.exists(output_path)
    result_df = pd.read_excel(output_path)

    # Should only contain Not Fulfillable orders (SKU-B with total quantity 13)
    assert len(result_df) == 1
    assert result_df.iloc[0]["Артикул"] == "SKU-B"
    assert result_df.iloc[0]["Наличност"] == 13


def test_stock_export_fulfillment_filter_disabled(tmp_path):
    """Test disabled filter - should include ALL orders."""
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Not Fulfillable", "Fulfillable"],
            "SKU": ["SKU-A", "SKU-B", "SKU-C"],
            "Quantity": [5, 10, 3],
        }
    )

    output_path = tmp_path / "test_disabled.xls"

    config = {"fulfillment_status_filter": {"enabled": False}}

    stock_export.create_stock_export(df, str(output_path), config=config)

    assert os.path.exists(output_path)
    result_df = pd.read_excel(output_path)

    # Should contain ALL SKUs
    assert len(result_df) == 3
    skus = result_df["Артикул"].tolist()
    assert "SKU-A" in skus
    assert "SKU-B" in skus
    assert "SKU-C" in skus


def test_stock_export_fulfillment_filter_multiple_statuses(tmp_path):
    """Test filtering for multiple statuses (OR logic)."""
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Not Fulfillable", "Partial", "Fulfillable"],
            "SKU": ["SKU-A", "SKU-B", "SKU-C", "SKU-A"],
            "Quantity": [5, 10, 3, 2],
        }
    )

    output_path = tmp_path / "test_multiple.xls"

    config = {"fulfillment_status_filter": {"enabled": True, "status": ["Fulfillable", "Partial"]}}

    stock_export.create_stock_export(df, str(output_path), config=config)

    assert os.path.exists(output_path)
    result_df = pd.read_excel(output_path)

    # Should contain Fulfillable and Partial orders (SKU-A: 7, SKU-C: 3)
    assert len(result_df) == 2
    skus = result_df["Артикул"].tolist()
    assert "SKU-A" in skus
    assert "SKU-C" in skus
    assert "SKU-B" not in skus  # Not Fulfillable


def test_stock_export_fulfillment_filter_with_additional_filters(tmp_path):
    """Test fulfillment filter combined with other filters."""
    df = pd.DataFrame(
        {
            "Order_Fulfillment_Status": ["Fulfillable", "Not Fulfillable", "Fulfillable", "Fulfillable"],
            "Order_Type": ["Single", "Single", "Multi", "Single"],
            "SKU": ["SKU-A", "SKU-B", "SKU-C", "SKU-D"],
            "Quantity": [5, 10, 3, 2],
        }
    )

    output_path = tmp_path / "test_combined.xls"

    config = {"fulfillment_status_filter": {"enabled": True, "status": "Fulfillable"}}
    filters = [{"field": "Order_Type", "operator": "==", "value": "Single"}]

    stock_export.create_stock_export(df, str(output_path), filters=filters, config=config)

    assert os.path.exists(output_path)
    result_df = pd.read_excel(output_path)

    # Should only contain Fulfillable + Single orders (SKU-A and SKU-D)
    assert len(result_df) == 2
    skus = result_df["Артикул"].tolist()
    assert "SKU-A" in skus
    assert "SKU-D" in skus
    assert "SKU-B" not in skus  # Not Fulfillable
    assert "SKU-C" not in skus  # Multi


def test_stock_export_build_fulfillment_filter_helper():
    """Test the _build_fulfillment_filter helper function directly."""
    # Test default behavior (empty config)
    assert stock_export._build_fulfillment_filter({}) == ["Order_Fulfillment_Status == 'Fulfillable'"]

    # Test explicit Fulfillable
    config = {"fulfillment_status_filter": {"enabled": True, "status": "Fulfillable"}}
    assert stock_export._build_fulfillment_filter(config) == ["Order_Fulfillment_Status == 'Fulfillable'"]

    # Test Not Fulfillable
    config = {"fulfillment_status_filter": {"enabled": True, "status": "Not Fulfillable"}}
    assert stock_export._build_fulfillment_filter(config) == ["Order_Fulfillment_Status == 'Not Fulfillable'"]

    # Test disabled filter
    config = {"fulfillment_status_filter": {"enabled": False}}
    assert stock_export._build_fulfillment_filter(config) == []

    # Test multiple statuses
    config = {"fulfillment_status_filter": {"enabled": True, "status": ["Fulfillable", "Partial"]}}
    assert stock_export._build_fulfillment_filter(config) == ["Order_Fulfillment_Status in ['Fulfillable', 'Partial']"]
