"""Tests for ClientSelectorWidget."""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest
from unittest.mock import Mock, patch, MagicMock

# Set Qt platform to offscreen for CI/headless environments
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from gui.client_settings_dialog import ClientSelectorWidget, ClientCreationDialog
from shopify_tool.profile_manager import ProfileManager, ValidationError
from shopify_tool.groups_manager import GroupsManager


@pytest.fixture
def mock_profile_manager():
    """Create a mock ProfileManager."""
    pm = Mock(spec=ProfileManager)
    pm.list_clients.return_value = ["M", "A", "B"]
    pm.client_exists.return_value = True
    return pm


@pytest.fixture
def client_selector(qtbot, mock_profile_manager):
    """Create a ClientSelectorWidget for testing."""
    widget = ClientSelectorWidget(mock_profile_manager)
    qtbot.addWidget(widget)
    return widget


def test_client_selector_initialization(client_selector, mock_profile_manager):
    """Test that ClientSelectorWidget initializes correctly."""
    # Should load clients on initialization
    mock_profile_manager.list_clients.assert_called_once()

    # Should populate combo box
    assert client_selector.client_combo.count() == 3
    assert client_selector.client_combo.itemText(0) == "M"


def test_client_selector_emits_signal_on_change(qtbot, client_selector):
    """Test that client_changed signal is emitted when selection changes."""
    with qtbot.waitSignal(client_selector.client_changed, timeout=1000) as blocker:
        client_selector.client_combo.setCurrentIndex(1)

    # Check that signal was emitted with correct client ID
    assert blocker.args == ["A"]


def test_client_selector_refresh_clients(client_selector, mock_profile_manager):
    """Test refreshing client list."""
    # Change mock to return different clients
    mock_profile_manager.list_clients.return_value = ["M", "A", "B", "C"]

    # Refresh
    client_selector.refresh_clients()

    # Should reload clients
    assert client_selector.client_combo.count() == 4


def test_client_selector_no_clients_available(qtbot, mock_profile_manager):
    """Test behavior when no clients are available."""
    mock_profile_manager.list_clients.return_value = []

    widget = ClientSelectorWidget(mock_profile_manager)
    qtbot.addWidget(widget)

    # Should show "(No clients available)"
    assert widget.client_combo.count() == 1
    assert widget.client_combo.itemText(0) == "(No clients available)"
    assert not widget.client_combo.isEnabled()


def test_client_creation_dialog_validation(qtbot, mock_profile_manager):
    """Test client creation dialog validation."""
    dialog = ClientCreationDialog(mock_profile_manager)
    qtbot.addWidget(dialog)

    # Test empty client ID
    with patch.object(ProfileManager, 'validate_client_id', return_value=(False, "Client ID is required")):
        with patch('gui.client_settings_dialog.QMessageBox.warning') as mock_warning:
            dialog.validate_and_accept()
            mock_warning.assert_called_once()


def test_client_creation_dialog_success(qtbot, mock_profile_manager):
    """Test successful client creation."""
    mock_profile_manager.create_client_profile.return_value = True

    dialog = ClientCreationDialog(mock_profile_manager)
    qtbot.addWidget(dialog)

    # Set valid inputs
    dialog.client_id_input.setText("TEST")
    dialog.client_name_input.setText("Test Client")

    with patch.object(ProfileManager, 'validate_client_id', return_value=(True, "")):
        with patch('gui.client_settings_dialog.QMessageBox.information') as mock_info:
            dialog.validate_and_accept()
            mock_info.assert_called_once()
            mock_profile_manager.create_client_profile.assert_called_once_with("TEST", "Test Client")


def test_get_current_client_id(client_selector):
    """Test getting current client ID."""
    client_selector.client_combo.setCurrentIndex(0)
    assert client_selector.get_current_client_id() == "M"


def test_set_current_client_id(client_selector):
    """Test setting current client ID."""
    client_selector.set_current_client_id("B")
    assert client_selector.client_combo.currentText() == "B"


# ==================== Enhanced ClientCreationDialog Tests ====================


@pytest.fixture
def mock_groups_manager():
    """Create a mock GroupsManager."""
    gm = Mock(spec=GroupsManager)
    gm.list_groups.return_value = [
        {"id": "group-1", "name": "VIP Clients", "color": "#FF5722"},
        {"id": "group-2", "name": "Priority", "color": "#2196F3"}
    ]
    return gm


def test_client_creation_dialog_with_groups_manager(qtbot, mock_profile_manager, mock_groups_manager):
    """Test that dialog with groups_manager populates dropdown."""
    dialog = ClientCreationDialog(
        profile_manager=mock_profile_manager,
        groups_manager=mock_groups_manager
    )
    qtbot.addWidget(dialog)

    # Should load groups into combo
    mock_groups_manager.list_groups.assert_called_once()

    # Combo should have 3 items: "(No group)" + 2 groups
    assert dialog.group_combo.count() == 3
    assert dialog.group_combo.itemText(0) == "(No group)"
    assert dialog.group_combo.itemText(1) == "VIP Clients"
    assert dialog.group_combo.itemText(2) == "Priority"


def test_client_creation_dialog_without_groups_manager(qtbot, mock_profile_manager):
    """Test that dialog without groups_manager disables dropdown."""
    dialog = ClientCreationDialog(
        profile_manager=mock_profile_manager,
        groups_manager=None
    )
    qtbot.addWidget(dialog)

    # Group combo should be disabled
    assert not dialog.group_combo.isEnabled()


def test_client_creation_dialog_color_picker(qtbot, mock_profile_manager):
    """Test color picker changes current_color."""
    dialog = ClientCreationDialog(mock_profile_manager)
    qtbot.addWidget(dialog)

    # Default color should be set
    assert dialog.current_color == "#4CAF50"

    # Mock color dialog to return new color
    from PySide6.QtGui import QColor
    with patch('gui.client_settings_dialog.QColorDialog.getColor') as mock_color_dialog:
        new_color = QColor("#FF0000")
        mock_color_dialog.return_value = new_color

        # Click color button
        dialog.color_button.click()

        # Color should be updated
        assert dialog.current_color == "#ff0000"  # Qt normalizes to lowercase


def test_client_creation_dialog_pin_checkbox(qtbot, mock_profile_manager):
    """Test pin checkbox state."""
    dialog = ClientCreationDialog(mock_profile_manager)
    qtbot.addWidget(dialog)

    # Initially unchecked
    assert not dialog.pin_checkbox.isChecked()

    # Check it
    dialog.pin_checkbox.setChecked(True)
    assert dialog.pin_checkbox.isChecked()


def test_client_creation_dialog_saves_ui_settings(qtbot, mock_profile_manager, mock_groups_manager):
    """Test that ui_settings are saved on creation."""
    mock_profile_manager.create_client_profile.return_value = True

    dialog = ClientCreationDialog(
        profile_manager=mock_profile_manager,
        groups_manager=mock_groups_manager
    )
    qtbot.addWidget(dialog)

    # Set form values
    dialog.client_id_input.setText("TEST")
    dialog.client_name_input.setText("Test Client")
    dialog.pin_checkbox.setChecked(True)
    dialog.group_combo.setCurrentIndex(1)  # Select first group
    dialog.current_color = "#FF5722"

    with patch.object(ProfileManager, 'validate_client_id', return_value=(True, "")):
        with patch('gui.client_settings_dialog.QMessageBox.information'):
            dialog.validate_and_accept()

            # Should create profile
            mock_profile_manager.create_client_profile.assert_called_once_with("TEST", "Test Client")

            # Should update ui_settings
            mock_profile_manager.update_ui_settings.assert_called_once()
            call_args = mock_profile_manager.update_ui_settings.call_args
            client_id = call_args[0][0]
            ui_settings = call_args[0][1]

            assert client_id == "TEST"
            assert ui_settings["is_pinned"] is True
            assert ui_settings["custom_color"] == "#FF5722"
            assert ui_settings["group_id"] == "group-1"  # First group ID
            assert ui_settings["custom_badges"] == []
            assert ui_settings["display_order"] == 0


def test_client_creation_dialog_color_picker_cancel(qtbot, mock_profile_manager):
    """Test that canceling color picker keeps original color."""
    dialog = ClientCreationDialog(mock_profile_manager)
    qtbot.addWidget(dialog)

    original_color = dialog.current_color

    # Mock color dialog to return invalid color (user canceled)
    from PySide6.QtGui import QColor
    with patch('gui.client_settings_dialog.QColorDialog.getColor') as mock_color_dialog:
        invalid_color = QColor()  # Invalid color
        mock_color_dialog.return_value = invalid_color

        # Click color button
        dialog.color_button.click()

        # Color should remain unchanged
        assert dialog.current_color == original_color
