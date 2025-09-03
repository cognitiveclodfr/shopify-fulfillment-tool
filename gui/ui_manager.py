import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QTabWidget, QGroupBox, QTableView, QPlainTextEdit, QTableWidget, QLineEdit
)
from PySide6.QtCore import Qt
from .pandas_model import PandasModel


class UIManager:
    """Handles the creation and layout of all UI widgets for the main window."""

    def __init__(self, main_window):
        self.mw = main_window
        self.log = logging.getLogger(__name__)

    def create_widgets(self):
        """Create and layout all widgets in the main window."""
        self.log.info("Creating UI widgets.")
        central_widget = QWidget()
        self.mw.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        main_layout.addWidget(self._create_session_group())
        main_layout.addWidget(self._create_files_group())
        main_layout.addLayout(self._create_actions_layout())

        self.mw.tab_view = self._create_tab_view()
        main_layout.addWidget(self.mw.tab_view)
        main_layout.setStretchFactor(self.mw.tab_view, 1)
        self.log.info("UI widgets created successfully.")

    def _create_session_group(self):
        """Creates the 'Session' group box."""
        group = QGroupBox("Session")
        layout = QHBoxLayout()
        group.setLayout(layout)

        self.mw.new_session_btn = QPushButton("Create New Session")
        self.mw.new_session_btn.setToolTip("Creates a new unique, dated folder for all generated reports.")
        self.mw.session_path_label = QLabel("No session started.")

        layout.addWidget(self.mw.new_session_btn)
        layout.addWidget(self.mw.session_path_label)
        layout.addStretch()
        return group

    def _create_files_group(self):
        """Creates the 'Load Data' group box."""
        group = QGroupBox("Load Data")
        layout = QGridLayout()
        group.setLayout(layout)

        self.mw.load_orders_btn = QPushButton("Load Orders File (.csv)")
        self.mw.load_orders_btn.setToolTip("Select the orders_export.csv file from Shopify.")
        self.mw.orders_file_path_label = QLabel("Orders file not selected")
        self.mw.orders_file_status_label = QLabel("")
        self.mw.load_orders_btn.setEnabled(False)

        self.mw.load_stock_btn = QPushButton("Load Stock File (.csv)")
        self.mw.load_stock_btn.setToolTip("Select the inventory/stock CSV file.")
        self.mw.stock_file_path_label = QLabel("Stock file not selected")
        self.mw.stock_file_status_label = QLabel("")
        self.mw.load_stock_btn.setEnabled(False)

        layout.addWidget(self.mw.load_orders_btn, 0, 0)
        layout.addWidget(self.mw.orders_file_path_label, 0, 1)
        layout.addWidget(self.mw.orders_file_status_label, 0, 2)
        layout.addWidget(self.mw.load_stock_btn, 1, 0)
        layout.addWidget(self.mw.stock_file_path_label, 1, 1)
        layout.addWidget(self.mw.stock_file_status_label, 1, 2)
        layout.setColumnStretch(1, 1)
        return group

    def _create_actions_layout(self):
        """Creates the layout containing the 'Reports' and 'Actions' group boxes."""
        layout = QHBoxLayout()
        layout.addWidget(self._create_reports_group(), 1)
        layout.addWidget(self._create_main_actions_group(), 3)
        return layout

    def _create_reports_group(self):
        """Creates the 'Reports' group box."""
        group = QGroupBox("Reports")
        layout = QVBoxLayout()
        group.setLayout(layout)

        self.mw.packing_list_button = QPushButton("Create Packing List")
        self.mw.packing_list_button.setToolTip("Generate packing lists based on pre-defined filters.")
        self.mw.stock_export_button = QPushButton("Create Stock Export")
        self.mw.stock_export_button.setToolTip("Generate stock export files for couriers.")
        self.mw.report_builder_button = QPushButton("Report Builder")
        self.mw.report_builder_button.setToolTip("Create a custom report with your own filters and columns.")

        self.mw.packing_list_button.setEnabled(False)
        self.mw.stock_export_button.setEnabled(False)
        self.mw.report_builder_button.setEnabled(False)

        layout.addWidget(self.mw.packing_list_button)
        layout.addWidget(self.mw.stock_export_button)
        layout.addWidget(self.mw.report_builder_button)
        layout.addStretch()
        return group

    def _create_main_actions_group(self):
        """Creates the 'Actions' group box with the main run button."""
        group = QGroupBox("Actions")
        layout = QGridLayout()
        group.setLayout(layout)

        self.mw.run_analysis_button = QPushButton("Run Analysis")
        self.mw.run_analysis_button.setMinimumHeight(60)
        self.mw.run_analysis_button.setEnabled(False)
        self.mw.run_analysis_button.setToolTip("Start the fulfillment analysis based on the loaded files.")

        self.mw.settings_button = QPushButton("⚙️")
        self.mw.settings_button.setFixedSize(40, 40)
        self.mw.settings_button.setToolTip("Open the application settings window.")

        layout.addWidget(self.mw.run_analysis_button, 0, 0, 1, 2)
        layout.addWidget(self.mw.settings_button, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        layout.setRowStretch(0, 1)
        layout.setColumnStretch(0, 1)
        return group

    def _create_tab_view(self):
        """Creates the main tab widget for displaying data and logs."""
        tab_view = QTabWidget()
        self.mw.execution_log_edit = QPlainTextEdit()
        self.mw.execution_log_edit.setReadOnly(True)
        tab_view.addTab(self.mw.execution_log_edit, "Execution Log")

        self.mw.activity_log_tab = self._create_activity_log_tab()
        tab_view.addTab(self.mw.activity_log_tab, "Activity Log")

        self.mw.data_view_tab = self._create_data_view_tab()
        tab_view.addTab(self.mw.data_view_tab, "Analysis Data")

        self.mw.stats_tab = QWidget()
        self.create_statistics_tab(self.mw.stats_tab)
        tab_view.addTab(self.mw.stats_tab, "Statistics")

        return tab_view

    def _create_activity_log_tab(self):
        """Creates the 'Activity Log' tab with a table."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.mw.activity_log_table = QTableWidget()
        self.mw.activity_log_table.setColumnCount(3)
        self.mw.activity_log_table.setHorizontalHeaderLabels(["Time", "Operation", "Description"])
        self.mw.activity_log_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.mw.activity_log_table)
        return tab

    def _create_data_view_tab(self):
        """Creates the 'Analysis Data' tab with frozen and main tables."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        top_bar_layout = QHBoxLayout()
        self.mw.column_manager_button = QPushButton("Manage Columns")
        self.mw.column_manager_button.setEnabled(False)
        self.mw.filter_input = QLineEdit()
        self.mw.filter_input.setPlaceholderText("Filter table...")
        top_bar_layout.addWidget(self.mw.column_manager_button)
        top_bar_layout.addWidget(self.mw.filter_input)
        top_bar_layout.setStretchFactor(self.mw.filter_input, 1)
        layout.addLayout(top_bar_layout)

        table_layout = QHBoxLayout()
        self.mw.frozen_table = QTableView()
        self.mw.frozen_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mw.main_table = QTableView()
        self.mw.main_table.setSortingEnabled(True)
        self.mw.main_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mw.frozen_table.setFixedWidth(120)
        self.mw.frozen_table.horizontalHeader().setStretchLastSection(True)
        self.mw.frozen_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table_layout.addWidget(self.mw.frozen_table)
        table_layout.addWidget(self.mw.main_table)
        layout.addLayout(table_layout)
        return tab

    def create_statistics_tab(self, tab_widget):
        """Creates the UI elements for the Statistics tab."""
        layout = QGridLayout(tab_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.mw.stats_labels = {}
        stat_keys = {
            "total_orders_completed": "Total Orders Completed:",
            "total_orders_not_completed": "Total Orders Not Completed:",
            "total_items_to_write_off": "Total Items to Write Off:",
            "total_items_not_to_write_off": "Total Items Not to Write Off:",
        }
        row_counter = 0
        for key, text in stat_keys.items():
            label = QLabel(text)
            value_label = QLabel("-")
            self.mw.stats_labels[key] = value_label
            layout.addWidget(label, row_counter, 0)
            layout.addWidget(value_label, row_counter, 1)
            row_counter += 1

        courier_header = QLabel("Couriers Stats:")
        courier_header.setStyleSheet("font-weight: bold; margin-top: 15px;")
        layout.addWidget(courier_header, row_counter, 0, 1, 2)
        row_counter += 1
        self.mw.courier_stats_layout = QGridLayout()
        layout.addLayout(self.mw.courier_stats_layout, row_counter, 0, 1, 2)
        self.log.info("Statistics tab created.")

    def set_ui_busy(self, is_busy):
        """Enable or disable UI elements based on busy status."""
        self.mw.run_analysis_button.setEnabled(not is_busy)
        is_data_loaded = not self.mw.analysis_results_df.empty
        self.mw.packing_list_button.setEnabled(not is_busy and is_data_loaded)
        self.mw.stock_export_button.setEnabled(not is_busy and is_data_loaded)
        self.mw.report_builder_button.setEnabled(not is_busy and is_data_loaded)
        self.log.debug(f"UI busy state set to: {is_busy}")

    def update_results_table(self, data_df):
        """Updates the table views with new data."""
        self.log.info("Updating results table with new data.")
        if data_df.empty:
            self.log.warning("Received empty dataframe, clearing tables.")

        # Reset columns if this is the first data load
        if not self.mw.all_columns:
            self.mw.all_columns = [c for c in data_df.columns if c != "Order_Number"]
            self.mw.visible_columns = self.mw.all_columns[:]

        frozen_df = data_df[["Order_Number"]].copy()
        main_df_cols = [col for col in self.mw.visible_columns if col in data_df.columns]
        main_df = data_df[main_df_cols].copy()

        source_model = PandasModel(main_df)
        self.mw.proxy_model.setSourceModel(source_model)

        # The frozen table does not get sorted/filtered, so it uses the source model directly
        frozen_model = PandasModel(frozen_df)
        self.mw.frozen_table.setModel(frozen_model)
        self.mw.main_table.setModel(self.mw.proxy_model)

        # Re-connect selection synchronization after setting new models
        try:
            self.mw.main_table.selectionModel().selectionChanged.disconnect()
            self.mw.frozen_table.selectionModel().selectionChanged.disconnect()
        except (RuntimeError, TypeError):
            pass  # Ignore errors if signals were not connected
        self.mw.main_table.selectionModel().selectionChanged.connect(self.mw.sync_selection_from_main)
        self.mw.frozen_table.selectionModel().selectionChanged.connect(self.mw.sync_selection_from_frozen)

        self.mw.main_table.resizeColumnsToContents()
        self.mw.column_manager_button.setEnabled(True)
