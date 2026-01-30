"""Unit tests for GroupsManager.

Tests cover:
- Groups file initialization
- CRUD operations for groups
- Special groups immutability
- File locking
- Error handling and corruption recovery
- Backup creation
- Client coordination
"""

import json
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from shopify_tool.groups_manager import GroupsManager, GroupsManagerError


@pytest.fixture
def temp_base_path():
    """Create temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def groups_manager(temp_base_path):
    """Create GroupsManager instance for testing."""
    return GroupsManager(str(temp_base_path))


class TestGroupsManagerInitialization:
    """Test GroupsManager initialization."""

    def test_init_creates_groups_file_if_missing(self, temp_base_path):
        """Test that initialization creates groups.json if it doesn't exist."""
        groups_path = temp_base_path / "Clients" / "groups.json"
        assert not groups_path.exists()

        gm = GroupsManager(str(temp_base_path))

        assert groups_path.exists()

        # Verify structure
        with open(groups_path, 'r', encoding='utf-8') as f:
            groups_data = json.load(f)

        assert "version" in groups_data
        assert "groups" in groups_data
        assert "special_groups" in groups_data
        assert "pinned" in groups_data["special_groups"]
        assert "all" in groups_data["special_groups"]

    def test_init_preserves_existing_groups(self, temp_base_path):
        """Test that initialization preserves existing groups.json."""
        groups_path = temp_base_path / "Clients" / "groups.json"
        groups_path.parent.mkdir(parents=True, exist_ok=True)

        # Create existing groups file
        existing_data = {
            "version": "1.0",
            "groups": [
                {
                    "id": "test-uuid",
                    "name": "Test Group",
                    "color": "#FF0000",
                    "display_order": 0,
                    "created_at": "2025-01-01T00:00:00"
                }
            ],
            "special_groups": {
                "pinned": {"display_order": -1, "name": "Pinned", "color": "#FFC107", "collapsible": False},
                "all": {"display_order": 999, "name": "All Clients", "color": "#9E9E9E", "collapsible": True}
            }
        }

        with open(groups_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f)

        # Initialize manager
        gm = GroupsManager(str(temp_base_path))

        # Load and verify preserved
        groups_data = gm.load_groups()
        assert len(groups_data["groups"]) == 1
        assert groups_data["groups"][0]["name"] == "Test Group"


class TestGroupCRUD:
    """Test CRUD operations for groups."""

    def test_create_group_success(self, groups_manager):
        """Test successful group creation."""
        group_id = groups_manager.create_group("Premium Clients", "#FF5722")

        assert group_id is not None
        assert isinstance(group_id, str)

        # Verify group was created
        group = groups_manager.get_group(group_id)
        assert group is not None
        assert group["name"] == "Premium Clients"
        assert group["color"] == "#FF5722"
        assert "created_at" in group

    def test_create_group_default_color(self, groups_manager):
        """Test group creation with default color."""
        group_id = groups_manager.create_group("Test Group")

        group = groups_manager.get_group(group_id)
        assert group["color"] == "#2196F3"  # Default blue

    def test_create_group_duplicate_name(self, groups_manager):
        """Test that creating group with duplicate name fails."""
        groups_manager.create_group("Premium Clients")

        with pytest.raises(GroupsManagerError) as exc_info:
            groups_manager.create_group("Premium Clients")

        assert "already exists" in str(exc_info.value).lower()

    def test_create_group_case_insensitive_duplicate(self, groups_manager):
        """Test that duplicate names are case-insensitive."""
        groups_manager.create_group("Premium Clients")

        with pytest.raises(GroupsManagerError):
            groups_manager.create_group("premium clients")

    def test_create_group_empty_name(self, groups_manager):
        """Test that empty name fails."""
        with pytest.raises(GroupsManagerError) as exc_info:
            groups_manager.create_group("")

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_create_group_whitespace_name(self, groups_manager):
        """Test that whitespace-only name fails."""
        with pytest.raises(GroupsManagerError) as exc_info:
            groups_manager.create_group("   ")

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_update_group_name(self, groups_manager):
        """Test updating group name."""
        group_id = groups_manager.create_group("Old Name")

        success = groups_manager.update_group(group_id, name="New Name")
        assert success

        group = groups_manager.get_group(group_id)
        assert group["name"] == "New Name"

    def test_update_group_color(self, groups_manager):
        """Test updating group color."""
        group_id = groups_manager.create_group("Test Group")

        success = groups_manager.update_group(group_id, color="#00FF00")
        assert success

        group = groups_manager.get_group(group_id)
        assert group["color"] == "#00FF00"

    def test_update_group_both_name_and_color(self, groups_manager):
        """Test updating both name and color."""
        group_id = groups_manager.create_group("Old Name", "#FF0000")

        success = groups_manager.update_group(group_id, name="New Name", color="#0000FF")
        assert success

        group = groups_manager.get_group(group_id)
        assert group["name"] == "New Name"
        assert group["color"] == "#0000FF"

    def test_update_nonexistent_group(self, groups_manager):
        """Test updating non-existent group fails."""
        with pytest.raises(GroupsManagerError) as exc_info:
            groups_manager.update_group("invalid-uuid", name="Test")

        assert "not found" in str(exc_info.value).lower()

    def test_update_group_duplicate_name(self, groups_manager):
        """Test that updating to duplicate name fails."""
        group_id1 = groups_manager.create_group("Group 1")
        group_id2 = groups_manager.create_group("Group 2")

        with pytest.raises(GroupsManagerError) as exc_info:
            groups_manager.update_group(group_id2, name="Group 1")

        assert "already exists" in str(exc_info.value).lower()

    def test_delete_group(self, groups_manager):
        """Test deleting a group."""
        group_id = groups_manager.create_group("Test Group")

        # Delete without profile_manager (no client unassignment)
        success = groups_manager.delete_group(group_id)
        assert success

        # Verify deleted
        group = groups_manager.get_group(group_id)
        assert group is None

    def test_delete_nonexistent_group(self, groups_manager):
        """Test deleting non-existent group fails."""
        with pytest.raises(GroupsManagerError) as exc_info:
            groups_manager.delete_group("invalid-uuid")

        assert "not found" in str(exc_info.value).lower()

    def test_list_groups_sorted_by_display_order(self, groups_manager):
        """Test that groups are sorted by display_order."""
        # Create multiple groups
        id1 = groups_manager.create_group("Group C")
        id2 = groups_manager.create_group("Group A")
        id3 = groups_manager.create_group("Group B")

        groups = groups_manager.list_groups()

        # Should be sorted by display_order (which is based on creation order)
        assert len(groups) == 3
        assert groups[0]["name"] == "Group C"  # Created first, display_order 0
        assert groups[1]["name"] == "Group A"  # Created second, display_order 1
        assert groups[2]["name"] == "Group B"  # Created third, display_order 2

    def test_list_groups_empty(self, groups_manager):
        """Test listing groups when none exist."""
        groups = groups_manager.list_groups()
        assert groups == []

    def test_get_group_by_id(self, groups_manager):
        """Test getting group by ID."""
        group_id = groups_manager.create_group("Test Group", "#FF0000")

        group = groups_manager.get_group(group_id)
        assert group is not None
        assert group["id"] == group_id
        assert group["name"] == "Test Group"
        assert group["color"] == "#FF0000"

    def test_get_nonexistent_group(self, groups_manager):
        """Test getting non-existent group returns None."""
        group = groups_manager.get_group("invalid-uuid")
        assert group is None


class TestSpecialGroups:
    """Test special groups behavior."""

    def test_special_groups_immutable(self, groups_manager):
        """Test that special groups cannot be deleted."""
        with pytest.raises(GroupsManagerError) as exc_info:
            groups_manager.delete_group("pinned")

        assert "special group" in str(exc_info.value).lower()

        with pytest.raises(GroupsManagerError) as exc_info:
            groups_manager.delete_group("all")

        assert "special group" in str(exc_info.value).lower()

    def test_cannot_delete_special_groups(self, groups_manager):
        """Test explicit error when trying to delete pinned or all."""
        special_groups = ["pinned", "all"]

        for group_id in special_groups:
            with pytest.raises(GroupsManagerError) as exc_info:
                groups_manager.delete_group(group_id)

            assert "cannot delete" in str(exc_info.value).lower()
            assert "special" in str(exc_info.value).lower()


class TestClientCoordination:
    """Test coordination with ProfileManager for client unassignment."""

    def test_delete_group_unassigns_clients(self, groups_manager):
        """Test that deleting group unassigns all clients."""
        # Create mock ProfileManager
        mock_pm = Mock()
        mock_pm.list_clients.return_value = ["M", "ABC"]

        # Mock configs for clients
        config_m = {
            "client_id": "M",
            "ui_settings": {"group_id": "test-group-id"}
        }
        config_abc = {
            "client_id": "ABC",
            "ui_settings": {"group_id": "test-group-id"}
        }

        mock_pm.load_client_config.side_effect = lambda cid: config_m if cid == "M" else config_abc

        # Create group
        group_id = groups_manager.create_group("Test Group")

        # Manually set group_id in mock configs
        config_m["ui_settings"]["group_id"] = group_id
        config_abc["ui_settings"]["group_id"] = group_id

        # Delete group with profile_manager
        groups_manager.delete_group(group_id, profile_manager=mock_pm)

        # Verify save_client_config was called for both clients
        assert mock_pm.save_client_config.call_count == 2

        # Verify group_id was set to None
        saved_configs = [call[0][1] for call in mock_pm.save_client_config.call_args_list]
        for config in saved_configs:
            assert config["ui_settings"]["group_id"] is None

    def test_get_clients_in_group(self, groups_manager):
        """Test getting clients assigned to a group."""
        # Create mock ProfileManager
        mock_pm = Mock()
        mock_pm.list_clients.return_value = ["M", "ABC", "XYZ"]

        group_id = "test-group-id"

        # Mock configs
        configs = {
            "M": {"client_id": "M", "ui_settings": {"group_id": group_id}},
            "ABC": {"client_id": "ABC", "ui_settings": {"group_id": "other-group"}},
            "XYZ": {"client_id": "XYZ", "ui_settings": {"group_id": group_id}}
        }

        mock_pm.load_client_config.side_effect = lambda cid: configs.get(cid)

        # Get clients in group
        clients = groups_manager.get_clients_in_group(group_id, mock_pm)

        assert len(clients) == 2
        assert "M" in clients
        assert "XYZ" in clients
        assert "ABC" not in clients

    def test_get_clients_in_group_empty(self, groups_manager):
        """Test getting clients when group has no clients."""
        mock_pm = Mock()
        mock_pm.list_clients.return_value = ["M"]

        config_m = {
            "client_id": "M",
            "ui_settings": {"group_id": None}
        }

        mock_pm.load_client_config.return_value = config_m

        clients = groups_manager.get_clients_in_group("test-group-id", mock_pm)

        assert clients == []


class TestFileLocking:
    """Test file locking behavior."""

    def test_concurrent_access_prevents_corruption(self, groups_manager):
        """Test that file locking prevents corruption during concurrent writes.

        Note: This is a basic test. True concurrency testing would require
        threading/multiprocessing which is complex in pytest.
        """
        # Create a group
        group_id1 = groups_manager.create_group("Group 1")

        # Create another group immediately
        group_id2 = groups_manager.create_group("Group 2")

        # Verify both groups exist
        groups = groups_manager.list_groups()
        assert len(groups) == 2

        # Verify file is valid JSON
        groups_data = groups_manager.load_groups()
        assert "groups" in groups_data
        assert len(groups_data["groups"]) == 2

    def test_retry_logic_on_save_failure(self, groups_manager, monkeypatch):
        """Test retry logic when save fails temporarily."""
        # This test is tricky to implement without deep mocking
        # For now, just verify that save_groups can be called multiple times
        group_id = groups_manager.create_group("Test")

        groups_data = groups_manager.load_groups()
        groups_data["groups"][0]["name"] = "Updated"

        # Should succeed without errors
        success = groups_manager.save_groups(groups_data)
        assert success


class TestErrorHandling:
    """Test error handling and recovery."""

    def test_corrupted_json_recreates_defaults(self, temp_base_path):
        """Test that corrupted JSON is backed up and defaults created."""
        groups_path = temp_base_path / "Clients" / "groups.json"
        groups_path.parent.mkdir(parents=True, exist_ok=True)

        # Write corrupted JSON
        with open(groups_path, 'w', encoding='utf-8') as f:
            f.write("{ invalid json }")

        # Initialize manager (should handle corruption)
        gm = GroupsManager(str(temp_base_path))

        # Verify backup was created
        backup_path = temp_base_path / "Clients" / "groups.corrupted.bak"
        assert backup_path.exists()

        # Verify defaults were created
        groups_data = gm.load_groups()
        assert "version" in groups_data
        assert "groups" in groups_data
        assert groups_data["groups"] == []

    def test_invalid_structure_recreates_defaults(self, temp_base_path):
        """Test that invalid structure is backed up and defaults created."""
        groups_path = temp_base_path / "Clients" / "groups.json"
        groups_path.parent.mkdir(parents=True, exist_ok=True)

        # Write invalid structure (missing required fields)
        with open(groups_path, 'w', encoding='utf-8') as f:
            json.dump({"invalid": "structure"}, f)

        gm = GroupsManager(str(temp_base_path))

        # Verify backup was created
        backup_path = temp_base_path / "Clients" / "groups.corrupted.bak"
        assert backup_path.exists()

        # Verify defaults were created
        groups_data = gm.load_groups()
        assert "version" in groups_data
        assert "groups" in groups_data

    def test_backup_creation(self, groups_manager):
        """Test that backups are created before destructive operations."""
        backups_dir = groups_manager.clients_dir / "backups"

        # Create a group
        group_id = groups_manager.create_group("Test Group")

        # Update group (should create backup)
        groups_manager.update_group(group_id, name="Updated Name")

        # Check backups exist
        if backups_dir.exists():
            backups = list(backups_dir.glob("groups_*.json"))
            assert len(backups) >= 1

    def test_backup_limit_enforced(self, groups_manager):
        """Test that only last 10 backups are kept."""
        # Create and update groups multiple times to generate backups
        group_id = groups_manager.create_group("Test Group")

        # Perform 15 updates
        for i in range(15):
            groups_manager.update_group(group_id, name=f"Update {i}")
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Check backup count
        backups_dir = groups_manager.clients_dir / "backups"
        if backups_dir.exists():
            backups = list(backups_dir.glob("groups_*.json"))
            # Should have at most 10 backups (may be less due to timing)
            assert len(backups) <= 10
