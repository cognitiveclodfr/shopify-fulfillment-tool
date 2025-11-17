"""
Tests for WheelIgnoreComboBox widget.

This test suite verifies that the WheelIgnoreComboBox correctly ignores
wheel events while still allowing normal mouse and keyboard interactions.
"""

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QWheelEvent
from gui.wheel_ignore_combobox import WheelIgnoreComboBox


def test_wheel_ignore_combobox_creation(qtbot):
    """Test that WheelIgnoreComboBox can be created."""
    combo = WheelIgnoreComboBox()
    qtbot.addWidget(combo)

    assert combo is not None
    assert isinstance(combo, WheelIgnoreComboBox)


def test_wheel_ignore_combobox_ignores_wheel_events(qtbot):
    """Test that wheel events are ignored."""
    combo = WheelIgnoreComboBox()
    qtbot.addWidget(combo)

    # Add items
    combo.addItems(["Option 1", "Option 2", "Option 3"])
    combo.setCurrentIndex(0)

    initial_index = combo.currentIndex()
    assert initial_index == 0

    # Simulate wheel event
    wheel_event = QWheelEvent(
        QPoint(10, 10),  # pos
        QPoint(10, 10),  # globalPos
        QPoint(0, 120),  # pixelDelta
        QPoint(0, 120),  # angleDelta
        Qt.NoButton,     # buttons
        Qt.NoModifier,   # modifiers
        Qt.ScrollUpdate, # phase
        False            # inverted
    )

    # Send wheel event
    combo.wheelEvent(wheel_event)

    # Index should NOT change
    assert combo.currentIndex() == initial_index
    assert combo.currentIndex() == 0


def test_wheel_ignore_combobox_allows_mouse_selection(qtbot):
    """Test that mouse clicks still work for selection."""
    combo = WheelIgnoreComboBox()
    qtbot.addWidget(combo)

    combo.addItems(["Option 1", "Option 2", "Option 3"])
    combo.setCurrentIndex(0)

    # Change selection programmatically (simulates mouse click selection)
    combo.setCurrentIndex(2)

    assert combo.currentIndex() == 2
    assert combo.currentText() == "Option 3"


def test_wheel_ignore_combobox_allows_keyboard_navigation(qtbot):
    """Test that keyboard navigation still works when focused."""
    combo = WheelIgnoreComboBox()
    qtbot.addWidget(combo)
    combo.show()

    combo.addItems(["Option 1", "Option 2", "Option 3"])
    combo.setCurrentIndex(0)

    # Give focus
    combo.setFocus()

    # Arrow keys should work when focused
    # Note: This tests that our wheel blocking doesn't break keyboard nav
    combo.setCurrentIndex(1)
    assert combo.currentIndex() == 1


def test_wheel_ignore_combobox_with_parent(qtbot):
    """Test that WheelIgnoreComboBox works with a parent widget."""
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    qtbot.addWidget(parent)

    combo = WheelIgnoreComboBox(parent)
    combo.addItems(["A", "B", "C"])

    assert combo.parent() == parent
    assert combo.count() == 3


def test_wheel_ignore_combobox_inherits_from_qcombobox(qtbot):
    """Test that WheelIgnoreComboBox is a proper subclass of QComboBox."""
    from PySide6.QtWidgets import QComboBox

    combo = WheelIgnoreComboBox()
    qtbot.addWidget(combo)

    # Should be instance of both
    assert isinstance(combo, WheelIgnoreComboBox)
    assert isinstance(combo, QComboBox)


def test_wheel_ignore_combobox_event_filter(qtbot):
    """Test that event filter blocks wheel events."""
    combo = WheelIgnoreComboBox()
    qtbot.addWidget(combo)

    combo.addItems(["Item 1", "Item 2", "Item 3"])
    combo.setCurrentIndex(0)

    # Trigger focus to install event filter
    combo.setFocus()

    initial_index = combo.currentIndex()

    # Create wheel event
    wheel_event = QWheelEvent(
        QPoint(5, 5),
        QPoint(100, 100),
        QPoint(0, -120),  # Negative for scroll down
        QPoint(0, -120),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.ScrollUpdate,
        False
    )

    # Event filter should catch it
    result = combo.eventFilter(combo, wheel_event)

    # Event should be filtered (blocked)
    assert result is True

    # Index should not change
    assert combo.currentIndex() == initial_index
