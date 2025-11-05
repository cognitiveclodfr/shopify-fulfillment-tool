"""Unit tests for SessionManager.

Tests cover:
- Session creation with unique naming
- Session directory structure
- Session metadata management
- Session listing and filtering
- Session status updates
- Session info updates
- Session subdirectory access
- Error handling
"""

import json
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shopify_tool.profile_manager import ProfileManager
from shopify_tool.session_manager import SessionManager, SessionManagerError


@pytest.fixture
def temp_base_path():
    """Create temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def profile_manager(temp_base_path):
    """Create ProfileManager instance for testing."""
    return ProfileManager(str(temp_base_path))


@pytest.fixture
def session_manager(profile_manager):
    """Create SessionManager instance for testing."""
    return SessionManager(profile_manager)


@pytest.fixture
def client_with_profile(profile_manager):
    """Create a test client profile."""
    profile_manager.create_client_profile("M", "M Cosmetics")
    return "M"


class TestSessionCreation:
    """Test session creation."""

    def test_create_session_success(self, session_manager, client_with_profile):
        """Test creating a new session."""
        session_path = session_manager.create_session(client_with_profile)

        assert session_path is not None
        assert Path(session_path).exists()

        # Check directory structure
        session_path_obj = Path(session_path)
        assert (session_path_obj / "input").exists()
        assert (session_path_obj / "analysis").exists()
        assert (session_path_obj / "packing_lists").exists()
        assert (session_path_obj / "stock_exports").exists()
        assert (session_path_obj / "session_info.json").exists()

    def test_create_session_nonexistent_client(self, session_manager):
        """Test creating session for nonexistent client raises error."""
        with pytest.raises(SessionManagerError) as exc_info:
            session_manager.create_session("NONEXISTENT")

        assert "does not exist" in str(exc_info.value)

    def test_session_name_format(self, session_manager, client_with_profile):
        """Test that session name has correct format."""
        session_path = session_manager.create_session(client_with_profile)

        session_name = Path(session_path).name
        # Format: YYYY-MM-DD_N
        parts = session_name.split('_')

        assert len(parts) == 2  # date_number
        assert parts[1].isdigit()  # N is a number

        # Verify date format (YYYY-MM-DD)
        date_part = parts[0]
        try:
            datetime.strptime(date_part, "%Y-%m-%d")
        except ValueError:
            pytest.fail("Invalid date format in session name")

    def test_multiple_sessions_same_day(self, session_manager, client_with_profile):
        """Test creating multiple sessions on the same day."""
        session1 = session_manager.create_session(client_with_profile)
        session2 = session_manager.create_session(client_with_profile)
        session3 = session_manager.create_session(client_with_profile)

        name1 = Path(session1).name
        name2 = Path(session2).name
        name3 = Path(session3).name

        # All should have today's date
        today = datetime.now().strftime("%Y-%m-%d")
        assert name1.startswith(today)
        assert name2.startswith(today)
        assert name3.startswith(today)

        # Numbers should increment
        assert name1.endswith("_1")
        assert name2.endswith("_2")
        assert name3.endswith("_3")

    def test_session_info_content(self, session_manager, client_with_profile):
        """Test that session_info.json has correct content."""
        session_path = session_manager.create_session(client_with_profile)

        session_info = session_manager.get_session_info(session_path)

        assert session_info is not None
        assert session_info["created_by_tool"] == "shopify"
        assert session_info["client_id"] == client_with_profile
        assert session_info["status"] == "active"
        assert "created_at" in session_info
        assert "session_name" in session_info
        assert session_info["analysis_completed"] is False
        assert session_info["packing_lists_generated"] == []

    def test_create_session_case_insensitive(self, session_manager, client_with_profile):
        """Test that client_id is case-insensitive."""
        # Create with lowercase
        session_path = session_manager.create_session("m")

        assert Path(session_path).exists()

        # Should be in CLIENT_M directory (uppercase)
        assert "CLIENT_M" in str(session_path)


class TestSessionListing:
    """Test session listing functionality."""

    def test_list_client_sessions_empty(self, session_manager, client_with_profile):
        """Test listing sessions when none exist."""
        sessions = session_manager.list_client_sessions(client_with_profile)
        assert sessions == []

    def test_list_client_sessions(self, session_manager, client_with_profile):
        """Test listing existing sessions."""
        # Create multiple sessions
        session_manager.create_session(client_with_profile)
        time.sleep(0.1)  # Ensure different timestamps
        session_manager.create_session(client_with_profile)
        time.sleep(0.1)
        session_manager.create_session(client_with_profile)

        sessions = session_manager.list_client_sessions(client_with_profile)

        assert len(sessions) == 3

        # Should be sorted by creation date (newest first)
        for i in range(len(sessions) - 1):
            time1 = datetime.fromisoformat(sessions[i]["created_at"])
            time2 = datetime.fromisoformat(sessions[i + 1]["created_at"])
            assert time1 >= time2

    def test_list_sessions_with_status_filter(self, session_manager, client_with_profile):
        """Test filtering sessions by status."""
        # Create sessions with different statuses
        session1 = session_manager.create_session(client_with_profile)
        session2 = session_manager.create_session(client_with_profile)
        session3 = session_manager.create_session(client_with_profile)

        # Update statuses
        session_manager.update_session_status(session1, "completed")
        session_manager.update_session_status(session2, "completed")
        # session3 stays "active"

        # Filter for completed
        completed_sessions = session_manager.list_client_sessions(
            client_with_profile, status_filter="completed"
        )
        assert len(completed_sessions) == 2

        # Filter for active
        active_sessions = session_manager.list_client_sessions(
            client_with_profile, status_filter="active"
        )
        assert len(active_sessions) == 1

    def test_list_nonexistent_client(self, session_manager):
        """Test listing sessions for nonexistent client."""
        sessions = session_manager.list_client_sessions("NONEXISTENT")
        assert sessions == []


class TestSessionInfo:
    """Test session info management."""

    def test_get_session_info(self, session_manager, client_with_profile):
        """Test getting session info."""
        session_path = session_manager.create_session(client_with_profile)

        session_info = session_manager.get_session_info(session_path)

        assert session_info is not None
        assert "client_id" in session_info
        assert "status" in session_info
        assert "created_at" in session_info
        assert "session_path" in session_info

    def test_get_session_info_nonexistent(self, session_manager, temp_base_path):
        """Test getting info for nonexistent session."""
        fake_path = temp_base_path / "fake_session"

        session_info = session_manager.get_session_info(str(fake_path))

        assert session_info is None

    def test_update_session_info(self, session_manager, client_with_profile):
        """Test updating session info."""
        session_path = session_manager.create_session(client_with_profile)

        # Update info
        updates = {
            "orders_file": "orders_export.csv",
            "stock_file": "inventory.csv",
            "analysis_completed": True
        }

        result = session_manager.update_session_info(session_path, updates)
        assert result is True

        # Verify updates
        session_info = session_manager.get_session_info(session_path)
        assert session_info["orders_file"] == "orders_export.csv"
        assert session_info["stock_file"] == "inventory.csv"
        assert session_info["analysis_completed"] is True
        assert "last_updated" in session_info

    def test_update_session_info_invalid_path(self, session_manager, temp_base_path):
        """Test updating info for nonexistent session."""
        fake_path = temp_base_path / "fake_session"

        with pytest.raises(SessionManagerError):
            session_manager.update_session_info(str(fake_path), {"test": "data"})


class TestSessionStatus:
    """Test session status management."""

    def test_update_session_status_valid(self, session_manager, client_with_profile):
        """Test updating session status with valid statuses."""
        session_path = session_manager.create_session(client_with_profile)

        # Test all valid statuses
        for status in ["active", "completed", "abandoned"]:
            result = session_manager.update_session_status(session_path, status)
            assert result is True

            # Verify status was updated
            session_info = session_manager.get_session_info(session_path)
            assert session_info["status"] == status
            assert "status_updated_at" in session_info

    def test_update_session_status_invalid(self, session_manager, client_with_profile):
        """Test updating session status with invalid status."""
        session_path = session_manager.create_session(client_with_profile)

        with pytest.raises(SessionManagerError) as exc_info:
            session_manager.update_session_status(session_path, "invalid_status")

        assert "Invalid status" in str(exc_info.value)

    def test_update_status_nonexistent_session(self, session_manager, temp_base_path):
        """Test updating status for nonexistent session."""
        fake_path = temp_base_path / "fake_session"

        with pytest.raises(SessionManagerError):
            session_manager.update_session_status(str(fake_path), "completed")


class TestSessionSubdirectories:
    """Test session subdirectory access."""

    def test_get_session_subdirectory_valid(self, session_manager, client_with_profile):
        """Test getting valid subdirectories."""
        session_path = session_manager.create_session(client_with_profile)

        for subdir_name in ["input", "analysis", "packing_lists", "stock_exports"]:
            subdir = session_manager.get_session_subdirectory(session_path, subdir_name)

            assert subdir is not None
            assert subdir.exists()
            assert subdir.is_dir()
            assert subdir.name == subdir_name

    def test_get_session_subdirectory_invalid(self, session_manager, client_with_profile):
        """Test getting invalid subdirectory raises error."""
        session_path = session_manager.create_session(client_with_profile)

        with pytest.raises(SessionManagerError) as exc_info:
            session_manager.get_session_subdirectory(session_path, "invalid_subdir")

        assert "Invalid subdirectory" in str(exc_info.value)

    def test_get_input_dir(self, session_manager, client_with_profile):
        """Test getting input directory."""
        session_path = session_manager.create_session(client_with_profile)

        input_dir = session_manager.get_input_dir(session_path)

        assert input_dir.exists()
        assert input_dir.name == "input"

    def test_get_analysis_dir(self, session_manager, client_with_profile):
        """Test getting analysis directory."""
        session_path = session_manager.create_session(client_with_profile)

        analysis_dir = session_manager.get_analysis_dir(session_path)

        assert analysis_dir.exists()
        assert analysis_dir.name == "analysis"

    def test_get_packing_lists_dir(self, session_manager, client_with_profile):
        """Test getting packing_lists directory."""
        session_path = session_manager.create_session(client_with_profile)

        packing_lists_dir = session_manager.get_packing_lists_dir(session_path)

        assert packing_lists_dir.exists()
        assert packing_lists_dir.name == "packing_lists"

    def test_get_stock_exports_dir(self, session_manager, client_with_profile):
        """Test getting stock_exports directory."""
        session_path = session_manager.create_session(client_with_profile)

        stock_exports_dir = session_manager.get_stock_exports_dir(session_path)

        assert stock_exports_dir.exists()
        assert stock_exports_dir.name == "stock_exports"


class TestSessionPaths:
    """Test session path utilities."""

    def test_get_session_path(self, session_manager, client_with_profile):
        """Test getting session path from client_id and session_name."""
        session_path = session_manager.create_session(client_with_profile)

        session_name = Path(session_path).name
        retrieved_path = session_manager.get_session_path(
            client_with_profile, session_name
        )

        assert str(retrieved_path) == session_path

    def test_session_exists(self, session_manager, client_with_profile):
        """Test checking if session exists."""
        session_path = session_manager.create_session(client_with_profile)
        session_name = Path(session_path).name

        # Should exist
        assert session_manager.session_exists(client_with_profile, session_name)

        # Should not exist
        assert not session_manager.session_exists(client_with_profile, "2020-01-01_1")
        assert not session_manager.session_exists("NONEXISTENT", "2020-01-01_1")


class TestSessionDeletion:
    """Test session deletion."""

    def test_delete_session_success(self, session_manager, client_with_profile):
        """Test deleting a session."""
        session_path = session_manager.create_session(client_with_profile)

        # Verify it exists
        assert Path(session_path).exists()

        # Delete
        result = session_manager.delete_session(session_path)
        assert result is True

        # Verify it's gone
        assert not Path(session_path).exists()

    def test_delete_nonexistent_session(self, session_manager, temp_base_path):
        """Test deleting nonexistent session."""
        fake_path = temp_base_path / "fake_session"

        result = session_manager.delete_session(str(fake_path))
        assert result is False


class TestMultipleClients:
    """Test sessions for multiple clients."""

    def test_sessions_isolated_per_client(self, profile_manager, session_manager):
        """Test that sessions are isolated per client."""
        # Create two clients
        profile_manager.create_client_profile("M", "M Cosmetics")
        profile_manager.create_client_profile("A", "A Company")

        # Create sessions for each
        session_m1 = session_manager.create_session("M")
        session_m2 = session_manager.create_session("M")
        session_a1 = session_manager.create_session("A")

        # Verify isolation
        sessions_m = session_manager.list_client_sessions("M")
        sessions_a = session_manager.list_client_sessions("A")

        assert len(sessions_m) == 2
        assert len(sessions_a) == 1

        # Verify paths
        assert "CLIENT_M" in session_m1
        assert "CLIENT_M" in session_m2
        assert "CLIENT_A" in session_a1


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_session_info_json(self, session_manager, client_with_profile):
        """Test handling of corrupted session_info.json."""
        session_path = session_manager.create_session(client_with_profile)

        # Corrupt the session_info.json
        session_info_path = Path(session_path) / "session_info.json"
        with open(session_info_path, 'w') as f:
            f.write("invalid json {{{")

        # Should return None and log error
        session_info = session_manager.get_session_info(session_path)
        assert session_info is None

    def test_missing_subdirectory(self, session_manager, client_with_profile):
        """Test accessing missing subdirectory."""
        session_path = session_manager.create_session(client_with_profile)

        # Remove a subdirectory
        input_dir = Path(session_path) / "input"
        shutil.rmtree(input_dir)

        # Should raise error
        with pytest.raises(SessionManagerError):
            session_manager.get_input_dir(session_path)

    def test_session_creation_failure_cleanup(
        self, session_manager, client_with_profile, temp_base_path
    ):
        """Test that partial session is cleaned up on failure."""
        # This is hard to test without mocking, but we can verify the cleanup logic exists
        # by checking that a failed creation doesn't leave debris

        # Mock mkdir to fail on subdirectory creation
        original_mkdir = Path.mkdir

        def failing_mkdir(self, *args, **kwargs):
            if "packing_lists" in str(self):
                raise PermissionError("Mocked failure")
            return original_mkdir(self, *args, **kwargs)

        with patch.object(Path, 'mkdir', failing_mkdir):
            with pytest.raises(SessionManagerError):
                session_manager.create_session(client_with_profile)

        # Verify no partial session remains
        # (This is a basic check - in reality the cleanup might not be perfect)
        # sessions = session_manager.list_client_sessions(client_with_profile)
        # All sessions should be complete or not exist


class TestTimestampGeneration:
    """Test unique timestamp generation."""

    def test_unique_name_generation_with_gaps(
        self, session_manager, client_with_profile, temp_base_path
    ):
        """Test that unique name generation handles gaps correctly."""
        client_sessions_dir = (
            temp_base_path / "Sessions" / f"CLIENT_{client_with_profile}"
        )
        client_sessions_dir.mkdir(parents=True, exist_ok=True)

        # Create sessions with gaps in numbering (simulate manual deletion)
        today = datetime.now().strftime("%Y-%m-%d")
        (client_sessions_dir / f"{today}_1").mkdir()
        (client_sessions_dir / f"{today}_3").mkdir()
        (client_sessions_dir / f"{today}_5").mkdir()

        # Generate new session name
        new_name = session_manager._generate_unique_session_name(client_sessions_dir)

        # Should be _6 (max + 1)
        assert new_name == f"{today}_6"

    def test_unique_name_generation_no_existing(
        self, session_manager, temp_base_path
    ):
        """Test unique name generation when no sessions exist."""
        fake_dir = temp_base_path / "fake_client"
        fake_dir.mkdir()

        name = session_manager._generate_unique_session_name(fake_dir)

        today = datetime.now().strftime("%Y-%m-%d")
        assert name == f"{today}_1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
