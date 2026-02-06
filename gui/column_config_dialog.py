"""
Column Configuration Dialog

Provides UI for managing table column visibility, order, and views.

Phase 4 of table customization feature.
"""

import logging
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QLabel,
    QMessageBox,
    QInputDialog,
    QGroupBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

logger = logging.getLogger(__name__)


class ColumnConfigDialog(QDialog):
    """Dialog for configuring table column visibility and order."""

    # Signal emitted when configuration is applied
    config_applied = Signal()

    def __init__(self, table_config_manager, parent=None):
        """
        Initialize the Column Configuration Dialog.

        Args:
            table_config_manager: TableConfigManager instance
            parent: Parent widget (MainWindow)
        """
        super().__init__(parent)
        self.table_config_manager = table_config_manager
        self.parent_window = parent

        # Track original configuration for cancel
        self._original_config = None
        self._original_view_name = None  # Store original view name for cancel
        self._current_columns: List[str] = []
        self._is_loading = False

        self.setWindowTitle("Manage Table Columns")
        self.setMinimumSize(600, 700)
        self.setModal(True)

        self._init_ui()
        self._connect_signals()
        self._load_current_config()

    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)

        # Search section
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter columns...")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        # Column list section
        list_group = QGroupBox("Columns")
        list_layout = QVBoxLayout()

        self.column_list = QListWidget()
        self.column_list.setSelectionMode(QListWidget.SingleSelection)
        list_layout.addWidget(self.column_list)

        # Reorder buttons
        reorder_layout = QHBoxLayout()
        self.up_button = QPushButton("↑ Move Up")
        self.down_button = QPushButton("↓ Move Down")
        reorder_layout.addWidget(self.up_button)
        reorder_layout.addWidget(self.down_button)
        list_layout.addLayout(reorder_layout)

        list_group.setLayout(list_layout)
        main_layout.addWidget(list_group)

        # Visibility controls section
        visibility_group = QGroupBox("Visibility Controls")
        visibility_layout = QVBoxLayout()

        visibility_buttons_layout = QHBoxLayout()
        self.show_all_button = QPushButton("Show All")
        self.hide_all_button = QPushButton("Hide All")
        visibility_buttons_layout.addWidget(self.show_all_button)
        visibility_buttons_layout.addWidget(self.hide_all_button)
        visibility_layout.addLayout(visibility_buttons_layout)

        self.auto_hide_checkbox = QCheckBox("Auto-hide empty columns")
        self.auto_hide_checkbox.setToolTip(
            "Automatically hide columns that contain no data"
        )
        visibility_layout.addWidget(self.auto_hide_checkbox)

        visibility_group.setLayout(visibility_layout)
        main_layout.addWidget(visibility_group)

        # View management section
        view_group = QGroupBox("View Management")
        view_layout = QVBoxLayout()

        view_select_layout = QHBoxLayout()
        view_label = QLabel("Active View:")
        self.view_combo = QComboBox()
        view_select_layout.addWidget(view_label)
        view_select_layout.addWidget(self.view_combo, 1)
        view_layout.addLayout(view_select_layout)

        view_buttons_layout = QHBoxLayout()
        self.save_view_button = QPushButton("Save View As...")
        self.delete_view_button = QPushButton("Delete View")
        view_buttons_layout.addWidget(self.save_view_button)
        view_buttons_layout.addWidget(self.delete_view_button)
        view_layout.addLayout(view_buttons_layout)

        view_group.setLayout(view_layout)
        main_layout.addWidget(view_group)

        # Reset section
        reset_layout = QHBoxLayout()
        self.reset_button = QPushButton("Reset to Default")
        self.reset_button.setToolTip("Reset all columns to default visibility and order")
        reset_layout.addStretch()
        reset_layout.addWidget(self.reset_button)
        main_layout.addLayout(reset_layout)

        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.apply_button = QPushButton("Apply")
        self.apply_button.setDefault(True)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)
        main_layout.addLayout(button_layout)

    def _connect_signals(self):
        """Connect UI signals to slots."""
        # Search
        self.search_input.textChanged.connect(self._on_search_changed)

        # Column list
        self.column_list.itemChanged.connect(self._on_item_changed)
        self.column_list.currentRowChanged.connect(self._update_button_states)

        # Reorder buttons
        self.up_button.clicked.connect(self._on_move_up)
        self.down_button.clicked.connect(self._on_move_down)

        # Visibility controls
        self.show_all_button.clicked.connect(self._on_show_all)
        self.hide_all_button.clicked.connect(self._on_hide_all)
        self.auto_hide_checkbox.toggled.connect(self._on_auto_hide_toggled)

        # View management
        self.view_combo.currentTextChanged.connect(self._on_view_changed)
        self.save_view_button.clicked.connect(self._on_save_view)
        self.delete_view_button.clicked.connect(self._on_delete_view)

        # Reset
        self.reset_button.clicked.connect(self._on_reset)

        # Dialog buttons
        self.cancel_button.clicked.connect(self._on_cancel)
        self.apply_button.clicked.connect(self._on_apply)

    def _load_current_config(self):
        """Load the current table configuration."""
        if not hasattr(self.parent_window, 'current_client_id'):
            logger.warning("No client selected, using default config")
            return

        client_id = self.parent_window.current_client_id
        self._is_loading = True

        try:
            # Get current configuration
            config = self.table_config_manager.get_current_config()
            if config is None:
                # Load config for current client
                config = self.table_config_manager.load_config(client_id)

            # Store original config and view name for cancel
            self._original_config = config
            self._original_view_name = self.table_config_manager.get_current_view_name()

            # Load auto-hide setting
            self.auto_hide_checkbox.setChecked(config.auto_hide_empty)

            # Load views
            self._load_views()

            # Load columns
            self._load_columns(config)

        finally:
            self._is_loading = False

    def _load_views(self):
        """Load available views into the combo box."""
        self._is_loading = True
        try:
            self.view_combo.clear()
            views = self.table_config_manager.list_views()

            if not views:
                views = ["Default"]

            self.view_combo.addItems(views)

            # Set current view
            current_view = self.table_config_manager.get_current_view_name()
            index = self.view_combo.findText(current_view)
            if index >= 0:
                self.view_combo.setCurrentIndex(index)

            # Update delete button state
            self._update_delete_button_state()

        finally:
            self._is_loading = False

    def _load_columns(self, config):
        """Load columns into the list widget."""
        self.column_list.clear()
        self._current_columns = []

        # Get columns from current DataFrame or config
        if hasattr(self.parent_window, 'analysis_results_df') and \
           self.parent_window.analysis_results_df is not None:
            df = self.parent_window.analysis_results_df
            all_columns = df.columns.tolist()
        else:
            # No DataFrame, use config columns
            all_columns = config.column_order if config.column_order else list(config.visible_columns.keys())

        # Use config order if available, otherwise use DataFrame order
        if config.column_order:
            # Start with ordered columns
            ordered_columns = [col for col in config.column_order if col in all_columns]
            # Add any new columns not in config
            for col in all_columns:
                if col not in ordered_columns:
                    ordered_columns.append(col)
            columns = ordered_columns
        else:
            columns = all_columns

        # Create list items
        for col_name in columns:
            item = QListWidgetItem(col_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

            # Check if column is visible
            is_visible = config.visible_columns.get(col_name, True)
            item.setCheckState(Qt.Checked if is_visible else Qt.Unchecked)

            # Mark locked columns
            if col_name in config.locked_columns:
                item.setToolTip("⚠ Locked column (always visible and first)")
                # Set bold font for locked columns
                font = item.font()
                font.setBold(True)
                item.setFont(font)

            self.column_list.addItem(item)
            self._current_columns.append(col_name)

        # Update button states
        self._update_button_states()

    def _on_search_changed(self, text: str):
        """Handle search text change."""
        text = text.lower()

        for i in range(self.column_list.count()):
            item = self.column_list.item(i)
            column_name = item.text()

            # Show/hide based on search
            if text in column_name.lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def _on_item_changed(self, item: QListWidgetItem):
        """Handle item check state change."""
        if self._is_loading:
            return

        column_name = item.text()
        config = self.table_config_manager.get_current_config()

        # Prevent unchecking locked columns
        if column_name in config.locked_columns and item.checkState() == Qt.Unchecked:
            self._is_loading = True
            item.setCheckState(Qt.Checked)
            self._is_loading = False

            QMessageBox.warning(
                self,
                "Cannot Hide Column",
                f"Column '{column_name}' is locked and cannot be hidden."
            )

    def _on_move_up(self):
        """Move selected column up in the order."""
        current_row = self.column_list.currentRow()
        if current_row <= 0:
            return

        config = self.table_config_manager.get_current_config()
        item = self.column_list.currentItem()
        column_name = item.text()

        # Prevent moving locked columns or moving to locked position
        if column_name in config.locked_columns:
            QMessageBox.warning(
                self,
                "Cannot Move Column",
                f"Column '{column_name}' is locked and cannot be moved."
            )
            return

        # Prevent moving to position 0 if Order_Number is locked there
        if current_row == 1 and "Order_Number" in config.locked_columns:
            target_col = self.column_list.item(0).text()
            if target_col == "Order_Number":
                QMessageBox.warning(
                    self,
                    "Cannot Move Column",
                    "Cannot move column before locked 'Order_Number' column."
                )
                return

        # Move the item
        item = self.column_list.takeItem(current_row)
        self.column_list.insertItem(current_row - 1, item)
        self.column_list.setCurrentRow(current_row - 1)

        # Update internal list
        self._current_columns.insert(current_row - 1, self._current_columns.pop(current_row))

    def _on_move_down(self):
        """Move selected column down in the order."""
        current_row = self.column_list.currentRow()
        if current_row < 0 or current_row >= self.column_list.count() - 1:
            return

        config = self.table_config_manager.get_current_config()
        item = self.column_list.currentItem()
        column_name = item.text()

        # Prevent moving locked columns
        if column_name in config.locked_columns:
            QMessageBox.warning(
                self,
                "Cannot Move Column",
                f"Column '{column_name}' is locked and cannot be moved."
            )
            return

        # Prevent moving above locked column to position 0
        if current_row == 0 and "Order_Number" in config.locked_columns:
            QMessageBox.warning(
                self,
                "Cannot Move Column",
                "Cannot move locked column."
            )
            return

        # Move the item
        item = self.column_list.takeItem(current_row)
        self.column_list.insertItem(current_row + 1, item)
        self.column_list.setCurrentRow(current_row + 1)

        # Update internal list
        self._current_columns.insert(current_row + 1, self._current_columns.pop(current_row))

    def _on_show_all(self):
        """Show all columns and disable auto-hide."""
        self._is_loading = True
        try:
            for i in range(self.column_list.count()):
                item = self.column_list.item(i)
                item.setCheckState(Qt.Checked)
        finally:
            self._is_loading = False

        # Disable auto-hide so empty columns stay visible after Apply
        self.auto_hide_checkbox.setChecked(False)

    def _on_hide_all(self):
        """Hide all columns (except locked ones)."""
        config = self.table_config_manager.get_current_config()

        self._is_loading = True
        try:
            for i in range(self.column_list.count()):
                item = self.column_list.item(i)
                column_name = item.text()

                # Skip locked columns
                if column_name in config.locked_columns:
                    continue

                item.setCheckState(Qt.Unchecked)
        finally:
            self._is_loading = False

    def _on_auto_hide_toggled(self, checked: bool):
        """Handle auto-hide toggle."""
        # Will be saved when Apply is clicked
        pass

    def _on_view_changed(self, view_name: str):
        """Handle view selection change."""
        if self._is_loading or not view_name:
            return

        # Load the selected view
        config = self.table_config_manager.load_view(view_name)
        if config:
            self._is_loading = True
            try:
                # Update UI with new config
                self.auto_hide_checkbox.setChecked(config.auto_hide_empty)
                self._load_columns(config)
            finally:
                self._is_loading = False

        # Update delete button state
        self._update_delete_button_state()

    def _on_save_view(self):
        """Save current configuration as a named view."""
        # Get view name from user
        view_name, ok = QInputDialog.getText(
            self,
            "Save View As",
            "Enter view name:",
            text=""
        )

        if not ok or not view_name.strip():
            return

        view_name = view_name.strip()

        # Check if view already exists
        existing_views = self.table_config_manager.list_views()
        if view_name in existing_views:
            reply = QMessageBox.question(
                self,
                "Overwrite View",
                f"View '{view_name}' already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Create config from current UI state
        config = self._get_config_from_ui()

        # Save view
        try:
            self.table_config_manager.save_view(view_name, config)
            logger.info(f"View '{view_name}' saved successfully")

            # Reload views and select the new one
            self._load_views()
            index = self.view_combo.findText(view_name)
            if index >= 0:
                self.view_combo.setCurrentIndex(index)

            QMessageBox.information(
                self,
                "View Saved",
                f"View '{view_name}' has been saved successfully."
            )
        except Exception as e:
            logger.error(f"Failed to save view '{view_name}': {e}")
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save view: {str(e)}"
            )

    def _on_delete_view(self):
        """Delete the currently selected view."""
        view_name = self.view_combo.currentText()

        if not view_name or view_name == "Default":
            QMessageBox.warning(
                self,
                "Cannot Delete",
                "Cannot delete the Default view."
            )
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete View",
            f"Are you sure you want to delete view '{view_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        # Delete view
        try:
            self.table_config_manager.delete_view(view_name)
            logger.info(f"View '{view_name}' deleted successfully")

            # Reload views and select Default
            self._load_views()
            index = self.view_combo.findText("Default")
            if index >= 0:
                self.view_combo.setCurrentIndex(index)

        except Exception as e:
            logger.error(f"Failed to delete view '{view_name}': {e}")
            QMessageBox.critical(
                self,
                "Delete Failed",
                f"Failed to delete view: {str(e)}"
            )

    def _on_reset(self):
        """Reset to default configuration."""
        reply = QMessageBox.question(
            self,
            "Reset to Default",
            "This will reset all columns to default visibility and order. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        # Get default config
        if hasattr(self.parent_window, 'analysis_results_df') and \
           self.parent_window.analysis_results_df is not None:
            df = self.parent_window.analysis_results_df
            columns = df.columns.tolist()
        else:
            # Use current columns
            columns = self._current_columns

        default_config = self.table_config_manager.get_default_config(columns)

        # Load default config into UI
        self._is_loading = True
        try:
            self.auto_hide_checkbox.setChecked(default_config.auto_hide_empty)
            self._load_columns(default_config)
        finally:
            self._is_loading = False

    def _on_cancel(self):
        """Cancel changes and restore original view."""
        # Restore original view if it was changed
        if self._original_view_name and hasattr(self.parent_window, 'current_client_id'):
            client_id = self.parent_window.current_client_id
            if client_id:
                # Reload original view
                self.table_config_manager.load_config(client_id, self._original_view_name)
                logger.info(f"Restored original view: {self._original_view_name}")

        # Close dialog
        self.reject()

    def _on_apply(self):
        """Apply the current configuration."""
        try:
            # Create config from UI state
            config = self._get_config_from_ui()

            # Save configuration
            if hasattr(self.parent_window, 'current_client_id') and self.parent_window.current_client_id:
                client_id = self.parent_window.current_client_id
                view_name = self.view_combo.currentText() or "Default"
                self.table_config_manager.save_config(client_id, config, view_name)

                # Apply to table view if available
                if hasattr(self.parent_window, 'tableView') and \
                   hasattr(self.parent_window, 'analysis_results_df') and \
                   self.parent_window.analysis_results_df is not None:
                    self.table_config_manager.apply_config_to_view(
                        self.parent_window.tableView,
                        self.parent_window.analysis_results_df
                    )

                logger.info("Column configuration applied successfully")

                # Emit signal
                self.config_applied.emit()

                # Close dialog
                self.accept()
            else:
                QMessageBox.warning(
                    self,
                    "No Client Selected",
                    "Please select a client before applying configuration."
                )

        except Exception as e:
            logger.error(f"Failed to apply configuration: {e}")
            QMessageBox.critical(
                self,
                "Apply Failed",
                f"Failed to apply configuration: {str(e)}"
            )

    def _get_config_from_ui(self):
        """Create TableConfig from current UI state."""
        from gui.table_config_manager import TableConfig

        # Get column order and visibility
        visible_columns = {}
        column_order = []

        for i in range(self.column_list.count()):
            item = self.column_list.item(i)
            column_name = item.text()
            is_visible = item.checkState() == Qt.Checked

            visible_columns[column_name] = is_visible
            column_order.append(column_name)

        # Get current config for widths and locked columns
        current_config = self.table_config_manager.get_current_config()
        if current_config is None:
            current_config = self.table_config_manager.get_default_config(column_order)

        # Create new config
        config = TableConfig(
            version=1,
            visible_columns=visible_columns,
            column_order=column_order,
            column_widths=current_config.column_widths.copy(),
            auto_hide_empty=self.auto_hide_checkbox.isChecked(),
            locked_columns=current_config.locked_columns.copy()
        )

        return config

    def _update_button_states(self):
        """Update enabled state of reorder buttons."""
        current_row = self.column_list.currentRow()
        count = self.column_list.count()

        # Up button: enabled if not first row
        self.up_button.setEnabled(current_row > 0)

        # Down button: enabled if not last row
        self.down_button.setEnabled(current_row >= 0 and current_row < count - 1)

    def _update_delete_button_state(self):
        """Update enabled state of delete view button."""
        view_name = self.view_combo.currentText()
        # Cannot delete Default view
        self.delete_view_button.setEnabled(view_name != "Default" and bool(view_name))
