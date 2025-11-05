"""Client Selector Widget for selecting and managing clients.

This widget provides a dropdown for selecting clients and a button for managing
(creating/editing) client profiles.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox,
    QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox, QFormLayout
)
from PySide6.QtCore import Signal

from shopify_tool.profile_manager import ProfileManager, ValidationError, ProfileManagerError


logger = logging.getLogger(__name__)


class ClientCreationDialog(QDialog):
    """Dialog for creating a new client profile."""

    def __init__(self, profile_manager: ProfileManager, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.setWindowTitle("Create New Client")
        self.setModal(True)
        self.setMinimumWidth(400)

        # Create layout
        layout = QVBoxLayout(self)

        # Form layout for inputs
        form_layout = QFormLayout()

        self.client_id_input = QLineEdit()
        self.client_id_input.setPlaceholderText("e.g., M, A, B")
        self.client_id_input.setToolTip(
            "Client ID (letters, numbers, underscore only)\n"
            "Max 20 characters\n"
            "Don't include 'CLIENT_' prefix"
        )
        form_layout.addRow("Client ID:", self.client_id_input)

        self.client_name_input = QLineEdit()
        self.client_name_input.setPlaceholderText("e.g., M Cosmetics")
        self.client_name_input.setToolTip("Full name of the client")
        form_layout.addRow("Client Name:", self.client_name_input)

        layout.addLayout(form_layout)

        # Add info label
        info_label = QLabel(
            "This will create a new client profile with default Shopify configuration.\n"
            "You can customize it later in Profile Settings."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 10pt; padding: 10px;")
        layout.addWidget(info_label)

        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def validate_and_accept(self):
        """Validate inputs and create client profile."""
        client_id = self.client_id_input.text().strip()
        client_name = self.client_name_input.text().strip()

        # Validate inputs
        if not client_id:
            QMessageBox.warning(self, "Validation Error", "Client ID is required.")
            return

        if not client_name:
            QMessageBox.warning(self, "Validation Error", "Client Name is required.")
            return

        # Validate client ID format
        is_valid, error_msg = ProfileManager.validate_client_id(client_id)
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error_msg)
            return

        # Try to create client profile
        try:
            success = self.profile_manager.create_client_profile(client_id, client_name)
            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Client profile 'CLIENT_{client_id.upper()}' created successfully!"
                )
                self.accept()
            else:
                QMessageBox.warning(
                    self,
                    "Profile Exists",
                    f"Client profile 'CLIENT_{client_id.upper()}' already exists."
                )
        except (ValidationError, ProfileManagerError) as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create client profile:\n{str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error creating client: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"An unexpected error occurred:\n{str(e)}"
            )


class ClientSelectorWidget(QWidget):
    """Widget for selecting active client and managing client profiles.

    Provides:
    - Dropdown to select active client
    - "Manage Clients" button to create new clients
    - Signal when client selection changes

    Signals:
        client_changed: Emitted when client selection changes (client_id: str)
    """

    client_changed = Signal(str)  # Emits client_id

    def __init__(self, profile_manager: ProfileManager, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.current_client_id = None

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Label
        label = QLabel("Client:")
        label.setToolTip("Select the active client")
        layout.addWidget(label)

        # Client dropdown
        self.client_combo = QComboBox()
        self.client_combo.setMinimumWidth(150)
        self.client_combo.setToolTip("Select active client to work with")
        self.client_combo.currentTextChanged.connect(self._on_client_changed)
        layout.addWidget(self.client_combo, 1)

        # Manage clients button
        self.manage_btn = QPushButton("Manage Clients")
        self.manage_btn.setToolTip("Create or manage client profiles")
        self.manage_btn.clicked.connect(self._open_manage_dialog)
        layout.addWidget(self.manage_btn)

        # Load clients
        self.refresh_clients()

        logger.info("ClientSelectorWidget initialized")

    def refresh_clients(self):
        """Reload client list from profile manager."""
        try:
            # Save current selection
            current_client = self.client_combo.currentText()

            # Block signals to avoid triggering client_changed multiple times
            self.client_combo.blockSignals(True)
            self.client_combo.clear()

            # Load clients
            clients = self.profile_manager.list_clients()

            if not clients:
                self.client_combo.addItem("(No clients available)")
                self.client_combo.setEnabled(False)
                logger.warning("No clients found on file server")
            else:
                self.client_combo.addItems(clients)
                self.client_combo.setEnabled(True)

                # Restore previous selection if it still exists
                if current_client in clients:
                    self.client_combo.setCurrentText(current_client)

            # Re-enable signals
            self.client_combo.blockSignals(False)

            # Manually trigger client changed if we have clients
            if clients:
                self._on_client_changed(self.client_combo.currentText())

        except Exception as e:
            logger.error(f"Failed to refresh clients: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to load clients from server:\n{str(e)}"
            )

    def _on_client_changed(self, client_id: str):
        """Handle client selection change."""
        if not client_id or client_id == "(No clients available)":
            return

        if client_id != self.current_client_id:
            self.current_client_id = client_id
            logger.info(f"Client changed to: {client_id}")
            self.client_changed.emit(client_id)

    def _open_manage_dialog(self):
        """Open dialog for managing clients."""
        dialog = ClientCreationDialog(self.profile_manager, self)
        if dialog.exec():
            # Refresh client list after successful creation
            self.refresh_clients()

    def get_current_client_id(self) -> str:
        """Get currently selected client ID.

        Returns:
            str: Current client ID or empty string if none selected
        """
        text = self.client_combo.currentText()
        if text == "(No clients available)":
            return ""
        return text

    def set_current_client_id(self, client_id: str):
        """Set the currently selected client.

        Args:
            client_id: Client ID to select
        """
        index = self.client_combo.findText(client_id)
        if index >= 0:
            self.client_combo.setCurrentIndex(index)
