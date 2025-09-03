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
from gui.column_manager_window_pyside import ColumnManagerWindow


class MainWindow(QMainWindow):
    """The main window of the Shopify Fulfillment Tool."""

    def __init__(self):
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
        """Initializes and loads the application configuration from a JSON file."""
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
        """Sets up the Qt-based logger."""
        self.log_handler = QtLogHandler()
        self.log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)
        self.log_handler.log_message_received.connect(self.execution_log_edit.appendPlainText)

    def connect_signals(self):
        """Connects all widget signals to their corresponding slots."""
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
        self.column_manager_button.clicked.connect(self.open_column_manager)
        self.frozen_table.customContextMenuRequested.connect(self.show_context_menu)
        self.main_table.customContextMenuRequested.connect(self.show_context_menu)
        self.frozen_table.doubleClicked.connect(self.on_table_double_clicked)
        self.main_table.doubleClicked.connect(self.on_table_double_clicked)

        # Scroll synchronization
        self.main_table.verticalScrollBar().valueChanged.connect(self.frozen_table.verticalScrollBar().setValue)
        self.frozen_table.verticalScrollBar().valueChanged.connect(self.main_table.verticalScrollBar().setValue)

        # Custom signals
        self.actions_handler.data_changed.connect(self._update_all_views)

        # Filter input
        self.filter_input.textChanged.connect(self.filter_table)

    def filter_table(self, text):
        """Filters the table based on the input text."""
        self.proxy_model.setFilterRegularExpression(text)

    def _update_all_views(self):
        """Central slot to refresh all UI components after data changes."""
        self.analysis_stats = recalculate_statistics(self.analysis_results_df)
        self.ui_manager.update_results_table(self.analysis_results_df)
        self.update_statistics_tab()
        self.ui_manager.set_ui_busy(False)
        # The column manager button is enabled within update_results_table

    def update_statistics_tab(self):
        """Populates the Statistics tab with the latest analysis data."""
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
        """Adds a new entry to the Activity Log table."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.activity_log_table.insertRow(0)
        self.activity_log_table.setItem(0, 0, QTableWidgetItem(current_time))
        self.activity_log_table.setItem(0, 1, QTableWidgetItem(op_type))
        self.activity_log_table.setItem(0, 2, QTableWidgetItem(desc))

    def open_column_manager(self):
        """Opens the column manager dialog."""
        if self.analysis_results_df.empty:
            QMessageBox.warning(self, "No Data", "Please run an analysis to load data first.")
            return
        dialog = ColumnManagerWindow(self.all_columns, self.visible_columns, self)
        dialog.columns_updated.connect(self.update_table_columns)
        dialog.exec()

    def update_table_columns(self, visible_columns):
        """Slot to update visible columns and refresh the table view."""
        self.visible_columns = visible_columns
        self.ui_manager.update_results_table(self.analysis_results_df)
        logging.info("Column visibility updated.")

    def on_table_double_clicked(self, index: QModelIndex):
        """Handles double-click events on the tables."""
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
        """Shows a context menu for table view items."""
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

    def sync_selection_from_main(self, selected, deselected):
        """Synchronizes selection from the main table to the frozen table."""
        if self.is_syncing_selection:
            return
        self.is_syncing_selection = True
        self.frozen_table.selectionModel().select(selected, self.main_table.selectionModel().Select)
        self.frozen_table.selectionModel().select(deselected, self.main_table.selectionModel().Deselect)
        self.is_syncing_selection = False

    def sync_selection_from_frozen(self, selected, deselected):
        """Synchronizes selection from the frozen table to the main table."""
        if self.is_syncing_selection:
            return
        self.is_syncing_selection = True
        self.main_table.selectionModel().select(selected, self.frozen_table.selectionModel().Select)
        self.main_table.selectionModel().select(deselected, self.frozen_table.selectionModel().Deselect)
        self.is_syncing_selection = False

    def closeEvent(self, event):
        """Saves the session data on application close."""
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
        """Loads a previous session if available."""
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
