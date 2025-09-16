import sys
import os
import pandas as pd
import pytest
from PySide6.QtCore import Qt

# Mock the QtMultimedia module before it's imported by the application code
# This is necessary to avoid an ImportError in environments without the required system libraries (e.g., libpulse.so.0)
from unittest.mock import MagicMock
sys.modules['PySide6.QtMultimedia'] = MagicMock()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from gui.fulfillment_window import FulfillmentWindow  # noqa: E402

@pytest.fixture
def fulfillment_data():
    """Provides a sample DataFrame for fulfillment tests."""
    data = {
        'Order_Number': ['1001', '1001', '1002'],
        'SKU': ['A-1', 'B-2', 'C-3'],
        'Product_Name': ['Product A', 'Product B', 'Product C'],
        'Quantity': [1, 2, 1]
    }
    return pd.DataFrame(data)

def test_fulfillment_window_init(qtbot, fulfillment_data):
    """Tests the basic initialization of the FulfillmentWindow."""
    window = FulfillmentWindow(final_df=fulfillment_data)
    qtbot.addWidget(window)
    assert window.windowTitle() == "Fulfillment Mode"
    assert not window.sku_scan_input.isEnabled()

def test_load_order_success(qtbot, fulfillment_data):
    """Tests successfully loading an order by scanning its barcode."""
    window = FulfillmentWindow(final_df=fulfillment_data)
    qtbot.addWidget(window)

    # Simulate scanning an order
    window.order_scan_input.setText("1001")
    qtbot.keyPress(window.order_scan_input, Qt.Key_Return)

    assert window.items_model.rowCount() == 2
    assert "Order #1001 loaded" in window.status_label.text()
    assert window.sku_scan_input.isEnabled()
    assert not window.order_scan_input.isEnabled()

def test_load_order_not_found(qtbot, fulfillment_data):
    """Tests scanning an order number that does not exist."""
    window = FulfillmentWindow(final_df=fulfillment_data)
    qtbot.addWidget(window)

    window.order_scan_input.setText("9999")
    qtbot.keyPress(window.order_scan_input, Qt.Key_Return)

    assert window.items_model.rowCount() == 0
    assert "Order '9999' not found" in window.status_label.text()
    assert not window.sku_scan_input.isEnabled()

def test_sku_scanning_and_completion(qtbot, fulfillment_data):
    """Tests the full workflow of scanning SKUs and completing an order."""
    window = FulfillmentWindow(final_df=fulfillment_data)
    qtbot.addWidget(window)

    # Load order 1001
    window.order_scan_input.setText("1001")
    qtbot.keyPress(window.order_scan_input, Qt.Key_Return)

    # Scan first item (A-1, requires 1)
    window.sku_scan_input.setText("A-1")
    qtbot.keyPress(window.sku_scan_input, Qt.Key_Return)
    assert "Item collected" in window.status_label.text()
    assert window.items_model._data.loc[window.items_model._data['SKU'] == 'A-1', 'Collected'].iloc[0] == 1
    assert window.items_model._data.loc[window.items_model._data['SKU'] == 'A-1', 'Status'].iloc[0] == "Complete"

    # Scan second item (B-2, requires 2) - first scan
    window.sku_scan_input.setText("B-2")
    qtbot.keyPress(window.sku_scan_input, Qt.Key_Return)
    assert "Item collected" in window.status_label.text()
    assert window.items_model._data.loc[window.items_model._data['SKU'] == 'B-2', 'Collected'].iloc[0] == 1
    assert window.items_model._data.loc[window.items_model._data['SKU'] == 'B-2', 'Status'].iloc[0] == "Pending"

    # Scan incorrect SKU
    window.sku_scan_input.setText("WRONG-SKU")
    qtbot.keyPress(window.sku_scan_input, Qt.Key_Return)
    assert "Scanned SKU not in this order" in window.status_label.text()

    # Scan second item (B-2, requires 2) - second scan (completes the order)
    window.sku_scan_input.setText("B-2")
    qtbot.keyPress(window.sku_scan_input, Qt.Key_Return)
    assert window.items_model._data.loc[window.items_model._data['SKU'] == 'B-2', 'Collected'].iloc[0] == 2
    assert window.items_model._data.loc[window.items_model._data['SKU'] == 'B-2', 'Status'].iloc[0] == "Complete"
    assert "Order #1001 complete!" in window.status_label.text()
    assert not window.sku_scan_input.isEnabled()

    # Wait for the UI to reset
    qtbot.wait(3100) # Wait for the 3-second QTimer
    assert window.order_scan_input.isEnabled()
    assert "Scan an order to begin" in window.status_label.text()
