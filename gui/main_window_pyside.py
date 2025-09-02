import sys
import os
import json
import shutil
import pickle
import logging
from datetime import datetime
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPushButton, QLabel, QTabWidget, QFrame, QGroupBox,
    QFileDialog, QMessageBox, QTableView, QTableWidget, QTableWidgetItem,
    QMenu, QInputDialog, QHeaderView, QPlainTextEdit
)
from PySide6.QtCore import Qt, QPoint, QThreadPool, QModelIndex
from PySide6.QtGui import QAction, QTextCursor

# It's better to add the project root to the path to ensure all modules are found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shopify_tool import core
from shopify_tool.utils import get_persistent_data_path, resource_path
from shopify_tool.analysis import recalculate_statistics, toggle_order_fulfillment
from gui.pandas_model import PandasModel
from gui.settings_window_pyside import SettingsWindow
from gui.report_selection_dialog import ReportSelectionDialog
from gui.column_manager_window_pyside import ColumnManagerWindow
from gui.report_builder_window_pyside import ReportBuilderWindow
from gui.worker import Worker
from gui.log_handler import QtLogHandler

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Shopify Fulfillment Tool (PySide6)")
        self.setGeometry(100, 100, 950, 800)

        self.session_path = None
        self.config = None
        self.config_path = None
        self.orders_file_path = None
        self.stock_file_path = None
        self.analysis_results_df = pd.DataFrame()
        self.analysis_stats = None
        self.threadpool = QThreadPool()

        self.all_columns = []
        self.visible_columns = []
        self.is_syncing_selection = False

        self._init_and_load_config()

        self.session_file = get_persistent_data_path('session_data.pkl')

        self.create_widgets()
        self.connect_signals()
        self.setup_logging()

        self.load_session()


    def _init_and_load_config(self):
        persistent_config_path = get_persistent_data_path('config.json')
        default_config_path = resource_path('config.json')
        if not os.path.exists(persistent_config_path):
            try:
                shutil.copy(default_config_path, persistent_config_path)
            except Exception as e:
                QMessageBox.critical(self, "Fatal Error", f"Could not create user configuration file: {e}")
                QApplication.quit()
                return
        self.config_path = persistent_config_path
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Configuration Error", f"Failed to load config.json: {e}")
            QApplication.quit()

    def create_widgets(self):
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        session_group = QGroupBox("Session"); session_layout = QHBoxLayout(); session_group.setLayout(session_layout)
        self.new_session_btn = QPushButton("Create New Session"); self.new_session_btn.setToolTip("Creates a new unique, dated folder for all generated reports.")
        self.session_path_label = QLabel("No session started.")
        session_layout.addWidget(self.new_session_btn); session_layout.addWidget(self.session_path_label); session_layout.addStretch()
        main_layout.addWidget(session_group)
        files_group = QGroupBox("Load Data"); files_layout = QGridLayout(); files_group.setLayout(files_layout)
        self.load_orders_btn = QPushButton("Load Orders File (.csv)"); self.load_orders_btn.setToolTip("Select the orders_export.csv file from Shopify.")
        self.orders_file_path_label = QLabel("Orders file not selected"); self.orders_file_status_label = QLabel(""); self.load_orders_btn.setEnabled(False)
        self.load_stock_btn = QPushButton("Load Stock File (.csv)"); self.load_stock_btn.setToolTip("Select the inventory/stock CSV file.")
        self.stock_file_path_label = QLabel("Stock file not selected"); self.stock_file_status_label = QLabel(""); self.load_stock_btn.setEnabled(False)
        files_layout.addWidget(self.load_orders_btn, 0, 0); files_layout.addWidget(self.orders_file_path_label, 0, 1); files_layout.addWidget(self.orders_file_status_label, 0, 2)
        files_layout.addWidget(self.load_stock_btn, 1, 0); files_layout.addWidget(self.stock_file_path_label, 1, 1); files_layout.addWidget(self.stock_file_status_label, 1, 2)
        files_layout.setColumnStretch(1, 1); main_layout.addWidget(files_group)
        actions_layout = QHBoxLayout()
        reports_group = QGroupBox("Reports"); reports_v_layout = QVBoxLayout(); reports_group.setLayout(reports_v_layout)
        self.packing_list_button = QPushButton("Create Packing List"); self.packing_list_button.setToolTip("Generate packing lists based on pre-defined filters.")
        self.stock_export_button = QPushButton("Create Stock Export"); self.stock_export_button.setToolTip("Generate stock export files for couriers.")
        self.report_builder_button = QPushButton("Report Builder"); self.report_builder_button.setToolTip("Create a custom report with your own filters and columns.")
        self.packing_list_button.setEnabled(False); self.stock_export_button.setEnabled(False); self.report_builder_button.setEnabled(False)
        reports_v_layout.addWidget(self.packing_list_button); reports_v_layout.addWidget(self.stock_export_button); reports_v_layout.addWidget(self.report_builder_button); reports_v_layout.addStretch()
        main_actions_group = QGroupBox("Actions"); main_actions_grid_layout = QGridLayout(); main_actions_group.setLayout(main_actions_grid_layout)
        self.run_analysis_button = QPushButton("Run Analysis"); self.run_analysis_button.setMinimumHeight(60); self.run_analysis_button.setEnabled(False)
        self.run_analysis_button.setToolTip("Start the fulfillment analysis based on the loaded files.")
        self.settings_button = QPushButton("⚙️"); self.settings_button.setFixedSize(40, 40); self.settings_button.setToolTip("Open the application settings window.")
        main_actions_grid_layout.addWidget(self.run_analysis_button, 0, 0, 1, 2); main_actions_grid_layout.addWidget(self.settings_button, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        main_actions_grid_layout.setRowStretch(0, 1); main_actions_grid_layout.setColumnStretch(0, 1)
        actions_layout.addWidget(reports_group, 1); actions_layout.addWidget(main_actions_group, 3); main_layout.addLayout(actions_layout)
        self.tab_view = QTabWidget()

        self.execution_log_edit = QPlainTextEdit(); self.execution_log_edit.setReadOnly(True)
        self.tab_view.addTab(self.execution_log_edit, "Execution Log")

        self.activity_log_tab = QWidget(); activity_layout = QVBoxLayout(self.activity_log_tab)
        self.activity_log_table = QTableWidget(); self.activity_log_table.setColumnCount(3)
        self.activity_log_table.setHorizontalHeaderLabels(["Time", "Operation", "Description"]); self.activity_log_table.horizontalHeader().setStretchLastSection(True)
        activity_layout.addWidget(self.activity_log_table); self.tab_view.addTab(self.activity_log_tab, "Activity Log")

        self.data_view_tab = QWidget(); self.data_view_layout = QVBoxLayout(self.data_view_tab)
        top_bar_layout = QHBoxLayout(); self.column_manager_button = QPushButton("Manage Columns"); self.column_manager_button.setEnabled(False)
        top_bar_layout.addWidget(self.column_manager_button); top_bar_layout.addStretch(); self.data_view_layout.addLayout(top_bar_layout)

        table_layout = QHBoxLayout()
        self.frozen_table = QTableView(); self.frozen_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.main_table = QTableView(); self.main_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.frozen_table.setFixedWidth(120); self.frozen_table.horizontalHeader().setStretchLastSection(True)
        self.frozen_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table_layout.addWidget(self.frozen_table); table_layout.addWidget(self.main_table)
        self.data_view_layout.addLayout(table_layout)
        self.tab_view.addTab(self.data_view_tab, "Analysis Data")

        self.stats_tab = QWidget(); self.create_statistics_tab(); self.tab_view.addTab(self.stats_tab, "Statistics")
        main_layout.addWidget(self.tab_view); main_layout.setStretchFactor(self.tab_view, 1)

    def setup_logging(self):
        self.log_handler = QtLogHandler()
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)
        self.log_handler.log_message_received.connect(self.execution_log_edit.appendPlainText)

    def create_statistics_tab(self):
        layout = QGridLayout(self.stats_tab); layout.setAlignment(Qt.AlignmentFlag.AlignTop); self.stats_labels = {}
        stat_keys = {"total_orders_completed": "Total Orders Completed:", "total_orders_not_completed": "Total Orders Not Completed:", "total_items_to_write_off": "Total Items to Write Off:", "total_items_not_to_write_off": "Total Items Not to Write Off:"}
        row_counter = 0
        for key, text in stat_keys.items():
            label = QLabel(text); value_label = QLabel("-"); self.stats_labels[key] = value_label
            layout.addWidget(label, row_counter, 0); layout.addWidget(value_label, row_counter, 1); row_counter += 1
        courier_header = QLabel("Couriers Stats:"); courier_header.setStyleSheet("font-weight: bold; margin-top: 15px;")
        layout.addWidget(courier_header, row_counter, 0, 1, 2); row_counter += 1
        self.courier_stats_layout = QGridLayout(); layout.addLayout(self.courier_stats_layout, row_counter, 0, 1, 2)

    def update_statistics_tab(self):
        if not self.analysis_stats: return
        for key, label in self.stats_labels.items(): label.setText(str(self.analysis_stats.get(key, "N/A")))
        while self.courier_stats_layout.count():
            child = self.courier_stats_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        courier_stats = self.analysis_stats.get('couriers_stats')
        if courier_stats:
            headers = ["Courier ID", "Orders Assigned", "Repeated Orders"]
            for i, header_text in enumerate(headers):
                header_label = QLabel(header_text); header_label.setStyleSheet("font-weight: bold;")
                self.courier_stats_layout.addWidget(header_label, 0, i)
            for i, stats in enumerate(courier_stats, start=1):
                self.courier_stats_layout.addWidget(QLabel(stats.get('courier_id', 'N/A')), i, 0)
                self.courier_stats_layout.addWidget(QLabel(str(stats.get('orders_assigned', 'N/A'))), i, 1)
                self.courier_stats_layout.addWidget(QLabel(str(stats.get('repeated_orders_found', 'N/A'))), i, 2)
        else:
            self.courier_stats_layout.addWidget(QLabel("No courier stats available."), 0, 0)

    def log_activity(self, op_type, desc):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.activity_log_table.insertRow(0)
        self.activity_log_table.setItem(0, 0, QTableWidgetItem(current_time))
        self.activity_log_table.setItem(0, 1, QTableWidgetItem(op_type))
        self.activity_log_table.setItem(0, 2, QTableWidgetItem(desc))

    def connect_signals(self):
        self.new_session_btn.clicked.connect(self.create_new_session)
        self.load_orders_btn.clicked.connect(self.select_orders_file)
        self.load_stock_btn.clicked.connect(self.select_stock_file)
        self.run_analysis_button.clicked.connect(self.run_analysis)
        self.settings_button.clicked.connect(self.open_settings_window)
        self.report_builder_button.clicked.connect(self.open_report_builder_window)
        self.frozen_table.customContextMenuRequested.connect(self.show_context_menu)
        self.main_table.customContextMenuRequested.connect(self.show_context_menu)
        self.frozen_table.doubleClicked.connect(self.on_table_double_clicked)
        self.main_table.doubleClicked.connect(self.on_table_double_clicked)
        self.packing_list_button.clicked.connect(lambda: self.open_report_selection_dialog('packing_lists'))
        self.stock_export_button.clicked.connect(lambda: self.open_report_selection_dialog('stock_exports'))
        self.column_manager_button.clicked.connect(self.open_column_manager)
        self.main_table.verticalScrollBar().valueChanged.connect(self.frozen_table.verticalScrollBar().setValue)
        self.frozen_table.verticalScrollBar().valueChanged.connect(self.main_table.verticalScrollBar().setValue)

    def sync_selection_from_main(self, selected, deselected):
        if self.is_syncing_selection: return
        self.is_syncing_selection = True
        self.frozen_table.selectionModel().select(selected, self.main_table.selectionModel().Select)
        self.frozen_table.selectionModel().select(deselected, self.main_table.selectionModel().Deselect)
        self.is_syncing_selection = False

    def sync_selection_from_frozen(self, selected, deselected):
        if self.is_syncing_selection: return
        self.is_syncing_selection = True
        self.main_table.selectionModel().select(selected, self.frozen_table.selectionModel().Select)
        self.main_table.selectionModel().select(deselected, self.frozen_table.selectionModel().Deselect)
        self.is_syncing_selection = False

    def open_column_manager(self):
        logging.info("Attempting to open Column Manager window...")
        if not self.all_columns:
            QMessageBox.warning(self, "No Data", "Please run an analysis to load data first.")
            return
        dialog = ColumnManagerWindow(self.all_columns, self.visible_columns, self)

        # Move dialog to the center of the parent window
        parent_geometry = self.geometry()
        dialog_geometry = dialog.frameGeometry()
        center_point = parent_geometry.center()
        dialog_geometry.moveCenter(center_point)
        dialog.move(dialog_geometry.topLeft())

        if dialog.exec():
            self.visible_columns = dialog.new_visible_columns
            self.update_data_viewer()
            logging.info("Column settings applied.")

    def open_report_builder_window(self):
        if self.analysis_results_df.empty:
            QMessageBox.warning(self, "No Data", "Please run an analysis before using the Report Builder.")
            return
        dialog = ReportBuilderWindow(self.analysis_results_df, self)
        parent_geometry = self.geometry()
        dialog_geometry = dialog.frameGeometry()
        center_point = parent_geometry.center()
        dialog_geometry.moveCenter(center_point)
        dialog.move(dialog_geometry.topLeft())
        dialog.exec()

    def open_report_selection_dialog(self, report_type):
        reports_config = self.config.get(report_type, [])
        if not reports_config:
            QMessageBox.information(self, "No Reports", f"No {report_type.replace('_', ' ')} configured in settings.")
            return
        dialog = ReportSelectionDialog(report_type, reports_config, self)
        dialog.reportSelected.connect(lambda rc: self.run_report_logic(report_type, rc))

        parent_geometry = self.geometry()
        dialog_geometry = dialog.frameGeometry()
        center_point = parent_geometry.center()
        dialog_geometry.moveCenter(center_point)
        dialog.move(dialog_geometry.topLeft())

        dialog.exec()

    def run_report_logic(self, report_type, report_config):
        if not self.session_path:
            QMessageBox.critical(self, "Session Error", "Please create a new session before generating reports."); return
        self.log_activity("Report", f"Generating report: {report_config.get('name')}")
        if report_type == "packing_lists":
            relative_path = report_config.get('output_filename', 'default_packing_list.xlsx'); output_file = os.path.join(self.session_path, os.path.basename(relative_path))
            report_config_copy = report_config.copy(); report_config_copy['output_filename'] = output_file
            worker = Worker(core.create_packing_list_report, analysis_df=self.analysis_results_df, report_config=report_config_copy)
        elif report_type == "stock_exports":
            templates_path = resource_path(self.config['paths']['templates'])
            worker = Worker(core.create_stock_export_report, analysis_df=self.analysis_results_df, report_config=report_config, templates_path=templates_path, output_path=self.session_path)
        else:
            QMessageBox.critical(self, "Error", "Unknown report type."); return
        worker.signals.result.connect(self.on_report_generation_complete); worker.signals.error.connect(self.on_task_error); self.threadpool.start(worker)

    def on_report_generation_complete(self, result):
        success, message = result
        if success: self.log_activity("Report Generation", message)
        else: QMessageBox.critical(self, "Error", message)

    def show_context_menu(self, pos: QPoint):
        if self.analysis_results_df.empty: return
        table = self.sender()
        index = table.indexAt(pos)
        if index.isValid():
            row = index.row(); order_number = self.analysis_results_df.iloc[row]['Order_Number']
            sku = self.analysis_results_df.iloc[row]['SKU']
            menu = QMenu(); change_status_action = QAction("Change Status", self); add_tag_action = QAction("Add Tag Manually...", self)
            remove_item_action = QAction(f"Remove Item {sku} from Order", self); remove_order_action = QAction(f"Remove Entire Order {order_number}", self)
            copy_order_action = QAction(f"Copy Order Number: {order_number}", self); copy_sku_action = QAction(f"Copy SKU: {sku}", self)
            change_status_action.triggered.connect(lambda: self.toggle_fulfillment_status_for_order(order_number)); add_tag_action.triggered.connect(lambda: self.add_tag_manually(order_number))
            remove_item_action.triggered.connect(lambda: self.remove_item_from_order(row)); remove_order_action.triggered.connect(lambda: self.remove_entire_order(order_number))
            copy_order_action.triggered.connect(lambda: self.copy_to_clipboard(order_number)); copy_sku_action.triggered.connect(lambda: self.copy_to_clipboard(sku))
            menu.addAction(change_status_action); menu.addAction(add_tag_action); menu.addSeparator(); menu.addAction(remove_item_action)
            menu.addAction(remove_order_action); menu.addSeparator(); menu.addAction(copy_order_action); menu.addAction(copy_sku_action)
            menu.exec(table.viewport().mapToGlobal(pos))

    def on_table_double_clicked(self, index: QModelIndex):
        if index.isValid():
            row = index.row(); order_number = self.analysis_results_df.iloc[row]['Order_Number']
            self.toggle_fulfillment_status_for_order(order_number)

    def add_tag_manually(self, order_number):
        tag_to_add, ok = QInputDialog.getText(self, "Add Manual Tag", "Enter tag to add:")
        if ok and tag_to_add:
            order_rows_indices = self.analysis_results_df[self.analysis_results_df['Order_Number'] == order_number].index
            if 'Status_Note' not in self.analysis_results_df.columns: self.analysis_results_df['Status_Note'] = ''
            for index in order_rows_indices:
                current_notes = self.analysis_results_df.loc[index, 'Status_Note']
                if pd.isna(current_notes) or current_notes == '': new_notes = tag_to_add
                elif tag_to_add not in current_notes.split(','): new_notes = f"{current_notes}, {tag_to_add}"
                else: new_notes = current_notes
                self.analysis_results_df.loc[index, 'Status_Note'] = new_notes
            self._post_analysis_ui_update(); self.log_activity("Manual Tag", f"Added note '{tag_to_add}' to order {order_number}.")

    def remove_item_from_order(self, row_index):
        order_number = self.analysis_results_df.iloc[row_index]['Order_Number']; sku = self.analysis_results_df.iloc[row_index]['SKU']
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to remove item {sku} from order {order_number}?\nThis cannot be undone.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.analysis_results_df.drop(self.analysis_results_df.index[row_index], inplace=True); self.analysis_results_df.reset_index(drop=True, inplace=True)
            self.analysis_stats = recalculate_statistics(self.analysis_results_df); self._post_analysis_ui_update()
            self.log_activity("Data Edit", f"Removed item {sku} from order {order_number}.")

    def remove_entire_order(self, order_number):
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to remove the entire order {order_number}?\nThis cannot be undone.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.analysis_results_df = self.analysis_results_df[self.analysis_results_df['Order_Number'] != order_number].reset_index(drop=True)
            self.analysis_stats = recalculate_statistics(self.analysis_results_df); self._post_analysis_ui_update()
            self.log_activity("Data Edit", f"Removed order {order_number}.")

    def copy_to_clipboard(self, text):
        QApplication.clipboard().setText(str(text)); self.log_activity("Clipboard", f"Copied '{text}' to clipboard.")

    def toggle_fulfillment_status_for_order(self, order_number):
        success, result, updated_df = toggle_order_fulfillment(self.analysis_results_df, order_number)
        if success:
            self.analysis_results_df = updated_df; self.analysis_stats = recalculate_statistics(self.analysis_results_df); self._post_analysis_ui_update()
            new_status = self.analysis_results_df.loc[self.analysis_results_df['Order_Number'] == order_number, 'Order_Fulfillment_Status'].iloc[0]
            self.log_activity("Manual Edit", f"Order {order_number} status changed to '{new_status}'.")
        else:
            QMessageBox.critical(self, "Error", result)

    def open_settings_window(self):
        dialog = SettingsWindow(self, self.config)
        if dialog.exec():
            self.config = dialog.config_data
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f: json.dump(self.config, f, indent=2, ensure_ascii=False)
                self.log_activity("Settings", "Settings saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to write settings to file: {e}")

    def create_new_session(self):
        try:
            base_output_dir = self.config['paths'].get('output_dir_stock', 'data/output'); os.makedirs(base_output_dir, exist_ok=True)
            date_str = datetime.now().strftime('%Y-%m-%d'); session_id = 1
            while True:
                session_path = os.path.join(base_output_dir, f"{date_str}_session_{session_id}")
                if not os.path.exists(session_path): break
                session_id += 1
            os.makedirs(session_path, exist_ok=True); self.session_path = session_path
            self.session_path_label.setText(f"Current Session: {os.path.basename(self.session_path)}")
            self.load_orders_btn.setEnabled(True); self.load_stock_btn.setEnabled(True); self.log_activity("Session", f"New session started. Output: {self.session_path}")
        except Exception as e:
            QMessageBox.critical(self, "Session Error", f"Could not create a new session folder.\nError: {e}")

    def select_orders_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Orders File", "", "CSV files (*.csv)");
        if filepath:
            self.orders_file_path = filepath; self.orders_file_path_label.setText(os.path.basename(filepath))
            self.validate_file('orders'); self.check_files_ready()

    def select_stock_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Stock File", "", "CSV files (*.csv)")
        if filepath:
            self.stock_file_path = filepath; self.stock_file_path_label.setText(os.path.basename(filepath))
            self.validate_file('stock'); self.check_files_ready()

    def validate_file(self, file_type):
        if file_type == 'orders':
            path = self.orders_file_path; label = self.orders_file_status_label; required_cols = self.config.get('column_mappings', {}).get('orders_required', []); delimiter = ','
        else:
            path = self.stock_file_path; label = self.stock_file_status_label; required_cols = self.config.get('column_mappings', {}).get('stock_required', []); delimiter = self.config.get('settings', {}).get('stock_csv_delimiter', ';')
        is_valid, missing_cols = core.validate_csv_headers(path, required_cols, delimiter)
        if is_valid:
            label.setText("✓"); label.setStyleSheet("color: green; font-weight: bold;")
        else:
            label.setText("✗"); label.setStyleSheet("color: red; font-weight: bold;"); label.setToolTip(f"Missing columns: {', '.join(missing_cols)}")

    def check_files_ready(self):
        orders_ok = self.orders_file_path and self.orders_file_status_label.text() == "✓"
        stock_ok = self.stock_file_path and self.stock_file_status_label.text() == "✓"
        if orders_ok and stock_ok: self.run_analysis_button.setEnabled(True)

    def _post_analysis_ui_update(self):
        self.update_data_viewer()
        self.update_statistics_tab()
        self.set_ui_busy(False)
        self.column_manager_button.setEnabled(True)
        self.tab_view.setCurrentWidget(self.stats_tab)

    def update_data_viewer(self):
        if self.analysis_results_df.empty: return
        if not self.all_columns:
            self.all_columns = [c for c in self.analysis_results_df.columns if c != 'Order_Number']
            self.visible_columns = self.all_columns[:]

        frozen_df = self.analysis_results_df[['Order_Number']]
        main_df_cols = [col for col in self.visible_columns if col in self.analysis_results_df.columns]
        main_df = self.analysis_results_df[main_df_cols]

        self.frozen_table.setModel(PandasModel(frozen_df))
        self.main_table.setModel(PandasModel(main_df))

        try:
            self.main_table.selectionModel().selectionChanged.disconnect()
            self.frozen_table.selectionModel().selectionChanged.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.main_table.selectionModel().selectionChanged.connect(self.sync_selection_from_main)
        self.frozen_table.selectionModel().selectionChanged.connect(self.sync_selection_from_frozen)

    def run_analysis(self):
        if not self.session_path:
            QMessageBox.critical(self, "Session Error", "Please create a new session before running an analysis."); return
        self.set_ui_busy(True)
        stock_delimiter = self.config['settings']['stock_csv_delimiter']
        worker = Worker(core.run_full_analysis, self.stock_file_path, self.orders_file_path, self.session_path, stock_delimiter, self.config)
        worker.signals.result.connect(self.on_analysis_complete); worker.signals.error.connect(self.on_task_error)
        worker.signals.finished.connect(lambda: self.set_ui_busy(False)); self.threadpool.start(worker)

    def on_analysis_complete(self, result):
        success, result_msg, df, stats = result
        if success:
            self.analysis_results_df = df; self.analysis_stats = stats; self._post_analysis_ui_update()
            self.log_activity("Analysis", f"Analysis complete. Report saved to: {result_msg}")
        else:
            QMessageBox.critical(self, "Analysis Error", f"An error occurred during analysis:\n{result_msg}")

    def on_task_error(self, error):
        exctype, value, tb = error
        QMessageBox.critical(self, "Task Exception", f"An unexpected error occurred in a background task:\n{value}\n\nTraceback:\n{tb}")

    def set_ui_busy(self, is_busy):
        self.run_analysis_button.setEnabled(not is_busy)
        is_data_loaded = not self.analysis_results_df.empty
        self.packing_list_button.setEnabled(not is_busy and is_data_loaded)
        self.stock_export_button.setEnabled(not is_busy and is_data_loaded)
        self.report_builder_button.setEnabled(not is_busy and is_data_loaded)

    def closeEvent(self, event):
        if self.analysis_results_df is not None and not self.analysis_results_df.empty:
            try:
                session_data = {'dataframe': self.analysis_results_df, 'visible_columns': self.visible_columns}
                with open(self.session_file, 'wb') as f: pickle.dump(session_data, f)
                self.log_activity("Session", "Session data saved on exit.")
            except Exception as e: print(f"Error saving session automatically: {e}")
        event.accept()

    def load_session(self):
        if os.path.exists(self.session_file):
            reply = QMessageBox.question(self, "Restore Session", "A previous session was found. Do you want to restore it?")
            if reply == QMessageBox.Yes:
                try:
                    with open(self.session_file, 'rb') as f: session_data = pickle.load(f)
                    self.analysis_results_df = session_data.get('dataframe', pd.DataFrame())
                    all_df_cols = [c for c in self.analysis_results_df.columns if c != 'Order_Number']
                    self.visible_columns = session_data.get('visible_columns', all_df_cols); self.all_columns = all_df_cols
                    self.analysis_stats = recalculate_statistics(self.analysis_results_df); self._post_analysis_ui_update()
                    self.log_activity("Session", "Restored previous session.")
                except Exception as e:
                    QMessageBox.critical(self, "Load Error", f"Failed to load session file: {e}")
            try:
                os.remove(self.session_file)
            except Exception as e:
                self.log_activity("Error", f"Failed to remove session file: {e}")


if __name__ == '__main__':
    if 'pytest' in sys.modules or os.environ.get("CI"): QApplication.setPlatform("offscreen")
    app = QApplication(sys.argv); window = MainWindow()
    if QApplication.platformName() != "offscreen":
        window.show(); sys.exit(app.exec())
    else:
        print("Running in offscreen mode for verification.")
