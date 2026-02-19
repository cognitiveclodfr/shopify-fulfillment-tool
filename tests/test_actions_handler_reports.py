import sys
import os
import json
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gui.actions_handler import ActionsHandler


def test_create_analysis_json(tmp_path):
    """
    Tests that _create_analysis_json creates proper JSON structure for Packing Tool.
    Uses build_packing_order_data() from core for canonical field names.
    """
    # Create mock main window
    mw = Mock()
    mw.session_path = tmp_path / "session_123"

    # Create actions handler
    handler = ActionsHandler(mw)

    # Create test DataFrame with all metadata fields
    df = pd.DataFrame(
        {
            "Order_Number": ["A1", "A1", "A2"],
            "SKU": ["SKU-001", "SKU-002", "SKU-003"],
            "Product_Name": ["Product 1", "Product 2", "Product 3"],
            "Warehouse_Name": ["Склад Продукт 1", "Склад Продукт 2", "N/A"],
            "Quantity": [2, 1, 3],
            "Order_Fulfillment_Status": ["Fulfillable", "Fulfillable", "Fulfillable"],
            "Order_Type": ["Regular", "Regular", "Priority"],
            "Shipping_Provider": ["DHL", "DHL", "PostOne"],
            "Destination_Country": ["BG", "BG", "US"],
            "Tags": ["tag1,tag2", "tag1,tag2", "tag3"],
            "Notes": ["Pack carefully", "Pack carefully", ""],
            "System_note": ["Repeat", "Repeat", ""],
            "Status_Note": ["confirmed", "", "pending"],
            "Internal_Tags": ['["URGENT"]', '["URGENT"]', "[]"],
            "Order_Min_Box": ["M", "M", None],
        }
    )

    # Create JSON
    result = handler._create_analysis_json(df)

    # Verify top-level structure
    assert "session_id" in result
    assert result["session_id"] == "session_123"
    assert "created_at" in result
    assert "total_orders" in result
    assert result["total_orders"] == 2  # 2 unique orders
    assert "total_items" in result
    assert result["total_items"] == 6  # 2+1+3
    assert "orders" in result
    assert len(result["orders"]) == 2

    # Check first order - canonical field names
    order_a1 = next(o for o in result["orders"] if o["order_number"] == "A1")
    assert order_a1["order_type"] == "Regular"
    assert order_a1["shipping_provider"] == "DHL"
    assert order_a1["destination_country"] == "BG"
    assert order_a1["order_fulfillment_status"] == "Fulfillable"
    assert order_a1["tags"] == ["tag1", "tag2"]
    assert order_a1["notes"] == "Pack carefully"
    assert order_a1["system_note"] == "Repeat"
    assert order_a1["internal_tags"] == ["URGENT"]
    assert order_a1["order_min_box"] == "M"
    assert len(order_a1["items"]) == 2

    # Check items in first order - should use Warehouse_Name + new item fields
    item_1 = next(i for i in order_a1["items"] if i["sku"] == "SKU-001")
    assert item_1["product_name"] == "Склад Продукт 1"  # ✅ Warehouse_Name used
    assert item_1["quantity"] == 2
    assert item_1["order_fulfillment_status"] == "Fulfillable"
    assert item_1["status_note"] == "confirmed"
    assert item_1["system_note"] == "Repeat"

    item_2 = next(i for i in order_a1["items"] if i["sku"] == "SKU-002")
    assert item_2["product_name"] == "Склад Продукт 2"  # ✅ Warehouse_Name used

    # Check second order - Warehouse_Name is "N/A", should fallback to Product_Name
    order_a2 = next(o for o in result["orders"] if o["order_number"] == "A2")
    assert order_a2["order_type"] == "Priority"
    assert order_a2["shipping_provider"] == "PostOne"
    assert order_a2["destination_country"] == "US"
    assert order_a2["tags"] == ["tag3"]
    assert order_a2["notes"] == ""
    assert order_a2["system_note"] == ""
    assert order_a2["internal_tags"] == []
    assert order_a2["order_min_box"] is None
    assert len(order_a2["items"]) == 1

    item_3 = order_a2["items"][0]
    assert item_3["product_name"] == "Product 3"  # ✅ Fallback to Product_Name
    assert item_3["status_note"] == "pending"


@patch('gui.actions_handler.packing_lists')
def test_generate_single_report_packing_with_json(mock_packing_lists, tmp_path):
    """
    Tests that _generate_single_report creates both XLSX and JSON for packing lists.
    """
    # Create mock main window
    mw = Mock()
    mw.analysis_results_df = pd.DataFrame(
        {
            "Order_Number": ["A1", "A2"],
            "SKU": ["SKU-001", "SKU-002"],
            "Product_Name": ["Product 1", "Product 2"],
            "Quantity": [1, 2],
            "Order_Fulfillment_Status": ["Fulfillable", "Fulfillable"],
            "Order_Type": ["Regular", "Regular"],
            "Shipping_Provider": ["DHL", "DHL"],
            "Destination_Country": ["BG", "US"],
            "Tags": ["", ""],
            "Notes": ["", ""],
            "System_note": ["", ""],
            "Status_Note": ["", ""],
            "Internal_Tags": ["[]", "[]"],
        }
    )
    mw.session_path = tmp_path / "session_456"

    # Mock log_activity and QMessageBox
    mw.log_activity = Mock()

    # Create actions handler
    handler = ActionsHandler(mw)

    # Mock _apply_filters to return all data
    handler._apply_filters = Mock(return_value=mw.analysis_results_df)

    # Report config
    report_config = {
        "name": "Test Packing List",
        "output_filename": "test_packing.xlsx",
        "filters": [],
        "exclude_skus": []
    }

    # Mock QMessageBox
    with patch('gui.actions_handler.QMessageBox'):
        # Generate report
        handler._generate_single_report("packing_lists", report_config, mw.session_path)

    # Verify packing_lists.create_packing_list was called
    mock_packing_lists.create_packing_list.assert_called_once()

    # Check call arguments
    call_args = mock_packing_lists.create_packing_list.call_args
    assert call_args[1]["report_name"] == "Test Packing List"
    assert call_args[1]["exclude_skus"] == []

    # Verify JSON file was created
    json_path = tmp_path / "session_456" / "packing_lists" / "test_packing.json"
    assert json_path.exists()

    # Verify JSON content
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    assert json_data["session_id"] == "session_456"
    assert json_data["total_orders"] == 2
    assert json_data["total_items"] == 3


@patch('gui.actions_handler.stock_export')
def test_generate_single_report_stock_export(mock_stock_export, tmp_path):
    """
    Tests that _generate_single_report creates stock export correctly.
    """
    # Create mock main window
    mw = Mock()
    mw.analysis_results_df = pd.DataFrame(
        {
            "Order_Number": ["A1", "A2"],
            "SKU": ["SKU-001", "SKU-002"],
            "Product_Name": ["Product 1", "Product 2"],
            "Quantity": [1, 2],
            "Order_Fulfillment_Status": ["Fulfillable", "Fulfillable"],
            "Shipping_Provider": ["DHL", "DHL"],
        }
    )
    mw.session_path = tmp_path / "session_789"
    mw.log_activity = Mock()

    # Create actions handler
    handler = ActionsHandler(mw)
    handler._apply_filters = Mock(return_value=mw.analysis_results_df)

    # Report config
    report_config = {
        "name": "Test Stock Export",
        "output_filename": "",  # Should auto-generate
        "filters": []
    }

    # Mock QMessageBox
    with patch('gui.actions_handler.QMessageBox'):
        # Generate report
        handler._generate_single_report("stock_exports", report_config, mw.session_path)

    # Verify stock_export.create_stock_export was called
    mock_stock_export.create_stock_export.assert_called_once()

    # Check call arguments
    call_args = mock_stock_export.create_stock_export.call_args
    assert call_args[1]["report_name"] == "Test Stock Export"

    # Verify output file has .xls extension
    output_file = call_args[1]["output_file"]
    assert output_file.endswith(".xls")

    # Verify NO JSON file was created (stock exports don't need JSON)
    session_dir = tmp_path / "session_789" / "stock_exports"
    if session_dir.exists():
        json_files = list(session_dir.glob("*.json"))
        assert len(json_files) == 0


@patch('gui.actions_handler.packing_lists')
def test_generate_packing_list_with_exclude_skus(mock_packing_lists, tmp_path):
    """
    Tests that exclude_skus from config are properly passed to packing_lists module.
    """
    # Create mock main window
    mw = Mock()
    mw.analysis_results_df = pd.DataFrame(
        {
            "Order_Number": ["A1", "A1"],
            "SKU": ["SKU-001", "SKU-EXCLUDE"],
            "Product_Name": ["Product 1", "Product 2"],
            "Quantity": [1, 1],
            "Order_Fulfillment_Status": ["Fulfillable", "Fulfillable"],
            "Order_Type": ["Regular", "Regular"],
            "Shipping_Provider": ["DHL", "DHL"],
            "Destination_Country": ["BG", "BG"],
            "Tags": ["", ""],
            "Notes": ["", ""],
            "System_note": ["", ""],
            "Status_Note": ["", ""],
            "Internal_Tags": ["[]", "[]"],
        }
    )
    mw.session_path = tmp_path / "session_exclude"
    mw.log_activity = Mock()

    # Create actions handler
    handler = ActionsHandler(mw)
    handler._apply_filters = Mock(return_value=mw.analysis_results_df)

    # Report config with exclude_skus
    report_config = {
        "name": "Test Exclude",
        "output_filename": "test_exclude.xlsx",
        "filters": [],
        "exclude_skus": ["SKU-EXCLUDE"]
    }

    # Mock QMessageBox
    with patch('gui.actions_handler.QMessageBox'):
        # Generate report
        handler._generate_single_report("packing_lists", report_config, mw.session_path)

    # Verify exclude_skus was passed correctly
    call_args = mock_packing_lists.create_packing_list.call_args
    assert call_args[1]["exclude_skus"] == ["SKU-EXCLUDE"]

    # Verify JSON was created and doesn't contain excluded SKU
    json_path = tmp_path / "session_exclude" / "packing_lists" / "test_exclude.json"
    assert json_path.exists()

    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    # JSON should exclude SKU-EXCLUDE (same as XLSX)
    assert len(json_data["orders"]) == 1
    assert len(json_data["orders"][0]["items"]) == 1  # Only SKU-001, SKU-EXCLUDE is excluded
    assert json_data["orders"][0]["items"][0]["sku"] == "SKU-001"
    assert json_data["total_items"] == 1  # Only 1 item after exclusion
