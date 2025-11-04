"""Main Application Window - Central Hub for Shopify Fulfillment Tool.

This module implements the primary application window that serves as the
central hub for all user interactions. It orchestrates the complex interplay
between UI components, data processing, and configuration management.

Architecture:
    The MainWindow follows a delegation pattern, distributing responsibilities
    across specialized handler objects:
    - UIManager: Widget creation and layout
    - FileHandler: File selection and validation
    - ActionsHandler: Business logic execution
    - ClientManager: Server-based client configuration management

Key Responsibilities:
    1. Application lifecycle management (init, close, session persistence)
    2. Client configuration management (load, save, switch via ClientManager)
    3. Server connection and error handling
    4. UI state coordination across tabs and widgets
    5. Data model management (analysis_results_df, proxy filtering)
    6. Event routing (signals/slots between components)

Client System:
    Multi-client support allows users to maintain separate configurations
    for different warehouses or workflows. Each client contains:
    - Settings (delimiters, thresholds, paths)
    - Rules (automation logic)
    - Packing Lists (report templates)
    - Stock Exports (courier templates)
    - Column Mappings (CSV field definitions)

    Clients are stored on a file server, managed by ClientManager:
    - Each client has a dedicated folder: CLIENTS/{CLIENT_ID}/
    - Configuration stored in: CLIENTS/{CLIENT_ID}/shopify_config.json
    - Centralized access from multiple users/machines

Session Persistence:
    On close, the application saves:
    - Current analysis DataFrame
    - Visible column selection
    These are restored on next launch if user confirms.

    ⚠️ CRITICAL ISSUE (see CRITICAL_ANALYSIS.md Section 7.1):
        Uses pickle for session data (security risk, not human-readable)
        Recommended: Replace with Parquet + JSON

Data Flow:
    User Action → Signal → Handler Method → Backend Function → Update DataFrame
    → Emit data_changed Signal → Update All Views (table, stats, logs)

Thread Safety:
    - Most operations run on main UI thread
    - Long-running tasks (analysis, reports) use QThreadPool Workers
    - Workers emit signals back to main thread for UI updates

Critical Issues:
    - Section 7.1: Pickle for session persistence (security risk)
    - Network dependency: Application requires file server access to start

Memory Management:
    - analysis_results_df can be large (10k+ rows)
    - Proxy model adds overhead for filtering/sorting
    - Session pickle can grow to several MB
"""

import sys
import os
import json
import shutil
import pickle
import logging
from datetime import datetime

import pandas as pd
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QMenu, QTableWidgetItem, QLabel, QInputDialog
from PySide6.QtCore import QThreadPool, QPoint, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QAction

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shopify_tool.utils import get_persistent_data_path, resource_path
from shopify_tool.analysis import recalculate_statistics
from gui.log_handler import QtLogHandler
from gui.ui_manager import UIManager
from gui.file_handler import FileHandler
from gui.actions_handler import ActionsHandler
from common.client_manager import ClientManager


class MainWindow(QMainWindow):
    """The main window for the Shopify Fulfillment Tool application.

    This class encapsulates the main user interface and orchestrates the
    interactions between the UI elements, the data processing backend, and
    various handlers for files, actions, and UI management.

    Attributes:
        session_path (str): The directory path for the current work session.
        client_manager (ClientManager): Manages client configurations on file server.
        active_client_id (str): The ID of the currently active client.
        active_profile_config (dict): The configuration for the active client (shopify section).
        orders_file_path (str): The path to the loaded orders CSV file.
        stock_file_path (str): The path to the loaded stock CSV file.
        analysis_results_df (pd.DataFrame): The main DataFrame holding the
            results of the fulfillment analysis.
        analysis_stats (dict): A dictionary of statistics derived from the
            analysis results.
        threadpool (QThreadPool): A thread pool for running background tasks.
        proxy_model (QSortFilterProxyModel): The proxy model for filtering and
            sorting the main results table.
        ui_manager (UIManager): Handles the creation and state of UI widgets.
        file_handler (FileHandler): Manages file selection and loading logic.
        actions_handler (ActionsHandler): Handles user actions like running
            analysis or generating reports.
    """

    def __init__(self):
        """Initializes the MainWindow, sets up UI, and connects signals."""
        super().__init__()
        self.setWindowTitle("Shopify Fulfillment Tool (PySide6 Refactored)")
        self.setGeometry(100, 100, 950, 800)

        # Core application attributes
        self.session_path = None

        # Initialize ClientManager
        SERVER_PATH = r"\\192.168.88.101\Z_GreenDelivery\WAREHOUSE\1FULFILMENT tool"
        try:
            self.client_manager = ClientManager(SERVER_PATH)
            logging.info("ClientManager initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize ClientManager: {e}")
            QMessageBox.critical(
                self,
                "Server Connection Error",
                f"Cannot connect to file server:\n\n{SERVER_PATH}\n\n{e}\n\n"
                f"Please check your network connection."
            )
            sys.exit(1)

        # Client state (replaces profile state)
        self.active_client_id = None
        self.active_profile_config = {}  # Keep this name for compatibility with rest of code

        self.orders_file_path = None
        self.stock_file_path = None
        self.analysis_results_df = pd.DataFrame()
        self.analysis_stats = None
        self.threadpool = QThreadPool()

        # Table display attributes
        self.all_columns = []
        self.visible_columns = []
        self.is_syncing_selection = False

        # Models
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)  # Search across all columns

        # Initialize handlers
        self.ui_manager = UIManager(self)
        self.file_handler = FileHandler(self)
        self.actions_handler = ActionsHandler(self)

        self._init_and_load_clients()
        self.session_file = get_persistent_data_path("session_data.pkl")

        # Setup UI and connect signals
        self.ui_manager.create_widgets()
        self.connect_signals()
        self.setup_logging()

        self.load_session()
        self.update_client_combo()

    def _init_and_load_clients(self):
        """Initialize and load client configurations from server."""
        try:
            # Get list of available clients
            clients = self.client_manager.list_clients()

            if not clients:
                # No clients exist - create first one
                reply = QMessageBox.question(
                    self,
                    "No Clients Found",
                    "No clients found on server. Create first client?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    name, ok = QInputDialog.getText(
                        self, "Create Client", "Enter client name:"
                    )
                    if ok and name:
                        client_id = f"CLIENT_{name.upper().replace(' ', '_')}"
                        success = self.client_manager.create_client(client_id, name)
                        if success:
                            clients = self.client_manager.list_clients()
                        else:
                            QMessageBox.critical(self, "Error", "Failed to create client")
                            sys.exit(1)
                    else:
                        sys.exit(1)
                else:
                    sys.exit(1)

            # Load first client as active (in future: load from saved preference)
            first_client = clients[0]
            self.active_client_id = first_client["client_id"]

            # Load full client config
            client_config = self.client_manager.load_config(self.active_client_id)

            # Set active_profile_config to shopify section (for compatibility)
            self.active_profile_config = client_config.get("shopify", {})

            logging.info(f"Loaded client: {first_client['name']} ({self.active_client_id})")

        except Exception as e:
            logging.error(f"Failed to load clients: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"Failed to load client configurations:\n\n{e}"
            )
            sys.exit(1)

    def _save_client_config(self):
        """Save active client configuration to server."""
        if not self.active_client_id:
            logging.warning("No active client to save")
            return

        try:
            # Load full client config
            client_config = self.client_manager.load_config(self.active_client_id)

            # Update shopify section with current active_profile_config
            client_config["shopify"] = self.active_profile_config

            # Save back to server
            success = self.client_manager.save_config(self.active_client_id, client_config)

            if success:
                logging.info(f"Saved configuration for client: {self.active_client_id}")
            else:
                logging.error(f"Failed to save configuration for client: {self.active_client_id}")
                QMessageBox.warning(
                    self,
                    "Save Error",
                    "Failed to save configuration to server."
                )
        except Exception as e:
            logging.error(f"Error saving client config: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save configuration:\n\n{e}"
            )

    def _get_default_shopify_config(self):
        """
        Get default shopify configuration section.

        This returns ONLY the 'shopify' section of the config.
        Top-level fields (client_id, name, etc.) are handled by ClientManager.
        """
        return {
            "column_mappings": {
                "orders": {
                    "name": "Name",
                    "sku": "Lineitem sku",
                    "quantity": "Lineitem quantity",
                    "shipping_provider": "Shipping Provider",
                    "fulfillment_status": "Fulfillment Status",
                    "financial_status": "Financial Status",
                    "order_number": "Name"
                },
                "stock": {
                    "sku": "Артикул",
                    "stock": "Наличност"
                },
                "orders_required": ["Name", "Lineitem sku", "Lineitem quantity"],
                "stock_required": ["Артикул", "Наличност"]
            },
            "settings": {
                "stock_csv_delimiter": ";",
                "low_stock_threshold": 10
            },
            "courier_mappings": {
                "type": "pattern_matching",
                "case_sensitive": False,
                "rules": [
                    {"pattern": "dhl", "standardized_name": "DHL"},
                    {"pattern": "speedy", "standardized_name": "Speedy"},
                    {"pattern": "econt", "standardized_name": "Econt"},
                    {"pattern": "dpd", "standardized_name": "DPD"},
                    {"pattern": "ups", "standardized_name": "UPS"}
                ],
                "default": "Other"
            },
            "rules": [],
            "packing_lists": [],
            "stock_exports": [],
            "virtual_products": {},
            "deduction_rules": {}
        }

    def setup_logging(self):
        """Sets up the Qt-based logging handler.

        Initializes a `QtLogHandler` that emits a signal whenever a log
        message is received. This signal is connected to a slot that appends
        the message to the 'Execution Log' text box in the UI.
        """
        self.log_handler = QtLogHandler()
        self.log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)
        self.log_handler.log_message_received.connect(self.execution_log_edit.appendPlainText)

    def connect_signals(self):
        """Connects all UI widget signals to their corresponding slots.

        This method centralizes all signal-slot connections for the main
        window, including button clicks, text changes, and custom signals
        from handler classes. This makes the UI event flow easier to trace.
        """
        # Client management
        self.profile_combo.currentIndexChanged.connect(self.set_active_client)
        self.manage_profiles_btn.clicked.connect(self.open_client_manager)

        # Session and file loading
        self.new_session_btn.clicked.connect(self.actions_handler.create_new_session)
        self.load_orders_btn.clicked.connect(self.file_handler.select_orders_file)
        self.load_stock_btn.clicked.connect(self.file_handler.select_stock_file)

        # Main actions
        self.run_analysis_button.clicked.connect(self.actions_handler.run_analysis)
        self.settings_button.clicked.connect(self.actions_handler.open_settings_window)

        # Reports
        self.report_builder_button.clicked.connect(self.actions_handler.open_report_builder_window)
        self.packing_list_button.clicked.connect(
            lambda: self.actions_handler.open_report_selection_dialog("packing_lists")
        )
        self.stock_export_button.clicked.connect(
            lambda: self.actions_handler.open_report_selection_dialog("stock_exports")
        )

        # Table interactions
        self.tableView.customContextMenuRequested.connect(self.show_context_menu)
        self.tableView.doubleClicked.connect(self.on_table_double_clicked)

        # Custom signals
        self.actions_handler.data_changed.connect(self._update_all_views)

        # Filter input
        self.filter_input.textChanged.connect(self.filter_table)
        self.filter_column_selector.currentIndexChanged.connect(self.filter_table)
        self.case_sensitive_checkbox.stateChanged.connect(self.filter_table)
        self.clear_filter_button.clicked.connect(self.clear_filter)

    def clear_filter(self):
        """Clears the filter input text box."""
        self.filter_input.clear()

    # --- Client Management ---
    def update_client_combo(self):
        """Update the client selection dropdown."""
        try:
            self.profile_combo.blockSignals(True)
            self.profile_combo.clear()

            # Get clients from server
            clients = self.client_manager.list_clients()

            # Add clients to combo box
            for client in clients:
                # Display name, store client_id as data
                self.profile_combo.addItem(client["name"], client["client_id"])

            # Set current client
            if self.active_client_id:
                index = self.profile_combo.findData(self.active_client_id)
                if index >= 0:
                    self.profile_combo.setCurrentIndex(index)

            self.profile_combo.blockSignals(False)
            logging.info(f"Client combo updated with {len(clients)} clients")

        except Exception as e:
            logging.error(f"Error updating client combo: {e}", exc_info=True)

    def set_active_client(self, client_id_or_index):
        """Switch to a different client."""
        # Handle both direct calls and combo box signals
        if isinstance(client_id_or_index, int):
            client_id = self.profile_combo.itemData(client_id_or_index)
        else:
            client_id = client_id_or_index

        if not client_id or client_id == self.active_client_id:
            return

        try:
            # Load client config from server
            client_config = self.client_manager.load_config(client_id)

            # Validate and repair config if needed
            needs_save = False

            # Ensure 'shopify' section exists
            if "shopify" not in client_config:
                logging.warning(f"Client {client_id} missing 'shopify' section, adding default")
                client_config["shopify"] = self._get_default_shopify_config()
                needs_save = True

            # Validate all required keys in shopify section
            default_shopify = self._get_default_shopify_config()
            for key, default_value in default_shopify.items():
                if key not in client_config["shopify"]:
                    logging.warning(f"Client {client_id} missing shopify.{key}, adding default")
                    client_config["shopify"][key] = default_value
                    needs_save = True

            # Save repaired config back to server
            if needs_save:
                self.client_manager.save_config(client_id, client_config)
                logging.info(f"Repaired and saved config for client {client_id}")

            # Update active state
            self.active_client_id = client_id
            self.active_profile_config = client_config["shopify"]

            # Ensure client session directory exists
            self.client_manager.ensure_client_session_dir(client_id)

            # Log the switch
            client_name = client_config.get("name", client_id)
            self.log_activity("Clients", f"Switched to client: {client_name}")
            logging.info(f"Switched to client: {client_name} ({client_id})")

            # Clear analysis data
            self.analysis_results_df = pd.DataFrame()
            self.analysis_stats = None

            # Refresh UI
            self._update_all_views()
            self.update_client_combo()

        except Exception as e:
            logging.error(f"Error switching to client {client_id}: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "Client Switch Error",
                f"Could not switch to selected client:\n\n{e}"
            )
            # Revert combo box to previous selection
            if self.active_client_id:
                index = self.profile_combo.findData(self.active_client_id)
                if index >= 0:
                    self.profile_combo.blockSignals(True)
                    self.profile_combo.setCurrentIndex(index)
                    self.profile_combo.blockSignals(False)

    def open_client_manager(self):
        """Open client management dialog."""
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton
            from PySide6.QtCore import Qt

            clients = self.client_manager.list_clients()

            # Track newly created client
            newly_created_client = {"client_id": None}

            # Create simple dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Client Management")
            dialog.setMinimumWidth(400)

            layout = QVBoxLayout(dialog)

            # Client list
            list_label = QLabel("Active Clients:")
            layout.addWidget(list_label)

            client_list = QListWidget()
            for client in clients:
                item = QListWidgetItem(f"{client['name']} ({client['client_id']})")
                item.setData(Qt.UserRole, client['client_id'])
                client_list.addItem(item)
            layout.addWidget(client_list)

            # Buttons
            btn_layout = QHBoxLayout()

            # New Client button
            new_btn = QPushButton("Create New Client")
            new_btn.clicked.connect(lambda: self._create_new_client_dialog(dialog, client_list, newly_created_client))
            btn_layout.addWidget(new_btn)

            # Delete Client button
            delete_btn = QPushButton("Delete Client")
            delete_btn.clicked.connect(lambda: self._delete_client_dialog(client_list))
            btn_layout.addWidget(delete_btn)

            # Switch Client button
            switch_btn = QPushButton("Switch to Selected")
            switch_btn.clicked.connect(lambda: self._switch_to_selected_client(dialog, client_list))
            btn_layout.addWidget(switch_btn)

            # Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(close_btn)

            layout.addLayout(btn_layout)

            result = dialog.exec()

            # After dialog closes, refresh UI and select newly created client if any
            if result == QDialog.Accepted or newly_created_client["client_id"]:
                # Refresh client dropdown
                self.update_client_combo()

                # Select newly created client if any
                if newly_created_client["client_id"]:
                    index = self.profile_combo.findData(newly_created_client["client_id"])
                    if index >= 0:
                        self.profile_combo.setCurrentIndex(index)

        except Exception as e:
            logging.error(f"Error opening client manager: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to open client manager:\n\n{e}")

    def _create_new_client_dialog(self, parent_dialog, client_list, newly_created_client):
        """Create new client dialog."""
        name, ok = QInputDialog.getText(
            parent_dialog,
            "Create New Client",
            "Enter client name:"
        )

        if ok and name:
            client_id = f"CLIENT_{name.upper().replace(' ', '_')}"

            success = self.client_manager.create_client(client_id, name)

            if success:
                QMessageBox.information(parent_dialog, "Success", f"Client '{name}' created successfully")

                # Store newly created client ID
                newly_created_client["client_id"] = client_id

                # Refresh list
                from PySide6.QtWidgets import QListWidgetItem
                from PySide6.QtCore import Qt

                client_list.clear()
                clients = self.client_manager.list_clients()
                for client in clients:
                    item = QListWidgetItem(f"{client['name']} ({client['client_id']})")
                    item.setData(Qt.UserRole, client['client_id'])
                    client_list.addItem(item)
            else:
                QMessageBox.warning(parent_dialog, "Error", "Failed to create client")

    def _delete_client_dialog(self, client_list):
        """Delete selected client."""
        current_item = client_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a client to delete")
            return

        from PySide6.QtCore import Qt
        client_id = current_item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete client:\n\n{current_item.text()}\n\n"
            f"This will mark the client as inactive.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = self.client_manager.delete_client(client_id)
            if success:
                QMessageBox.information(self, "Success", "Client deleted (marked inactive)")
                client_list.takeItem(client_list.currentRow())
            else:
                QMessageBox.warning(self, "Error", "Failed to delete client")

    def _switch_to_selected_client(self, dialog, client_list):
        """Switch to selected client and close dialog."""
        current_item = client_list.currentItem()
        if not current_item:
            QMessageBox.warning(dialog, "No Selection", "Please select a client")
            return

        from PySide6.QtCore import Qt
        client_id = current_item.data(Qt.UserRole)
        self.set_active_client(client_id)
        dialog.accept()

    def open_client_selector(self):
        """Legacy method - redirect to open_client_manager."""
        self.open_client_manager()

    def filter_table(self):
        """Applies the current filter settings to the results table view.

        Reads the filter text, selected column, and case sensitivity setting
        from the UI controls and applies them to the `QSortFilterProxyModel`
        to update the visible rows in the table.
        """
        text = self.filter_input.text()
        column_index = self.filter_column_selector.currentIndex()

        # First item is "All Columns", so filter should be -1
        filter_column = column_index - 1

        case_sensitivity = Qt.CaseSensitive if self.case_sensitive_checkbox.isChecked() else Qt.CaseInsensitive

        self.proxy_model.setFilterKeyColumn(filter_column)
        self.proxy_model.setFilterCaseSensitivity(case_sensitivity)
        self.proxy_model.setFilterRegularExpression(text)

    def _update_all_views(self):
        """Central slot to refresh all UI components after data changes.

        This method is called whenever the main `analysis_results_df` is
        modified. It recalculates statistics, updates the main results table,
        refreshes the statistics tab, and repopulates the column filter
        dropdown. It acts as a single point of refresh for the UI.
        """
        self.analysis_stats = recalculate_statistics(self.analysis_results_df)
        self.ui_manager.update_results_table(self.analysis_results_df)
        self.update_statistics_tab()

        # Populate filter dropdown
        self.filter_column_selector.clear()
        self.filter_column_selector.addItem("All Columns")
        if not self.analysis_results_df.empty:
            self.filter_column_selector.addItems(self.all_columns)
        self.ui_manager.set_ui_busy(False)
        # The column manager button is enabled within update_results_table

    def update_statistics_tab(self):
        """Populates the 'Statistics' tab with the latest analysis data.

        Clears any existing data and redraws the statistics display,
        including the main stats labels and the detailed grid of courier
        statistics.
        """
        if not self.analysis_stats:
            return
        for key, label in self.stats_labels.items():
            label.setText(str(self.analysis_stats.get(key, "N/A")))

        # Clear previous stats
        while self.courier_stats_layout.count():
            child = self.courier_stats_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        courier_stats = self.analysis_stats.get("couriers_stats")
        if courier_stats:
            # Re-create headers and data
            headers = ["Courier ID", "Orders Assigned", "Repeated Orders"]
            for i, header_text in enumerate(headers):
                header_label = QLabel(header_text)
                header_label.setStyleSheet("font-weight: bold;")
                self.courier_stats_layout.addWidget(header_label, 0, i)
            for i, stats in enumerate(courier_stats, start=1):
                self.courier_stats_layout.addWidget(QLabel(stats.get("courier_id", "N/A")), i, 0)
                self.courier_stats_layout.addWidget(QLabel(str(stats.get("orders_assigned", "N/A"))), i, 1)
                self.courier_stats_layout.addWidget(QLabel(str(stats.get("repeated_orders_found", "N/A"))), i, 2)
        else:
            self.courier_stats_layout.addWidget(QLabel("No courier stats available."), 0, 0)

    def log_activity(self, op_type, desc):
        """Adds a new entry to the 'Activity Log' table in the UI.

        Args:
            op_type (str): The type of operation (e.g., "Session", "Analysis").
            desc (str): A description of the activity.
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.activity_log_table.insertRow(0)
        self.activity_log_table.setItem(0, 0, QTableWidgetItem(current_time))
        self.activity_log_table.setItem(0, 1, QTableWidgetItem(op_type))
        self.activity_log_table.setItem(0, 2, QTableWidgetItem(desc))

    def on_table_double_clicked(self, index: QModelIndex):
        """Handles double-click events on the results table.

        A double-click on a row triggers the toggling of the fulfillment
        status for the corresponding order.

        Args:
            index (QModelIndex): The model index of the cell that was
                double-clicked.
        """
        if not index.isValid():
            return

        source_index = self.proxy_model.mapToSource(index)
        source_model = self.proxy_model.sourceModel()

        # We need the original, unfiltered dataframe for this operation
        order_number_col_idx = source_model.get_column_index("Order_Number")
        order_number = source_model.index(source_index.row(), order_number_col_idx).data()

        if order_number:
            self.actions_handler.toggle_fulfillment_status_for_order(order_number)

    def show_context_menu(self, pos: QPoint):
        """Shows a context menu for the results table view.

        The menu is populated with actions relevant to the clicked row,
        such as changing order status, copying data, or removing items/orders.

        Args:
            pos (QPoint): The position where the right-click occurred, in the
                table's viewport coordinates.
        """
        if self.analysis_results_df.empty:
            return
        table = self.sender()
        index = table.indexAt(pos)
        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            source_model = self.proxy_model.sourceModel()

            order_col_idx = source_model.get_column_index("Order_Number")
            sku_col_idx = source_model.get_column_index("SKU")

            order_number = source_model.index(source_index.row(), order_col_idx).data()
            sku = source_model.index(source_index.row(), sku_col_idx).data()

            if not order_number:
                return

            menu = QMenu()
            # Dynamically create actions and connect them
            actions = [
                ("Change Status", lambda: self.actions_handler.toggle_fulfillment_status_for_order(order_number)),
                ("Add Tag Manually...", lambda: self.actions_handler.add_tag_manually(order_number)),
                ("---", None),
                (
                    f"Remove Item {sku} from Order",
                    lambda: self.actions_handler.remove_item_from_order(source_index.row()),
                ),
                (f"Remove Entire Order {order_number}", lambda: self.actions_handler.remove_entire_order(order_number)),
                ("---", None),
                ("Copy Order Number", lambda: QApplication.clipboard().setText(order_number)),
                ("Copy SKU", lambda: QApplication.clipboard().setText(sku)),
            ]
            for text, func in actions:
                if text == "---":
                    menu.addSeparator()
                else:
                    action = QAction(text, self)
                    action.triggered.connect(func)
                    menu.addAction(action)
            menu.exec(table.viewport().mapToGlobal(pos))

    def closeEvent(self, event):
        """Handles the application window being closed.

        Saves the current analysis DataFrame and visible columns to a session
        pickle file, allowing the user to restore their work later.

        Args:
            event: The close event.
        """
        if not self.analysis_results_df.empty:
            try:
                session_data = {"dataframe": self.analysis_results_df, "visible_columns": self.visible_columns}
                with open(self.session_file, "wb") as f:
                    pickle.dump(session_data, f)
                self.log_activity("Session", "Session data saved on exit.")
            except Exception as e:
                logging.error(f"Error saving session automatically: {e}", exc_info=True)
        event.accept()

    def load_session(self):
        """Loads a previous session from a pickle file if available.

        If a session file exists, it prompts the user to restore it. If they
        agree, the DataFrame and column visibility are loaded from the file,
        and the UI is updated. The session file is deleted after the attempt.
        """
        if os.path.exists(self.session_file):
            reply = QMessageBox.question(
                self, "Restore Session", "A previous session was found. Do you want to restore it?"
            )
            if reply == QMessageBox.Yes:
                try:
                    with open(self.session_file, "rb") as f:
                        session_data = pickle.load(f)
                    self.analysis_results_df = session_data.get("dataframe", pd.DataFrame())
                    all_df_cols = [c for c in self.analysis_results_df.columns if c != "Order_Number"]
                    self.visible_columns = session_data.get("visible_columns", all_df_cols)
                    self.all_columns = all_df_cols
                    self._update_all_views()
                    self.log_activity("Session", "Restored previous session.")
                except Exception as e:
                    QMessageBox.critical(self, "Load Error", f"Failed to load session file: {e}")
            try:
                os.remove(self.session_file)
            except Exception as e:
                self.log_activity("Error", f"Failed to remove session file: {e}")


if __name__ == "__main__":
    if "pytest" in sys.modules or os.environ.get("CI"):
        QApplication.setPlatform("offscreen")
    app = QApplication(sys.argv)
    window = MainWindow()
    if QApplication.platformName() != "offscreen":
        window.show()
        sys.exit(app.exec())
    else:
        print("Running in offscreen mode for verification.")
