"""Session Browser Widget for viewing and opening client sessions.

This widget shows a list of sessions for the currently selected client,
with filtering by status and the ability to open existing sessions.
"""

import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QGroupBox, QHeaderView, QMessageBox, QLineEdit
)
from PySide6.QtCore import Signal, Qt, QThread

from shopify_tool.session_manager import SessionManager
from gui.wheel_ignore_combobox import WheelIgnoreComboBox
from gui.theme_manager import get_theme_manager


logger = logging.getLogger(__name__)


class SessionLoaderWorker(QThread):
    """Background worker thread for loading session metadata.

    Loads session list from file server in background to prevent UI freezing
    on slow network connections.

    Signals:
        sessions_loaded: Emitted when sessions are successfully loaded (passes list of session dicts)
        error_occurred: Emitted when an error occurs during loading (passes error message string)
    """

    sessions_loaded = Signal(list)  # Emits list of session info dicts
    error_occurred = Signal(str)    # Emits error message

    def __init__(self, session_manager: SessionManager, client_id: str, status_filter=None):
        """Initialize worker.

        Args:
            session_manager: SessionManager instance
            client_id: Client ID to load sessions for
            status_filter: Optional status filter ("active", "completed", etc.)
        """
        super().__init__()
        self.session_manager = session_manager
        self.client_id = client_id
        self.status_filter = status_filter

    def run(self):
        """Load sessions in background thread.

        This method runs in a separate thread and should not directly
        modify UI elements. Results are emitted via signals.
        """
        try:
            logger.debug(f"Background loading sessions for CLIENT_{self.client_id}")
            sessions_data = self.session_manager.list_client_sessions(
                self.client_id,
                status_filter=self.status_filter
            )
            logger.debug(f"Background load complete: {len(sessions_data)} sessions")
            self.sessions_loaded.emit(sessions_data)
        except Exception as e:
            logger.error(f"Background session load failed: {e}", exc_info=True)
            self.error_occurred.emit(str(e))


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

        # Create group box with client name
        self.group_box = QGroupBox("Session Browser")
        group_layout = QVBoxLayout(self.group_box)

        # Filter and actions bar
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Status:"))

        self.status_filter = WheelIgnoreComboBox()
        self.status_filter.addItems(["All", "Active", "Completed", "Abandoned", "Archived"])
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
        self.sessions_table.setColumnCount(7)
        self.sessions_table.setHorizontalHeaderLabels([
            "Session Name",
            "Created",
            "Status",
            "Orders",
            "Items",
            "Packing Lists",
            "Comments"
        ])
        self.sessions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sessions_table.setSelectionMode(QTableWidget.SingleSelection)
        self.sessions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sessions_table.doubleClicked.connect(self._on_session_double_clicked)
        self.sessions_table.setSortingEnabled(True)

        # Set column widths
        header = self.sessions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 150)  # Session Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 150)  # Created
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 100)  # Status
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 80)   # Orders
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 80)   # Items
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, 120)  # Packing Lists
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # Comments

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

        main_layout.addWidget(self.group_box)

        # Enable open button when selection changes
        self.sessions_table.itemSelectionChanged.connect(self._on_selection_changed)

    def set_client(self, client_id: str):
        """Set the client to show sessions for.

        Args:
            client_id: Client ID to load sessions for
        """
        if client_id != self.current_client_id:
            self.current_client_id = client_id
            # Update title with client name
            self.group_box.setTitle(f"Session Browser - CLIENT_{client_id}")
            # Clear table immediately to avoid confusion with old client's data
            self.sessions_table.setRowCount(0)
            self.sessions_data = []
            self.refresh_sessions()

    def refresh_sessions(self):
        """Reload sessions from the session manager in background thread."""
        if not self.current_client_id:
            self.sessions_table.setRowCount(0)
            logger.debug("No client selected, clearing sessions table")
            return

        # Show loading state
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Loading...")

        # Get status filter
        status_filter = self.status_filter.currentText().lower()
        if status_filter == "all":
            status_filter = None

        # Start background worker
        self.worker = SessionLoaderWorker(
            self.session_manager,
            self.current_client_id,
            status_filter
        )
        self.worker.sessions_loaded.connect(self._on_sessions_loaded)
        self.worker.error_occurred.connect(self._on_load_error)
        self.worker.start()

    def _on_sessions_loaded(self, sessions_data: list):
        """Handle loaded sessions from background thread.

        Args:
            sessions_data: List of session info dictionaries
        """
        self.sessions_data = sessions_data
        self._populate_table()

        logger.info(f"Loaded {len(self.sessions_data)} sessions for CLIENT_{self.current_client_id}")

        # Restore button state
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh")

    def _on_load_error(self, error_message: str):
        """Handle load error from background thread.

        Args:
            error_message: Error message string
        """
        logger.error(f"Failed to load sessions: {error_message}")
        QMessageBox.warning(
            self,
            "Error",
            f"Failed to load sessions:\n{error_message}"
        )

        # Restore button state
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh")

    def _populate_table(self):
        """Populate the table with sessions data."""
        self.sessions_table.setSortingEnabled(False)
        self.sessions_table.setRowCount(len(self.sessions_data))

        for row, session_info in enumerate(self.sessions_data):
            session_path = session_info.get("session_path", "")
            stats = session_info.get("statistics", {})

            # Column 0: Session name
            name_item = QTableWidgetItem(session_info.get("session_name", ""))
            self.sessions_table.setItem(row, 0, name_item)

            # Column 1: Created at
            created_at = session_info.get("created_at", "")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at)
                    created_str = dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError) as e:
                    # Invalid datetime format, use original string
                    created_str = created_at
            else:
                created_str = ""
            created_item = QTableWidgetItem(created_str)
            self.sessions_table.setItem(row, 1, created_item)

            # Column 2: Status (EDITABLE COMBOBOX)
            status = session_info.get("status", "active")
            status_combo = WheelIgnoreComboBox()
            status_combo.addItems(["Active", "Completed", "Abandoned", "Archived"])
            status_combo.setCurrentText(status.capitalize())
            # Color code by status
            if status == "active":
                status_combo.setStyleSheet("QComboBox { color: blue; }")
            elif status == "completed":
                status_combo.setStyleSheet("QComboBox { color: darkgreen; }")
            elif status == "abandoned":
                status_combo.setStyleSheet("QComboBox { color: red; }")
            elif status == "archived":
                theme = get_theme_manager().get_current_theme()
                status_combo.setStyleSheet(f"QComboBox {{ color: {theme.text_secondary}; }}")
            status_combo.currentTextChanged.connect(
                lambda new_status, path=session_path: self._on_status_changed(path, new_status)
            )
            self.sessions_table.setCellWidget(row, 2, status_combo)

            # Column 3: Orders (READ-ONLY)
            orders_count = stats.get("total_orders", 0)
            orders_item = QTableWidgetItem(str(orders_count) if orders_count > 0 else "N/A")
            orders_item.setTextAlignment(Qt.AlignCenter)
            self.sessions_table.setItem(row, 3, orders_item)

            # Column 4: Items (READ-ONLY)
            items_count = stats.get("total_items", 0)
            items_item = QTableWidgetItem(str(items_count) if items_count > 0 else "N/A")
            items_item.setTextAlignment(Qt.AlignCenter)
            self.sessions_table.setItem(row, 4, items_item)

            # Column 5: Packing Lists (READ-ONLY)
            packing_lists_count = stats.get("packing_lists_count", 0)
            packing_lists_item = QTableWidgetItem(str(packing_lists_count))
            packing_lists_item.setTextAlignment(Qt.AlignCenter)
            self.sessions_table.setItem(row, 5, packing_lists_item)

            # Column 6: Comments (EDITABLE LINE EDIT)
            comments = session_info.get("comments", "")
            comments_edit = QLineEdit(comments)
            comments_edit.setPlaceholderText("Add comments...")
            comments_edit.editingFinished.connect(
                lambda path=session_path, widget=comments_edit: self._on_comments_changed(path, widget.text())
            )
            self.sessions_table.setCellWidget(row, 6, comments_edit)

            # Build tooltip with full info
            packing_lists_str = ", ".join(stats.get("packing_lists", [])) or "None"
            tooltip = f"""Session: {session_info.get('session_name', '')}
Created: {created_str}
Status: {status.capitalize()}
Orders: {orders_count if orders_count > 0 else 'N/A'}
Items: {items_count if items_count > 0 else 'N/A'}
Packing Lists ({packing_lists_count}): {packing_lists_str}
Comments: {comments if comments else 'None'}"""

            # Apply tooltip to all cells in row
            for col in range(7):
                item = self.sessions_table.item(row, col)
                if item:
                    item.setToolTip(tooltip)

        self.sessions_table.setSortingEnabled(True)
        # Sort by created date descending (newest first)
        self.sessions_table.sortItems(1, Qt.DescendingOrder)

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

    def _on_status_changed(self, session_path: str, new_status: str):
        """Handle status change in table.

        Args:
            session_path: Full path to session directory
            new_status: New status text (capitalized)
        """
        try:
            # Convert to lowercase for storage
            status = new_status.lower()

            # Update session_info.json
            self.session_manager.update_session_status(session_path, status)

            logger.info(f"Updated session status: {session_path} -> {status}")

        except Exception as e:
            logger.error(f"Failed to update status: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update status:\n{str(e)}"
            )
            # Revert to previous value
            self.refresh_sessions()

    def _on_comments_changed(self, session_path: str, comments: str):
        """Handle comments change in table.

        Args:
            session_path: Full path to session directory
            comments: New comments text
        """
        try:
            # Update session_info.json
            self.session_manager.update_session_info(session_path, {
                "comments": comments
            })

            logger.info(f"Updated session comments: {session_path}")

        except Exception as e:
            logger.error(f"Failed to update comments: {e}")
            # Don't show error dialog for comments (less critical)
            # Just log the error
