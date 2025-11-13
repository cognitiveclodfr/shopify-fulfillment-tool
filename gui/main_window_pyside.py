import sys
import os
import json
import shutil
import pickle
import logging
from datetime import datetime

import pandas as pd
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QMenu, QTableWidgetItem, QLabel
from PySide6.QtCore import QThreadPool, QPoint, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QAction

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shopify_tool.utils import resource_path
from shopify_tool.analysis import recalculate_statistics
from shopify_tool.profile_manager import ProfileManager, NetworkError
from shopify_tool.session_manager import SessionManager
from gui.log_handler import QtLogHandler
from gui.ui_manager import UIManager
from gui.file_handler import FileHandler
from gui.actions_handler import ActionsHandler
from gui.client_selector_widget import ClientSelectorWidget
from gui.session_browser_widget import SessionBrowserWidget
from gui.profile_manager_dialog import ProfileManagerDialog


class MainWindow(QMainWindow):
    """The main window for the Shopify Fulfillment Tool application.

    This class encapsulates the main user interface and orchestrates the
    interactions between the UI elements, the data processing backend, and
    various handlers for files, actions, and UI management.

    Attributes:
        session_path (str): The directory path for the current work session.
        config (dict): The application's configuration settings.
        config_path (str): The path to the user's config.json file.
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
        self.setWindowTitle("Shopify Fulfillment Tool - New Architecture")
        self.setGeometry(100, 100, 1100, 900)

        # Setup status bar for user feedback
        self.statusBar().showMessage("Ready")

        # Core application attributes
        self.session_path = None
        self.current_client_id = None
        self.current_client_config = None
        self.active_profile_config = {}

        self.orders_file_path = None
        self.stock_file_path = None
        self.analysis_results_df = None
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

        # Initialize new architecture managers
        self._init_managers()

        # Initialize handlers
        self.ui_manager = UIManager(self)
        self.file_handler = FileHandler(self)
        self.actions_handler = ActionsHandler(self)

        # Setup UI and connect signals
        self.ui_manager.create_widgets()
        self.connect_signals()
        self.setup_logging()

    def _init_managers(self):
        """Initialize ProfileManager and SessionManager for the new architecture."""
        # ProfileManager now auto-detects environment:
        # 1. First checks FULFILLMENT_SERVER_PATH environment variable (dev mode)
        # 2. Falls back to default production path
        # This allows seamless switching between dev and production without code changes

        # Initialize ProfileManager with auto-detection (pass None or no argument)
        try:
            self.profile_manager = ProfileManager()  # Auto-detects from environment
            self.session_manager = SessionManager(self.profile_manager)
            logging.info("ProfileManager and SessionManager initialized successfully")
        except NetworkError as e:
            QMessageBox.critical(
                self,
                "Network Error",
                f"Cannot connect to file server:\n\n{str(e)}\n\n"
                f"The application will use offline mode with limited functionality."
            )
            # For now, exit the application if we can't connect
            # In the future, we could implement an offline mode
            QApplication.quit()
            return
        except Exception as e:
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"Failed to initialize profile managers:\n{str(e)}"
            )
            QApplication.quit()
            return

    def load_client_config(self, client_id: str):
        """Load configuration for the selected client.

        Args:
            client_id: Client ID to load configuration for
        """
        if not client_id:
            return

        try:
            # Load shopify config for this client
            config = self.profile_manager.load_shopify_config(client_id)

            if config:
                self.active_profile_config = config
                self.current_client_id = client_id
                logging.info(f"Loaded configuration for CLIENT_{client_id}")

                # Update UI to reflect new client
                self.session_path_label.setText(f"Client: CLIENT_{client_id} - No session started")

                # Enable client-specific buttons
                self.new_session_btn.setEnabled(True)
                self.settings_button.setEnabled(True)

                # Reset analysis data when switching clients
                self.analysis_results_df = None
                self.analysis_stats = None
                self.session_path = None
                self._update_all_views()

                # Disable file loading buttons until a session is created/selected
                self.load_orders_btn.setEnabled(False)
                self.load_stock_btn.setEnabled(False)

                # Disable report buttons until new analysis
                self.run_analysis_button.setEnabled(False)
                if hasattr(self, 'packing_list_button'):
                    self.packing_list_button.setEnabled(False)
                if hasattr(self, 'stock_export_button'):
                    self.stock_export_button.setEnabled(False)
                if hasattr(self, 'add_product_button'):
                    self.add_product_button.setEnabled(False)

                self.log_activity("Client", f"Switched to CLIENT_{client_id}")
            else:
                QMessageBox.warning(
                    self,
                    "Configuration Error",
                    f"Could not load configuration for CLIENT_{client_id}"
                )
        except Exception as e:
            logging.error(f"Failed to load client config: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load client configuration:\n{str(e)}"
            )

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
        # Client selection (new architecture)
        self.client_selector.client_changed.connect(self.on_client_changed)

        # Session browser (new architecture - Phase 4)
        if hasattr(self, 'session_browser'):
            self.session_browser.session_selected.connect(self.on_session_selected)

        # Session and file loading
        self.new_session_btn.clicked.connect(self.actions_handler.create_new_session)

        # Connect mode change signals
        self.orders_single_radio.toggled.connect(self.ui_manager.on_orders_mode_changed)
        self.stock_single_radio.toggled.connect(self.ui_manager.on_stock_mode_changed)

        # Connect file/folder selection buttons (will handle both modes)
        self.load_orders_btn.clicked.connect(self.file_handler.on_orders_select_clicked)
        self.load_stock_btn.clicked.connect(self.file_handler.on_stock_select_clicked)

        # Main actions
        self.run_analysis_button.clicked.connect(self.actions_handler.run_analysis)
        self.settings_button.clicked.connect(self.actions_handler.open_settings_window)
        if hasattr(self, 'add_product_button'):
            self.add_product_button.clicked.connect(self.actions_handler.show_add_product_dialog)

        # Reports
        self.packing_list_button.clicked.connect(
            lambda: self.actions_handler.open_report_selection_dialog("packing_lists")
        )
        self.stock_export_button.clicked.connect(
            lambda: self.actions_handler.open_report_selection_dialog("stock_exports")
        )

        # Open session folder button (NEW)
        self.open_folder_button.clicked.connect(self.ui_manager.open_session_folder)

        # Tab 2 action buttons (duplicates for convenience)
        if hasattr(self, 'packing_list_button_tab2'):
            self.packing_list_button_tab2.clicked.connect(
                lambda: self.actions_handler.open_report_selection_dialog("packing_lists")
            )
        if hasattr(self, 'stock_export_button_tab2'):
            self.stock_export_button_tab2.clicked.connect(
                lambda: self.actions_handler.open_report_selection_dialog("stock_exports")
            )
        if hasattr(self, 'open_folder_button_tab2'):
            self.open_folder_button_tab2.clicked.connect(self.ui_manager.open_session_folder)

        # Table interactions (Phase 3)
        if hasattr(self, 'tableView'):
            self.tableView.customContextMenuRequested.connect(self.show_context_menu)
            self.tableView.doubleClicked.connect(self.on_table_double_clicked)

        # Custom signals
        self.actions_handler.data_changed.connect(self._update_all_views)

        # Filter input (Phase 3)
        if hasattr(self, 'filter_input'):
            self.filter_input.textChanged.connect(self.filter_table)
            self.filter_column_selector.currentIndexChanged.connect(self.filter_table)
            self.case_sensitive_checkbox.stateChanged.connect(self.filter_table)
            self.clear_filter_button.clicked.connect(self.clear_filter)

    def clear_filter(self):
        """Clears the filter input text box."""
        self.filter_input.clear()

    # --- Client and Session Management (New Architecture) ---
    def on_client_changed(self, client_id: str):
        """Handle client selection change.

        Args:
            client_id: Newly selected client ID
        """
        logging.info(f"Client changed to: {client_id}")

        # Store current client ID
        self.current_client_id = client_id

        # Load configuration for this client
        try:
            self.current_client_config = self.profile_manager.load_shopify_config(client_id)
            if not self.current_client_config:
                QMessageBox.warning(
                    self,
                    "Configuration Error",
                    f"Failed to load configuration for client {client_id}"
                )
                return

            # Also load it via the existing method for backward compatibility
            self.load_client_config(client_id)

            # Clear currently loaded files (they're for different client)
            self.orders_file_path = None
            self.stock_file_path = None
            self.orders_file_path_label.setText("No file loaded")
            self.stock_file_path_label.setText("No file loaded")
            self.orders_file_status_label.setText("")
            self.stock_file_status_label.setText("")

            # Disable Run Analysis button until files are loaded
            self.run_analysis_button.setEnabled(False)

            # Update session browser to show this client's sessions
            self.session_browser.set_client(client_id)

            logging.info(f"Client {client_id} loaded successfully")

        except Exception as e:
            logging.error(f"Error changing client: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to change client: {str(e)}"
            )

    def on_session_selected(self, session_path: str):
        """Handle session selection from session browser.

        Args:
            session_path: Path to the selected session
        """
        logging.info(f"Session selected: {session_path}")

        reply = QMessageBox.question(
            self,
            "Open Session",
            f"Do you want to open this session?\n\n{session_path}\n\n"
            f"This will load any existing analysis data from the session.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.load_existing_session(session_path)

    def _load_session_analysis(self, session_path):
        """Load analysis data from session directory.

        Args:
            session_path: Path to session directory (can be str or Path)

        Returns:
            True if loaded successfully, False otherwise
        """
        from pathlib import Path

        try:
            session_path = Path(session_path)

            # Check for analysis_data.json first
            analysis_data_file = session_path / "analysis" / "analysis_data.json"

            if not analysis_data_file.exists():
                logging.warning(f"Analysis data not found: {analysis_data_file}")
                return False

            logging.info(f"Found analysis data: {analysis_data_file}")

            # Load the actual Excel report to get DataFrame
            report_file = session_path / "analysis" / "fulfillment_analysis.xlsx"

            if not report_file.exists():
                # Try alternative name
                report_file = session_path / "analysis" / "analysis_report.xlsx"

            if not report_file.exists():
                logging.warning(f"Analysis report not found: {report_file}")
                return False

            logging.info(f"Loading analysis from: {report_file}")

            # Load DataFrame from Excel
            self.analysis_results_df = pd.read_excel(report_file)

            # Recalculate statistics
            self.analysis_stats = recalculate_statistics(self.analysis_results_df)

            logging.info(f"Loaded {len(self.analysis_results_df)} rows from session")
            return True

        except Exception as e:
            logging.error(f"Failed to load session analysis: {e}", exc_info=True)
            return False

    def load_existing_session(self, session_path: str):
        """Load data from an existing session.

        Args:
            session_path: Path to the session directory
        """
        from pathlib import Path

        try:
            # Set as current session
            self.session_path = session_path
            session_name = os.path.basename(session_path)

            # Update session labels (FIX #1)
            if hasattr(self, 'session_path_label'):
                self.session_path_label.setText(f"Session: {session_name}")

            # Update global header session info (FIX #1)
            if hasattr(self.ui_manager, 'update_session_info_label'):
                self.ui_manager.update_session_info_label()

            # Load session info
            session_info = self.session_manager.get_session_info(session_path)

            if session_info:
                # Try to load analysis data if it exists
                if self._load_session_analysis(session_path):
                    # Analysis loaded successfully
                    self._update_all_views()

                    # Enable report buttons (handled by set_ui_busy now)
                    if hasattr(self, 'packing_list_button'):
                        self.packing_list_button.setEnabled(True)
                    if hasattr(self, 'stock_export_button'):
                        self.stock_export_button.setEnabled(True)
                    if hasattr(self, 'add_product_button'):
                        self.add_product_button.setEnabled(True)

                    # Update Tab 2 buttons too (FIX #3)
                    self.ui_manager.set_ui_busy(False)

                    self.log_activity("Session", f"Loaded session: {session_name}")
                    QMessageBox.information(
                        self,
                        "Session Loaded",
                        f"Session loaded successfully:\n{session_name}\n\n"
                        f"Analysis data: {len(self.analysis_results_df)} rows"
                    )
                else:
                    # Session exists but no analysis yet
                    # Update UI state for Open Folder button (FIX #2)
                    self.ui_manager.set_ui_busy(False)

                    self.log_activity("Session", f"Opened session (no analysis): {session_name}")
                    QMessageBox.information(
                        self,
                        "Session Opened",
                        f"Session opened:\n{session_name}\n\n"
                        f"No analysis data found. You can run a new analysis."
                    )

                # Enable file loading buttons
                self.load_orders_btn.setEnabled(True)
                self.load_stock_btn.setEnabled(True)

        except Exception as e:
            logging.error(f"Failed to load session: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load session:\n{str(e)}"
            )

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
        # Update statistics ONLY if analysis results exist
        if self.analysis_results_df is not None and not self.analysis_results_df.empty:
            try:
                self.analysis_stats = recalculate_statistics(self.analysis_results_df)
                self.ui_manager.update_results_table(self.analysis_results_df)
                self.update_statistics_tab()

                # Update summary bar (NEW - Phase 3)
                if hasattr(self.ui_manager, 'update_summary_bar'):
                    self.ui_manager.update_summary_bar()
            except Exception as e:
                logging.error(f"Failed to recalculate statistics: {e}", exc_info=True)
                self.analysis_stats = None
                self._clear_statistics_view()
        else:
            # No analysis results - clear statistics
            self.analysis_stats = None
            self._clear_statistics_view()
            self.ui_manager.update_results_table(pd.DataFrame())

        # Populate filter dropdown
        if hasattr(self, 'filter_column_selector'):
            self.filter_column_selector.clear()
            self.filter_column_selector.addItem("All Columns")
            if self.analysis_results_df is not None and not self.analysis_results_df.empty:
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

    def _clear_statistics_view(self):
        """Clear statistics display when no analysis results."""
        # Clear main stats labels
        if hasattr(self, 'stats_labels'):
            for label in self.stats_labels.values():
                label.setText("N/A")

        # Clear courier stats layout
        if hasattr(self, 'courier_stats_layout'):
            while self.courier_stats_layout.count():
                child = self.courier_stats_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            # Add placeholder text
            placeholder = QLabel("No analysis data available.")
            placeholder.setStyleSheet("color: gray; font-style: italic;")
            self.courier_stats_layout.addWidget(placeholder, 0, 0)

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
        if self.analysis_results_df is None or self.analysis_results_df.empty:
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
        # Session data is now managed by SessionManager on the server
        # No need to save local session files
        event.accept()


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
