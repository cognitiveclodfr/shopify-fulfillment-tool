"""Unit tests for bulk operations functionality.

Tests cover:
- SelectionHelper class
- BulkOperationsToolbar widget
- Bulk operation methods in ActionsHandler
- Bulk undo handlers in UndoManager
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch


class TestSelectionHelper:
    """Test SelectionHelper class."""

    @pytest.fixture
    def mock_main_window(self):
        """Create mock main window with test data."""
        mw = Mock()
        mw.analysis_results_df = pd.DataFrame({
            'Order_Number': ['#001', '#001', '#002', '#003'],
            'SKU': ['SKU-A', 'SKU-B', 'SKU-A', 'SKU-C'],
            'Order_Fulfillment_Status': ['Fulfillable', 'Fulfillable', 'Not Fulfillable', 'Fulfillable'],
            'Internal_Tags': ['[]', '["urgent"]', '[]', '["vip"]']
        })
        return mw

    @pytest.fixture
    def mock_proxy_model(self):
        """Create mock proxy model."""
        proxy = Mock()
        proxy.rowCount.return_value = 4

        def mock_index(row, col):
            index = Mock()
            index.row.return_value = row
            return index

        proxy.index.side_effect = mock_index

        def mock_map_to_source(index):
            source_index = Mock()
            source_index.row.return_value = index.row()
            return source_index

        proxy.mapToSource.side_effect = mock_map_to_source
        return proxy

    @pytest.fixture
    def selection_helper(self, mock_main_window, mock_proxy_model):
        """Create SelectionHelper instance."""
        from gui.selection_helper import SelectionHelper
        mock_table = Mock()
        return SelectionHelper(mock_table, mock_proxy_model, mock_main_window)

    def test_toggle_row_selects_entire_order(self, selection_helper):
        """Test that toggling a row selects all rows of the same order."""
        # Row 0 is part of order #001 (which has rows 0 and 1)
        assert not selection_helper.is_row_checked(0)
        assert not selection_helper.is_row_checked(1)

        # Toggle row 0 - should select both row 0 and 1 (same order #001)
        selection_helper.toggle_row(0)
        assert selection_helper.is_row_checked(0)
        assert selection_helper.is_row_checked(1)  # Also selected!

        # Toggle again - should unselect both
        selection_helper.toggle_row(0)
        assert not selection_helper.is_row_checked(0)
        assert not selection_helper.is_row_checked(1)

    def test_toggle_single_item_order(self, selection_helper):
        """Test toggling a single-item order (row 2 = #002, row 3 = #003)."""
        # Row 2 is order #002 (single item)
        selection_helper.toggle_row(2)
        assert selection_helper.is_row_checked(2)
        assert selection_helper.get_checked_count() == 1

        # Row 3 is order #003 (single item)
        selection_helper.toggle_row(3)
        assert selection_helper.is_row_checked(3)
        assert selection_helper.get_checked_count() == 2

    def test_toggle_multiple_orders(self, selection_helper):
        """Test toggling multiple different orders."""
        # Select order #001 (rows 0, 1)
        selection_helper.toggle_row(0)
        # Select order #002 (row 2)
        selection_helper.toggle_row(2)
        # Select order #003 (row 3)
        selection_helper.toggle_row(3)

        assert selection_helper.is_row_checked(0)
        assert selection_helper.is_row_checked(1)  # Part of #001
        assert selection_helper.is_row_checked(2)
        assert selection_helper.is_row_checked(3)
        assert selection_helper.get_checked_count() == 4  # All 4 rows

    def test_get_selection_summary(self, selection_helper, mock_main_window):
        """Test selection summary calculation."""
        # Select order #001 (rows 0, 1) and order #002 (row 2)
        selection_helper.toggle_row(0)  # Selects both rows 0 and 1
        selection_helper.toggle_row(2)

        orders_count, items_count = selection_helper.get_selection_summary()

        assert orders_count == 2  # #001 and #002
        assert items_count == 3  # 2 items from #001 + 1 from #002

    def test_get_selection_summary_single_order(self, selection_helper, mock_main_window):
        """Test selection summary with items from same order."""
        # Select order #001 by clicking on row 0 (auto-selects row 1 too)
        selection_helper.toggle_row(0)

        orders_count, items_count = selection_helper.get_selection_summary()

        assert orders_count == 1  # Only #001
        assert items_count == 2  # Both rows of #001

    def test_clear_selection(self, selection_helper):
        """Test clear all selection."""
        # Toggle order #001 (selects rows 0 and 1) and #002 (row 2)
        selection_helper.toggle_row(0)  # Selects rows 0, 1
        selection_helper.toggle_row(2)  # Selects row 2

        assert len(selection_helper.checked_rows) == 3  # Rows 0, 1, 2

        selection_helper.clear_selection()

        assert len(selection_helper.checked_rows) == 0
        assert not selection_helper.has_selection()

    def test_select_all(self, selection_helper, mock_proxy_model):
        """Test select all visible rows."""
        selection_helper.select_all()

        # Should select all 4 rows (based on mock proxy_model.rowCount)
        assert selection_helper.get_checked_count() == 4
        assert selection_helper.is_row_checked(0)
        assert selection_helper.is_row_checked(1)
        assert selection_helper.is_row_checked(2)
        assert selection_helper.is_row_checked(3)

    def test_get_selected_source_rows(self, selection_helper):
        """Test getting sorted list of selected row indexes."""
        # Toggle order #003 (row 3) and order #001 (rows 0, 1)
        selection_helper.toggle_row(3)  # Selects row 3
        selection_helper.toggle_row(0)  # Selects rows 0, 1

        selected_rows = selection_helper.get_selected_source_rows()

        # Should be sorted and include all rows of selected orders
        assert selected_rows == [0, 1, 3]

    def test_get_selected_orders_data(self, selection_helper, mock_main_window):
        """Test getting DataFrame slice of selected rows."""
        # Toggle order #001 (rows 0, 1) and #002 (row 2)
        selection_helper.toggle_row(0)  # Selects rows 0, 1
        selection_helper.toggle_row(2)  # Selects row 2

        selected_df = selection_helper.get_selected_orders_data()

        assert len(selected_df) == 3  # All 3 rows (2 from #001 + 1 from #002)
        assert '#001' in selected_df['Order_Number'].values
        assert '#002' in selected_df['Order_Number'].values

    def test_get_selected_orders_data_empty(self, selection_helper):
        """Test getting empty DataFrame when no selection."""
        selected_df = selection_helper.get_selected_orders_data()
        assert selected_df.empty

    def test_has_selection(self, selection_helper):
        """Test has_selection method."""
        assert not selection_helper.has_selection()

        selection_helper.toggle_row(0)
        assert selection_helper.has_selection()

        selection_helper.toggle_row(0)
        assert not selection_helper.has_selection()


class TestBulkOperationsToolbar:
    """Test BulkOperationsToolbar class."""

    @pytest.fixture
    def toolbar(self):
        """Create toolbar instance."""
        # Skip if no display available
        pytest.importorskip("PySide6.QtWidgets")

        import os
        if 'CI' in os.environ or os.environ.get('DISPLAY') is None:
            pytest.skip("No display available")

        from PySide6.QtWidgets import QApplication
        from gui.bulk_operations_toolbar import BulkOperationsToolbar

        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        return BulkOperationsToolbar()

    def test_selection_count_update(self, toolbar):
        """Test selection counter update."""
        toolbar.update_selection_count(5, 12)

        assert "5 orders" in toolbar.selection_label.text()
        assert "12 items" in toolbar.selection_label.text()

    def test_selection_count_zero(self, toolbar):
        """Test selection counter with zero values."""
        toolbar.update_selection_count(0, 0)

        assert "0 orders" in toolbar.selection_label.text()
        assert "0 items" in toolbar.selection_label.text()

    def test_buttons_disabled_when_no_selection(self, toolbar):
        """Test buttons are disabled when no selection."""
        toolbar.set_enabled(False)

        # Check that operation buttons are disabled
        assert not toolbar.fulfillable_btn.isEnabled()
        assert not toolbar.not_fulfillable_btn.isEnabled()
        assert not toolbar.add_tag_btn.isEnabled()
        assert not toolbar.remove_tag_btn.isEnabled()
        assert not toolbar.delete_menu_btn.isEnabled()

    def test_buttons_enabled_when_selection(self, toolbar):
        """Test buttons are enabled when selection exists."""
        toolbar.set_enabled(True)

        # Check that operation buttons are enabled
        assert toolbar.fulfillable_btn.isEnabled()
        assert toolbar.not_fulfillable_btn.isEnabled()
        assert toolbar.add_tag_btn.isEnabled()
        assert toolbar.remove_tag_btn.isEnabled()

    def test_signals_emitted(self, toolbar):
        """Test that signals are properly emitted."""
        # Use a simple signal tracking approach instead of QSignalSpy
        select_all_emitted = []
        change_status_emitted = []

        toolbar.select_all_clicked.connect(lambda: select_all_emitted.append(True))
        toolbar.change_status_clicked.connect(lambda x: change_status_emitted.append(x))

        # Test select_all signal
        toolbar.select_all_clicked.emit()
        assert len(select_all_emitted) == 1

        # Test change_status signal
        toolbar.change_status_clicked.emit(True)
        assert len(change_status_emitted) == 1
        assert change_status_emitted[0] is True


class TestBulkUndoOperations:
    """Test bulk undo handlers in UndoManager."""

    @pytest.fixture
    def mock_main_window(self):
        """Create mock main window."""
        mw = Mock()
        mw.analysis_results_df = pd.DataFrame({
            'Order_Number': ['#001', '#001', '#002'],
            'SKU': ['SKU-A', 'SKU-B', 'SKU-A'],
            'Order_Fulfillment_Status': ['Fulfillable', 'Fulfillable', 'Not Fulfillable'],
            'Internal_Tags': ['[]', '[]', '["urgent"]']
        })
        mw.session_path = None
        return mw

    @pytest.fixture
    def undo_manager(self, mock_main_window):
        """Create UndoManager instance."""
        from shopify_tool.undo_manager import UndoManager
        return UndoManager(mock_main_window)

    def test_undo_bulk_change_status(self, undo_manager, mock_main_window):
        """Test undoing bulk status change."""
        # Setup: affected rows before change
        affected_rows_before = pd.DataFrame({
            'Order_Number': ['#001', '#001'],
            'SKU': ['SKU-A', 'SKU-B'],
            'Order_Fulfillment_Status': ['Fulfillable', 'Fulfillable'],
            'Internal_Tags': ['[]', '[]']
        })

        # After bulk change (simulated)
        mock_main_window.analysis_results_df.loc[[0, 1], 'Order_Fulfillment_Status'] = 'Not Fulfillable'

        # Verify the change happened
        assert mock_main_window.analysis_results_df.loc[0, 'Order_Fulfillment_Status'] == 'Not Fulfillable'

        # Undo
        params = {'affected_indexes': [0, 1], 'is_fulfillable': False}
        result = undo_manager._undo_bulk_change_status(params, affected_rows_before)

        # Verify successful
        assert result is True
        assert mock_main_window.analysis_results_df.loc[0, 'Order_Fulfillment_Status'] == 'Fulfillable'
        assert mock_main_window.analysis_results_df.loc[1, 'Order_Fulfillment_Status'] == 'Fulfillable'

    def test_undo_bulk_delete_orders(self, undo_manager, mock_main_window):
        """Test undoing bulk order deletion."""
        # Setup: rows that were deleted
        deleted_rows = pd.DataFrame({
            'Order_Number': ['#003', '#003'],
            'SKU': ['SKU-X', 'SKU-Y'],
            'Order_Fulfillment_Status': ['Fulfillable', 'Fulfillable'],
            'Internal_Tags': ['["vip"]', '["vip"]']
        })

        original_count = len(mock_main_window.analysis_results_df)

        # Undo (restore deleted rows)
        params = {'deleted_orders': 1, 'deleted_items': 2}
        result = undo_manager._undo_bulk_delete_orders(params, deleted_rows)

        # Verify successful
        assert result is True
        assert len(mock_main_window.analysis_results_df) == original_count + 2

    def test_undo_bulk_add_tag(self, undo_manager, mock_main_window):
        """Test undoing bulk tag addition."""
        # Setup: affected rows before adding tag
        affected_rows_before = pd.DataFrame({
            'Order_Number': ['#001', '#001'],
            'SKU': ['SKU-A', 'SKU-B'],
            'Order_Fulfillment_Status': ['Fulfillable', 'Fulfillable'],
            'Internal_Tags': ['[]', '[]']
        }, index=[0, 1])

        # After adding tag (simulated)
        mock_main_window.analysis_results_df.loc[[0, 1], 'Internal_Tags'] = '["priority"]'

        # Undo
        params = {'tag': 'priority', 'affected_indexes': [0, 1]}
        result = undo_manager._undo_bulk_add_tag(params, affected_rows_before)

        # Verify successful
        assert result is True
        assert mock_main_window.analysis_results_df.loc[0, 'Internal_Tags'] == '[]'
        assert mock_main_window.analysis_results_df.loc[1, 'Internal_Tags'] == '[]'


class TestPandasModelWithCheckboxes:
    """Test PandasModel with checkbox column support."""

    @pytest.fixture
    def test_dataframe(self):
        """Create test DataFrame."""
        return pd.DataFrame({
            'Order_Number': ['#001', '#002'],
            'SKU': ['SKU-A', 'SKU-B'],
            'Order_Fulfillment_Status': ['Fulfillable', 'Not Fulfillable']
        })

    def test_column_count_without_checkboxes(self, test_dataframe):
        """Test column count without checkbox column."""
        from gui.pandas_model import PandasModel
        model = PandasModel(test_dataframe, enable_checkboxes=False)
        assert model.columnCount() == 3

    def test_column_count_with_checkboxes(self, test_dataframe):
        """Test column count with checkbox column added."""
        from gui.pandas_model import PandasModel
        model = PandasModel(test_dataframe, enable_checkboxes=True)
        assert model.columnCount() == 4  # 3 + 1 for checkbox

    def test_header_data_without_checkboxes(self, test_dataframe):
        """Test header data without checkboxes."""
        from gui.pandas_model import PandasModel
        from PySide6.QtCore import Qt

        model = PandasModel(test_dataframe, enable_checkboxes=False)

        assert model.headerData(0, Qt.Horizontal) == 'Order_Number'
        assert model.headerData(1, Qt.Horizontal) == 'SKU'
        assert model.headerData(2, Qt.Horizontal) == 'Order_Fulfillment_Status'

    def test_header_data_with_checkboxes(self, test_dataframe):
        """Test header data with checkbox column."""
        from gui.pandas_model import PandasModel
        from PySide6.QtCore import Qt

        model = PandasModel(test_dataframe, enable_checkboxes=True)

        assert model.headerData(0, Qt.Horizontal) == ''  # Checkbox column header
        assert model.headerData(1, Qt.Horizontal) == 'Order_Number'
        assert model.headerData(2, Qt.Horizontal) == 'SKU'

    def test_get_column_index_without_checkboxes(self, test_dataframe):
        """Test get_column_index without checkboxes."""
        from gui.pandas_model import PandasModel
        model = PandasModel(test_dataframe, enable_checkboxes=False)

        assert model.get_column_index('Order_Number') == 0
        assert model.get_column_index('SKU') == 1

    def test_get_column_index_with_checkboxes(self, test_dataframe):
        """Test get_column_index with checkbox column offset."""
        from gui.pandas_model import PandasModel
        model = PandasModel(test_dataframe, enable_checkboxes=True)

        # With checkboxes, column indexes are shifted by 1
        assert model.get_column_index('Order_Number') == 1
        assert model.get_column_index('SKU') == 2
