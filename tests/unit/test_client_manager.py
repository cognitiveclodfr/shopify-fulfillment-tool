"""
Unit tests for ClientManager.

These tests verify that the ClientManager correctly:
1. Creates clients with exact reference structure
2. Validates and repairs missing config keys
3. Creates session directories correctly
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from common.client_manager import ClientManager


@pytest.fixture
def temp_server_path():
    """Create a temporary directory to simulate the file server."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def manager(temp_server_path):
    """Create a ClientManager instance with temporary path."""
    return ClientManager(temp_server_path)


def test_create_client_structure(manager, temp_server_path):
    """Verify new client has exact reference structure."""
    client_id = "CLIENT_TEST"
    client_name = "Test Client"

    success = manager.create_client(client_id, client_name)
    assert success, "Client creation failed"

    # Load and verify structure
    config = manager.load_config(client_id)

    # Check top-level fields
    assert config["client_id"] == client_id
    assert config["name"] == client_name
    assert config["active"] == True
    assert "created_at" in config
    assert "updated_at" in config

    # Check shopify section exists
    assert "shopify" in config

    # Check all required shopify keys
    required_keys = [
        "column_mappings", "settings", "courier_mappings",
        "rules", "packing_lists", "stock_exports",
        "virtual_products", "deduction_rules"
    ]
    for key in required_keys:
        assert key in config["shopify"], f"Missing key: {key}"

    # Verify column_mappings structure
    assert "orders" in config["shopify"]["column_mappings"]
    assert "stock" in config["shopify"]["column_mappings"]
    assert "orders_required" in config["shopify"]["column_mappings"]
    assert "stock_required" in config["shopify"]["column_mappings"]

    # Verify orders column mappings have all required fields
    orders_mappings = config["shopify"]["column_mappings"]["orders"]
    assert "name" in orders_mappings
    assert "sku" in orders_mappings
    assert "quantity" in orders_mappings
    assert "shipping_provider" in orders_mappings
    assert "fulfillment_status" in orders_mappings
    assert "financial_status" in orders_mappings
    assert "order_number" in orders_mappings

    # Verify stock column mappings
    stock_mappings = config["shopify"]["column_mappings"]["stock"]
    assert "sku" in stock_mappings
    assert "stock" in stock_mappings

    # Verify courier_mappings structure
    assert config["shopify"]["courier_mappings"]["type"] == "pattern_matching"
    assert "rules" in config["shopify"]["courier_mappings"]
    assert len(config["shopify"]["courier_mappings"]["rules"]) > 0
    assert config["shopify"]["courier_mappings"]["default"] == "Other"

    # Verify settings
    assert "stock_csv_delimiter" in config["shopify"]["settings"]
    assert "low_stock_threshold" in config["shopify"]["settings"]


def test_session_directory_creation(manager, temp_server_path):
    """Test that session directories are created correctly."""
    client_id = "CLIENT_TEST"
    manager.create_client(client_id, "Test")

    # Ensure session dir
    success = manager.ensure_client_session_dir(client_id)
    assert success

    # Check path structure
    session_dir = manager.get_session_dir(client_id)
    expected = Path(temp_server_path) / "SESSIONS" / client_id
    assert session_dir == expected
    assert session_dir.exists()


def test_session_directory_with_session_name(manager, temp_server_path):
    """Test session directory creation with specific session name."""
    client_id = "CLIENT_TEST"
    manager.create_client(client_id, "Test")

    session_name = "Session_2025-11-04_10-30-00"
    session_dir = manager.get_session_dir(client_id, session_name)

    # Create the directory
    session_dir.mkdir(parents=True, exist_ok=True)

    # Verify structure
    expected = Path(temp_server_path) / "SESSIONS" / client_id / session_name
    assert session_dir == expected
    assert session_dir.exists()


def test_client_already_exists(manager):
    """Test that creating duplicate client returns False."""
    client_id = "CLIENT_TEST"

    success1 = manager.create_client(client_id, "Test")
    assert success1

    success2 = manager.create_client(client_id, "Test")
    assert not success2


def test_load_and_save_config(manager):
    """Test loading and saving client config."""
    client_id = "CLIENT_TEST"
    manager.create_client(client_id, "Test")

    # Load config
    config = manager.load_config(client_id)

    # Modify config
    config["shopify"]["rules"].append({"name": "Test Rule"})

    # Save config
    success = manager.save_config(client_id, config)
    assert success

    # Load again and verify
    config2 = manager.load_config(client_id)
    assert len(config2["shopify"]["rules"]) == 1
    assert config2["shopify"]["rules"][0]["name"] == "Test Rule"


def test_list_clients(manager):
    """Test listing active clients."""
    # Create multiple clients
    manager.create_client("CLIENT_A", "Client A")
    manager.create_client("CLIENT_B", "Client B")

    clients = manager.list_clients()

    assert len(clients) == 2
    client_ids = [c["client_id"] for c in clients]
    assert "CLIENT_A" in client_ids
    assert "CLIENT_B" in client_ids


def test_delete_client_marks_inactive(manager):
    """Test that delete marks client as inactive."""
    client_id = "CLIENT_TEST"
    manager.create_client(client_id, "Test")

    # Delete (soft delete)
    success = manager.delete_client(client_id)
    assert success

    # Client should not appear in list
    clients = manager.list_clients()
    client_ids = [c["client_id"] for c in clients]
    assert client_id not in client_ids

    # But config should still exist and be marked inactive
    config = manager.load_config(client_id)
    assert config["active"] == False


def test_sku_mapping_operations(manager):
    """Test SKU mapping load and save."""
    client_id = "CLIENT_TEST"
    manager.create_client(client_id, "Test")

    # Load initial (should be empty)
    mappings = manager.load_sku_mapping(client_id)
    assert len(mappings) == 0

    # Save new mappings
    new_mappings = {
        "SKU001": "Product A",
        "SKU002": "Product B"
    }
    success = manager.save_sku_mapping(client_id, new_mappings)
    assert success

    # Load and verify
    mappings = manager.load_sku_mapping(client_id)
    assert len(mappings) == 2
    assert mappings["SKU001"] == "Product A"
    assert mappings["SKU002"] == "Product B"
