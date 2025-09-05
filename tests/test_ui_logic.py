"""Unit tests for UI-related logic, specifically the PandasModel.

This module contains tests for the `PandasModel` class, which is a key
component of the GUI for displaying DataFrame data in a `QTableView`.
"""

import sys
import os
import pytest
import pandas as pd
from PySide6.QtCore import Qt

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gui.pandas_model import PandasModel

@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Provides a sample DataFrame for model testing.

    Returns:
        A sample pandas DataFrame.
    """
    return pd.DataFrame({
        'Order_Number': ['1001', '1002', '1003'],
        'SKU': ['A', 'B', 'C'],
        'Quantity': [1, 2, 3]
    })

def test_pandas_model_initialization(sample_dataframe: pd.DataFrame) -> None:
    """Tests that the PandasModel initializes correctly.

    Args:
        sample_dataframe: The sample DataFrame fixture.
    """
    model = PandasModel(sample_dataframe)
    assert model.rowCount() == 3
    assert model.columnCount() == 3
    assert model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == 'Order_Number'

def test_pandas_model_data_retrieval(sample_dataframe: pd.DataFrame) -> None:
    """Tests that data is retrieved correctly from the model.

    Args:
        sample_dataframe: The sample DataFrame fixture.
    """
    model = PandasModel(sample_dataframe)
    index = model.index(1, 1)  # Row 1, Column 1 should be 'B'
    assert model.data(index) == "B"

def test_column_reordering_in_model(sample_dataframe: pd.DataFrame) -> None:
    """Tests that the column order can be changed in the model.

    Args:
        sample_dataframe: The sample DataFrame fixture.
    """
    model = PandasModel(sample_dataframe)

    # Define a new column order
    new_order = ['Quantity', 'Order_Number', 'SKU']
    visible_columns = ['Quantity', 'SKU']

    # Apply the new order
    model.set_column_order_and_visibility(new_order, visible_columns)

    # Check that the internal dataframe columns are now in the new order
    assert model._dataframe.columns.tolist() == new_order

    # Check that the header data reflects the new order
    assert model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == 'Quantity'
    assert model.headerData(1, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == 'Order_Number'
    assert model.headerData(2, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == 'SKU'

    # Check that the hidden_columns attribute is set correctly
    assert hasattr(model, 'hidden_columns')
    assert model.hidden_columns == ['Order_Number']

def test_get_column_index(sample_dataframe: pd.DataFrame) -> None:
    """Tests the get_column_index helper method.

    Args:
        sample_dataframe: The sample DataFrame fixture.
    """
    model = PandasModel(sample_dataframe)
    assert model.get_column_index("SKU") == 1
    assert model.get_column_index("NonExistentColumn") is None
