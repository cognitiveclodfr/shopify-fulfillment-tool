import sys
import os
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from PySide6.QtCore import Qt, QPoint

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.main_window_pyside import MainWindow
from gui.pandas_model import PandasModel
from PySide6.QtWidgets import QMessageBox, QMenu


@pytest.fixture
def mock_dependencies(mocker, tmp_path):
    """Mocks dependencies required by MainWindow for instantiation."""
    mocker.patch("gui.main_window_pyside.FileHandler", return_value=MagicMock())
    mocker.patch("gui.main_window_pyside.ActionsHandler", return_value=MagicMock())
    mocker.patch("gui.main_window_pyside.QtLogHandler", return_value=MagicMock())

    mocker.patch("gui.main_window_pyside.recalculate_statistics", return_value={"total_orders_completed": 0})

    mock_config_path = tmp_path / "config.json"
    mock_session_path = tmp_path / "session_data.pkl"

    def mock_get_path(filename):
        if filename == "config.json":
            mock_config_path.write_text('{"settings": {}}')
            return str(mock_config_path)
        if filename == "session_data.pkl":
            return str(mock_session_path)
        return str(tmp_path / filename)

    mocker.patch("gui.main_window_pyside.get_persistent_data_path", side_effect=mock_get_path)
    mocker.patch("gui.main_window_pyside.resource_path", return_value="dummy_resource_path")
    mocker.patch("os.path.exists", lambda path: "config.json" in path)
    mocker.patch("shutil.copy")

    mocker.patch.object(QMessageBox, "question", return_value=QMessageBox.No)
    mocker.patch.object(QMessageBox, "critical")
    mocker.patch("logging.getLogger")


@pytest.fixture
def app(qtbot, mock_dependencies):
    """Fixture to create the main window and set it up with test data."""
    window = MainWindow()
    qtbot.addWidget(window)

    test_df = pd.DataFrame({
        'Order_Number': ['1001', '1002', '1003'],
        'SKU': ['A-1', 'B-2', 'A-1'],
        'Name': ['Item A', 'Item B', 'Item A'],
        'Quantity': [1, 2, 3],
        'Order_Fulfillment_Status': ['Fulfillable', 'Unfulfillable', 'Fulfillable'],
        'Shipping_Provider': ['DHL', 'DPD', 'DHL'],
        'System_note': ['', 'Repeat', '']
    })
    window.analysis_results_df = test_df
    window._update_all_views()

    yield window
    window.close()


def test_main_window_creation(app):
    """Test that the main window can be created successfully."""
    assert app is not None
    assert "Shopify Fulfillment Tool" in app.windowTitle()
    assert app.new_session_btn is not None


def test_table_filter(app, qtbot):
    """Test that the table view is actually filtered when using the filter controls."""
    assert app.proxy_model.rowCount() == 3

    app.filter_input.setText('1002')
    app.filter_table()

    assert app.proxy_model.rowCount() == 1

    app.clear_filter_button.click()
    assert app.proxy_model.rowCount() == 3

    app.filter_column_selector.setCurrentText('SKU')
    app.filter_input.setText('A-1')
    app.filter_table()
    assert app.proxy_model.rowCount() == 2


def test_table_double_click_calls_handler(app):
    """Test that double-clicking a cell calls the correct handler."""
    index = app.proxy_model.index(0, 0)
    app.on_table_double_clicked(index)
    app.actions_handler.toggle_fulfillment_status_for_order.assert_called_once_with('1001')


def test_context_menu(app, qtbot, mocker):
    """Test that the context menu is created and its actions call the handlers."""
    table = app.tableView

    # Mock the QMenu class to prevent it from actually showing
    mock_menu_instance = MagicMock()
    mocker.patch('gui.main_window_pyside.QMenu', return_value=mock_menu_instance)

    # Simulate a right-click by emitting the customContextMenuRequested signal
    pos = QPoint(10, 10)
    table.customContextMenuRequested.emit(pos)

    # Check that the menu was created and shown
    mock_menu_instance.exec.assert_called_once()

    # Check that actions were added
    assert mock_menu_instance.addAction.call_count > 0
    assert any("Copy SKU" in call.args[0].text() for call in mock_menu_instance.addAction.call_args_list)
