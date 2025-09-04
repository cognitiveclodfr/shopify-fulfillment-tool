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

from shopify_tool.utils import get_persistent_data_path, resource_path
from shopify_tool.analysis import recalculate_statistics
from gui.log_handler import QtLogHandler
from gui.ui_manager import UIManager
from gui.file_handler import FileHandler
from gui.actions_handler import ActionsHandler


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
        self.setWindowTitle("Shopify Fulfillment Tool (PySide6 Refactored)")
        self.setGeometry(100, 100, 950, 800)

        # Core application attributes
        self.session_path = None
        self.config = None
        self.config_path = None
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

        self._init_and_load_config()
        self.session_file = get_persistent_data_path("session_data.pkl")

        # Setup UI and connect signals
        self.ui_manager.create_widgets()
        self.connect_signals()
        self.setup_logging()

        self.load_session()

    def _init_and_load_config(self):
        """Initializes and loads the application configuration.

        Ensures a 'config.json' exists in the user's persistent data
        directory. If it doesn't, a default config is copied from the
        application's resources. It then loads this configuration into
        `self.config`. If loading fails, it shows a critical error and
        quits the application.
        """
        self.config_path = get_persistent_data_path("config.json")
        default_config_path = resource_path("config.json")
        if not os.path.exists(self.config_path):
            try:
                shutil.copy(default_config_path, self.config_path)
            except Exception as e:
                QMessageBox.critical(self, "Fatal Error", f"Could not create user configuration file: {e}")
                QApplication.quit()
                return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Configuration Error", f"Failed to load config.json: {e}")
            QApplication.quit()

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
