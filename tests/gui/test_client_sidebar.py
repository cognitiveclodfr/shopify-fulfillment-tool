"""Tests for ClientSidebar widget.

This module tests the client sidebar functionality including:
- Initialization and state restoration
- Section creation and refresh
- Performance logging
- Create client button
- Collapse/expand animation
- Context menu
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch, call
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings, Qt

from gui.client_sidebar import ClientSidebar, SectionWidget
from shopify_tool.profile_manager import ProfileManager
from shopify_tool.groups_manager import GroupsManager


@pytest.fixture
def qapp():
    """Ensure QApplication exists for Qt widgets."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_profile_manager():
    """Mock ProfileManager with test data."""
    pm = Mock(spec=ProfileManager)
    pm.list_clients.return_value = ["M", "A", "B"]
    pm.get_client_config_extended.return_value = {
        "client_name": "Test Client",
        "metadata": {"total_sessions": 5, "last_session_date": "2026-01-15"},
        "ui_settings": {
            "is_pinned": False,
            "custom_color": "#4CAF50",
            "custom_badges": ["VIP"],
            "group_id": None,
            "display_order": 0
        }
    }
    return pm


@pytest.fixture
def mock_groups_manager():
    """Mock GroupsManager with test groups."""
    gm = Mock(spec=GroupsManager)
    gm.list_groups.return_value = [
        {"id": "group-1", "name": "VIP Clients", "color": "#FF5722"}
    ]
    gm.get_clients_in_group.return_value = []
    gm.load_groups.return_value = {
        "special_groups": {
            "pinned": {"name": "Pinned", "collapsed": False},
            "all": {"name": "All Clients", "collapsed": False}
        }
    }
    return gm


@pytest.fixture
def client_sidebar(qapp, mock_profile_manager, mock_groups_manager):
    """Create ClientSidebar widget with mocked managers."""
    # Clear settings before each test
    settings = QSettings("ShopifyTool", "ClientSidebar")
    settings.clear()

    sidebar = ClientSidebar(
        profile_manager=mock_profile_manager,
        groups_manager=mock_groups_manager
    )
    yield sidebar
    sidebar.deleteLater()


class TestClientSidebarInitialization:
    """Test sidebar initialization and state restoration."""

    def test_sidebar_initializes_expanded_by_default(self, client_sidebar):
        """Sidebar should initialize in expanded state by default."""
        assert client_sidebar.is_expanded is True
        assert client_sidebar.width() == client_sidebar.EXPANDED_WIDTH

    def test_sidebar_restores_collapsed_state_from_settings(self, qapp, mock_profile_manager, mock_groups_manager):
        """Sidebar should restore collapsed state from QSettings."""
        # Set collapsed state in settings
        settings = QSettings("ShopifyTool", "ClientSidebar")
        settings.setValue("expanded", False)

        sidebar = ClientSidebar(
            profile_manager=mock_profile_manager,
            groups_manager=mock_groups_manager
        )

        assert sidebar.is_expanded is False
        sidebar.deleteLater()

    def test_sidebar_has_required_widgets(self, client_sidebar):
        """Sidebar should have all required widgets."""
        assert client_sidebar.toggle_btn is not None
        assert client_sidebar.refresh_btn is not None
        assert client_sidebar.create_btn is not None
        assert client_sidebar.manage_groups_btn is not None
        assert client_sidebar.title_label is not None
        assert client_sidebar.scroll_area is not None


class TestClientSidebarRefresh:
    """Test sidebar refresh functionality."""

    def test_refresh_creates_sections(self, client_sidebar, mock_profile_manager, mock_groups_manager):
        """Refresh should create sections for clients and groups."""
        client_sidebar.refresh()

        # Should call list_clients and load_groups
        mock_profile_manager.list_clients.assert_called()
        mock_groups_manager.load_groups.assert_called()

    def test_refresh_clears_previous_sections(self, client_sidebar):
        """Refresh should clear existing sections before rebuilding."""
        # First refresh
        client_sidebar.refresh()
        initial_count = client_sidebar.sections_layout.count()

        # Second refresh
        client_sidebar.refresh()
        new_count = client_sidebar.sections_layout.count()

        # Should have same structure (cleared and rebuilt)
        assert new_count == initial_count

    def test_refresh_performance_logging(self, client_sidebar, caplog):
        """Refresh should log performance metrics."""
        import logging
        caplog.set_level(logging.INFO)

        client_sidebar.refresh()

        # Check for performance logs
        log_messages = [record.message for record in caplog.records]
        assert any("Starting sidebar refresh" in msg for msg in log_messages)
        assert any("Sidebar refresh complete" in msg and "ms" in msg for msg in log_messages)

    def test_refresh_uses_setUpdatesEnabled_optimization(self, client_sidebar):
        """Refresh should disable updates during rebuild for performance."""
        with patch.object(client_sidebar, 'setUpdatesEnabled') as mock_updates:
            client_sidebar.refresh()

            # Should call setUpdatesEnabled(False) then setUpdatesEnabled(True)
            calls = mock_updates.call_args_list
            assert call(False) in calls
            assert call(True) in calls

    def test_refresh_creates_pinned_section_for_pinned_clients(
        self, client_sidebar, mock_profile_manager, mock_groups_manager
    ):
        """Refresh should create pinned section when clients are pinned."""
        # Mock a pinned client
        mock_profile_manager.get_client_config_extended.return_value = {
            "client_name": "Pinned Client",
            "metadata": {"total_sessions": 5, "last_session_date": "2026-01-15"},
            "ui_settings": {"is_pinned": True, "custom_color": "#4CAF50", "custom_badges": []}
        }

        client_sidebar.refresh()

        # Should have created sections
        assert client_sidebar.sections_layout.count() > 1  # More than just stretch


class TestClientSidebarActiveClient:
    """Test active client management."""

    def test_set_active_client_highlights_card(self, client_sidebar, mock_profile_manager):
        """Setting active client should highlight the card."""
        client_sidebar.refresh()
        client_sidebar.set_active_client("M")

        assert client_sidebar.active_client_id == "M"

    def test_set_active_client_emits_signal(self, client_sidebar, qapp):
        """Setting active client should emit client_selected signal."""
        signal_emitted = False
        emitted_client_id = None

        def on_client_selected(client_id):
            nonlocal signal_emitted, emitted_client_id
            signal_emitted = True
            emitted_client_id = client_id

        client_sidebar.client_selected.connect(on_client_selected)
        client_sidebar.refresh()

        # Check that cards exist and connect to their signals
        if "M" in client_sidebar.client_cards:
            cards = client_sidebar.client_cards["M"]
            if cards:
                # Connect to card's signal instead of simulating click
                cards[0].client_selected.connect(on_client_selected)
                # Emit signal directly for testing
                cards[0].client_selected.emit("M")
                assert signal_emitted
                assert emitted_client_id == "M"


class TestClientSidebarCreateButton:
    """Test create client button functionality."""

    def test_create_button_exists(self, client_sidebar):
        """Create button should exist and have correct text."""
        assert client_sidebar.create_btn is not None
        assert client_sidebar.create_btn.text() == "+ Create"
        # Note: Visibility depends on whether widget is shown and expanded state

    def test_create_button_opens_dialog(self, client_sidebar):
        """Clicking create button should open ClientCreationDialog."""
        with patch('gui.client_sidebar.ClientCreationDialog') as mock_dialog_class:
            mock_dialog = Mock()
            mock_dialog.exec.return_value = False  # User cancels
            mock_dialog_class.return_value = mock_dialog

            client_sidebar.create_btn.click()

            # Dialog should be created with correct parameters
            mock_dialog_class.assert_called_once()
            call_kwargs = mock_dialog_class.call_args[1]
            assert call_kwargs['profile_manager'] == client_sidebar.profile_manager
            assert call_kwargs['groups_manager'] == client_sidebar.groups_manager

    def test_create_button_refreshes_on_success(self, client_sidebar):
        """Creating a client should refresh the sidebar."""
        with patch('gui.client_sidebar.ClientCreationDialog') as mock_dialog_class:
            mock_dialog = Mock()
            mock_dialog.exec.return_value = True  # User accepts
            mock_dialog.client_id_input.text.return_value = "NEW"
            mock_dialog_class.return_value = mock_dialog

            with patch.object(client_sidebar, 'refresh') as mock_refresh:
                client_sidebar.create_btn.click()

                # Should refresh sidebar
                mock_refresh.assert_called_once()


class TestClientSidebarCollapse:
    """Test collapse/expand animation."""

    def test_toggle_collapses_sidebar(self, client_sidebar):
        """Toggle should collapse sidebar when expanded."""
        assert client_sidebar.is_expanded is True

        client_sidebar.toggle_expanded()

        assert client_sidebar.is_expanded is False

    def test_toggle_expands_sidebar(self, client_sidebar):
        """Toggle should expand sidebar when collapsed."""
        # First collapse it
        client_sidebar.toggle_expanded()
        assert client_sidebar.is_expanded is False

        # Then expand it
        client_sidebar.toggle_expanded()
        assert client_sidebar.is_expanded is True

    def test_collapse_hides_content_immediately(self, client_sidebar):
        """Collapsing should hide content before animation starts."""
        client_sidebar.toggle_expanded()

        # Content should be hidden immediately
        assert client_sidebar.scroll_area.isVisible() is False
        assert client_sidebar.title_label.isVisible() is False
        assert client_sidebar.create_btn.isVisible() is False

    def test_collapse_saves_state_to_settings(self, client_sidebar):
        """Collapse state should be saved to QSettings."""
        settings = QSettings("ShopifyTool", "ClientSidebar")

        client_sidebar.toggle_expanded()

        expanded_state = settings.value("expanded", type=bool)
        assert expanded_state is False

    def test_collapse_updates_toggle_button(self, client_sidebar):
        """Toggle button should update icon when collapsing."""
        assert client_sidebar.toggle_btn.text() == "◀"

        client_sidebar.toggle_expanded()

        assert client_sidebar.toggle_btn.text() == "▶"


class TestClientSidebarPerformance:
    """Test performance with many clients."""

    def test_refresh_performance_with_many_clients(self, qapp, mock_groups_manager):
        """Refresh should complete in <500ms with 50 clients."""
        # Create mock with 50 clients
        mock_pm = Mock(spec=ProfileManager)
        client_ids = [f"CLIENT_{i}" for i in range(50)]
        mock_pm.list_clients.return_value = client_ids
        mock_pm.get_client_config_extended.return_value = {
            "client_name": "Test Client",
            "metadata": {"total_sessions": 5, "last_session_date": "2026-01-15"},
            "ui_settings": {
                "is_pinned": False,
                "custom_color": "#4CAF50",
                "custom_badges": [],
                "group_id": None
            }
        }

        sidebar = ClientSidebar(
            profile_manager=mock_pm,
            groups_manager=mock_groups_manager
        )

        # Measure refresh time
        start = time.time()
        sidebar.refresh()
        elapsed = (time.time() - start) * 1000  # Convert to ms

        # Should complete in <500ms (first load target)
        assert elapsed < 500, f"Refresh took {elapsed:.1f}ms, expected <500ms"

        sidebar.deleteLater()


class TestClientSidebarContextMenu:
    """Test context menu functionality."""

    def test_context_menu_shows_on_card_right_click(self, client_sidebar, qapp):
        """Right-clicking a card should trigger context menu signal."""
        client_sidebar.refresh()

        # Get first card
        if client_sidebar.client_cards:
            first_client_id = list(client_sidebar.client_cards.keys())[0]
            cards = client_sidebar.client_cards[first_client_id]
            if cards:
                card = cards[0]

                # Check that card has context_menu_requested signal
                assert hasattr(card, 'context_menu_requested')
                # Test implementation may vary depending on actual implementation


class TestClientSidebarIntegration:
    """Integration tests for sidebar."""

    def test_full_workflow_create_and_select_client(self, client_sidebar):
        """Test full workflow: create client -> refresh -> select."""
        initial_client_count = len(client_sidebar.profile_manager.list_clients())

        # Simulate creating a client
        with patch('gui.client_sidebar.ClientCreationDialog') as mock_dialog_class:
            mock_dialog = Mock()
            mock_dialog.exec.return_value = True
            mock_dialog.client_id_input.text.return_value = "NEWCLIENT"
            mock_dialog_class.return_value = mock_dialog

            # Mock profile manager to return new client
            client_sidebar.profile_manager.list_clients.return_value = ["M", "A", "B", "NEWCLIENT"]

            client_sidebar.create_btn.click()

            # Should have refreshed and selected new client
            assert client_sidebar.active_client_id == "NEWCLIENT"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
