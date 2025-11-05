"""Session Browser Widget for viewing and opening client sessions.

This widget shows a list of sessions for the currently selected client,
with filtering by status and the ability to open existing sessions.
"""

import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QGroupBox, QHeaderView, QMessageBox
)
from PySide6.QtCore import Signal, Qt

from shopify_tool.session_manager import SessionManager


logger = logging.getLogger(__name__)


class SessionBrowserWidget(QWidget):
    """Widget for browsing and opening client sessions.

    Provides:
    - Table showing list of sessions with key info
    - Status filter (all/active/completed)
    - "Refresh" button to reload sessions
    - Double-click or "Open Session" to load a session

    Signals:
        session_selected: Emitted when user wants to open a session (session_path: str)
    """

    session_selected = Signal(str)  # Emits session_path

    def __init__(self, session_manager: SessionManager, parent=None):
        super().__init__(parent)
        self.session_manager = session_manager
        self.current_client_id = None
        self.sessions_data = []

        self._init_ui()
        logger.info("SessionBrowserWidget initialized")

    def _init_ui(self):
        """Initialize the UI components."""
        main_layout = QVBoxLayout(self)

        # Create group box
        group = QGroupBox("Existing Sessions")
        group_layout = QVBoxLayout(group)

        # Filter and actions bar
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Status:"))

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Active", "Completed", "Abandoned"])
        self.status_filter.setToolTip("Filter sessions by status")
        self.status_filter.currentTextChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.status_filter)

        filter_layout.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Reload sessions from server")
        self.refresh_btn.clicked.connect(self.refresh_sessions)
        filter_layout.addWidget(self.refresh_btn)

        group_layout.addLayout(filter_layout)

        # Sessions table
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(5)
        self.sessions_table.setHorizontalHeaderLabels([
            "Session Name",
            "Status",
            "Created At",
            "Orders",
            "Analysis Complete"
        ])
        self.sessions_table.horizontalHeader().setStretchLastSection(True)
        self.sessions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sessions_table.setSelectionMode(QTableWidget.SingleSelection)
        self.sessions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sessions_table.doubleClicked.connect(self._on_session_double_clicked)
        self.sessions_table.setSortingEnabled(True)

        # Set column widths
        header = self.sessions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        group_layout.addWidget(self.sessions_table)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.open_btn = QPushButton("Open Selected Session")
        self.open_btn.setToolTip("Load the selected session")
        self.open_btn.clicked.connect(self._on_open_clicked)
        self.open_btn.setEnabled(False)
        button_layout.addWidget(self.open_btn)

        group_layout.addLayout(button_layout)

        main_layout.addWidget(group)

        # Enable open button when selection changes
        self.sessions_table.itemSelectionChanged.connect(self._on_selection_changed)

    def set_client(self, client_id: str):
        """Set the client to show sessions for.

        Args:
            client_id: Client ID to load sessions for
        """
        if client_id != self.current_client_id:
            self.current_client_id = client_id
            self.refresh_sessions()

    def refresh_sessions(self):
        """Reload sessions from the session manager."""
        if not self.current_client_id:
            self.sessions_table.setRowCount(0)
            logger.debug("No client selected, clearing sessions table")
            return

        try:
            # Get status filter
            status_filter = self.status_filter.currentText().lower()
            if status_filter == "all":
                status_filter = None

            # Load sessions
            self.sessions_data = self.session_manager.list_client_sessions(
                self.current_client_id,
                status_filter=status_filter
            )

            # Populate table
            self._populate_table()

            logger.info(f"Loaded {len(self.sessions_data)} sessions for CLIENT_{self.current_client_id}")

        except Exception as e:
            logger.error(f"Failed to load sessions: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to load sessions:\n{str(e)}"
            )

    def _populate_table(self):
        """Populate the table with sessions data."""
        self.sessions_table.setSortingEnabled(False)
        self.sessions_table.setRowCount(len(self.sessions_data))

        for row, session_info in enumerate(self.sessions_data):
            # Session name
            name_item = QTableWidgetItem(session_info.get("session_name", ""))
            self.sessions_table.setItem(row, 0, name_item)

            # Status
            status = session_info.get("status", "unknown")
            status_item = QTableWidgetItem(status.capitalize())
            # Color code by status
            if status == "active":
                status_item.setForeground(Qt.blue)
            elif status == "completed":
                status_item.setForeground(Qt.darkGreen)
            elif status == "abandoned":
                status_item.setForeground(Qt.red)
            self.sessions_table.setItem(row, 1, status_item)

            # Created at
            created_at = session_info.get("created_at", "")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at)
                    created_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    created_str = created_at
            else:
                created_str = ""
            created_item = QTableWidgetItem(created_str)
            self.sessions_table.setItem(row, 2, created_item)

            # Orders count (from analysis_data if available)
            orders_count = "-"
            # We don't have orders count in session_info by default,
            # but could add it or read from analysis files
            orders_item = QTableWidgetItem(orders_count)
            orders_item.setTextAlignment(Qt.AlignCenter)
            self.sessions_table.setItem(row, 3, orders_item)

            # Analysis complete
            analysis_complete = session_info.get("analysis_completed", False)
            complete_item = QTableWidgetItem("Yes" if analysis_complete else "No")
            complete_item.setTextAlignment(Qt.AlignCenter)
            if analysis_complete:
                complete_item.setForeground(Qt.darkGreen)
            self.sessions_table.setItem(row, 4, complete_item)

        self.sessions_table.setSortingEnabled(True)
        # Sort by created date descending (newest first)
        self.sessions_table.sortItems(2, Qt.DescendingOrder)

    def _apply_filter(self):
        """Apply the status filter."""
        self.refresh_sessions()

    def _on_selection_changed(self):
        """Handle table selection change."""
        has_selection = len(self.sessions_table.selectedItems()) > 0
        self.open_btn.setEnabled(has_selection)

    def _on_session_double_clicked(self, index):
        """Handle double-click on session."""
        self._open_selected_session()

    def _on_open_clicked(self):
        """Handle "Open Session" button click."""
        self._open_selected_session()

    def _open_selected_session(self):
        """Open the currently selected session."""
        current_row = self.sessions_table.currentRow()
        if current_row < 0 or current_row >= len(self.sessions_data):
            return

        session_info = self.sessions_data[current_row]
        session_path = session_info.get("session_path")

        if session_path:
            logger.info(f"Opening session: {session_path}")
            self.session_selected.emit(session_path)
        else:
            QMessageBox.warning(
                self,
                "Error",
                "Selected session has no valid path."
            )

    def get_selected_session_path(self) -> str:
        """Get the path of the currently selected session.

        Returns:
            str: Session path or empty string if none selected
        """
        current_row = self.sessions_table.currentRow()
        if current_row < 0 or current_row >= len(self.sessions_data):
            return ""

        session_info = self.sessions_data[current_row]
        return session_info.get("session_path", "")
