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
