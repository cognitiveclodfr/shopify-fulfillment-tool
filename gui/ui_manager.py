import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QTabWidget, QGroupBox, QTableView, QPlainTextEdit, QTableWidget, QLineEdit,
    QComboBox, QCheckBox, QRadioButton, QListWidget, QListWidgetItem, QFrame, QStyle
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QShortcut, QKeySequence, QFont
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
        entire widget hierarchy for the `MainWindow` with a new tab-based layout.

        NEW STRUCTURE:
        - Global Header (client selector + session info) - always visible
        - 4 Main Tabs:
          1. Session Setup (file loading, actions)
          2. Analysis Results (table, filters, actions)
          3. Session Browser (session management)
          4. Information (statistics, logs)
        """
        self.log.info("Creating UI widgets with new tab-based structure.")

        # Create central widget
        central_widget = QWidget()
        self.mw.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Step 1: Create global header (always visible)
        header_widget = self._create_global_header()
        main_layout.addWidget(header_widget)

        # Step 2: Create main tab widget
        self.main_tabs = QTabWidget()
        self.main_tabs.setDocumentMode(True)  # Cleaner appearance
        self.main_tabs.setTabPosition(QTabWidget.North)
        self.main_tabs.setMovable(False)  # Prevent accidental tab reordering

        # Create tabs (empty for now - will populate in later phases)
        tab1 = self._create_tab1_session_setup()
        tab2 = self._create_tab2_analysis_results()
        tab3 = self._create_tab3_session_browser()
        tab4 = self._create_tab4_information()

        # Add tabs with icons (using QStyle standard icons)
        file_icon = self.mw.style().standardIcon(QStyle.SP_FileIcon)
        table_icon = self.mw.style().standardIcon(QStyle.SP_FileDialogDetailedView)
        folder_icon = self.mw.style().standardIcon(QStyle.SP_DirIcon)
        info_icon = self.mw.style().standardIcon(QStyle.SP_MessageBoxInformation)

        self.main_tabs.addTab(tab1, file_icon, "Session Setup")
        self.main_tabs.addTab(tab2, table_icon, "Analysis Results")
        self.main_tabs.addTab(tab3, folder_icon, "Session Browser")
        self.main_tabs.addTab(tab4, info_icon, "Information")

        # Setup keyboard shortcuts
        self._setup_tab_shortcuts()

        # Add tabs to main layout with stretch
        main_layout.addWidget(self.main_tabs, 1)  # Stretch factor: 1

        # Setup status bar
        self.mw.statusBar().showMessage("Ready")

        self.log.info("UI widgets created successfully with tab structure.")

    def _create_global_header(self):
        """Create global header with client selector and session info.

        Always visible above tabs. Contains:
        - Client selector (ClientSelectorWidget)
        - Session info label
        """
        header = QWidget()
        header.setMaximumHeight(80)
        layout = QVBoxLayout(header)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Row 1: Client selector (reuse existing widget)
        from gui.client_selector_widget import ClientSelectorWidget

        self.mw.client_selector = ClientSelectorWidget(
            self.mw.profile_manager,
            self.mw
        )
        layout.addWidget(self.mw.client_selector)

        # Row 2: Session info
        session_row = QHBoxLayout()

        folder_icon = self.mw.style().standardIcon(QStyle.SP_DirIcon)
        session_icon_label = QLabel()
        session_icon_label.setPixmap(folder_icon.pixmap(16, 16))
        session_row.addWidget(session_icon_label)

        session_row.addWidget(QLabel("Session:"))

        self.session_info_label = QLabel("No session")
        self.session_info_label.setStyleSheet("font-weight: bold;")
        session_row.addWidget(self.session_info_label)

        session_row.addStretch()

        layout.addLayout(session_row)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        return header

    def _setup_tab_shortcuts(self):
        """Setup keyboard shortcuts for tab switching."""
        # Tab switching shortcuts
        QShortcut(QKeySequence("Ctrl+1"), self.mw,
                  lambda: self.main_tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self.mw,
                  lambda: self.main_tabs.setCurrentIndex(1))
        QShortcut(QKeySequence("Ctrl+3"), self.mw,
                  lambda: self.main_tabs.setCurrentIndex(2))
        QShortcut(QKeySequence("Ctrl+4"), self.mw,
                  lambda: self.main_tabs.setCurrentIndex(3))

        # Set tooltips for tabs
        self.main_tabs.setTabToolTip(0, "Session setup and file loading (Ctrl+1)")
        self.main_tabs.setTabToolTip(1, "View and edit analysis results (Ctrl+2)")
        self.main_tabs.setTabToolTip(2, "Browse past sessions (Ctrl+3)")
        self.main_tabs.setTabToolTip(3, "Statistics and logs (Ctrl+4)")

    def _create_tab1_session_setup(self):
        """Create Tab 1: Session Setup.

        Contains:
        - Session management (Create New Session button + session label)
        - File loading (orders + stock with single/folder modes)
        - Actions (Run Analysis + Settings buttons)
        - Reports (Packing List + Stock Export + Open Folder buttons)
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Section 1: Session Management
        session_group = self._create_session_management_section()
        layout.addWidget(session_group)

        # Section 2: File Loading (2 columns: Orders | Stock)
        files_group = self._create_files_loading_section()
        layout.addWidget(files_group)

        # Section 3: Actions (Run Analysis, Settings)
        actions_group = self._create_actions_section()
        layout.addWidget(actions_group)

        # Section 4: Reports (enabled after analysis)
        reports_group = self._create_reports_section()
        layout.addWidget(reports_group)

        # Stretch at bottom to push everything up
        layout.addStretch()

        return tab

    def _create_tab2_analysis_results(self):
        """Create Tab 2: Analysis Results.

        Contains:
        - Filter controls (column selector, text input, case sensitive, clear)
        - Action buttons (Add Product, Export buttons, Open Folder)
        - Results table (QTableView with proxy model)
        - Summary bar (order/item counts)
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # Section 1: Filter controls
        filter_widget = self._create_filter_controls()
        layout.addWidget(filter_widget)

        # Section 2: Action buttons
        actions_widget = self._create_results_actions()
        layout.addWidget(actions_widget)

        # Section 3: Results table (MAIN content)
        table_widget = self._create_results_table()
        layout.addWidget(table_widget, 1)  # Stretch factor: 1

        # Section 4: Summary bar
        summary_widget = self._create_summary_bar()
        layout.addWidget(summary_widget)

        return tab

    def _create_tab3_session_browser(self):
        """Create Tab 3: Session Browser.

        Contains:
        - SessionBrowserWidget (full tab space)
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # REUSE existing SessionBrowserWidget (full height)
        from gui.session_browser_widget import SessionBrowserWidget

        self.mw.session_browser = SessionBrowserWidget(
            self.mw.session_manager,
            self.mw
        )

        layout.addWidget(self.mw.session_browser, 1)  # Full stretch

        return tab

    def _create_tab4_information(self):
        """Create Tab 4: Information.

        Contains sub-tabs:
        - Statistics
        - Activity Log
        - Execution Log
        """
        # Create sub-tab widget
        sub_tabs = QTabWidget()
        sub_tabs.setTabPosition(QTabWidget.North)

        # Sub-tab 1: Statistics
        stats_tab = self._create_statistics_subtab()
        sub_tabs.addTab(stats_tab, "📊 Statistics")

        # Sub-tab 2: Activity Log
        activity_tab = self._create_activity_log_subtab()
        sub_tabs.addTab(activity_tab, "📋 Activity Log")

        # Sub-tab 3: Execution Log
        execution_tab = self._create_execution_log_subtab()
        sub_tabs.addTab(execution_tab, "🔧 Execution Log")

        return sub_tabs

    # ========== TAB 1 CONTENT METHODS (Phase 2) ==========

    def _create_session_management_section(self):
        """Create session management UI for Tab 1."""
        group = QGroupBox("📂 Session Management")
        layout = QHBoxLayout(group)

        # Create new session button
        self.mw.new_session_btn = QPushButton("Create New Session")
        self.mw.new_session_btn.setIcon(
            self.mw.style().standardIcon(QStyle.SP_FileDialogNewFolder)
        )
        self.mw.new_session_btn.setEnabled(False)  # Enabled when client is selected
        self.mw.new_session_btn.setToolTip(
            "Create a new analysis session for the selected client"
        )
        layout.addWidget(self.mw.new_session_btn)

        # Session path label
        layout.addWidget(QLabel("Current:"))
        self.mw.session_path_label = QLabel("No session")
        layout.addWidget(self.mw.session_path_label)

        layout.addStretch()

        return group

    def _create_files_loading_section(self):
        """Create file loading section for Tab 1.

        REUSE existing _create_files_group() logic but adapt layout.
        """
        group = QGroupBox("📁 Load Data")
        layout = QHBoxLayout(group)
        layout.setSpacing(10)

        # Orders section (left) - REUSE existing method!
        orders_section = self._create_orders_file_section()
        layout.addWidget(orders_section, 1)

        # Stock section (right) - REUSE existing method!
        stock_section = self._create_stock_file_section()
        layout.addWidget(stock_section, 1)

        return group

    def _create_actions_section(self):
        """Create main actions section for Tab 1 (Run Analysis, Settings)."""
        group = QGroupBox("⚙️ Actions")
        layout = QHBoxLayout(group)

        # Run Analysis button (prominent)
        self.mw.run_analysis_button = QPushButton("▶️ Run Analysis")
        self.mw.run_analysis_button.setMinimumHeight(50)
        self.mw.run_analysis_button.setStyleSheet("""
            QPushButton {
                font-size: 14pt;
                font-weight: bold;
            }
        """)
        self.mw.run_analysis_button.setEnabled(False)  # Disabled until files loaded
        self.mw.run_analysis_button.setToolTip(
            "Run fulfillment analysis (Ctrl+R)"
        )
        layout.addWidget(self.mw.run_analysis_button, 3)  # 3x width

        # Settings button
        self.mw.settings_button = QPushButton("⚙️ Client Settings")
        self.mw.settings_button.setMinimumHeight(50)
        self.mw.settings_button.setEnabled(False)  # Disabled until client selected
        self.mw.settings_button.setToolTip(
            "Open client configuration settings"
        )
        layout.addWidget(self.mw.settings_button, 1)  # 1x width

        # Keyboard shortcut for Run Analysis
        QShortcut(QKeySequence("Ctrl+R"), self.mw,
                  lambda: self.mw.run_analysis_button.click()
                          if self.mw.run_analysis_button.isEnabled() else None)

        return group

    def _create_reports_section(self):
        """Create reports section for Tab 1 (enabled after analysis)."""
        group = QGroupBox("📤 Reports")
        layout = QHBoxLayout(group)

        # Packing List button
        self.mw.packing_list_button = QPushButton("📄 Create Packing List")
        self.mw.packing_list_button.setEnabled(False)
        self.mw.packing_list_button.setToolTip("Generate packing lists based on pre-defined filters.")
        layout.addWidget(self.mw.packing_list_button)

        # Stock Export button
        self.mw.stock_export_button = QPushButton("📊 Create Stock Export")
        self.mw.stock_export_button.setEnabled(False)
        self.mw.stock_export_button.setToolTip("Generate stock export files for couriers.")
        layout.addWidget(self.mw.stock_export_button)

        # Open session folder button (NEW!)
        self.mw.open_folder_button = QPushButton("📁 Open Session Folder")
        self.mw.open_folder_button.setIcon(
            self.mw.style().standardIcon(QStyle.SP_DirOpenIcon)
        )
        self.mw.open_folder_button.setEnabled(False)
        self.mw.open_folder_button.setToolTip("Open session folder in file explorer")
        layout.addWidget(self.mw.open_folder_button)

        layout.addStretch()

        return group

    # ========== TAB 2 CONTENT METHODS (Phase 3) ==========

    def _create_filter_controls(self):
        """Create filter controls row for Tab 2."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Filter by:"))

        # Column selector
        self.mw.filter_column_selector = QComboBox()
        self.mw.filter_column_selector.addItem("All Columns")
        layout.addWidget(self.mw.filter_column_selector)

        # Filter input with clear button
        self.mw.filter_input = QLineEdit()
        self.mw.filter_input.setPlaceholderText("Enter filter text...")
        self.mw.filter_input.setClearButtonEnabled(True)  # Built-in clear button!
        layout.addWidget(self.mw.filter_input, 1)

        # Case sensitive checkbox
        self.mw.case_sensitive_checkbox = QCheckBox("Case Sensitive")
        layout.addWidget(self.mw.case_sensitive_checkbox)

        # Clear button
        self.mw.clear_filter_button = QPushButton("Clear")
        self.mw.clear_filter_button.setIcon(
            self.mw.style().standardIcon(QStyle.SP_DialogResetButton)
        )
        layout.addWidget(self.mw.clear_filter_button)

        # Keyboard shortcut for filter focus
        QShortcut(QKeySequence("Ctrl+F"), self.mw,
                  lambda: self.mw.filter_input.setFocus())

        return widget

    def _create_results_actions(self):
        """Create action buttons for Tab 2 (results tab)."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Add Product button
        self.mw.add_product_button = QPushButton("➕ Add Product to Order")
        self.mw.add_product_button.setEnabled(False)
        self.mw.add_product_button.setToolTip(
            "Manually add a product to an existing order"
        )
        layout.addWidget(self.mw.add_product_button)

        # Packing List button (duplicate for convenience)
        packing_btn = QPushButton("📄 Packing List")
        packing_btn.setEnabled(False)
        layout.addWidget(packing_btn)
        self.mw.packing_list_button_tab2 = packing_btn

        # Stock Export button
        stock_btn = QPushButton("📊 Stock Export")
        stock_btn.setEnabled(False)
        layout.addWidget(stock_btn)
        self.mw.stock_export_button_tab2 = stock_btn

        # Open folder button
        folder_btn = QPushButton("📁 Open Folder")
        folder_btn.setIcon(
            self.mw.style().standardIcon(QStyle.SP_DirOpenIcon)
        )
        folder_btn.setEnabled(False)
        layout.addWidget(folder_btn)
        self.mw.open_folder_button_tab2 = folder_btn

        layout.addStretch()

        return widget

    def _create_results_table(self):
        """Create results table with proxy model for Tab 2."""
        # Table view
        self.mw.tableView = QTableView()
        self.mw.tableView.setSelectionBehavior(QTableView.SelectRows)
        self.mw.tableView.setSelectionMode(QTableView.ExtendedSelection)
        self.mw.tableView.setAlternatingRowColors(True)
        self.mw.tableView.setSortingEnabled(True)
        self.mw.tableView.setContextMenuPolicy(Qt.CustomContextMenu)

        # Proxy model for filtering/sorting (already created in MainWindow __init__)
        # Just set it to the table view
        self.mw.tableView.setModel(self.mw.proxy_model)

        return self.mw.tableView

    def _create_summary_bar(self):
        """Create summary bar at bottom of Tab 2."""
        widget = QWidget()
        widget.setMaximumHeight(30)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        self.mw.summary_label = QLabel("No analysis data")
        self.mw.summary_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.mw.summary_label)

        layout.addStretch()

        return widget

    def update_summary_bar(self):
        """Update summary bar with current analysis stats."""
        if not hasattr(self.mw, 'analysis_results_df') or self.mw.analysis_results_df is None:
            self.mw.summary_label.setText("No analysis data")
            return

        df = self.mw.analysis_results_df

        total_orders = df['Order_Number'].nunique() if 'Order_Number' in df.columns else 0
        total_items = len(df)
        fulfillable = 0
        if 'Order_Fulfillment_Status' in df.columns:
            fulfillable = (df['Order_Fulfillment_Status'] == 'Fulfillable').sum()

        self.mw.summary_label.setText(
            f"📊 {total_orders} orders │ {total_items} items │ "
            f"{fulfillable} fulfillable"
        )

    # ========== TAB 4 SUB-TABS METHODS (Phase 5) ==========

    def _create_statistics_subtab(self):
        """Create statistics sub-tab for Tab 4."""
        tab = QWidget()
        self.create_statistics_tab(tab)  # REUSE existing method!
        return tab

    def _create_activity_log_subtab(self):
        """Create activity log sub-tab for Tab 4."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        # Activity table
        self.mw.activity_log_table = QTableWidget()
        self.mw.activity_log_table.setColumnCount(3)
        self.mw.activity_log_table.setHorizontalHeaderLabels(["Time", "Operation", "Description"])
        self.mw.activity_log_table.horizontalHeader().setStretchLastSection(True)
        self.mw.activity_log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.mw.activity_log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.mw.activity_log_table.setAlternatingRowColors(True)

        layout.addWidget(self.mw.activity_log_table)

        return tab

    def _create_execution_log_subtab(self):
        """Create execution log sub-tab for Tab 4."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        # Log text widget
        self.mw.execution_log_edit = QPlainTextEdit()
        self.mw.execution_log_edit.setReadOnly(True)
        self.mw.execution_log_edit.setLineWrapMode(QPlainTextEdit.NoWrap)

        # Monospace font for logs
        font = QFont("Courier New", 9)
        self.mw.execution_log_edit.setFont(font)

        layout.addWidget(self.mw.execution_log_edit)

        return tab

    # ========== OLD METHODS (kept for reference, will be reused in phases 2-5) ==========

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

        self.mw.settings_button = QPushButton("Open Client Settings")
        self.mw.settings_button.setToolTip("Open the settings window for the active client.")
        self.mw.settings_button.setEnabled(False)  # Enabled when client is selected

        actions_layout.addWidget(self.mw.run_analysis_button, 1)
        actions_layout.addWidget(self.mw.settings_button)
        main_layout.addLayout(actions_layout)

        # Manual operations
        manual_layout = QHBoxLayout()
        self.mw.add_product_button = QPushButton("➕ Add Product to Order")
        self.mw.add_product_button.setEnabled(False)  # Disabled until analysis run
        self.mw.add_product_button.setToolTip(
            "Manually add a product to an existing order"
        )
        manual_layout.addWidget(self.mw.add_product_button)
        manual_layout.addStretch()
        main_layout.addLayout(manual_layout)

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

        # Check states
        is_data_loaded = (
            self.mw.analysis_results_df is not None
            and not self.mw.analysis_results_df.empty
        )
        has_session = bool(self.mw.session_path)

        # Tab 1: Report buttons
        self.mw.packing_list_button.setEnabled(not is_busy and is_data_loaded)
        self.mw.stock_export_button.setEnabled(not is_busy and is_data_loaded)
        self.mw.open_folder_button.setEnabled(not is_busy and has_session)

        # Tab 2: Action buttons (duplicates)
        if hasattr(self.mw, 'add_product_button'):
            self.mw.add_product_button.setEnabled(not is_busy and is_data_loaded)

        if hasattr(self.mw, 'packing_list_button_tab2'):
            self.mw.packing_list_button_tab2.setEnabled(not is_busy and is_data_loaded)

        if hasattr(self.mw, 'stock_export_button_tab2'):
            self.mw.stock_export_button_tab2.setEnabled(not is_busy and is_data_loaded)

        if hasattr(self.mw, 'open_folder_button_tab2'):
            self.mw.open_folder_button_tab2.setEnabled(not is_busy and has_session)

        self.log.debug(f"UI busy state: {is_busy}, data_loaded: {is_data_loaded}, has_session: {has_session}")

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

    def update_session_info_label(self):
        """Update global header session info label.

        Shows current session name or "No session" if none active.
        """
        if not hasattr(self, 'session_info_label'):
            return

        if not self.mw.session_path:
            self.session_info_label.setText("No session")
            return

        import os
        session_name = os.path.basename(self.mw.session_path)
        self.session_info_label.setText(session_name)

        # Also update session_path_label in Tab 1 if it exists
        if hasattr(self.mw, 'session_path_label'):
            self.mw.session_path_label.setText(session_name)

    def open_session_folder(self):
        """Open session folder in OS file explorer.

        Opens the current session directory in the system's default file manager.
        Works on Windows, macOS, and Linux.
        """
        import subprocess
        import platform

        if not self.mw.session_path:
            self.log.warning("No session path available to open")
            return

        try:
            system = platform.system()
            if system == "Windows":
                subprocess.Popen(f'explorer "{self.mw.session_path}"')
            elif system == "Darwin":  # macOS
                subprocess.Popen(["open", self.mw.session_path])
            else:  # Linux and others
                subprocess.Popen(["xdg-open", self.mw.session_path])

            self.log.info(f"Opened session folder: {self.mw.session_path}")
            self.mw.statusBar().showMessage(f"Opened session folder", 3000)
        except Exception as e:
            self.log.error(f"Failed to open session folder: {e}", exc_info=True)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self.mw,
                "Error",
                f"Failed to open session folder:\n{str(e)}"
            )
