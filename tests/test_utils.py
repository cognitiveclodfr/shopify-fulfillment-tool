"""Unit tests for the utility functions.

This module contains tests for the helper functions in `shopify_tool/utils.py`,
such as path handling for different operating systems and execution environments.
"""

import os
import sys


from shopify_tool import utils


def test_get_persistent_data_path_windows(mocker) -> None:
    """Tests the persistent data path on Windows using APPDATA.

    Args:
        mocker: The pytest-mock fixture for mocking objects.
    """
    mocker.patch("os.name", "nt")
    mocker.patch("os.getenv", return_value="/appdata")
    mock_makedirs = mocker.patch("os.makedirs")
    mocker.patch("os.path.join", side_effect=os.path.join)

    path = utils.get_persistent_data_path("test.json")

    expected_dir = os.path.join("/appdata", "ShopifyFulfillmentTool")
    mock_makedirs.assert_called_once_with(expected_dir, exist_ok=True)
    assert path == os.path.join(expected_dir, "test.json")


def test_get_persistent_data_path_other_os(mocker) -> None:
    """Tests the persistent data path on non-Windows OS using home directory.

    Args:
        mocker: The pytest-mock fixture for mocking objects.
    """
    mocker.patch("os.name", "posix")
    mocker.patch("os.getenv", return_value=None)
    mocker.patch("os.path.expanduser", return_value="/home/user")
    mock_makedirs = mocker.patch("os.makedirs")
    mocker.patch("os.path.join", side_effect=os.path.join)

    path = utils.get_persistent_data_path("test.json")

    expected_dir = os.path.join("/home/user", "ShopifyFulfillmentTool")
    mock_makedirs.assert_called_once_with(expected_dir, exist_ok=True)
    assert path == os.path.join(expected_dir, "test.json")


def test_get_persistent_data_path_os_error(mocker) -> None:
    """Tests that the function falls back to the current directory on OSError.

    Args:
        mocker: The pytest-mock fixture for mocking objects.
    """
    mocker.patch("os.getenv", return_value="/appdata")
    mocker.patch("os.makedirs", side_effect=OSError("Permission denied"))
    mocker.patch("os.path.join", side_effect=os.path.join)
    mock_logger = mocker.patch("shopify_tool.utils.logger.error")

    path = utils.get_persistent_data_path("test.json")

    mock_logger.assert_called_once()
    assert path == os.path.join(".", "test.json")


def test_resource_path_dev_mode(mocker) -> None:
    """Tests that the resource path is correct in a development environment.

    Args:
        mocker: The pytest-mock fixture for mocking objects.
    """
    mocker.patch("os.path.abspath", return_value="/dev/path")
    mocker.patch("os.path.join", side_effect=os.path.join)

    # Ensure sys._MEIPASS does not exist to simulate dev environment
    if hasattr(sys, "_MEIPASS"):
        delattr(sys, "_MEIPASS")

    path = utils.resource_path("data/file.txt")
    assert path == os.path.join("/dev/path", "data/file.txt")


def test_resource_path_pyinstaller_mode(mocker) -> None:
    """Tests that the resource path is correct in a PyInstaller bundle.

    Args:
        mocker: The pytest-mock fixture for mocking objects.
    """
    mocker.patch("os.path.join", side_effect=os.path.join)
    # Mock the PyInstaller-specific attribute
    mocker.patch.object(sys, "_MEIPASS", "/frozen/path", create=True)

    path = utils.resource_path("data/file.txt")
    assert path == os.path.join("/frozen/path", "data/file.txt")
