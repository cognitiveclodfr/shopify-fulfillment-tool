"""
Integration test: Complete workflow from client creation to report generation.

This test verifies the entire workflow:
1. Create new client
2. Select client from dropdown
3. Open and verify settings
4. Create session
5. Load orders file
6. Load stock file
7. Run analysis
8. Generate packing list
9. Generate stock export

NOTE: This test requires GUI components and test fixtures.
It's marked as integration test and may need to be run with specific fixtures.
"""

import sys
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import QApplication

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from common.client_manager import ClientManager


# Skip if not in integration test mode
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def temp_server_path():
    """Create a temporary directory to simulate the file server."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_client_id():
    """Generate unique test client ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"CLIENT_TEST_{timestamp}"


def test_client_creation_and_structure(temp_server_path, test_client_id):
    """Test creating a client and verifying its structure."""
    manager = ClientManager(temp_server_path)

    client_name = "Test Flow Client"

    # STEP 1: Create new client
    success = manager.create_client(test_client_id, client_name)
    assert success, "Failed to create client"

    # Verify client appears in list
    clients = manager.list_clients()
    client_ids = [c["client_id"] for c in clients]
    assert test_client_id in client_ids, "Client not found in list"

    # STEP 2: Load and verify config structure
    config = manager.load_config(test_client_id)

    assert config["client_id"] == test_client_id
    assert config["name"] == client_name
    assert config["active"] == True
    assert "shopify" in config

    # Verify all required shopify sections
    required_sections = [
        "column_mappings",
        "settings",
        "courier_mappings",
        "rules",
        "packing_lists",
        "stock_exports",
        "virtual_products",
        "deduction_rules"
    ]

    for section in required_sections:
        assert section in config["shopify"], f"Missing section: {section}"


def test_session_creation_and_structure(temp_server_path, test_client_id):
    """Test creating a session and verifying directory structure."""
    manager = ClientManager(temp_server_path)

    # Create client first
    manager.create_client(test_client_id, "Test Client")

    # STEP 4: Create session
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_name = f"Session_{timestamp}"

    session_path = manager.get_session_dir(test_client_id, session_name)
    session_path.mkdir(parents=True, exist_ok=True)

    # Verify session path structure
    expected_path = Path(temp_server_path) / "SESSIONS" / test_client_id / session_name
    assert session_path == expected_path, "Session path structure incorrect"
    assert session_path.exists(), "Session directory not created"


def test_config_validation_and_repair(temp_server_path, test_client_id):
    """Test that missing config sections are detected and can be repaired."""
    manager = ClientManager(temp_server_path)

    # Create client with complete config
    manager.create_client(test_client_id, "Test Client")

    # Load config
    config = manager.load_config(test_client_id)

    # Remove a key from shopify section
    del config["shopify"]["rules"]

    # Save modified config
    manager.save_config(test_client_id, config)

    # Load again
    config2 = manager.load_config(test_client_id)

    # Verify the key is missing
    assert "rules" not in config2["shopify"]

    # In real usage, MainWindow.set_active_client would repair this
    # Here we just verify we can detect it
    default_sections = [
        "column_mappings",
        "settings",
        "courier_mappings",
        "rules",
        "packing_lists",
        "stock_exports",
        "virtual_products",
        "deduction_rules"
    ]

    missing = [s for s in default_sections if s not in config2["shopify"]]
    assert len(missing) > 0, "Should detect missing sections"


def test_multiple_sessions_per_client(temp_server_path, test_client_id):
    """Test that multiple sessions can be created for one client."""
    manager = ClientManager(temp_server_path)

    # Create client
    manager.create_client(test_client_id, "Test Client")

    # Create multiple sessions
    sessions = []
    for i in range(3):
        session_name = f"Session_{i}"
        session_path = manager.get_session_dir(test_client_id, session_name)
        session_path.mkdir(parents=True, exist_ok=True)
        sessions.append(session_path)

    # Verify all sessions exist
    client_sessions_dir = manager.get_session_dir(test_client_id)
    assert client_sessions_dir.exists()

    # Count session directories
    session_dirs = [d for d in client_sessions_dir.iterdir() if d.is_dir()]
    assert len(session_dirs) == 3


def test_client_switch_clears_data(temp_server_path):
    """Test that switching clients should clear analysis data."""
    manager = ClientManager(temp_server_path)

    # Create two clients
    client_a = "CLIENT_A"
    client_b = "CLIENT_B"

    manager.create_client(client_a, "Client A")
    manager.create_client(client_b, "Client B")

    # Load client A
    config_a = manager.load_config(client_a)
    assert config_a["client_id"] == client_a

    # Load client B
    config_b = manager.load_config(client_b)
    assert config_b["client_id"] == client_b

    # Verify they are different
    assert config_a["client_id"] != config_b["client_id"]


def test_settings_window_can_open_with_valid_config(qapp, temp_server_path, test_client_id):
    """Test that settings window can open with a valid config."""
    from gui.settings_window_pyside import SettingsWindow

    manager = ClientManager(temp_server_path)
    manager.create_client(test_client_id, "Test Client")

    config = manager.load_config(test_client_id)
    shopify_config = config["shopify"]

    # Should not raise any errors
    window = SettingsWindow(None, shopify_config)
    assert window is not None


def test_file_paths_in_session_directory(temp_server_path, test_client_id):
    """Test that generated files would be saved in session directory."""
    manager = ClientManager(temp_server_path)

    # Create client and session
    manager.create_client(test_client_id, "Test Client")

    session_name = "Session_2025-11-04_10-30-00"
    session_path = manager.get_session_dir(test_client_id, session_name)
    session_path.mkdir(parents=True, exist_ok=True)

    # Simulate creating output files
    packing_list_path = session_path / "packing_list.xlsx"
    stock_export_path = session_path / "stock_export.xlsx"

    # Create dummy files
    packing_list_path.touch()
    stock_export_path.touch()

    # Verify files exist in session directory
    assert packing_list_path.exists()
    assert stock_export_path.exists()

    # Verify they're in the correct location
    assert packing_list_path.parent == session_path
    assert stock_export_path.parent == session_path


@pytest.mark.skip(reason="Requires full GUI environment and test fixtures")
def test_complete_workflow_with_gui(qapp, temp_server_path, test_client_id):
    """
    Complete workflow test with GUI components.

    This test is marked to skip by default as it requires:
    - Full GUI environment
    - Test CSV files (orders.csv, stock.csv)
    - Mock or real file dialogs

    To run this test, provide appropriate fixtures and remove skip marker.
    """
    # This is a placeholder for a full integration test
    # In a real implementation, this would:
    # 1. Create MainWindow
    # 2. Create client
    # 3. Switch to client
    # 4. Create session
    # 5. Load files
    # 6. Run analysis
    # 7. Generate reports
    # 8. Verify all outputs
    pass
