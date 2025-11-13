import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QTabWidget, QGroupBox, QTableView, QPlainTextEdit, QTableWidget, QLineEdit,
    QComboBox, QCheckBox, QRadioButton, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from .pandas_model import PandasModel


class UIManager:
    """Handles the creation, layout, and state of all UI widgets.

    This class is responsible for building the graphical user interface of the
    main window. It creates all the widgets (buttons, labels, tables, etc.),
    arranges them in layouts and group boxes, and provides methods to update
    their state (e.g., enabling/disabling buttons, populating tables).

    It decouples the raw widget creation and layout logic from the main
    application logic in `MainWindow`.

    Attributes:
        mw (MainWindow): A reference to the main window instance.
        log (logging.Logger): A logger for this class.
    """

    def __init__(self, main_window):
        """Initializes the UIManager.

        Args:
            main_window (MainWindow): The main window instance that this
                manager will build the UI for.
        """
        self.mw = main_window
        self.log = logging.getLogger(__name__)

    def create_widgets(self):
        """Creates and lays out all widgets in the main window.

        This is the main entry point for building the UI. It constructs the
        entire widget hierarchy for the `MainWindow`.
        """
        self.log.info("Creating UI widgets.")
        central_widget = QWidget()
        self.mw.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Add client selector (new architecture)
        main_layout.addWidget(self._create_client_selector_group())

        # Add session browser and session management
        main_layout.addWidget(self._create_session_management_group())

        main_layout.addWidget(self._create_files_group())
        main_layout.addLayout(self._create_actions_layout())

        self.mw.tab_view = self._create_tab_view()
        main_layout.addWidget(self.mw.tab_view)
        main_layout.setStretchFactor(self.mw.tab_view, 1)
        self.log.info("UI widgets created successfully.")

    def _create_client_selector_group(self):
        """Creates the 'Client Selection' QGroupBox with ClientSelectorWidget."""
        from gui.client_selector_widget import ClientSelectorWidget

        group = QGroupBox("Client Selection")
        layout = QHBoxLayout()
        group.setLayout(layout)

        # Add client selector widget
        self.mw.client_selector = ClientSelectorWidget(
            self.mw.profile_manager,
            self.mw
        )
        layout.addWidget(self.mw.client_selector)
        layout.addStretch()

        return group

    def _create_session_management_group(self):
        """Creates the 'Session Management' QGroupBox."""
        from gui.session_browser_widget import SessionBrowserWidget

        group = QGroupBox("Session Management")
        layout = QVBoxLayout()
        group.setLayout(layout)

        # Create new session row
        session_row = QHBoxLayout()
        self.mw.new_session_btn = QPushButton("Create New Session")
        self.mw.new_session_btn.setToolTip("Creates a new session for the current client.")
        self.mw.new_session_btn.setEnabled(False)  # Enabled when client is selected
        self.mw.session_path_label = QLabel("No client/session selected.")

        session_row.addWidget(self.mw.new_session_btn)
        session_row.addWidget(self.mw.session_path_label, 1)

        layout.addLayout(session_row)

        # Add session browser
        self.mw.session_browser = SessionBrowserWidget(
            self.mw.session_manager,
            self.mw
        )
        layout.addWidget(self.mw.session_browser)

        return group

    def _create_files_group(self):
        """Creates the 'Load Data' QGroupBox with folder support."""
        group = QGroupBox("Load Data")
        layout = QHBoxLayout()
        group.setLayout(layout)

        # Orders section
        layout.addWidget(self._create_orders_file_section())

        # Stock section
        layout.addWidget(self._create_stock_file_section())

        return group

    def _create_orders_file_section(self):
        """Creates Orders file selection with folder support."""
        group_box = QGroupBox("📦 Orders File")
        layout = QVBoxLayout()

        # Mode selector (Radio buttons)
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Load Mode:")

        self.mw.orders_single_radio = QRadioButton("Single File")
        self.mw.orders_folder_radio = QRadioButton("Folder (Multiple Files)")
        self.mw.orders_single_radio.setChecked(True)  # Default

        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mw.orders_single_radio)
        mode_layout.addWidget(self.mw.orders_folder_radio)
        mode_layout.addStretch()

        layout.addLayout(mode_layout)

        # Select button (text changes based on mode)
        self.mw.load_orders_btn = QPushButton("Load Orders File (.csv)")
        self.mw.load_orders_btn.setToolTip("Select the orders_export.csv file from Shopify.")
        self.mw.load_orders_btn.setEnabled(False)
        layout.addWidget(self.mw.load_orders_btn)

        # File path label (shows filename or "X files merged")
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Selected:"))
        self.mw.orders_file_path_label = QLabel("Orders file not selected")
        self.mw.orders_file_status_label = QLabel("")
        path_layout.addWidget(self.mw.orders_file_path_label)
        path_layout.addWidget(self.mw.orders_file_status_label)
        path_layout.addStretch()

        layout.addLayout(path_layout)

        # File list preview (only visible in folder mode)
        self.mw.orders_file_list_widget = QListWidget()
        self.mw.orders_file_list_widget.setMaximumHeight(120)
        self.mw.orders_file_list_widget.setVisible(False)
        layout.addWidget(self.mw.orders_file_list_widget)

        # File count label
        self.mw.orders_file_count_label = QLabel("")
        self.mw.orders_file_count_label.setVisible(False)
        layout.addWidget(self.mw.orders_file_count_label)

        # Options (only visible in folder mode)
        self.mw.orders_options_widget = QWidget()
        options_layout = QVBoxLayout()

        self.mw.orders_recursive_checkbox = QCheckBox("Include subfolders")
        self.mw.orders_remove_duplicates_checkbox = QCheckBox("Remove duplicate orders")
        self.mw.orders_remove_duplicates_checkbox.setChecked(True)
        self.mw.orders_remove_duplicates_checkbox.setToolTip(
            "Remove orders with same Order Number + SKU (keeps first occurrence)"
        )

        options_layout.addWidget(self.mw.orders_recursive_checkbox)
        options_layout.addWidget(self.mw.orders_remove_duplicates_checkbox)
        self.mw.orders_options_widget.setLayout(options_layout)
        self.mw.orders_options_widget.setVisible(False)

        layout.addWidget(self.mw.orders_options_widget)

        group_box.setLayout(layout)
        return group_box

    def _create_stock_file_section(self):
        """Creates Stock file selection with folder support."""
        group_box = QGroupBox("📊 Stock File")
        layout = QVBoxLayout()

        # Mode selector (Radio buttons)
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Load Mode:")

        self.mw.stock_single_radio = QRadioButton("Single File")
        self.mw.stock_folder_radio = QRadioButton("Folder (Multiple Files)")
        self.mw.stock_single_radio.setChecked(True)  # Default

        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mw.stock_single_radio)
        mode_layout.addWidget(self.mw.stock_folder_radio)
        mode_layout.addStretch()

        layout.addLayout(mode_layout)

        # Select button (text changes based on mode)
        self.mw.load_stock_btn = QPushButton("Load Stock File (.csv)")
        self.mw.load_stock_btn.setToolTip("Select the inventory/stock CSV file.")
        self.mw.load_stock_btn.setEnabled(False)
        layout.addWidget(self.mw.load_stock_btn)

        # File path label (shows filename or "X files merged")
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Selected:"))
        self.mw.stock_file_path_label = QLabel("Stock file not selected")
        self.mw.stock_file_status_label = QLabel("")
        path_layout.addWidget(self.mw.stock_file_path_label)
        path_layout.addWidget(self.mw.stock_file_status_label)
        path_layout.addStretch()

        layout.addLayout(path_layout)

        # File list preview (only visible in folder mode)
        self.mw.stock_file_list_widget = QListWidget()
        self.mw.stock_file_list_widget.setMaximumHeight(120)
        self.mw.stock_file_list_widget.setVisible(False)
        layout.addWidget(self.mw.stock_file_list_widget)

        # File count label
        self.mw.stock_file_count_label = QLabel("")
        self.mw.stock_file_count_label.setVisible(False)
        layout.addWidget(self.mw.stock_file_count_label)

        # Options (only visible in folder mode)
        self.mw.stock_options_widget = QWidget()
        options_layout = QVBoxLayout()

        self.mw.stock_recursive_checkbox = QCheckBox("Include subfolders")
        self.mw.stock_remove_duplicates_checkbox = QCheckBox("Remove duplicate items")
        self.mw.stock_remove_duplicates_checkbox.setChecked(True)
        self.mw.stock_remove_duplicates_checkbox.setToolTip(
            "Remove items with same SKU (keeps first occurrence)"
        )

        options_layout.addWidget(self.mw.stock_recursive_checkbox)
        options_layout.addWidget(self.mw.stock_remove_duplicates_checkbox)
        self.mw.stock_options_widget.setLayout(options_layout)
        self.mw.stock_options_widget.setVisible(False)

        layout.addWidget(self.mw.stock_options_widget)

        group_box.setLayout(layout)
        return group_box

    def on_orders_mode_changed(self, checked):
        """Handle mode change between Single and Folder for Orders."""
        is_folder_mode = self.mw.orders_folder_radio.isChecked()

        # Update button text
        if is_folder_mode:
            self.mw.load_orders_btn.setText("Select Orders Folder...")
        else:
            self.mw.load_orders_btn.setText("Load Orders File (.csv)")

        # Show/hide folder-specific widgets
        self.mw.orders_file_list_widget.setVisible(is_folder_mode)
        self.mw.orders_file_count_label.setVisible(is_folder_mode)
        self.mw.orders_options_widget.setVisible(is_folder_mode)

        # Clear selection when switching modes
        self.mw.orders_file_path = None
        self.mw.orders_file_path_label.setText("Orders file not selected")
        self.mw.orders_file_status_label.setText("")
        self.mw.orders_file_list_widget.clear()

    def on_stock_mode_changed(self, checked):
        """Handle mode change between Single and Folder for Stock."""
        is_folder_mode = self.mw.stock_folder_radio.isChecked()

        # Update button text
        if is_folder_mode:
            self.mw.load_stock_btn.setText("Select Stock Folder...")
        else:
            self.mw.load_stock_btn.setText("Load Stock File (.csv)")

        # Show/hide folder-specific widgets
        self.mw.stock_file_list_widget.setVisible(is_folder_mode)
        self.mw.stock_file_count_label.setVisible(is_folder_mode)
        self.mw.stock_options_widget.setVisible(is_folder_mode)

        # Clear selection when switching modes
        self.mw.stock_file_path = None
        self.mw.stock_file_path_label.setText("Stock file not selected")
        self.mw.stock_file_status_label.setText("")
        self.mw.stock_file_list_widget.clear()

    def _create_actions_layout(self):
        """Creates the QHBoxLayout containing the 'Reports' and 'Actions' groups."""
        layout = QHBoxLayout()
        layout.addWidget(self._create_reports_group(), 1)
        layout.addWidget(self._create_main_actions_group(), 3)
        return layout

    def _create_reports_group(self):
        """Creates the 'Reports' QGroupBox."""
        group = QGroupBox("Reports")
        layout = QVBoxLayout()
        group.setLayout(layout)

        self.mw.packing_list_button = QPushButton("Create Packing List")
        self.mw.packing_list_button.setToolTip("Generate packing lists based on pre-defined filters.")
        self.mw.stock_export_button = QPushButton("Create Stock Export")
        self.mw.stock_export_button.setToolTip("Generate stock export files for couriers.")

        self.mw.packing_list_button.setEnabled(False)
        self.mw.stock_export_button.setEnabled(False)

        layout.addWidget(self.mw.packing_list_button)
        layout.addWidget(self.mw.stock_export_button)
        layout.addStretch()
        return group

    def _create_main_actions_group(self):
        """Creates the 'Actions' QGroupBox containing the main 'Run' button."""
        group = QGroupBox("Actions")
        main_layout = QVBoxLayout(group)

        # Main action buttons
        actions_layout = QHBoxLayout()
        self.mw.run_analysis_button = QPushButton("Run Analysis")
        self.mw.run_analysis_button.setMinimumHeight(60)
        self.mw.run_analysis_button.setEnabled(False)
        self.mw.run_analysis_button.setToolTip("Start the fulfillment analysis based on the loaded files.")

        self.mw.add_product_button = QPushButton("➕ Add Product to Order")
        self.mw.add_product_button.setMinimumHeight(60)
        self.mw.add_product_button.setEnabled(False)  # Enabled after successful analysis
        self.mw.add_product_button.setToolTip("Manually add a product to an existing order")

        self.mw.settings_button = QPushButton("Open Client Settings")
        self.mw.settings_button.setToolTip("Open the settings window for the active client.")
        self.mw.settings_button.setEnabled(False)  # Enabled when client is selected

        actions_layout.addWidget(self.mw.run_analysis_button, 1)
        actions_layout.addWidget(self.mw.add_product_button, 1)
        actions_layout.addWidget(self.mw.settings_button)
        main_layout.addLayout(actions_layout)

        return group

    def _create_tab_view(self):
        """Creates the main QTabWidget for displaying data and logs."""
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
        """Creates the 'Activity Log' tab with its QTableWidget."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.mw.activity_log_table = QTableWidget()
        self.mw.activity_log_table.setColumnCount(3)
        self.mw.activity_log_table.setHorizontalHeaderLabels(["Time", "Operation", "Description"])
        self.mw.activity_log_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.mw.activity_log_table)
        return tab

    def _create_data_view_tab(self):
        """Creates the 'Analysis Data' tab, including the filter controls and table view."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # --- Advanced Filter Controls ---
        filter_layout = QHBoxLayout()
        self.mw.filter_column_selector = QComboBox()
        self.mw.filter_input = QLineEdit()
        self.mw.filter_input.setPlaceholderText("Enter filter text...")
        self.mw.case_sensitive_checkbox = QCheckBox("Case Sensitive")
        self.mw.clear_filter_button = QPushButton("Clear")

        filter_layout.addWidget(QLabel("Filter by:"))
        filter_layout.addWidget(self.mw.filter_column_selector)
        filter_layout.addWidget(self.mw.filter_input, 1) # Allow stretching
        filter_layout.addWidget(self.mw.case_sensitive_checkbox)
        filter_layout.addWidget(self.mw.clear_filter_button)
        layout.addLayout(filter_layout)


        # --- Table View ---
        self.mw.tableView = QTableView()
        self.mw.tableView.setSortingEnabled(True)
        self.mw.tableView.setContextMenuPolicy(Qt.CustomContextMenu)
        layout.addWidget(self.mw.tableView)
        return tab

    def create_statistics_tab(self, tab_widget):
        """Creates and lays out the UI elements for the 'Statistics' tab.

        Args:
            tab_widget (QWidget): The parent widget (the tab) to populate.
        """
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
        """Enables or disables key UI elements based on application state.

        This is used to prevent user interaction while a long-running process
        (like the main analysis) is active. It also enables report buttons
        only when data is loaded.

        Args:
            is_busy (bool): If True, disables interactive widgets. If False,
                enables them based on the current application state.
        """
        self.mw.run_analysis_button.setEnabled(not is_busy)

        # FIX: Check that DataFrame is not None before calling .empty
        is_data_loaded = (
            self.mw.analysis_results_df is not None
            and not self.mw.analysis_results_df.empty
        )

        self.mw.packing_list_button.setEnabled(not is_busy and is_data_loaded)
        self.mw.stock_export_button.setEnabled(not is_busy and is_data_loaded)

        self.log.debug(f"UI busy state set to: {is_busy}, data_loaded: {is_data_loaded}")

    def update_results_table(self, data_df):
        """Populates the main results table with new data from a DataFrame.

        It sets up a `PandasModel` and a `QSortFilterProxyModel` to efficiently
        display and filter the potentially large dataset of analysis results.

        Args:
            data_df (pd.DataFrame): The DataFrame containing the analysis
                results to display.
        """
        self.log.info("Updating results table with new data.")
        if data_df.empty:
            self.log.warning("Received empty dataframe, clearing tables.")

        # Reset columns if this is the first data load
        if not self.mw.all_columns:
            self.mw.all_columns = data_df.columns.tolist()
            self.mw.visible_columns = self.mw.all_columns[:]

        # Use all columns from the dataframe, visibility is handled by the view
        main_df = data_df.copy()

        source_model = PandasModel(main_df)
        self.mw.proxy_model.setSourceModel(source_model)
        self.mw.tableView.setModel(self.mw.proxy_model)

        self.mw.tableView.resizeColumnsToContents()
