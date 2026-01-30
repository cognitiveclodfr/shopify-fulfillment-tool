import sys
import os
import json
import pandas as pd
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QTabWidget,
    QWidget,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QComboBox,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QSpinBox,
)
from PySide6.QtCore import Qt

from shopify_tool.core import get_unique_column_values
from gui.column_mapping_widget import ColumnMappingWidget
from gui.wheel_ignore_combobox import WheelIgnoreComboBox
from shopify_tool.set_decoder import import_sets_from_csv, export_sets_to_csv


class SettingsWindow(QDialog):
    """A dialog window for viewing and editing all application settings.

    This window provides a tabbed interface for modifying different sections
    of the application's configuration, including:
    - General settings and paths.
    - The rule engine's rule definitions.
    - Pre-configured packing list reports.
    - Pre-configured stock export reports.

    The UI is built dynamically based on the current configuration data that
    is passed in during initialization. It allows for adding, editing, and
    deleting rules, reports, and their constituent parts.

    Attributes:
        config_data (dict): A deep copy of the application's configuration.
        analysis_df (pd.DataFrame): The main analysis DataFrame, used to
            populate dynamic dropdowns for filter values.
        rule_widgets (list): A list of dictionaries, each holding references
            to the UI widgets for a single rule.
        packing_list_widgets (list): References to packing list UI widgets.
        stock_export_widgets (list): References to stock export UI widgets.
    """

    # Constants for builders
    FILTERABLE_COLUMNS = [
        "Order_Number",
        "Order_Type",
        "SKU",
        "Product_Name",
        "Stock_Alert",
        "Order_Fulfillment_Status",
        "Shipping_Provider",
        "Destination_Country",
        "Tags",
        "System_note",
        "Status_Note",
        "Total Price",
    ]
    FILTER_OPERATORS = ["==", "!=", "in", "not in", "contains"]
    # Group order-level fields first for better UX
    ORDER_LEVEL_FIELDS = [
        "--- ORDER-LEVEL FIELDS ---",
        "item_count",
        "total_quantity",
        "has_sku",
        "Has_SKU",
        "--- ARTICLE-LEVEL FIELDS ---",
    ]
    CONDITION_FIELDS = ORDER_LEVEL_FIELDS + FILTERABLE_COLUMNS
    CONDITION_OPERATORS = [
        "equals",
        "does not equal",
        "contains",
        "does not contain",
        "is greater than",
        "is less than",
        "is greater than or equal",
        "is less than or equal",
        "starts with",
        "ends with",
        "is empty",
        "is not empty",
        "in list",
        "not in list",
        "between",
        "not between",
        "date before",
        "date after",
        "date equals",
        "matches regex",
    ]
    ACTION_TYPES = [
        "ADD_TAG",
        "ADD_ORDER_TAG",
        "ADD_INTERNAL_TAG",
        "SET_STATUS",
    ]

    def __init__(self, client_id, client_config, profile_manager, analysis_df=None, parent=None):
        """Initializes the SettingsWindow.

        Args:
            client_id (str): The client ID for which settings are being edited.
            client_config (dict): The client's configuration dictionary. A deep
                copy is made to avoid modifying the original until saved.
            profile_manager: The ProfileManager instance for saving settings.
            analysis_df (pd.DataFrame, optional): The current analysis
                DataFrame, used for populating filter value dropdowns.
                Defaults to None.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.client_id = client_id
        self.config_data = json.loads(json.dumps(client_config))
        self.profile_manager = profile_manager
        self.analysis_df = analysis_df if analysis_df is not None else pd.DataFrame()

        # Ensure config structure exists
        if not isinstance(self.config_data.get("column_mappings"), dict):
            self.config_data["column_mappings"] = {
                "orders_required": [],
                "stock_required": []
            }

        if "courier_mappings" not in self.config_data:
            self.config_data["courier_mappings"] = {}

        if "settings" not in self.config_data:
            self.config_data["settings"] = {
                "low_stock_threshold": 5,
                "stock_csv_delimiter": ";"
            }

        if "rules" not in self.config_data:
            self.config_data["rules"] = []

        if "packing_list_configs" not in self.config_data:
            self.config_data["packing_list_configs"] = []

        if "stock_export_configs" not in self.config_data:
            self.config_data["stock_export_configs"] = []

        # Widget lists
        self.rule_widgets = []
        self.packing_list_widgets = []
        self.stock_export_widgets = []
        self.courier_mapping_widgets = []

        self.setWindowTitle(f"Settings - CLIENT_{self.client_id}")
        self.setMinimumSize(900, 750)  # Slightly larger for new tabs
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Create all tabs
        self.create_general_tab()
        self.create_rules_tab()
        self.create_packing_lists_tab()
        self.create_stock_exports_tab()
        self.create_mappings_tab()
        self.create_sets_tab()  # Sets/Bundles tab

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    # Generic helper to delete a widget and its reference from a list
    def _delete_widget_from_list(self, widget_refs, ref_list):
        """Generic helper to delete a group box widget and its reference from a list."""
        widget_refs["group_box"].deleteLater()
        ref_list.remove(widget_refs)

    # Generic helper to delete a row widget and its reference from a list
    def _delete_row_from_list(self, row_widget, ref_list, ref_dict):
        """Generic helper to delete a row widget and its reference from a list."""
        row_widget.deleteLater()
        ref_list.remove(ref_dict)

    def get_available_rule_fields(self):
        """Get all available fields for rules from DataFrame + common fields.

        Returns a list of field names including:
        - Order-level fields (shown first)
        - Common article-level fields
        - All other DataFrame columns (dynamically discovered)
        - Separators (disabled items starting with "---")
        """
        import logging
        logger = logging.getLogger(__name__)

        # Start with order-level fields (these are ALWAYS available)
        order_level_fields = [
            "--- ORDER-LEVEL FIELDS ---",
            "item_count",
            "total_quantity",
            "has_sku",
        ]

        # Common article-level fields
        common_fields = [
            "--- COMMON ARTICLE FIELDS ---",
            "Order_Number",
            "Order_Type",
            "SKU",
            "Product_Name",
            "Quantity",
            "Stock",
            "Final_Stock",
            "Shipping_Provider",
            "Shipping_Method",
            "Destination_Country",
        ]

        # Get ALL columns from DataFrame
        if self.analysis_df is not None and not self.analysis_df.empty:
            all_columns = sorted(self.analysis_df.columns.tolist())
            logger.info(f"[RULE ENGINE] DataFrame has {len(all_columns)} columns")
            logger.info(f"[RULE ENGINE] ALL COLUMNS: {all_columns}")

            # Check if specific columns exist
            logger.info(f"[RULE ENGINE] 'Stock' in columns: {'Stock' in all_columns}")
            logger.info(f"[RULE ENGINE] 'Total_Price' in columns: {'Total_Price' in all_columns}")

            # Filter out internal columns (starting with _) and already listed common fields
            # But keep separators for checking
            common_field_names = [f for f in common_fields if not f.startswith("---")]

            custom_columns = [
                col for col in all_columns
                if not col.startswith('_')
                and col not in common_field_names  # Avoid duplicates
            ]

            logger.info(f"[RULE ENGINE] Found {len(custom_columns)} custom columns: {custom_columns}")

            # Combine: order-level fields first, then common fields, then separator, then custom
            if custom_columns:
                return order_level_fields + common_fields + [
                    "--- OTHER AVAILABLE FIELDS ---"
                ] + custom_columns
            else:
                return order_level_fields + common_fields
        else:
            logger.warning(f"[RULE ENGINE] No analysis_df available (is None: {self.analysis_df is None})")

        return order_level_fields + common_fields  # Fallback to order-level + common only

    def create_general_tab(self):
        """Creates the 'General Settings' tab."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)

        # Settings GroupBox
        settings_box = QGroupBox("General Settings")
        settings_layout = QFormLayout(settings_box)

        # Stock CSV delimiter with improved tooltip
        delimiter_label = QLabel("Stock CSV Delimiter:")
        self.stock_delimiter_edit = QLineEdit(
            self.config_data.get("settings", {}).get("stock_csv_delimiter", ";")
        )
        self.stock_delimiter_edit.setMaximumWidth(100)

        # Add informative tooltip
        self.stock_delimiter_edit.setToolTip(
            "Character used to separate columns in stock CSV file.\n\n"
            "Common values:\n"
            "  • Semicolon (;) - for exports from local warehouse\n"
            "  • Comma (,) - for Shopify exports\n\n"
            "Make sure this matches your stock CSV file format."
        )

        settings_layout.addRow(delimiter_label, self.stock_delimiter_edit)

        # Orders CSV Delimiter
        orders_delimiter_label = QLabel("Orders CSV Delimiter:")
        self.orders_delimiter_edit = QLineEdit(
            self.config_data.get("settings", {}).get("orders_csv_delimiter", ",")
        )
        self.orders_delimiter_edit.setMaximumWidth(100)
        self.orders_delimiter_edit.setPlaceholderText(",")

        # Add informative tooltip
        self.orders_delimiter_edit.setToolTip(
            "Character used to separate columns in orders CSV file.\n\n"
            "Common values:\n"
            "  • Comma (,) - standard Shopify exports\n"
            "  • Semicolon (;) - European Excel exports\n"
            "  • Tab (\\t) - tab-separated files\n\n"
            "The tool will auto-detect delimiter when you select a file,\n"
            "but you can override it here if needed."
        )

        settings_layout.addRow(orders_delimiter_label, self.orders_delimiter_edit)

        # Low stock threshold with improved tooltip
        threshold_label = QLabel("Low Stock Threshold:")
        self.low_stock_edit = QLineEdit(
            str(self.config_data.get("settings", {}).get("low_stock_threshold", 5))
        )
        self.low_stock_edit.setMaximumWidth(100)

        # Add informative tooltip
        self.low_stock_edit.setToolTip(
            "Trigger stock alerts when quantity falls below this number.\n\n"
            "Items with stock below this threshold will be marked in analysis."
        )

        settings_layout.addRow(threshold_label, self.low_stock_edit)

        # Repeat Detection Window
        repeat_days_label = QLabel("Repeat Detection Window (days):")
        self.repeat_days_input = QSpinBox()
        self.repeat_days_input.setMinimum(1)
        self.repeat_days_input.setMaximum(365)
        self.repeat_days_input.setValue(
            self.config_data.get("settings", {}).get("repeat_detection_days", 1)
        )
        self.repeat_days_input.setToolTip(
            "Orders fulfilled within this many days are marked as 'Repeat'.\n"
            "Default: 1 day (only yesterday's fulfillments)\n"
            "Increase for longer detection window (e.g., 7 days, 30 days)"
        )

        settings_layout.addRow(repeat_days_label, self.repeat_days_input)

        main_layout.addWidget(settings_box)

        # Info about removed fields
        info_box = QGroupBox("Note")
        info_layout = QVBoxLayout(info_box)
        info_label = QLabel(
            "Templates and custom output directories are no longer used.\n"
            "All reports are now generated in session-specific folders automatically."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        info_layout.addWidget(info_label)
        main_layout.addWidget(info_box)

        main_layout.addStretch()

        self.tab_widget.addTab(tab, "General")

    def create_rules_tab(self):
        """Creates the 'Rules' tab for dynamically managing automation rules."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        add_rule_btn = QPushButton("Add New Rule")
        add_rule_btn.clicked.connect(self.add_rule_widget)
        main_layout.addWidget(add_rule_btn, 0, Qt.AlignLeft)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)
        scroll_content = QWidget()
        self.rules_layout = QVBoxLayout(scroll_content)
        self.rules_layout.setAlignment(Qt.AlignTop)
        scroll_area.setWidget(scroll_content)
        self.tab_widget.addTab(tab, "Rules")
        for rule_config in self.config_data.get("rules", []):
            self.add_rule_widget(rule_config)

    def add_rule_widget(self, config=None):
        """Adds a new group of widgets for creating/editing a single rule.

        Args:
            config (dict, optional): The configuration for a pre-existing
                rule to load into the widgets. If None, creates a new,
                blank rule.
        """
        if not isinstance(config, dict):
            config = {"name": "New Rule", "level": "article", "match": "ALL", "conditions": [], "actions": []}
        rule_box = QGroupBox()
        rule_layout = QVBoxLayout(rule_box)
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Rule Name:"))
        name_edit = QLineEdit(config.get("name", ""))
        header_layout.addWidget(name_edit)
        delete_rule_btn = QPushButton("Delete Rule")
        header_layout.addWidget(delete_rule_btn)
        rule_layout.addLayout(header_layout)

        # Add level selector
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Rule Level:"))

        level_combo = WheelIgnoreComboBox()
        level_combo.addItems(["article", "order"])
        level_combo.setCurrentText(config.get("level", "article"))
        level_combo.setToolTip(
            "article: Apply to each item (row) individually\n"
            "  → Use article-level fields (SKU, Product_Name, etc.)\n"
            "  → All actions apply to matching rows\n\n"
            "order: Evaluate entire order based on aggregate data\n"
            "  → Use order-level fields:\n"
            "     • item_count - number of rows in order\n"
            "     • total_quantity - sum of all quantities\n"
            "     • has_sku - check if order contains specific SKU\n"
            "  → Actions behavior:\n"
            "     • ADD_TAG - applies to ALL rows (for filtering)\n"
            "     • ADD_ORDER_TAG - applies to first row only (for counting)\n"
            "     • SET_PACKAGING_TAG - applies to first row only (for counting)\n"
            "     • ADD_INTERNAL_TAG - applies to ALL rows (structured tags)"
        )
        level_layout.addWidget(level_combo)
        level_layout.addStretch()

        rule_layout.addLayout(level_layout)
        conditions_box = QGroupBox("IF")
        conditions_layout = QVBoxLayout(conditions_box)
        match_layout = QHBoxLayout()
        match_layout.addWidget(QLabel("Execute actions if"))
        match_combo = WheelIgnoreComboBox()
        match_combo.addItems(["ALL", "ANY"])
        match_combo.setCurrentText(config.get("match", "ALL"))
        match_layout.addWidget(match_combo)
        match_layout.addWidget(QLabel("of the following conditions are met:"))
        match_layout.addStretch()
        conditions_layout.addLayout(match_layout)
        conditions_rows_layout = QVBoxLayout()
        conditions_layout.addLayout(conditions_rows_layout)
        add_condition_btn = QPushButton("Add Condition")
        conditions_layout.addWidget(add_condition_btn, 0, Qt.AlignLeft)
        rule_layout.addWidget(conditions_box)
        actions_box = QGroupBox("THEN perform these actions:")
        actions_layout = QVBoxLayout(actions_box)
        actions_rows_layout = QVBoxLayout()
        actions_layout.addLayout(actions_rows_layout)
        add_action_btn = QPushButton("Add Action")
        actions_layout.addWidget(add_action_btn, 0, Qt.AlignLeft)
        rule_layout.addWidget(actions_box)
        self.rules_layout.addWidget(rule_box)
        widget_refs = {
            "group_box": rule_box,
            "name_edit": name_edit,
            "level_combo": level_combo,
            "match_combo": match_combo,
            "conditions_layout": conditions_rows_layout,
            "actions_layout": actions_rows_layout,
            "conditions": [],
            "actions": [],
        }
        self.rule_widgets.append(widget_refs)
        add_condition_btn.clicked.connect(lambda: self.add_condition_row(widget_refs))
        add_action_btn.clicked.connect(lambda: self.add_action_row(widget_refs))
        delete_rule_btn.clicked.connect(lambda: self._delete_widget_from_list(widget_refs, self.rule_widgets))
        for cond_config in config.get("conditions", []):
            self.add_condition_row(widget_refs, cond_config)
        for act_config in config.get("actions", []):
            self.add_action_row(widget_refs, act_config)

    def add_condition_row(self, rule_widget_refs, config=None):
        """Adds a new row of widgets for a single condition within a rule.

        This method now supports dynamic value widgets, allowing for either a
        `QLineEdit` or a `QComboBox` based on the selected field and operator.

        Args:
            rule_widget_refs (dict): A dictionary of widget references for the
                parent rule.
            config (dict, optional): The configuration for a pre-existing
                condition. If None, creates a new, blank condition.
        """
        if not isinstance(config, dict):
            config = {}
        row_layout = QHBoxLayout()
        field_combo = WheelIgnoreComboBox()

        # Get dynamic fields from analysis DataFrame
        available_fields = self.get_available_rule_fields()

        # Add fields with separators disabled
        for field in available_fields:
            if field.startswith("---"):
                # Add separator as disabled item
                field_combo.addItem(field)
                # Disable the separator item
                model = field_combo.model()
                item = model.item(field_combo.count() - 1)
                item.setEnabled(False)
            else:
                field_combo.addItem(field)

        op_combo = WheelIgnoreComboBox()
        op_combo.addItems(self.CONDITION_OPERATORS)
        delete_btn = QPushButton("X")

        row_layout.addWidget(field_combo)
        row_layout.addWidget(op_combo)
        # The value widget will be inserted at index 2 by the handler

        # Set current text, skipping separators
        initial_field = config.get("field", "")
        if initial_field and not initial_field.startswith("---"):
            # Find the index of the field in the combo box
            index = field_combo.findText(initial_field)
            if index >= 0:
                field_combo.setCurrentIndex(index)
            else:
                # Field not found in combo box - add it to preserve saved value
                field_combo.addItem(initial_field)
                field_combo.setCurrentText(initial_field)
        elif not initial_field:
            # Set to first non-separator field
            for i, field in enumerate(available_fields):
                if not field.startswith("---"):
                    field_combo.setCurrentIndex(i)
                    break
        op_combo.setCurrentText(config.get("operator", self.CONDITION_OPERATORS[0]))
        initial_value = config.get("value", "")

        row_widget = QWidget()
        row_widget.setLayout(row_layout)

        condition_refs = {
            "widget": row_widget,
            "field": field_combo,
            "op": op_combo,
            "value_widget": None,
            "value_layout": row_layout,
        }

        row_layout.addWidget(delete_btn)

        # Connect signals to the new handler
        field_combo.currentTextChanged.connect(lambda: self._on_rule_condition_changed(condition_refs))
        op_combo.currentTextChanged.connect(lambda: self._on_rule_condition_changed(condition_refs))

        # Create the initial value widget
        self._on_rule_condition_changed(condition_refs, initial_value=initial_value)

        rule_widget_refs["conditions_layout"].addWidget(row_widget)
        rule_widget_refs["conditions"].append(condition_refs)
        delete_btn.clicked.connect(
            lambda: self._delete_row_from_list(row_widget, rule_widget_refs["conditions"], condition_refs)
        )

    def _on_rule_condition_changed(self, condition_refs, initial_value=None):
        """Dynamically changes the rule's value widget based on other selections.

        This method is connected to the 'field' and 'operator' combo boxes
        for a rule condition. It creates a `QComboBox` for value selection if
        the field is in the DataFrame and the operator is suitable (e.g., 'equals').
        For operators like 'is_empty', it hides the value widget. Otherwise,
        it provides a standard `QLineEdit`.

        Args:
            condition_refs (dict): A dictionary of widget references for the
                condition row.
            initial_value (any, optional): The value to set in the newly
                created widget. Defaults to None.
        """
        field = condition_refs["field"].currentText()
        op = condition_refs["op"].currentText()

        # Remove the old value widget, if it exists
        if condition_refs["value_widget"]:
            condition_refs["value_widget"].deleteLater()
            condition_refs["value_widget"] = None

        # Operators that don't need a value input
        if op in ["is_empty", "is_not_empty"]:
            return  # No widget will be created or added

        # Determine if a ComboBox should be used
        use_combobox = (
            op in ["equals", "does not equal"]
            and not self.analysis_df.empty
            and field in self.analysis_df.columns
        )

        if use_combobox:
            unique_values = get_unique_column_values(self.analysis_df, field)
            new_widget = WheelIgnoreComboBox()
            new_widget.addItems([""] + unique_values)  # Add a blank option
            if initial_value and str(initial_value) in unique_values:
                new_widget.setCurrentText(str(initial_value))
        else:
            # Default to QLineEdit with smart placeholders
            new_widget = QLineEdit()

            # Set operator-specific placeholders
            placeholder = "Value"  # Default

            if op in ["in list", "not in list"]:
                placeholder = "Value1, Value2, Value3"
            elif op in ["between", "not between"]:
                placeholder = "10-100"
            elif op in ["date before", "date after", "date equals"]:
                placeholder = "2024-01-30"
            elif op == "matches regex":
                placeholder = "^SKU-\\d{4}$"

            new_widget.setPlaceholderText(placeholder)

            if initial_value is not None:
                new_widget.setText(str(initial_value))

        # Insert the new widget into the layout at the correct position
        condition_refs["value_layout"].insertWidget(2, new_widget, 1)
        condition_refs["value_widget"] = new_widget


    def add_action_row(self, rule_widget_refs, config=None):
        """Adds a new row of widgets for a single action within a rule.

        Args:
            rule_widget_refs (dict): A dictionary of widget references for the
                parent rule.
            config (dict, optional): The configuration for a pre-existing
                action. If None, creates a new, blank action.
        """
        if not isinstance(config, dict):
            config = {}
        row_layout = QHBoxLayout()
        type_combo = WheelIgnoreComboBox()
        type_combo.addItems(self.ACTION_TYPES)
        value_edit = QLineEdit()
        delete_btn = QPushButton("X")
        row_layout.addWidget(type_combo)
        row_layout.addWidget(value_edit, 1)
        row_layout.addWidget(delete_btn)
        type_combo.setCurrentText(config.get("type", self.ACTION_TYPES[0]))
        value_edit.setText(config.get("value", ""))
        row_widget = QWidget()
        row_widget.setLayout(row_layout)
        rule_widget_refs["actions_layout"].addWidget(row_widget)
        action_refs = {"widget": row_widget, "type": type_combo, "value": value_edit}
        rule_widget_refs["actions"].append(action_refs)
        delete_btn.clicked.connect(
            lambda: self._delete_row_from_list(row_widget, rule_widget_refs["actions"], action_refs)
        )

    def create_packing_lists_tab(self):
        """Creates the 'Packing Lists' tab for managing report configurations."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        add_btn = QPushButton("Add New Packing List")
        add_btn.clicked.connect(self.add_packing_list_widget)
        main_layout.addWidget(add_btn, 0, Qt.AlignLeft)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)
        scroll_content = QWidget()
        self.packing_lists_layout = QVBoxLayout(scroll_content)
        self.packing_lists_layout.setAlignment(Qt.AlignTop)
        scroll_area.setWidget(scroll_content)
        self.tab_widget.addTab(tab, "Packing Lists")
        for pl_config in self.config_data.get("packing_list_configs", []):
            self.add_packing_list_widget(pl_config)

    def add_packing_list_widget(self, config=None):
        """Adds a new group of widgets for a single packing list configuration.

        Args:
            config (dict, optional): The configuration for a pre-existing
                packing list. If None, creates a new, blank one.
        """
        if not isinstance(config, dict):
            config = {"name": "", "output_filename": "", "filters": [], "exclude_skus": []}
        pl_box = QGroupBox()
        pl_layout = QVBoxLayout(pl_box)
        form_layout = QFormLayout()
        name_edit = QLineEdit(config.get("name", ""))
        filename_edit = QLineEdit(config.get("output_filename", ""))
        exclude_skus_edit = QLineEdit(",".join(config.get("exclude_skus", [])))
        form_layout.addRow("Name:", name_edit)
        form_layout.addRow("Output Filename:", filename_edit)
        form_layout.addRow("Exclude SKUs (comma-separated):", exclude_skus_edit)
        pl_layout.addLayout(form_layout)
        filters_box = QGroupBox("Filters")
        filters_layout = QVBoxLayout(filters_box)
        filters_rows_layout = QVBoxLayout()
        filters_layout.addLayout(filters_rows_layout)
        add_filter_btn = QPushButton("Add Filter")
        filters_layout.addWidget(add_filter_btn, 0, Qt.AlignLeft)
        pl_layout.addWidget(filters_box)
        delete_btn = QPushButton("Delete Packing List")
        pl_layout.addWidget(delete_btn, 0, Qt.AlignRight)
        self.packing_lists_layout.addWidget(pl_box)
        widget_refs = {
            "group_box": pl_box,
            "name": name_edit,
            "filename": filename_edit,
            "exclude_skus": exclude_skus_edit,
            "filters_layout": filters_rows_layout,
            "filters": [],
        }
        self.packing_list_widgets.append(widget_refs)
        add_filter_btn.clicked.connect(
            lambda: self.add_filter_row(widget_refs, self.FILTERABLE_COLUMNS, self.FILTER_OPERATORS)
        )
        delete_btn.clicked.connect(lambda: self._delete_widget_from_list(widget_refs, self.packing_list_widgets))
        for f_config in config.get("filters", []):
            self.add_filter_row(widget_refs, self.FILTERABLE_COLUMNS, self.FILTER_OPERATORS, f_config)

    def add_filter_row(self, parent_widget_refs, fields, operators, config=None):
        """Adds a new row of widgets for a single filter criterion.

        This is a generic helper used by both packing list and stock export tabs.

        Args:
            parent_widget_refs (dict): Widget references for the parent report.
            fields (list[str]): The list of columns to show in the field dropdown.
            operators (list[str]): The list of operators to show.
            config (dict, optional): The configuration for a pre-existing
                filter. If None, creates a new, blank filter.
        """
        if not isinstance(config, dict):
            config = {}
        row_layout = QHBoxLayout()
        field_combo = WheelIgnoreComboBox()
        field_combo.addItems(fields)
        op_combo = WheelIgnoreComboBox()
        op_combo.addItems(operators)
        value_edit = QLineEdit()
        delete_btn = QPushButton("X")

        row_layout.addWidget(field_combo)
        row_layout.addWidget(op_combo)
        row_layout.addWidget(value_edit, 1)

        field_combo.setCurrentText(config.get("field", fields[0]))
        op_combo.setCurrentText(config.get("operator", operators[0]))
        val = config.get("value", "")

        row_widget = QWidget()
        row_widget.setLayout(row_layout)

        filter_refs = {
            "widget": row_widget,
            "field": field_combo,
            "op": op_combo,
            "value_widget": None,
            "value_layout": row_layout,
        }

        # Connect signals before setting initial value to trigger the handler
        field_combo.currentTextChanged.connect(lambda: self._on_filter_criteria_changed(filter_refs))
        op_combo.currentTextChanged.connect(lambda: self._on_filter_criteria_changed(filter_refs))

        self._on_filter_criteria_changed(filter_refs, initial_value=val)  # Set initial widget and value

        row_layout.addWidget(delete_btn)
        parent_widget_refs["filters_layout"].addWidget(row_widget)
        parent_widget_refs["filters"].append(filter_refs)
        delete_btn.clicked.connect(
            lambda: self._delete_row_from_list(row_widget, parent_widget_refs["filters"], filter_refs)
        )

    def _on_filter_criteria_changed(self, filter_refs, initial_value=None):
        """Dynamically changes the filter's value widget based on other selections.

        For example, if the operator is '==' and the field is 'Order_Type',
        this method will create a QComboBox with unique values from the
        DataFrame ('Single', 'Multi') instead of a plain QLineEdit.

        Args:
            filter_refs (dict): A dictionary of widget references for the filter row.
            initial_value (any, optional): The value to set in the newly
                created widget. Defaults to None.
        """
        field = filter_refs["field"].currentText()
        op = filter_refs["op"].currentText()

        if filter_refs["value_widget"]:
            filter_refs["value_widget"].deleteLater()

        use_combobox = op in ["==", "!="] and not self.analysis_df.empty and field in self.analysis_df.columns

        if use_combobox:
            try:
                unique_values = self.analysis_df[field].dropna().unique().tolist()
                unique_values = sorted([str(v) for v in unique_values])
                new_widget = WheelIgnoreComboBox()
                new_widget.addItems(unique_values)
                if initial_value and str(initial_value) in unique_values:
                    new_widget.setCurrentText(str(initial_value))
            except Exception:
                new_widget = QLineEdit()
                new_widget.setText(str(initial_value) if initial_value else "")
        else:
            new_widget = QLineEdit()
            placeholder = "Value"
            if op in ["in", "not in"]:
                placeholder = "Values, comma-separated"
            new_widget.setPlaceholderText(placeholder)
            text_value = ",".join(initial_value) if isinstance(initial_value, list) else (initial_value or "")
            new_widget.setText(str(text_value))

        filter_refs["value_layout"].insertWidget(2, new_widget, 1)
        filter_refs["value_widget"] = new_widget

    def create_stock_exports_tab(self):
        """Creates the 'Stock Exports' tab for managing report configurations."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        add_btn = QPushButton("Add New Stock Export")
        add_btn.clicked.connect(self.add_stock_export_widget)
        main_layout.addWidget(add_btn, 0, Qt.AlignLeft)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)
        scroll_content = QWidget()
        self.stock_exports_layout = QVBoxLayout(scroll_content)
        self.stock_exports_layout.setAlignment(Qt.AlignTop)
        scroll_area.setWidget(scroll_content)
        self.tab_widget.addTab(tab, "Stock Exports")
        for se_config in self.config_data.get("stock_export_configs", []):
            self.add_stock_export_widget(se_config)

    def add_stock_export_widget(self, config=None):
        """Adds a new group of widgets for a single stock export configuration.

        Args:
            config (dict, optional): The configuration for a pre-existing
                stock export. If None, creates a new, blank one.
        """
        if not isinstance(config, dict):
            config = {"name": "", "output_filename": "", "filters": []}
        se_box = QGroupBox()
        se_layout = QVBoxLayout(se_box)
        form_layout = QFormLayout()
        name_edit = QLineEdit(config.get("name", ""))
        filename_edit = QLineEdit(config.get("output_filename", ""))
        form_layout.addRow("Name:", name_edit)
        form_layout.addRow("Output Filename:", filename_edit)
        se_layout.addLayout(form_layout)
        filters_box = QGroupBox("Filters")
        filters_layout = QVBoxLayout(filters_box)
        filters_rows_layout = QVBoxLayout()
        filters_layout.addLayout(filters_rows_layout)
        add_filter_btn = QPushButton("Add Filter")
        filters_layout.addWidget(add_filter_btn, 0, Qt.AlignLeft)
        se_layout.addWidget(filters_box)
        delete_btn = QPushButton("Delete Stock Export")
        se_layout.addWidget(delete_btn, 0, Qt.AlignRight)
        self.stock_exports_layout.addWidget(se_box)
        widget_refs = {
            "group_box": se_box,
            "name": name_edit,
            "filename": filename_edit,
            "filters_layout": filters_rows_layout,
            "filters": [],
        }
        self.stock_export_widgets.append(widget_refs)
        add_filter_btn.clicked.connect(
            lambda: self.add_filter_row(widget_refs, self.FILTERABLE_COLUMNS, self.FILTER_OPERATORS)
        )
        delete_btn.clicked.connect(lambda: self._delete_widget_from_list(widget_refs, self.stock_export_widgets))
        for f_config in config.get("filters", []):
            self.add_filter_row(widget_refs, self.FILTERABLE_COLUMNS, self.FILTER_OPERATORS, f_config)

    def create_mappings_tab(self):
        """Creates the 'Mappings' tab for column mappings and courier mappings."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)

        # Add scroll area for the entire tab
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # ========================================
        # COLUMN MAPPINGS - Orders
        # ========================================
        orders_box = QGroupBox("📋 Orders CSV Column Mapping")
        orders_layout = QVBoxLayout(orders_box)

        # Define required and optional fields for orders
        orders_required = ["Order_Number", "SKU", "Quantity", "Shipping_Method"]
        orders_optional = ["Product_Name", "Shipping_Country", "Tags", "Notes", "Total_Price", "Subtotal"]

        # Get current mappings (v2 format)
        column_mappings = self.config_data.get("column_mappings", {})
        orders_mappings = column_mappings.get("orders", {})

        # Create widget
        self.orders_mapping_widget = ColumnMappingWidget(
            mapping_type="orders",
            current_mappings=orders_mappings,
            required_fields=orders_required,
            optional_fields=orders_optional
        )

        orders_layout.addWidget(self.orders_mapping_widget)
        scroll_layout.addWidget(orders_box)

        # ========================================
        # COLUMN MAPPINGS - Stock
        # ========================================
        stock_box = QGroupBox("📦 Stock CSV Column Mapping")
        stock_layout = QVBoxLayout(stock_box)

        # Define required and optional fields for stock
        stock_required = ["SKU", "Stock"]
        stock_optional = ["Product_Name"]

        # Get current mappings (v2 format)
        stock_mappings = column_mappings.get("stock", {})

        # Create widget
        self.stock_mapping_widget = ColumnMappingWidget(
            mapping_type="stock",
            current_mappings=stock_mappings,
            required_fields=stock_required,
            optional_fields=stock_optional
        )

        stock_layout.addWidget(self.stock_mapping_widget)
        scroll_layout.addWidget(stock_box)

        # ========================================
        # COURIER MAPPINGS
        # ========================================
        courier_mappings_box = QGroupBox("Courier Mappings")
        courier_main_layout = QVBoxLayout(courier_mappings_box)

        instructions2 = QLabel(
            "Map different shipping provider names to standardized courier codes.\n"
            "You can specify multiple patterns (comma-separated) for each courier."
        )
        instructions2.setWordWrap(True)
        instructions2.setStyleSheet("color: gray; font-style: italic; font-size: 10pt;")
        courier_main_layout.addWidget(instructions2)

        # Container for courier mapping rows
        self.courier_mappings_container = QWidget()
        self.courier_mappings_layout = QVBoxLayout(self.courier_mappings_container)
        self.courier_mappings_layout.setContentsMargins(0, 0, 0, 0)

        courier_main_layout.addWidget(self.courier_mappings_container)

        add_courier_btn = QPushButton("+ Add Courier Mapping")
        add_courier_btn.clicked.connect(lambda: self.add_courier_mapping_row())
        courier_main_layout.addWidget(add_courier_btn, 0, Qt.AlignLeft)

        scroll_layout.addWidget(courier_mappings_box)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        self.tab_widget.addTab(tab, "Mappings")

        # Populate existing courier mappings
        courier_mappings = self.config_data.get("courier_mappings", {})
        if isinstance(courier_mappings, dict):
            for courier_code, mapping_data in courier_mappings.items():
                if isinstance(mapping_data, dict):
                    patterns = mapping_data.get("patterns", [])
                    patterns_str = ", ".join(patterns) if patterns else ""
                    self.add_courier_mapping_row(courier_code, patterns_str)

        # Add at least one empty row if no mappings exist
        if not courier_mappings:
            self.add_courier_mapping_row()

    def add_courier_mapping_row(self, courier_code="", patterns_str=""):
        """Adds a new row for a single courier mapping.

        Args:
            courier_code: Standardized courier code (e.g., "DHL", "DPD", "Speedy")
            patterns_str: Comma-separated patterns (e.g., "dhl, dhl express, dhl_express")
        """
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 5, 0, 5)

        # Courier Code
        code_label = QLabel("Code:")
        code_label.setFixedWidth(50)
        courier_edit = QLineEdit(courier_code)
        courier_edit.setPlaceholderText("DHL, DPD, Speedy...")
        courier_edit.setMinimumWidth(100)
        courier_edit.setMaximumWidth(150)

        # Patterns
        patterns_label = QLabel("Patterns:")
        patterns_label.setFixedWidth(70)
        patterns_edit = QLineEdit(patterns_str)
        patterns_edit.setPlaceholderText("dhl, dhl express, dhl_express")
        patterns_edit.setMinimumWidth(300)

        # Delete button
        delete_btn = QPushButton("✕")
        delete_btn.setFixedWidth(30)
        delete_btn.setStyleSheet("color: red; font-weight: bold;")
        delete_btn.setToolTip("Remove this courier mapping")

        row_layout.addWidget(code_label)
        row_layout.addWidget(courier_edit, 1)
        row_layout.addWidget(patterns_label)
        row_layout.addWidget(patterns_edit, 3)
        row_layout.addWidget(delete_btn)
        row_layout.addStretch()

        self.courier_mappings_layout.addWidget(row_widget)

        row_refs = {
            "widget": row_widget,
            "courier_code": courier_edit,
            "patterns": patterns_edit,
        }
        self.courier_mapping_widgets.append(row_refs)

        delete_btn.clicked.connect(
            lambda: self._delete_row_from_list(row_widget, self.courier_mapping_widgets, row_refs)
        )

    # ========================================
    # SETS/BUNDLES TAB
    # ========================================
    def create_sets_tab(self):
        """Create the Sets/Bundles management tab."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header_label = QLabel("🎁 Set/Bundle Definitions")
        header_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        main_layout.addWidget(header_label)

        # Help text
        help_text = QLabel(
            "Define sets/bundles that will be automatically expanded into their component SKUs during analysis.\n"
            "Example: SET-WINTER-KIT → HAT(1x), GLOVES(1x), SCARF(1x)"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: gray; font-style: italic; margin-bottom: 10px;")
        main_layout.addWidget(help_text)

        # Sets table
        self.sets_table = QTableWidget()
        self.sets_table.setColumnCount(3)
        self.sets_table.setHorizontalHeaderLabels(["Set SKU", "Components", "Actions"])

        # Configure columns
        header = self.sets_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Set SKU
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Components
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Actions
        self.sets_table.setColumnWidth(2, 150)

        self.sets_table.setAlternatingRowColors(True)
        self.sets_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        main_layout.addWidget(self.sets_table)

        # Buttons row
        buttons_layout = QHBoxLayout()

        add_btn = QPushButton("➕ Add Set")
        add_btn.clicked.connect(self._add_set_dialog)
        buttons_layout.addWidget(add_btn)

        import_btn = QPushButton("📁 Import from CSV")
        import_btn.clicked.connect(self._import_sets_from_csv)
        buttons_layout.addWidget(import_btn)

        export_btn = QPushButton("💾 Export to CSV")
        export_btn.clicked.connect(self._export_sets_to_csv)
        buttons_layout.addWidget(export_btn)

        buttons_layout.addStretch()

        main_layout.addLayout(buttons_layout)

        # Tips
        tips_label = QLabel(
            "💡 Tips:\n"
            "• CSV format: Set_SKU, Component_SKU, Component_Quantity\n"
            "• Sets are expanded before fulfillment simulation\n"
            "• Components must exist in your stock file"
        )
        tips_label.setStyleSheet("color: #666; font-size: 9pt; margin-top: 10px;")
        tips_label.setWordWrap(True)
        main_layout.addWidget(tips_label)

        self.tab_widget.addTab(tab, "Sets")

        # Populate table with existing sets
        self._populate_sets_table()

    def _populate_sets_table(self):
        """Populate the sets table with current set definitions."""
        set_decoders = self.config_data.get("set_decoders", {})

        self.sets_table.setRowCount(len(set_decoders))

        for row_idx, (set_sku, components) in enumerate(set_decoders.items()):
            # Set SKU column
            sku_item = QTableWidgetItem(set_sku)
            sku_item.setFlags(sku_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Read-only
            self.sets_table.setItem(row_idx, 0, sku_item)

            # Components summary column
            if components:
                # Show first 5 components, then "..."
                comp_summary = ", ".join([
                    f"{comp['sku']}({comp['quantity']}x)"
                    for comp in components[:5]
                ])
                if len(components) > 5:
                    comp_summary += f" ... (+{len(components) - 5} more)"
            else:
                comp_summary = "(no components)"

            comp_item = QTableWidgetItem(comp_summary)
            comp_item.setFlags(comp_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Read-only
            self.sets_table.setItem(row_idx, 1, comp_item)

            # Actions column - Edit and Delete buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 2, 5, 2)
            actions_layout.setSpacing(5)

            edit_btn = QPushButton("✏️ Edit")
            edit_btn.setMaximumWidth(70)
            edit_btn.clicked.connect(lambda checked, sku=set_sku: self._edit_set_dialog(sku))
            actions_layout.addWidget(edit_btn)

            delete_btn = QPushButton("🗑️ Delete")
            delete_btn.setMaximumWidth(70)
            delete_btn.clicked.connect(lambda checked, sku=set_sku: self._delete_set(sku))
            actions_layout.addWidget(delete_btn)

            actions_layout.addStretch()
            self.sets_table.setCellWidget(row_idx, 2, actions_widget)

    def _add_set_dialog(self):
        """Show dialog to add a new set."""
        dialog = SetEditorDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            set_sku, components = dialog.get_set_definition()

            # Debug: print what we got
            print(f"[DEBUG] Adding set '{set_sku}' with {len(components)} components:")
            for i, comp in enumerate(components):
                print(f"  {i+1}. {comp['sku']} x {comp['quantity']}")

            # Add to config
            if "set_decoders" not in self.config_data:
                self.config_data["set_decoders"] = {}

            self.config_data["set_decoders"][set_sku] = components

            # Refresh table
            self._populate_sets_table()

            QMessageBox.information(
                self,
                "Success",
                f"Set '{set_sku}' added with {len(components)} components!"
            )

    def _edit_set_dialog(self, set_sku):
        """Show dialog to edit an existing set."""
        current_components = self.config_data.get("set_decoders", {}).get(set_sku, [])

        dialog = SetEditorDialog(set_sku=set_sku, components=current_components, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_set_sku, new_components = dialog.get_set_definition()

            # Remove old SKU if changed
            if new_set_sku != set_sku:
                del self.config_data["set_decoders"][set_sku]

            # Update with new definition
            self.config_data["set_decoders"][new_set_sku] = new_components

            # Refresh table
            self._populate_sets_table()

            QMessageBox.information(self, "Success", f"Set '{new_set_sku}' updated successfully!")

    def _delete_set(self, set_sku):
        """Delete a set after confirmation."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete set '{set_sku}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.config_data["set_decoders"][set_sku]
            self._populate_sets_table()
            QMessageBox.information(self, "Success", f"Set '{set_sku}' deleted successfully!")

    def _import_sets_from_csv(self):
        """Import sets from CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Sets from CSV",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Import using set_decoder module
            imported_sets = import_sets_from_csv(file_path)

            if not imported_sets:
                QMessageBox.warning(self, "Warning", "No sets found in CSV file.")
                return

            # Ask user: Replace all or Merge
            reply = QMessageBox.question(
                self,
                "Import Mode",
                f"Found {len(imported_sets)} sets in CSV.\n\n"
                "Yes = Replace all existing sets\n"
                "No = Merge (update existing, add new)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Cancel:
                return

            if reply == QMessageBox.StandardButton.Yes:
                # Replace all
                self.config_data["set_decoders"] = imported_sets
            else:
                # Merge
                if "set_decoders" not in self.config_data:
                    self.config_data["set_decoders"] = {}
                self.config_data["set_decoders"].update(imported_sets)

            # Refresh table
            self._populate_sets_table()

            QMessageBox.information(
                self,
                "Success",
                f"Successfully imported {len(imported_sets)} sets from CSV!"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Error",
                f"Failed to import sets from CSV:\n\n{str(e)}"
            )

    def _export_sets_to_csv(self):
        """Export sets to CSV file."""
        set_decoders = self.config_data.get("set_decoders", {})

        if not set_decoders:
            QMessageBox.warning(self, "Warning", "No sets to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Sets to CSV",
            "sets_export.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Export using set_decoder module
            export_sets_to_csv(set_decoders, file_path)

            QMessageBox.information(
                self,
                "Success",
                f"Successfully exported {len(set_decoders)} sets to:\n{file_path}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export sets to CSV:\n\n{str(e)}"
            )

    def save_settings(self):
        """Saves all settings from the UI back into the config dictionary."""
        try:
            # ========================================
            # General Tab - Settings ONLY
            # ========================================
            self.config_data["settings"]["stock_csv_delimiter"] = self.stock_delimiter_edit.text()
            self.config_data["settings"]["orders_csv_delimiter"] = self.orders_delimiter_edit.text()
            self.config_data["settings"]["low_stock_threshold"] = int(self.low_stock_edit.text())
            self.config_data["settings"]["repeat_detection_days"] = self.repeat_days_input.value()

            # ========================================
            # Rules Tab - Line Item Rules
            # ========================================
            new_rules = []
            for rule_w in self.rule_widgets:
                conditions = []
                for c in rule_w["conditions"]:
                    value_widget = c.get("value_widget")
                    val = ""
                    if value_widget:
                        if isinstance(value_widget, QComboBox):
                            val = value_widget.currentText()
                        else:
                            val = value_widget.text()

                    conditions.append({
                        "field": c["field"].currentText(),
                        "operator": c["op"].currentText(),
                        "value": val,
                    })

                actions = [
                    {
                        "type": a["type"].currentText(),
                        "value": a["value"].text()
                    }
                    for a in rule_w["actions"]
                ]

                new_rules.append({
                    "name": rule_w["name_edit"].text(),
                    "level": rule_w["level_combo"].currentText(),
                    "match": rule_w["match_combo"].currentText(),
                    "conditions": conditions,
                    "actions": actions,
                })

            self.config_data["rules"] = new_rules

            # ========================================
            # Packing Lists Tab
            # ========================================
            new_packing_lists = []
            for pl_w in self.packing_list_widgets:
                filters = []
                for f in pl_w["filters"]:
                    value_widget = f.get("value_widget")
                    val = ""
                    if value_widget:
                        if isinstance(value_widget, QComboBox):
                            val = value_widget.currentText()
                        else:
                            val = value_widget.text()

                    filters.append({
                        "field": f["field"].currentText(),
                        "operator": f["op"].currentText(),
                        "value": val,
                    })

                # Parse exclude_skus from comma-separated string
                exclude_skus_text = pl_w["exclude_skus"].text().strip()
                exclude_skus = []
                if exclude_skus_text:
                    exclude_skus = [s.strip() for s in exclude_skus_text.split(',') if s.strip()]

                new_packing_lists.append({
                    "name": pl_w["name"].text(),
                    "output_filename": pl_w["filename"].text(),
                    "filters": filters,
                    "exclude_skus": exclude_skus,
                })

            self.config_data["packing_list_configs"] = new_packing_lists

            # ========================================
            # Stock Exports Tab
            # ========================================
            new_stock_exports = []
            for se_w in self.stock_export_widgets:
                filters = []
                for f in se_w["filters"]:
                    value_widget = f.get("value_widget")
                    val = ""
                    if value_widget:
                        if isinstance(value_widget, QComboBox):
                            val = value_widget.currentText()
                        else:
                            val = value_widget.text()

                    filters.append({
                        "field": f["field"].currentText(),
                        "operator": f["op"].currentText(),
                        "value": val,
                    })

                new_stock_exports.append({
                    "name": se_w["name"].text(),
                    "output_filename": se_w["filename"].text(),
                    "filters": filters,
                })

            self.config_data["stock_export_configs"] = new_stock_exports

            # ========================================
            # Mappings Tab - Column Mappings (v2 format)
            # ========================================
            # Validate mappings before saving
            orders_valid, orders_error = self.orders_mapping_widget.validate_mappings()
            if not orders_valid:
                QMessageBox.warning(
                    self,
                    "Invalid Orders Mapping",
                    f"Orders column mapping is invalid:\n{orders_error}"
                )
                return

            stock_valid, stock_error = self.stock_mapping_widget.validate_mappings()
            if not stock_valid:
                QMessageBox.warning(
                    self,
                    "Invalid Stock Mapping",
                    f"Stock column mapping is invalid:\n{stock_error}"
                )
                return

            # Get mappings from widgets
            orders_mappings = self.orders_mapping_widget.get_mappings()
            stock_mappings = self.stock_mapping_widget.get_mappings()

            # Save in v2 format
            self.config_data["column_mappings"] = {
                "version": 2,
                "orders": orders_mappings,
                "stock": stock_mappings
            }

            # ========================================
            # Mappings Tab - Courier Mappings
            # ========================================
            self.config_data["courier_mappings"] = {}

            for row_refs in self.courier_mapping_widgets:
                courier_code = row_refs["courier_code"].text().strip()
                patterns_str = row_refs["patterns"].text().strip()

                if courier_code and patterns_str:
                    # Parse comma-separated patterns
                    patterns = [
                        p.strip()
                        for p in patterns_str.split(',')
                        if p.strip()
                    ]

                    self.config_data["courier_mappings"][courier_code] = {
                        "patterns": patterns,
                        "case_sensitive": False
                    }

            # ========================================
            # Save to server via ProfileManager
            # ========================================
            success = self.profile_manager.save_shopify_config(
                self.client_id,
                self.config_data
            )

            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    "Settings saved successfully!"
                )
                self.accept()  # Close dialog
            else:
                # Calculate config size for diagnostic info
                import json
                config_size = len(json.dumps(self.config_data, ensure_ascii=False))
                num_sets = len(self.config_data.get("set_decoders", {}))

                QMessageBox.critical(
                    self,
                    "Save Error",
                    f"Failed to save settings to server.\n\n"
                    f"Configuration size: {config_size:,} bytes\n"
                    f"Number of sets: {num_sets}\n\n"
                    f"Possible causes:\n"
                    f"• File is locked by another user\n"
                    f"• Network connection issue\n"
                    f"• Insufficient permissions\n\n"
                    f"Please wait a few seconds and try again."
                )

        except ValueError as e:
            QMessageBox.critical(
                self,
                "Validation Error",
                f"Invalid value entered:\n\n{str(e)}\n\nPlease check your inputs."
            )
        except Exception as e:
            import traceback
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save settings:\n\n{str(e)}\n\n{traceback.format_exc()}"
            )


# ========================================
# SetEditorDialog - Dialog for adding/editing set definitions
# ========================================
class SetEditorDialog(QDialog):
    """Dialog for adding or editing a set/bundle definition."""

    def __init__(self, set_sku=None, components=None, parent=None):
        """
        Initialize the Set Editor Dialog.

        Args:
            set_sku: Set SKU (None for new set, or existing SKU for edit)
            components: List of components (for edit mode)
            parent: Parent widget
        """
        super().__init__(parent)

        self.setWindowTitle("Add Set" if set_sku is None else f"Edit Set: {set_sku}")
        self.setMinimumSize(600, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Set SKU input
        sku_layout = QFormLayout()
        self.set_sku_edit = QLineEdit(set_sku or "")
        self.set_sku_edit.setPlaceholderText("e.g., SET-WINTER-KIT")
        sku_layout.addRow("Set SKU:", self.set_sku_edit)
        layout.addLayout(sku_layout)

        # Components table
        components_label = QLabel("Components:")
        components_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(components_label)

        self.components_table = QTableWidget()
        self.components_table.setColumnCount(3)
        self.components_table.setHorizontalHeaderLabels(["Component SKU", "Quantity", "Remove"])

        # Configure columns
        header = self.components_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Component SKU
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # Quantity
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Remove
        self.components_table.setColumnWidth(1, 100)
        self.components_table.setColumnWidth(2, 80)

        layout.addWidget(self.components_table)

        # Add component button
        add_comp_btn = QPushButton("+ Add Component")
        # Use lambda to avoid passing 'checked' bool as first argument
        add_comp_btn.clicked.connect(lambda: self._add_component_row())
        layout.addWidget(add_comp_btn)

        # Populate with existing components if provided
        if components:
            for comp in components:
                self._add_component_row(comp.get("sku", ""), comp.get("quantity", 1))
        else:
            # Add one empty row for new sets
            self._add_component_row()

        # Tips
        tips_label = QLabel(
            "💡 Tip: Components are SKUs that exist in your stock file.\n"
            "Quantity indicates how many of each component are in one set."
        )
        tips_label.setStyleSheet("color: gray; font-style: italic; font-size: 9pt; margin-top: 10px;")
        tips_label.setWordWrap(True)
        layout.addWidget(tips_label)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._validate_and_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _add_component_row(self, sku="", quantity=1):
        """Add a new row to the components table."""
        # Protection: if sku is bool (from button clicked signal), convert to empty string
        if isinstance(sku, bool):
            sku = ""

        row_idx = self.components_table.rowCount()
        self.components_table.insertRow(row_idx)

        # Component SKU
        sku_edit = QLineEdit(str(sku))  # Ensure it's a string
        sku_edit.setPlaceholderText("e.g., HAT-001")
        self.components_table.setCellWidget(row_idx, 0, sku_edit)

        # Quantity
        qty_spinbox = QSpinBox()
        qty_spinbox.setMinimum(1)
        qty_spinbox.setMaximum(9999)
        qty_spinbox.setValue(quantity)
        self.components_table.setCellWidget(row_idx, 1, qty_spinbox)

        # Remove button - використовуємо sender() щоб знайти правильний row
        remove_btn = QPushButton("🗑️")
        remove_btn.setMaximumWidth(60)
        remove_btn.clicked.connect(self._remove_component_row)
        self.components_table.setCellWidget(row_idx, 2, remove_btn)

    def _remove_component_row(self):
        """Remove a component row from the table."""
        # Знаходимо який button викликав цю функцію
        button = self.sender()
        if button:
            # Знаходимо row index цієї кнопки в таблиці
            for row in range(self.components_table.rowCount()):
                if self.components_table.cellWidget(row, 2) == button:
                    self.components_table.removeRow(row)
                    break

    def _validate_and_save(self):
        """Validate inputs and accept dialog if valid."""
        # Validate Set SKU
        set_sku = self.set_sku_edit.text().strip()
        if not set_sku:
            QMessageBox.warning(self, "Validation Error", "Set SKU cannot be empty!")
            return

        # Validate components
        components = []
        for row in range(self.components_table.rowCount()):
            sku_widget = self.components_table.cellWidget(row, 0)
            qty_widget = self.components_table.cellWidget(row, 1)

            if sku_widget and qty_widget:
                comp_sku = sku_widget.text().strip()
                comp_qty = qty_widget.value()

                if comp_sku:  # Only add non-empty SKUs
                    components.append({
                        "sku": comp_sku,
                        "quantity": comp_qty
                    })

        if not components:
            QMessageBox.warning(self, "Validation Error", "Set must have at least one component!")
            return

        # All valid, accept dialog
        self.accept()

    def get_set_definition(self):
        """
        Get the set definition from the dialog.

        Returns:
            Tuple of (set_sku, components_list)
        """
        set_sku = self.set_sku_edit.text().strip()
        components = []

        print(f"[DEBUG] get_set_definition: Reading {self.components_table.rowCount()} rows from table")

        for row in range(self.components_table.rowCount()):
            sku_widget = self.components_table.cellWidget(row, 0)
            qty_widget = self.components_table.cellWidget(row, 1)

            if sku_widget and qty_widget:
                comp_sku = sku_widget.text().strip()
                comp_qty = qty_widget.value()

                print(f"[DEBUG]   Row {row}: SKU='{comp_sku}', Qty={comp_qty}, Empty={not bool(comp_sku)}")

                if comp_sku:
                    components.append({
                        "sku": comp_sku,
                        "quantity": comp_qty
                    })
            else:
                print(f"[DEBUG]   Row {row}: widgets are None (sku_widget={sku_widget}, qty_widget={qty_widget})")

        print(f"[DEBUG] get_set_definition: Collected {len(components)} non-empty components")
        return set_sku, components


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dummy_config = {
        "settings": {"stock_csv_delimiter": ";", "low_stock_threshold": 5},
        "paths": {"templates": "data/templates", "output_dir_stock": "data/output"},
        "rules": [
            {
                "name": "Test Rule",
                "match": "ANY",
                "conditions": [{"field": "SKU", "operator": "contains", "value": "TEST"}],
                "actions": [{"type": "ADD_TAG", "value": "auto_tagged"}],
            }
        ],
        "packing_lists": [
            {
                "name": "Test PL",
                "output_filename": "test.xlsx",
                "filters": [{"field": "Order_Type", "operator": "==", "value": "Single"}],
                "exclude_skus": ["SKU1"],
            }
        ],
        "stock_exports": [
            {
                "name": "Test SE",
                "template": "template.xls",
                "filters": [{"field": "Shipping_Provider", "operator": "==", "value": "DHL"}],
            }
        ],
    }
    dialog = SettingsWindow(None, dummy_config)
    if dialog.exec():
        print("Settings saved:", json.dumps(dialog.config_data, indent=2))
    else:
        print("Cancelled.")
    sys.exit(0)
