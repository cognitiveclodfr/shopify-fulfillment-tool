import pytest
import pandas as pd
import sys
import os
import shutil
from unittest.mock import MagicMock

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shopify_tool.analysis import run_analysis
from gui.fulfillment_window import FulfillmentWindow
from gui.fulfillment_pandas_model import FulfillmentPandasModel
from PySide6.QtCore import QTimer

@pytest.fixture
def temp_output_dir(tmpdir):
    """Create a temporary directory for test outputs."""
    return str(tmpdir)

def test_barcode_generation(temp_output_dir):
    """
    Tests that barcodes are generated and paths are added to the DataFrame.
    """
    # 1. Create dummy data
    stock_df = pd.DataFrame({"Артикул": ["SKU-1"], "Име": ["Test Product"], "Наличност": [10]})
    orders_df = pd.DataFrame({
        "Name": ["#1001"],
        "Lineitem sku": ["SKU-1"],
        "Lineitem quantity": [1],
        "Shipping Method": ["dhl"],
        "Shipping Country": ["BG"],
        "Tags": [""],
        "Notes": [""],
    })
    history_df = pd.DataFrame(columns=["Order_Number", "Execution_Date"])

    # 2. Run analysis
    final_df, _, _, _ = run_analysis(stock_df, orders_df, history_df, temp_output_dir)

    # 3. Assertions
    barcode_dir = os.path.join(temp_output_dir, "barcodes")
    assert os.path.isdir(barcode_dir)

    expected_barcode_filename = "1001.png"
    expected_barcode_path = os.path.join(barcode_dir, expected_barcode_filename)
    assert os.path.isfile(expected_barcode_path)

    assert "Order_Barcode_Path" in final_df.columns
    assert final_df.iloc[0]["Order_Barcode_Path"] == expected_barcode_path

# --- Tests for FulfillmentWindow ---

@pytest.fixture
def sample_final_df():
    """Provides a sample final_df for testing the fulfillment window."""
    return pd.DataFrame({
        "Order_Number": ["#1001", "#1001", "#1002"],
        "SKU": ["SKU-A", "SKU-B", "SKU-A"],
        "Product_Name": ["Product A", "Product B", "Product A"],
        "Quantity": [1, 2, 3],
        "Order_Barcode_Path": ["/fake/path/1001.png", "/fake/path/1001.png", "/fake/path/1002.png"]
    })

@pytest.fixture
def fulfillment_window(qtbot, sample_final_df):
    """Creates a FulfillmentWindow instance for testing."""
    window = FulfillmentWindow(sample_final_df)
    qtbot.addWidget(window)
    window.show()
    return window

def test_load_order_success(fulfillment_window, qtbot):
    """Tests successfully loading an order."""
    window = fulfillment_window

    window.order_input.setText("#1001")
    window.load_order()

    assert window.current_order_number == "#1001"
    assert window.sku_input.isEnabled()
    assert not window.order_input.isEnabled()
    assert window.items_table.model().rowCount() == 2
    assert "Scan SKUs" in window.status_label.text()

def test_load_order_fail(fulfillment_window):
    """Tests failing to load a non-existent order."""
    window = fulfillment_window
    window.order_input.setText("#9999")
    window.load_order()

    assert window.current_order_number is None
    assert "not found" in window.status_label.text()
    assert not window.sku_input.isEnabled()

def test_scan_sku_success(fulfillment_window, qtbot):
    """Tests successfully scanning a correct SKU."""
    # First, load an order
    window = fulfillment_window
    window.order_input.setText("#1001")
    window.load_order()

    # Now, scan a valid SKU
    with qtbot.waitSignal(window.model.dataChanged, timeout=1000):
        window.sku_input.setText("SKU-A")
        window.scan_sku()

    model = window.items_table.model()
    df = model.get_dataframe()

    assert df[df['SKU'] == 'SKU-A']['Packed'].iloc[0] == 1
    assert df[df['SKU'] == 'SKU-A']['Status'].iloc[0] == 'Packed' # Since Quantity is 1
    assert "Packed SKU: SKU-A" in window.status_label.text()

def test_scan_sku_fail(fulfillment_window):
    """Tests scanning an incorrect SKU."""
    # First, load an order
    window = fulfillment_window
    window.order_input.setText("#1001")
    window.load_order()

    # Now, scan an invalid SKU
    window.sku_input.setText("SKU-C")
    window.scan_sku()

    model = window.items_table.model()
    df = model.get_dataframe()

    assert df['Packed'].sum() == 0 # No items should be packed
    assert "not in this order" in window.status_label.text()

def test_order_completion(fulfillment_window, qtbot):
    """Tests the full cycle of packing an order to completion."""
    window = fulfillment_window

    # Load order #1001
    window.order_input.setText("#1001")
    window.load_order()

    # Scan SKU-A (1 of 1)
    window.sku_input.setText("SKU-A")
    window.scan_sku()

    # Scan SKU-B (1 of 2)
    window.sku_input.setText("SKU-B")
    window.scan_sku()

    # Scan SKU-B again (2 of 2) - this should complete the order
    window.sku_input.setText("SKU-B")
    window.scan_sku()

    # The check for completion is triggered, which has a QTimer.
    # We need to wait for the timer to fire and reset the UI.
    def check_completion_and_reset():
        assert "complete" in window.status_label.text()
        # Wait for the reset timer
        QTimer.singleShot(3100, lambda: check_reset(window))

    def check_reset(win):
        assert win.current_order_number is None
        assert win.order_input.isEnabled()
        assert not win.sku_input.isEnabled()
        assert "Scan next order" in win.status_label.text()

    qtbot.waitUntil(check_completion_and_reset, timeout=5000)
