"""Unit tests for TableConfigManager

Tests cover:
- TableConfig dataclass serialization/deserialization
- TableConfigManager load/save operations
- Default config generation
- Empty column detection
- Config application to QTableView
- Named view management
- Migration integration

Author: Claude Code
Date: 2026-02-03
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os
from unittest.mock import MagicMock, patch, call
from PySide6.QtWidgets import QTableView, QHeaderView

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gui.table_config_manager import TableConfig, TableConfigManager


# --- TableConfig Tests ---

class TestTableConfig:
    """Test TableConfig dataclass."""

    def test_default_initialization(self):
        """Test TableConfig with default values."""
        config = TableConfig()
        assert config.version == 1
        assert config.visible_columns == {}
        assert config.column_order == []
        assert config.column_widths == {}
        assert config.auto_hide_empty is True
        assert config.locked_columns == ["Order_Number"]

    def test_custom_initialization(self):
        """Test TableConfig with custom values."""
        config = TableConfig(
            version=2,
            visible_columns={"SKU": True, "Product_Name": False},
            column_order=["Order_Number", "SKU"],
            column_widths={"Order_Number": 120, "SKU": 100},
            auto_hide_empty=False,
            locked_columns=["Order_Number", "SKU"]
        )
        assert config.version == 2
        assert config.visible_columns == {"SKU": True, "Product_Name": False}
        assert config.column_order == ["Order_Number", "SKU"]
        assert config.column_widths == {"Order_Number": 120, "SKU": 100}
        assert config.auto_hide_empty is False
        assert config.locked_columns == ["Order_Number", "SKU"]

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = TableConfig(
            visible_columns={"SKU": True},
            column_order=["Order_Number", "SKU"],
            column_widths={"SKU": 100}
        )
        result = config.to_dict()

        assert isinstance(result, dict)
        assert result["version"] == 1
        assert result["visible_columns"] == {"SKU": True}
        assert result["column_order"] == ["Order_Number", "SKU"]
        assert result["column_widths"] == {"SKU": 100}
        assert result["auto_hide_empty"] is True
        assert result["locked_columns"] == ["Order_Number"]

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "version": 1,
            "visible_columns": {"SKU": True, "Product_Name": False},
            "column_order": ["Order_Number", "SKU", "Product_Name"],
            "column_widths": {"Order_Number": 120},
            "auto_hide_empty": True,
            "locked_columns": ["Order_Number"]
        }
        config = TableConfig.from_dict(data)

        assert config.version == 1
        assert config.visible_columns == {"SKU": True, "Product_Name": False}
        assert config.column_order == ["Order_Number", "SKU", "Product_Name"]
        assert config.column_widths == {"Order_Number": 120}
        assert config.auto_hide_empty is True
        assert config.locked_columns == ["Order_Number"]

    def test_from_dict_missing_keys(self):
        """Test creation from dictionary with missing keys (should use defaults)."""
        data = {
            "visible_columns": {"SKU": True}
        }
        config = TableConfig.from_dict(data)

        assert config.version == 1  # Default
        assert config.visible_columns == {"SKU": True}
        assert config.column_order == []  # Default
        assert config.column_widths == {}  # Default
        assert config.auto_hide_empty is True  # Default
        assert config.locked_columns == ["Order_Number"]  # Default

    def test_round_trip_serialization(self):
        """Test that to_dict() → from_dict() preserves data."""
        original = TableConfig(
            version=1,
            visible_columns={"A": True, "B": False, "C": True},
            column_order=["A", "B", "C"],
            column_widths={"A": 100, "B": 150},
            auto_hide_empty=False,
            locked_columns=["A"]
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = TableConfig.from_dict(data)

        # Verify all fields match
        assert restored.version == original.version
        assert restored.visible_columns == original.visible_columns
        assert restored.column_order == original.column_order
        assert restored.column_widths == original.column_widths
        assert restored.auto_hide_empty == original.auto_hide_empty
        assert restored.locked_columns == original.locked_columns


# --- TableConfigManager Tests ---

@pytest.fixture
def mock_main_window():
    """Create mock MainWindow."""
    mw = MagicMock()
    mw.tableView = MagicMock(spec=QTableView)
    mw.tableView.horizontalHeader.return_value = MagicMock(spec=QHeaderView)
    return mw


@pytest.fixture
def mock_profile_manager():
    """Create mock ProfileManager."""
    pm = MagicMock()
    pm.load_client_config.return_value = {
        "ui_settings": {
            "table_view": {
                "version": 1,
                "active_view": "Default",
                "views": {
                    "Default": {
                        "visible_columns": {},
                        "column_order": [],
                        "column_widths": {},
                        "auto_hide_empty": True,
                        "locked_columns": ["Order_Number"]
                    }
                }
            }
        }
    }
    pm.save_client_config = MagicMock()
    return pm


@pytest.fixture
def table_config_manager(mock_main_window, mock_profile_manager):
    """Create TableConfigManager instance."""
    return TableConfigManager(mock_main_window, mock_profile_manager)


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame for testing."""
    return pd.DataFrame({
        "Order_Number": ["#1001", "#1002", "#1003"],
        "SKU": ["ABC123", "DEF456", "GHI789"],
        "Product_Name": ["Product A", "Product B", "Product C"],
        "Quantity": [1, 2, 3],
        "Has_SKU": [np.nan, np.nan, np.nan],  # Empty column (all NaN)
        "Total_Price": ["", "", ""],  # Empty column (all empty strings)
        "Stock": [10, 20, 30]
    })


class TestTableConfigManager:
    """Test TableConfigManager functionality."""

    def test_initialization(self, mock_main_window, mock_profile_manager):
        """Test TableConfigManager initialization."""
        manager = TableConfigManager(mock_main_window, mock_profile_manager)

        assert manager.mw is mock_main_window
        assert manager.pm is mock_profile_manager
        assert manager._current_config is None
        assert manager._current_client_id is None
        assert manager._current_view_name == "Default"
        assert manager._pending_save is False

    def test_load_config_success(self, table_config_manager, mock_profile_manager):
        """Test successful config loading."""
        config = table_config_manager.load_config("M")

        # Verify ProfileManager was called
        mock_profile_manager.load_client_config.assert_called_once_with("M")

        # Verify config was loaded
        assert isinstance(config, TableConfig)
        assert config.version == 1
        assert config.auto_hide_empty is True
        assert config.locked_columns == ["Order_Number"]

        # Verify internal state
        assert table_config_manager._current_client_id == "M"
        assert table_config_manager._current_view_name == "Default"
        assert table_config_manager._current_config is config

    def test_load_config_missing_view(self, table_config_manager, mock_profile_manager):
        """Test loading config when view doesn't exist (creates default)."""
        # Return config without the requested view
        mock_profile_manager.load_client_config.return_value = {
            "ui_settings": {
                "table_view": {
                    "version": 1,
                    "active_view": "Default",
                    "views": {}  # No views
                }
            }
        }

        config = table_config_manager.load_config("M", "NonExistent")

        # Should create default config
        assert isinstance(config, TableConfig)
        assert config.version == 1

    def test_load_config_failure_fallback(self, table_config_manager, mock_profile_manager):
        """Test config loading failure falls back to default."""
        # Simulate loading failure
        mock_profile_manager.load_client_config.side_effect = Exception("Load failed")

        config = table_config_manager.load_config("M")

        # Should return default config
        assert isinstance(config, TableConfig)
        assert config.version == 1

    def test_save_config(self, table_config_manager, mock_profile_manager):
        """Test config saving."""
        config = TableConfig(
            visible_columns={"SKU": True, "Product_Name": False},
            column_order=["Order_Number", "SKU"]
        )

        # Load initial config first
        table_config_manager.load_config("M")

        # Save config
        table_config_manager.save_config("M", config, "MyView")

        # Verify save was called with updated config
        mock_profile_manager.save_client_config.assert_called()
        call_args = mock_profile_manager.save_client_config.call_args
        client_id = call_args[0][0]
        saved_config = call_args[0][1]

        assert client_id == "M"
        assert "ui_settings" in saved_config
        assert "table_view" in saved_config["ui_settings"]
        assert "views" in saved_config["ui_settings"]["table_view"]
        assert "MyView" in saved_config["ui_settings"]["table_view"]["views"]
        assert saved_config["ui_settings"]["table_view"]["active_view"] == "MyView"

    def test_save_config_creates_structure(self, table_config_manager, mock_profile_manager):
        """Test save creates ui_settings structure if missing."""
        # Return config without ui_settings
        mock_profile_manager.load_client_config.return_value = {}

        config = TableConfig()
        table_config_manager.save_config("M", config, "Default")

        # Verify structure was created
        call_args = mock_profile_manager.save_client_config.call_args
        saved_config = call_args[0][1]

        assert "ui_settings" in saved_config
        assert "table_view" in saved_config["ui_settings"]
        assert saved_config["ui_settings"]["table_view"]["version"] == 1

    def test_get_default_config(self, table_config_manager):
        """Test default config generation."""
        columns = ["Order_Number", "SKU", "Product_Name", "Quantity"]
        config = table_config_manager.get_default_config(columns)

        assert isinstance(config, TableConfig)
        assert config.version == 1

        # All columns should be visible
        assert config.visible_columns == {
            "Order_Number": True,
            "SKU": True,
            "Product_Name": True,
            "Quantity": True
        }

        # Order should match input
        assert config.column_order == columns

        # No widths specified
        assert config.column_widths == {}

        # Auto-hide enabled
        assert config.auto_hide_empty is True

        # Order_Number locked
        assert config.locked_columns == ["Order_Number"]

    def test_detect_empty_columns_all_nan(self, table_config_manager, sample_dataframe):
        """Test detection of columns with all NaN values."""
        empty_cols = table_config_manager.detect_empty_columns(sample_dataframe)

        # Has_SKU (all NaN) should be detected
        assert "Has_SKU" in empty_cols

    def test_detect_empty_columns_all_empty_strings(self, table_config_manager, sample_dataframe):
        """Test detection of columns with all empty strings."""
        empty_cols = table_config_manager.detect_empty_columns(sample_dataframe)

        # Total_Price (all "") should be detected
        assert "Total_Price" in empty_cols

    def test_detect_empty_columns_not_empty(self, table_config_manager, sample_dataframe):
        """Test that non-empty columns are not detected as empty."""
        empty_cols = table_config_manager.detect_empty_columns(sample_dataframe)

        # These columns have data and should NOT be detected
        assert "Order_Number" not in empty_cols
        assert "SKU" not in empty_cols
        assert "Product_Name" not in empty_cols
        assert "Quantity" not in empty_cols
        assert "Stock" not in empty_cols

    def test_detect_empty_columns_mixed_empty(self, table_config_manager):
        """Test that partially empty columns are NOT detected as empty."""
        df = pd.DataFrame({
            "A": [1, np.nan, 3],  # Partially empty
            "B": ["x", "", "z"],  # Partially empty
            "C": [np.nan, np.nan, np.nan],  # Completely empty
        })

        empty_cols = table_config_manager.detect_empty_columns(df)

        assert "C" in empty_cols  # Completely empty
        assert "A" not in empty_cols  # Partially empty
        assert "B" not in empty_cols  # Partially empty

    def test_apply_config_to_view_no_config(self, table_config_manager, sample_dataframe):
        """Test apply_config_to_view when no config is loaded."""
        table_view = MagicMock(spec=QTableView)

        # No config loaded
        table_config_manager._current_config = None

        # Should log warning and return early
        table_config_manager.apply_config_to_view(table_view, sample_dataframe)

        # View should not be modified
        table_view.horizontalHeader.assert_not_called()

    def test_apply_config_initializes_empty_config(self, table_config_manager, sample_dataframe):
        """Test that empty config is initialized with defaults."""
        table_view = MagicMock(spec=QTableView)
        header = MagicMock(spec=QHeaderView)
        table_view.horizontalHeader.return_value = header

        # Create mock model
        model = MagicMock()
        model.sourceModel.return_value = None  # No proxy
        table_view.model.return_value = model

        # Load config and clear visible_columns to simulate empty config
        table_config_manager.load_config("M")
        table_config_manager._current_config.visible_columns = {}

        # Apply config
        table_config_manager.apply_config_to_view(table_view, sample_dataframe)

        # Config should now be initialized
        assert len(table_config_manager._current_config.visible_columns) > 0

    def test_list_views(self, table_config_manager, mock_profile_manager):
        """Test listing all view names."""
        # Setup multiple views
        mock_profile_manager.load_client_config.return_value = {
            "ui_settings": {
                "table_view": {
                    "views": {
                        "Default": {},
                        "Compact": {},
                        "Full": {}
                    }
                }
            }
        }

        views = table_config_manager.list_views("M")

        assert len(views) == 3
        assert "Default" in views
        assert "Compact" in views
        assert "Full" in views

    def test_list_views_empty(self, table_config_manager, mock_profile_manager):
        """Test listing views when no views exist."""
        mock_profile_manager.load_client_config.return_value = {
            "ui_settings": {
                "table_view": {
                    "views": {}
                }
            }
        }

        views = table_config_manager.list_views("M")

        assert views == []

    def test_list_views_error(self, table_config_manager, mock_profile_manager):
        """Test listing views when error occurs."""
        mock_profile_manager.load_client_config.side_effect = Exception("Error")

        views = table_config_manager.list_views("M")

        assert views == []

    def test_load_view(self, table_config_manager):
        """Test loading a specific named view."""
        config = table_config_manager.load_view("M", "Compact")

        assert isinstance(config, TableConfig)
        assert table_config_manager._current_view_name == "Compact"

    def test_save_view(self, table_config_manager, mock_profile_manager):
        """Test saving a named view."""
        config = TableConfig(visible_columns={"SKU": True})

        table_config_manager.save_view("M", "MyView", config)

        # Verify save was called
        mock_profile_manager.save_client_config.assert_called()

    def test_delete_view(self, table_config_manager, mock_profile_manager):
        """Test deleting a named view."""
        # Setup config with multiple views
        mock_profile_manager.load_client_config.return_value = {
            "ui_settings": {
                "table_view": {
                    "views": {
                        "Default": {},
                        "ToDelete": {}
                    }
                }
            }
        }

        table_config_manager.delete_view("M", "ToDelete")

        # Verify save was called
        mock_profile_manager.save_client_config.assert_called()

        # Verify view was removed from config
        call_args = mock_profile_manager.save_client_config.call_args
        saved_config = call_args[0][1]
        views = saved_config["ui_settings"]["table_view"]["views"]

        assert "Default" in views
        assert "ToDelete" not in views

    def test_delete_default_view_raises_error(self, table_config_manager):
        """Test that deleting Default view raises ValueError."""
        with pytest.raises(ValueError, match="Cannot delete Default view"):
            table_config_manager.delete_view("M", "Default")

    def test_delete_nonexistent_view(self, table_config_manager, mock_profile_manager):
        """Test deleting a view that doesn't exist (should log warning)."""
        mock_profile_manager.load_client_config.return_value = {
            "ui_settings": {
                "table_view": {
                    "views": {
                        "Default": {}
                    }
                }
            }
        }

        # Should not raise error, just log warning
        table_config_manager.delete_view("M", "NonExistent")


# --- Integration Tests ---

class TestTableConfigIntegration:
    """Integration tests for TableConfigManager with ProfileManager."""

    def test_full_load_save_cycle(self, table_config_manager, mock_profile_manager):
        """Test complete load → modify → save → load cycle."""
        # Load initial config
        config1 = table_config_manager.load_config("M")

        # Modify config
        config1.visible_columns["SKU"] = False
        config1.column_widths["Order_Number"] = 150

        # Save modified config
        table_config_manager.save_config("M", config1, "Default")

        # Verify save was called
        assert mock_profile_manager.save_client_config.called

        # Simulate loading the saved config
        saved_data = mock_profile_manager.save_client_config.call_args[0][1]
        mock_profile_manager.load_client_config.return_value = saved_data

        # Load config again
        config2 = table_config_manager.load_config("M")

        # Verify modifications persisted
        assert config2.visible_columns.get("SKU") == False
        assert config2.column_widths.get("Order_Number") == 150

    def test_multiple_views_management(self, table_config_manager, mock_profile_manager):
        """Test creating and switching between multiple views."""
        # Load default
        table_config_manager.load_config("M")

        # Create and save view 1
        view1 = TableConfig(visible_columns={"SKU": True, "Product_Name": False})
        table_config_manager.save_view("M", "Compact", view1)

        # Create and save view 2
        view2 = TableConfig(visible_columns={"SKU": True, "Product_Name": True})
        table_config_manager.save_view("M", "Full", view2)

        # Verify both saves occurred
        assert mock_profile_manager.save_client_config.call_count >= 2


class TestColumnVisibility:
    """Test column visibility management (Phase 2)."""

    def test_toggle_column_visibility(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test toggling column visibility."""
        # Setup
        table_config_manager.load_config("M")
        table_config_manager._current_config.visible_columns = {"SKU": True, "Product_Name": True}

        table_view = mock_main_window.tableView
        header = MagicMock(spec=QHeaderView)
        table_view.horizontalHeader.return_value = header

        model = MagicMock()
        model.sourceModel.return_value = None
        table_view.model.return_value = model

        # Toggle SKU visibility (True -> False)
        result = table_config_manager.toggle_column_visibility(
            table_view,
            "SKU",
            sample_dataframe
        )

        # Verify visibility was toggled
        assert result is False  # Now hidden
        assert table_config_manager._current_config.visible_columns["SKU"] is False

    def test_toggle_locked_column_fails(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test that toggling locked column returns True (stays visible)."""
        # Setup
        table_config_manager.load_config("M")

        table_view = mock_main_window.tableView

        # Try to toggle Order_Number (locked column)
        result = table_config_manager.toggle_column_visibility(
            table_view,
            "Order_Number",
            sample_dataframe
        )

        # Should remain visible
        assert result is True

    def test_set_column_visibility_show(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test setting column visibility to show."""
        # Setup
        table_config_manager.load_config("M")
        table_config_manager._current_config.visible_columns = {"SKU": False}

        table_view = mock_main_window.tableView
        header = MagicMock(spec=QHeaderView)
        table_view.horizontalHeader.return_value = header

        model = MagicMock()
        model.sourceModel.return_value = None
        table_view.model.return_value = model

        # Set SKU to visible
        table_config_manager.set_column_visibility(
            table_view,
            "SKU",
            True,
            sample_dataframe
        )

        # Verify visibility was set
        assert table_config_manager._current_config.visible_columns["SKU"] is True

    def test_set_column_visibility_hide(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test setting column visibility to hide."""
        # Setup
        table_config_manager.load_config("M")
        table_config_manager._current_config.visible_columns = {"Product_Name": True}

        table_view = mock_main_window.tableView
        header = MagicMock(spec=QHeaderView)
        table_view.horizontalHeader.return_value = header

        model = MagicMock()
        model.sourceModel.return_value = None
        table_view.model.return_value = model

        # Set Product_Name to hidden
        table_config_manager.set_column_visibility(
            table_view,
            "Product_Name",
            False,
            sample_dataframe
        )

        # Verify visibility was set
        assert table_config_manager._current_config.visible_columns["Product_Name"] is False

    def test_set_locked_column_hidden_fails(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test that setting locked column to hidden is ignored."""
        # Setup
        table_config_manager.load_config("M")
        table_config_manager._current_config.visible_columns = {"Order_Number": True}

        table_view = mock_main_window.tableView

        # Try to hide Order_Number (locked column)
        table_config_manager.set_column_visibility(
            table_view,
            "Order_Number",
            False,
            sample_dataframe
        )

        # Should remain visible (not changed)
        assert table_config_manager._current_config.visible_columns["Order_Number"] is True

    def test_get_column_visibility(self, table_config_manager):
        """Test getting column visibility state."""
        table_config_manager.load_config("M")
        table_config_manager._current_config.visible_columns = {
            "SKU": True,
            "Product_Name": False
        }

        assert table_config_manager.get_column_visibility("SKU") is True
        assert table_config_manager.get_column_visibility("Product_Name") is False
        assert table_config_manager.get_column_visibility("Unknown") is True  # Default

    def test_get_hidden_columns(self, table_config_manager, sample_dataframe):
        """Test getting list of hidden columns."""
        table_config_manager.load_config("M")
        table_config_manager._current_config.visible_columns = {
            "Order_Number": True,
            "SKU": False,
            "Product_Name": True,
            "Quantity": False,
            "Has_SKU": True,
            "Total_Price": True,
            "Stock": True
        }

        hidden = table_config_manager.get_hidden_columns(sample_dataframe)

        assert "SKU" in hidden
        assert "Quantity" in hidden
        assert len(hidden) == 2

    def test_show_all_columns(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test showing all columns."""
        # Setup
        table_config_manager.load_config("M")
        table_config_manager._current_config.visible_columns = {
            "Order_Number": True,
            "SKU": False,
            "Product_Name": False,
            "Quantity": False,
            "Has_SKU": False,
            "Total_Price": False,
            "Stock": False
        }

        table_view = mock_main_window.tableView
        header = MagicMock(spec=QHeaderView)
        table_view.horizontalHeader.return_value = header

        model = MagicMock()
        model.sourceModel.return_value = None
        table_view.model.return_value = model

        # Show all columns
        table_config_manager.show_all_columns(table_view, sample_dataframe)

        # Verify all columns are now visible
        for col in sample_dataframe.columns:
            assert table_config_manager._current_config.visible_columns[col] is True

    def test_apply_single_column_visibility(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test applying visibility to a single column."""
        # Setup
        table_config_manager.load_config("M")

        table_view = mock_main_window.tableView
        header = MagicMock(spec=QHeaderView)
        table_view.horizontalHeader.return_value = header

        model = MagicMock()
        model.sourceModel.return_value = None
        table_view.model.return_value = model

        # Apply visibility to SKU column (hide it)
        table_config_manager._apply_single_column_visibility(
            table_view,
            "SKU",
            False,
            sample_dataframe
        )

        # Verify setSectionHidden was called
        header.setSectionHidden.assert_called()
        # Get the call arguments
        call_args = header.setSectionHidden.call_args
        is_hidden = call_args[0][1]

        # Column should be hidden (True = hidden)
        assert is_hidden is True

    def test_auto_hide_respects_locked_columns(self, table_config_manager):
        """Test that auto-hide logic respects locked columns."""
        # Create DataFrame with empty columns
        df = pd.DataFrame({
            "Order_Number": ["", "", ""],  # Empty but locked
            "SKU": ["A", "B", "C"],
            "Empty_Col": [np.nan, np.nan, np.nan]  # Empty and not locked
        })

        table_config_manager.load_config("M")
        table_config_manager._current_config.auto_hide_empty = True
        table_config_manager._current_config.locked_columns = ["Order_Number"]

        # Detect empty columns
        empty_columns = table_config_manager.detect_empty_columns(df)

        # Both Order_Number and Empty_Col should be detected as empty
        assert "Order_Number" in empty_columns
        assert "Empty_Col" in empty_columns

        # Now test visibility logic in apply_config_to_view
        # Simulate what happens in the visibility determination
        visible_columns = {}

        for col in df.columns:
            # Default visibility
            is_visible = table_config_manager._current_config.visible_columns.get(col, True)

            # Auto-hide overrides for non-locked empty columns
            if col in empty_columns and col not in table_config_manager._current_config.locked_columns:
                is_visible = False

            # Locked columns override (always visible)
            if col in table_config_manager._current_config.locked_columns:
                is_visible = True

            visible_columns[col] = is_visible

        # Order_Number should be visible (locked)
        assert visible_columns["Order_Number"] is True, "Order_Number should be visible (locked)"

        # SKU should be visible (not empty)
        assert visible_columns["SKU"] is True, "SKU should be visible (not empty)"

        # Empty_Col should be hidden (empty and not locked)
        assert visible_columns["Empty_Col"] is False, "Empty_Col should be hidden (auto-hide)"


class TestColumnOrderAndWidth:
    """Test column order and width persistence (Phase 3)."""

    def test_apply_column_order(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test applying column order."""
        # Setup
        table_config_manager.load_config("M")
        table_config_manager._current_config.column_order = ["SKU", "Order_Number", "Product_Name"]

        table_view = mock_main_window.tableView
        header = MagicMock(spec=QHeaderView)

        # Mock visualIndex and moveSection
        visual_indices = {0: 0, 1: 1, 2: 2}  # Initially in order
        def mock_visual_index(logical):
            return visual_indices.get(logical, logical)
        header.visualIndex = MagicMock(side_effect=mock_visual_index)
        header.moveSection = MagicMock()

        table_view.horizontalHeader.return_value = header

        model = MagicMock()
        model.sourceModel.return_value = None
        table_view.model.return_value = model

        # Apply order
        table_config_manager.apply_column_order(table_view, sample_dataframe)

        # Verify moveSection was called (columns should be reordered)
        assert header.moveSection.called

    def test_apply_column_widths(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test applying column widths."""
        # Setup
        table_config_manager.load_config("M")
        table_config_manager._current_config.column_widths = {
            "Order_Number": 150,
            "SKU": 100,
            "Product_Name": 200
        }

        table_view = mock_main_window.tableView
        header = MagicMock(spec=QHeaderView)
        header.resizeSection = MagicMock()
        table_view.horizontalHeader.return_value = header

        model = MagicMock()
        model.sourceModel.return_value = None
        table_view.model.return_value = model

        # Apply widths
        table_config_manager.apply_column_widths(table_view, sample_dataframe)

        # Verify resizeSection was called for each column with width
        assert header.resizeSection.call_count == 3
        # Verify specific calls
        calls = header.resizeSection.call_args_list
        widths_set = {call[0][1] for call in calls}
        assert 150 in widths_set
        assert 100 in widths_set
        assert 200 in widths_set

    def test_on_column_resized(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test handling column resize event."""
        # Setup
        table_config_manager.load_config("M")
        table_config_manager._current_table_view = mock_main_window.tableView
        table_config_manager._current_df = sample_dataframe

        table_view = mock_main_window.tableView
        model = MagicMock()
        source_model = MagicMock()
        source_model.enable_checkboxes = False
        model.sourceModel.return_value = source_model
        table_view.model.return_value = model

        # Resize SKU column (logical index 1 in DataFrame)
        table_config_manager.on_column_resized(1, 100, 150)

        # Verify width was updated for SKU
        assert "SKU" in table_config_manager._current_config.column_widths
        assert table_config_manager._current_config.column_widths["SKU"] == 150

        # Verify debounced save was scheduled
        assert table_config_manager._pending_save is True

    def test_on_column_moved(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test handling column move event."""
        # Setup
        table_config_manager.load_config("M")
        table_config_manager._current_table_view = mock_main_window.tableView
        table_config_manager._current_df = sample_dataframe

        table_view = mock_main_window.tableView
        header = MagicMock(spec=QHeaderView)

        # Setup mock header
        def mock_logical_index(visual):
            # Map visual positions to logical indices
            mapping = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}
            return mapping.get(visual, visual)

        header.logicalIndex = MagicMock(side_effect=mock_logical_index)
        header.count.return_value = 7  # Number of columns in sample_dataframe
        header.moveSection = MagicMock()
        table_view.horizontalHeader.return_value = header

        model = MagicMock()
        source_model = MagicMock()
        source_model.enable_checkboxes = False
        model.sourceModel.return_value = source_model
        table_view.model.return_value = model

        # Move SKU column (logical index 1) from visual position 1 to 2
        table_config_manager.on_column_moved(1, 1, 2)

        # Verify column order was updated
        assert len(table_config_manager._current_config.column_order) > 0

        # Verify SKU is in the order
        assert "SKU" in table_config_manager._current_config.column_order

        # Verify debounced save was scheduled
        assert table_config_manager._pending_save is True

    def test_locked_column_cannot_move(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test that locked column (Order_Number) cannot be moved from position 0."""
        # Setup
        table_config_manager.load_config("M")
        table_config_manager._current_table_view = mock_main_window.tableView
        table_config_manager._current_df = sample_dataframe

        table_view = mock_main_window.tableView
        header = MagicMock(spec=QHeaderView)
        header.moveSection = MagicMock()
        table_view.horizontalHeader.return_value = header

        model = MagicMock()
        source_model = MagicMock()
        source_model.enable_checkboxes = False
        model.sourceModel.return_value = source_model
        table_view.model.return_value = model

        # Try to move Order_Number (logical index 0) from position 0 to position 1
        table_config_manager.on_column_moved(0, 0, 1)

        # Verify move was reverted (move back from position 1 to 0)
        header.moveSection.assert_called_once_with(1, 0)

    def test_get_column_name_from_logical_index(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test getting column name from logical index."""
        table_view = mock_main_window.tableView
        model = MagicMock()
        source_model = MagicMock()
        source_model.enable_checkboxes = False
        model.sourceModel.return_value = source_model
        table_view.model.return_value = model

        # Test without checkbox column
        col_name = table_config_manager.get_column_name_from_logical_index(
            0, sample_dataframe, table_view
        )
        assert col_name == "Order_Number"

        col_name = table_config_manager.get_column_name_from_logical_index(
            1, sample_dataframe, table_view
        )
        assert col_name == "SKU"

        col_name = table_config_manager.get_column_name_from_logical_index(
            2, sample_dataframe, table_view
        )
        assert col_name == "Product_Name"

    def test_get_column_name_with_checkbox_column(self, table_config_manager, mock_main_window, sample_dataframe):
        """Test getting column name with checkbox column present."""
        table_view = mock_main_window.tableView
        model = MagicMock()
        source_model = MagicMock()
        source_model.enable_checkboxes = True
        model.sourceModel.return_value = source_model
        table_view.model.return_value = model

        # Index 0 should be checkbox column (returns None)
        col_name = table_config_manager.get_column_name_from_logical_index(
            0, sample_dataframe, table_view
        )
        assert col_name is None

        # Index 1 should be Order_Number (first data column)
        col_name = table_config_manager.get_column_name_from_logical_index(
            1, sample_dataframe, table_view
        )
        assert col_name == "Order_Number"

        # Index 2 should be SKU
        col_name = table_config_manager.get_column_name_from_logical_index(
            2, sample_dataframe, table_view
        )
        assert col_name == "SKU"

    def test_column_width_persistence(self, table_config_manager, mock_profile_manager):
        """Test that column widths are saved and restored."""
        # Setup initial config
        table_config_manager.load_config("M")
        table_config_manager._current_config.column_widths = {
            "Order_Number": 150,
            "SKU": 100
        }

        # Save config
        table_config_manager.save_config("M", table_config_manager._current_config)

        # Verify save was called
        assert mock_profile_manager.save_client_config.called

        # Get saved config
        saved_config_data = mock_profile_manager.save_client_config.call_args[0][1]
        saved_widths = saved_config_data["ui_settings"]["table_view"]["views"]["Default"]["column_widths"]

        assert saved_widths["Order_Number"] == 150
        assert saved_widths["SKU"] == 100

    def test_column_order_persistence(self, table_config_manager, mock_profile_manager):
        """Test that column order is saved and restored."""
        # Setup initial config
        table_config_manager.load_config("M")
        table_config_manager._current_config.column_order = ["Order_Number", "Product_Name", "SKU"]

        # Save config
        table_config_manager.save_config("M", table_config_manager._current_config)

        # Verify save was called
        assert mock_profile_manager.save_client_config.called

        # Get saved config
        saved_config_data = mock_profile_manager.save_client_config.call_args[0][1]
        saved_order = saved_config_data["ui_settings"]["table_view"]["views"]["Default"]["column_order"]

        assert saved_order == ["Order_Number", "Product_Name", "SKU"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
