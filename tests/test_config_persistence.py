import sys
import os
import pytest
import json
import shutil
from unittest.mock import MagicMock

# Add the root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We need to import the App class to test its methods
from gui_main import App

@pytest.fixture
def mock_app_environment(tmp_path, mocker):
    """
    Sets up a mocked environment for the App class, simulating a home directory
    and an application resource directory.
    """
    # 1. Create mock directories
    app_data_dir = tmp_path / "appdata"
    app_data_dir.mkdir()

    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()

    # 2. Create a default config.json in the "bundle"
    default_config_content = {"settings": {"default_setting": "true"}}
    default_config_path = bundle_dir / "config.json"
    with open(default_config_path, 'w') as f:
        json.dump(default_config_content, f)

    # 3. Mock the helper functions to use our temporary paths
    mocker.patch('gui_main.get_persistent_data_path', return_value=str(app_data_dir / "config.json"))
    mocker.patch('gui_main.resource_path', return_value=str(default_config_path))

    # Mock the GUI components that are not needed for this test
    mocker.patch('customtkinter.CTk.__init__', return_value=None)
    mocker.patch('tkinter.messagebox.showerror', return_value=None)

    return {
        "app_data_dir": app_data_dir,
        "bundle_dir": bundle_dir,
        "default_config": default_config_content
    }

def test_first_launch_copies_config(mock_app_environment):
    """
    Tests if the config file is copied from the bundle to the app data
    directory on the first launch.
    """
    app_data_dir = mock_app_environment["app_data_dir"]
    user_config_path = app_data_dir / "config.json"

    # Pre-condition: User config does not exist
    assert not os.path.exists(user_config_path)

    # Instantiate a mock App object instead of a real one
    app = MagicMock()
    app.config = None
    app.config_path = None
    # We need a dummy after method for the error case in the tested function
    app.after = MagicMock()

    # Manually call the unbound method, passing the mock instance as 'self'
    App._init_and_load_config(app)

    # Assertions
    # 1. The user config file should now exist.
    assert os.path.exists(user_config_path)

    # 2. The content of the user config should match the default config.
    with open(user_config_path, 'r') as f:
        user_config_content = json.load(f)
    assert user_config_content == mock_app_environment["default_config"]

    # 3. The app's loaded config should match the default.
    assert app.config == mock_app_environment["default_config"]
    assert app.config_path == str(user_config_path)

def test_subsequent_launch_uses_existing_config(mock_app_environment):
    """
    Tests that an existing user config is loaded and not overwritten by the default.
    """
    app_data_dir = mock_app_environment["app_data_dir"]
    user_config_path = app_data_dir / "config.json"

    # Pre-condition: Create a modified user config file
    modified_config_content = {"settings": {"user_setting": "custom_value"}}
    with open(user_config_path, 'w') as f:
        json.dump(modified_config_content, f)

    # Instantiate a mock App object
    app = MagicMock()
    app.config = None
    app.config_path = None
    app.after = MagicMock()

    # Manually call the unbound method, passing the mock instance as 'self'
    App._init_and_load_config(app)

    # Assertions
    # 1. The app's loaded config should match the *modified* user config.
    assert app.config == modified_config_content

    # 2. The config file on disk should still be the modified version.
    with open(user_config_path, 'r') as f:
        on_disk_content = json.load(f)
    assert on_disk_content == modified_config_content
    assert app.config_path == str(user_config_path)
