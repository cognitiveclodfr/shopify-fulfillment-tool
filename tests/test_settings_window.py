import sys
import os
import pytest
from unittest.mock import MagicMock, mock_open

from PySide6.QtWidgets import QWidget, QDialogButtonBox, QPushButton, QApplication

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gui.settings_window_pyside import SettingsWindow


@pytest.fixture
def mock_settings_dependencies(mocker):
    """Mocks dependencies for the SettingsWindow."""
    mock_parent = QWidget()

    mock_parent.config = {
        "settings": {"low_stock_threshold": 10, "stock_csv_delimiter": ";"},
        "paths": {"templates": "data/templates", "output_dir_stock": "data/output"},
        "column_mappings": {},
        "rules": [],
        "packing_lists": [],
        "stock_exports": [],
    }

    mocker.patch("builtins.open", mock_open())

    return mock_parent


@pytest.fixture
def settings_app(qtbot, mock_settings_dependencies):
    """Fixture to create the settings window."""
    window = SettingsWindow(mock_settings_dependencies, mock_settings_dependencies.config)
    qtbot.addWidget(window)
    yield window
    window.close()


def test_settings_window_creation(settings_app):
    """Test that the SettingsWindow can be created and loads initial values."""
    assert settings_app is not None
    assert settings_app.windowTitle() == "Application Settings"
    assert settings_app.low_stock_edit.text() == "10"


def test_save_settings(settings_app, mocker):
    """Test that saving the settings updates the config data."""
    settings_app.low_stock_edit.setText("25")

    settings_app.accept = MagicMock()

    save_button = settings_app.findChild(QDialogButtonBox).button(QDialogButtonBox.Save)
    save_button.click()

    assert settings_app.config_data["settings"]["low_stock_threshold"] == 25

    settings_app.accept.assert_called_once()


def test_add_and_remove_rule(settings_app, qtbot):
    """Test that adding and removing a rule updates the UI and internal state."""
    assert len(settings_app.rule_widgets) == 0

    rules_tab = settings_app.findChild(QWidget, "rules_tab")
    add_rule_btn = rules_tab.findChild(QPushButton, "add_rule_btn")
    add_rule_btn.click()

    assert len(settings_app.rule_widgets) == 1

    rule_widget_refs = settings_app.rule_widgets[0]
    delete_button = rule_widget_refs["group_box"].findChild(QPushButton, "delete_rule_btn")
    delete_button.click()

    QApplication.processEvents()

    assert len(settings_app.rule_widgets) == 0
    assert not rule_widget_refs["group_box"].isVisible()
