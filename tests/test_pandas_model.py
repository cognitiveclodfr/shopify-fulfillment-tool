"""Tests for PandasModel (gui/pandas_model.py).

Covers:
- rowCount / columnCount
- data() DisplayRole
- data() BackgroundRole / ForegroundRole (color caching)
- Theme switch triggers dataChanged
- Checkbox column logic
- Header data
- get_column_index helper
"""

import os
import pytest
import pandas as pd

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import QApplication

from gui.pandas_model import PandasModel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def basic_df():
    return pd.DataFrame({
        "Order_Number": ["ORD-1", "ORD-2", "ORD-3"],
        "SKU": ["A", "B", "C"],
        "Order_Fulfillment_Status": ["Fulfillable", "Not Fulfillable", "Fulfillable"],
        "System_note": [None, None, "Repeat order"],
    })


@pytest.fixture
def model(qapp, basic_df):
    return PandasModel(basic_df)


class TestRowAndColumnCount:

    def test_row_count(self, model, basic_df):
        assert model.rowCount() == len(basic_df)

    def test_column_count(self, model, basic_df):
        assert model.columnCount() == len(basic_df.columns)

    def test_row_count_with_checkboxes(self, qapp, basic_df):
        m = PandasModel(basic_df, enable_checkboxes=True)
        assert m.rowCount() == len(basic_df)

    def test_column_count_with_checkboxes(self, qapp, basic_df):
        m = PandasModel(basic_df, enable_checkboxes=True)
        assert m.columnCount() == len(basic_df.columns) + 1

    def test_invalid_parent_returns_zero(self, model):
        invalid = model.index(0, 0)  # Valid index, but used as parent
        # A valid parent should return 0 children for table models
        assert model.rowCount(invalid) == 0
        assert model.columnCount(invalid) == 0

    def test_empty_dataframe(self, qapp):
        m = PandasModel(pd.DataFrame())
        assert m.rowCount() == 0
        assert m.columnCount() == 0


class TestDisplayRole:

    def test_returns_string_value(self, model):
        idx = model.index(0, 0)
        assert model.data(idx, Qt.ItemDataRole.DisplayRole) == "ORD-1"

    def test_nan_returns_empty_string(self, qapp):
        df = pd.DataFrame({"col": [float("nan"), "value"]})
        m = PandasModel(df)
        idx = m.index(0, 0)
        assert m.data(idx, Qt.ItemDataRole.DisplayRole) == ""

    def test_invalid_index_returns_none(self, model):
        assert model.data(QModelIndex()) is None

    def test_checkbox_column_display_returns_none(self, qapp, basic_df):
        m = PandasModel(basic_df, enable_checkboxes=True)
        idx = m.index(0, 0)  # checkbox column
        assert m.data(idx, Qt.ItemDataRole.DisplayRole) is None

    def test_data_column_offset_with_checkboxes(self, qapp, basic_df):
        m = PandasModel(basic_df, enable_checkboxes=True)
        # Column 1 with checkboxes = Column 0 of DataFrame (Order_Number)
        idx = m.index(0, 1)
        assert m.data(idx, Qt.ItemDataRole.DisplayRole) == "ORD-1"


class TestBackgroundAndForegroundRole:

    def test_fulfillable_has_background(self, model):
        # Row 0: Fulfillable
        idx = model.index(0, 0)
        bg = model.data(idx, Qt.ItemDataRole.BackgroundRole)
        assert bg is not None

    def test_not_fulfillable_has_background(self, model):
        # Row 1: Not Fulfillable
        idx = model.index(1, 0)
        bg = model.data(idx, Qt.ItemDataRole.BackgroundRole)
        assert bg is not None

    def test_repeat_system_note_has_background(self, model):
        # Row 2: Fulfillable but also has "Repeat" in System_note
        # Repeat takes priority over Fulfillable
        idx = model.index(2, 0)
        bg = model.data(idx, Qt.ItemDataRole.BackgroundRole)
        assert bg is not None

    def test_fulfillable_has_foreground(self, model):
        idx = model.index(0, 0)
        fg = model.data(idx, Qt.ItemDataRole.ForegroundRole)
        assert fg is not None

    def test_fulfillable_and_not_fulfillable_colors_differ(self, model):
        bg_fulfillable = model.data(model.index(0, 0), Qt.ItemDataRole.BackgroundRole)
        bg_not_fulfillable = model.data(model.index(1, 0), Qt.ItemDataRole.BackgroundRole)
        assert bg_fulfillable != bg_not_fulfillable

    def test_no_status_column_returns_none(self, qapp):
        df = pd.DataFrame({"col": ["x", "y"]})
        m = PandasModel(df)
        bg = m.data(m.index(0, 0), Qt.ItemDataRole.BackgroundRole)
        assert bg is None

    def test_row_color_cache_same_as_data_call(self, model):
        for row in range(model.rowCount()):
            cached_bg = model._row_bg_cache[row]
            idx = model.index(row, 0)
            data_bg = model.data(idx, Qt.ItemDataRole.BackgroundRole)
            assert cached_bg == data_bg


class TestHeaderData:

    def test_horizontal_header_returns_column_name(self, model):
        assert model.headerData(0, Qt.Orientation.Horizontal) == "Order_Number"
        assert model.headerData(1, Qt.Orientation.Horizontal) == "SKU"

    def test_vertical_header_returns_row_number(self, model):
        assert model.headerData(0, Qt.Orientation.Vertical) == "1"
        assert model.headerData(2, Qt.Orientation.Vertical) == "3"

    def test_header_with_checkboxes_offset(self, qapp, basic_df):
        m = PandasModel(basic_df, enable_checkboxes=True)
        # Section 0 = checkbox column (empty), section 1 = first DataFrame column
        assert m.headerData(0, Qt.Orientation.Horizontal) == ""
        assert m.headerData(1, Qt.Orientation.Horizontal) == "Order_Number"


class TestGetColumnIndex:

    def test_returns_correct_index(self, model):
        assert model.get_column_index("Order_Number") == 0
        assert model.get_column_index("SKU") == 1

    def test_returns_none_for_missing_column(self, model):
        assert model.get_column_index("NonExistent") is None

    def test_offset_with_checkboxes(self, qapp, basic_df):
        m = PandasModel(basic_df, enable_checkboxes=True)
        assert m.get_column_index("Order_Number") == 1  # +1 for checkbox col


class TestThemeSwitch:

    def test_theme_change_rebuilds_cache(self, qapp, basic_df):
        from gui.theme_manager import get_theme_manager
        m = PandasModel(basic_df)
        original_color = m._row_bg_cache[0]

        # Manually call _update_colors to simulate theme switch
        m._update_colors()

        # Cache should be rebuilt; same color (theme didn't actually change)
        assert m._row_bg_cache[0] == original_color

    def test_data_changed_signal_emitted_on_theme_change(self, qapp, basic_df):
        signals_received = []
        m = PandasModel(basic_df)
        m.dataChanged.connect(lambda tl, br, roles: signals_received.append(roles))
        m._update_colors()
        assert len(signals_received) >= 1
