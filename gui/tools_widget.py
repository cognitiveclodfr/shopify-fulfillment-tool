"""
Tools Widget - Main container for utility tools.

Contains sub-tabs:
- Reference Labels: PDF processing for reference numbers
- Barcode Generator: Future implementation
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel
)
from PySide6.QtCore import Qt

from gui.reference_labels_widget import ReferenceLabelsWidget


class ToolsWidget(QWidget):
    """Main Tools tab widget with sub-tabs for various utilities."""

    def __init__(self, main_window, parent=None):
        """
        Initialize Tools widget.

        Args:
            main_window: MainWindow instance for accessing session data
            parent: Parent widget
        """
        super().__init__(parent)
        self.mw = main_window
        self._init_ui()

    def _init_ui(self):
        """Initialize UI with sub-tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)

        # Create sub-tab widget
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setTabPosition(QTabWidget.North)

        # Sub-tab 1: Reference Labels
        self.reference_labels_widget = ReferenceLabelsWidget(self.mw)
        self.sub_tabs.addTab(
            self.reference_labels_widget,
            "📄 Reference Labels"
        )

        # Sub-tab 2: Barcode Generator (placeholder for future)
        barcode_widget = self._create_barcode_placeholder()
        self.sub_tabs.addTab(barcode_widget, "🔢 Barcode Generator")

        layout.addWidget(self.sub_tabs)

    def _create_barcode_placeholder(self):
        """Create placeholder widget for future Barcode Generator."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("🏗️ Barcode Generator")
        label.setStyleSheet("font-size: 24px; font-weight: bold; color: #888;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        sublabel = QLabel("Coming Soon in v1.9.2")
        sublabel.setStyleSheet("font-size: 14px; color: #aaa;")
        sublabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(sublabel)

        layout.addStretch()

        return widget
