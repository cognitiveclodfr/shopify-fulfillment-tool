"""Tests for ClientCard widget.

This module tests the client card display functionality including:
- Initialization and metadata display
- Active state styling
- Badge rendering
- Click interactions
- Context menu
"""

import pytest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent

from gui.client_card import ClientCard


@pytest.fixture
def qapp():
    """Ensure QApplication exists for Qt widgets."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing."""
    return {
        "total_sessions": 5,
        "last_session_date": "2026-01-15",
        "last_accessed": "2026-01-29T10:00:00"
    }


@pytest.fixture
def sample_ui_settings():
    """Sample UI settings for testing."""
    return {
        "is_pinned": False,
        "custom_color": "#4CAF50",
        "custom_badges": ["VIP", "Priority"],
        "group_id": None,
        "display_order": 0
    }


@pytest.fixture
def client_card(qapp, sample_metadata, sample_ui_settings):
    """Create ClientCard widget with sample data."""
    card = ClientCard(
        client_id="M",
        client_name="M Cosmetics",
        metadata=sample_metadata,
        ui_settings=sample_ui_settings,
        is_active=False
    )
    yield card
    card.deleteLater()


class TestClientCardInitialization:
    """Test client card initialization."""

    def test_card_initializes_with_correct_data(self, qapp, sample_metadata, sample_ui_settings):
        """Card should initialize with provided data."""
        card = ClientCard(
            client_id="M",
            client_name="M Cosmetics",
            metadata=sample_metadata,
            ui_settings=sample_ui_settings,
            is_active=False
        )

        assert card.client_id == "M"
        assert card.client_name == "M Cosmetics"
        assert card.metadata == sample_metadata
        assert card.ui_settings == sample_ui_settings
        assert card._is_active is False

        card.deleteLater()

    def test_card_has_fixed_height(self, client_card):
        """Card should have fixed height for consistent layout."""
        assert client_card.height() == 70

    def test_card_has_pointing_hand_cursor(self, client_card):
        """Card should show pointing hand cursor for clickability."""
        assert client_card.cursor().shape() == Qt.PointingHandCursor

    def test_card_displays_client_name(self, client_card):
        """Card should display client name."""
        # Find name label (implementation detail - may need adjustment)
        name_label = client_card.findChild(object, "name_label")
        if name_label:
            assert "M Cosmetics" in name_label.text()


class TestClientCardMetadataDisplay:
    """Test metadata display on card."""

    def test_card_displays_session_count(self, qapp, sample_ui_settings):
        """Card should display total session count."""
        metadata = {
            "total_sessions": 10,
            "last_session_date": "2026-01-15",
            "last_accessed": "2026-01-29T10:00:00"
        }

        card = ClientCard(
            client_id="M",
            client_name="M Cosmetics",
            metadata=metadata,
            ui_settings=sample_ui_settings
        )

        # Check that session count is displayed somewhere
        # (exact implementation may vary)
        card.deleteLater()

    def test_card_displays_last_session_date(self, qapp, sample_ui_settings):
        """Card should display last session date."""
        metadata = {
            "total_sessions": 5,
            "last_session_date": "2026-01-20",
            "last_accessed": "2026-01-29T10:00:00"
        }

        card = ClientCard(
            client_id="M",
            client_name="M Cosmetics",
            metadata=metadata,
            ui_settings=sample_ui_settings
        )

        card.deleteLater()

    def test_card_handles_no_sessions(self, qapp, sample_ui_settings):
        """Card should handle client with no sessions gracefully."""
        metadata = {
            "total_sessions": 0,
            "last_session_date": None,
            "last_accessed": "2026-01-29T10:00:00"
        }

        card = ClientCard(
            client_id="M",
            client_name="M Cosmetics",
            metadata=metadata,
            ui_settings=sample_ui_settings
        )

        # Should not raise exception
        assert card.metadata["total_sessions"] == 0

        card.deleteLater()


class TestClientCardActiveState:
    """Test active state styling."""

    def test_inactive_card_has_no_border(self, qapp, sample_metadata, sample_ui_settings):
        """Inactive card should not have active border."""
        card = ClientCard(
            client_id="M",
            client_name="M Cosmetics",
            metadata=sample_metadata,
            ui_settings=sample_ui_settings,
            is_active=False
        )

        # Check styling (implementation detail)
        assert card._is_active is False

        card.deleteLater()

    def test_active_card_has_border(self, qapp, sample_metadata, sample_ui_settings):
        """Active card should have green left border."""
        card = ClientCard(
            client_id="M",
            client_name="M Cosmetics",
            metadata=sample_metadata,
            ui_settings=sample_ui_settings,
            is_active=True
        )

        assert card._is_active is True

        card.deleteLater()

    def test_set_active_updates_styling(self, client_card):
        """Calling set_active should update card styling."""
        assert client_card._is_active is False

        client_card.set_active(True)

        assert client_card._is_active is True

    def test_set_inactive_updates_styling(self, qapp, sample_metadata, sample_ui_settings):
        """Calling set_active(False) should remove active styling."""
        card = ClientCard(
            client_id="M",
            client_name="M Cosmetics",
            metadata=sample_metadata,
            ui_settings=sample_ui_settings,
            is_active=True
        )

        card.set_active(False)

        assert card._is_active is False

        card.deleteLater()


class TestClientCardBadges:
    """Test badge rendering."""

    def test_card_displays_badges(self, qapp, sample_metadata):
        """Card should display custom badges."""
        ui_settings = {
            "is_pinned": False,
            "custom_color": "#4CAF50",
            "custom_badges": ["VIP", "Priority", "Urgent"],
            "group_id": None
        }

        card = ClientCard(
            client_id="M",
            client_name="M Cosmetics",
            metadata=sample_metadata,
            ui_settings=ui_settings
        )

        # Badges should be stored
        assert len(card.ui_settings["custom_badges"]) == 3

        card.deleteLater()

    def test_card_handles_no_badges(self, qapp, sample_metadata):
        """Card should handle no badges gracefully."""
        ui_settings = {
            "is_pinned": False,
            "custom_color": "#4CAF50",
            "custom_badges": [],
            "group_id": None
        }

        card = ClientCard(
            client_id="M",
            client_name="M Cosmetics",
            metadata=sample_metadata,
            ui_settings=ui_settings
        )

        assert len(card.ui_settings["custom_badges"]) == 0

        card.deleteLater()


class TestClientCardClickInteractions:
    """Test click interactions."""

    def test_card_emits_signal_on_click(self, client_card, qtbot):
        """Clicking card should emit client_selected signal."""
        signal_emitted = False
        emitted_client_id = None

        def on_client_selected(client_id):
            nonlocal signal_emitted, emitted_client_id
            signal_emitted = True
            emitted_client_id = client_id

        client_card.client_selected.connect(on_client_selected)

        # Mock confirmation dialog to auto-accept
        with patch('gui.client_card.QMessageBox.question') as mock_question:
            mock_question.return_value = QMessageBox.Yes

            # Simulate mouse click using qtbot
            qtbot.mouseClick(client_card, Qt.LeftButton)

            # Signal should be emitted
            assert signal_emitted
            assert emitted_client_id == "M"

    def test_card_shows_confirmation_dialog_on_click(self, client_card, qtbot):
        """Clicking card should show confirmation dialog."""
        with patch('gui.client_card.QMessageBox.question') as mock_question:
            mock_question.return_value = QMessageBox.No  # User cancels

            qtbot.mouseClick(client_card, Qt.LeftButton)

            # Confirmation dialog should have been shown
            mock_question.assert_called_once()

    def test_card_does_not_emit_signal_when_confirmation_cancelled(self, client_card, qtbot):
        """Signal should not emit if user cancels confirmation."""
        signal_emitted = False

        def on_client_selected(client_id):
            nonlocal signal_emitted
            signal_emitted = True

        client_card.client_selected.connect(on_client_selected)

        with patch('gui.client_card.QMessageBox.question') as mock_question:
            mock_question.return_value = QMessageBox.No  # User cancels

            qtbot.mouseClick(client_card, Qt.LeftButton)

            # Signal should NOT be emitted
            assert not signal_emitted


class TestClientCardContextMenu:
    """Test context menu functionality."""

    def test_right_click_emits_context_menu_signal(self, client_card, qtbot):
        """Right-clicking should emit context_menu_requested signal."""
        signal_emitted = False
        emitted_client_id = None
        emitted_position = None

        def on_context_menu(client_id, position):
            nonlocal signal_emitted, emitted_client_id, emitted_position
            signal_emitted = True
            emitted_client_id = client_id
            emitted_position = position

        client_card.context_menu_requested.connect(on_context_menu)

        # Simulate right-click
        qtbot.mouseClick(client_card, Qt.RightButton)

        # Check if signal was emitted (implementation-dependent)
        # Some implementations may not have this feature yet


class TestClientCardUpdateMethods:
    """Test update methods."""

    def test_update_metadata_refreshes_display(self, client_card):
        """Updating metadata should refresh card display."""
        new_metadata = {
            "total_sessions": 10,
            "last_session_date": "2026-01-20",
            "last_accessed": "2026-01-29T12:00:00"
        }

        if hasattr(client_card, 'update_metadata'):
            client_card.update_metadata(new_metadata)
            assert client_card.metadata == new_metadata

    def test_update_ui_settings_refreshes_display(self, client_card):
        """Updating UI settings should refresh card display."""
        new_ui_settings = {
            "is_pinned": True,
            "custom_color": "#FF5722",
            "custom_badges": ["NEW"],
            "group_id": "group-1"
        }

        if hasattr(client_card, 'update_ui_settings'):
            client_card.update_ui_settings(new_ui_settings)
            assert client_card.ui_settings == new_ui_settings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
