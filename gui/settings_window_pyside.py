import sys
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
)
from PySide6.QtCore import Qt

from shopify_tool.core import get_unique_column_values


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
    CONDITION_FIELDS = FILTERABLE_COLUMNS
    CONDITION_OPERATORS = [
        "equals",
        "does not equal",
        "contains",
        "does not contain",
        "is greater than",
        "is less than",
        "starts with",
        "ends with",
        "is empty",
        "is not empty",
    ]
    ACTION_TYPES = ["ADD_TAG", "SET_STATUS", "SET_PRIORITY", "EXCLUDE_FROM_REPORT", "EXCLUDE_SKU"]

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

        # Ensure order_rules exists
        if "order_rules" not in self.config_data:
            self.config_data["order_rules"] = []

        if "packing_list_configs" not in self.config_data:
            self.config_data["packing_list_configs"] = []

        if "stock_export_configs" not in self.config_data:
            self.config_data["stock_export_configs"] = []

        # Widget lists (existing + NEW)
        self.rule_widgets = []
        self.order_rule_widgets = []  # NEW
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
        self.create_order_rules_tab()  # NEW TAB
        self.create_packing_lists_tab()
        self.create_stock_exports_tab()
        self.create_mappings_tab()

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
            config = {"name": "New Rule", "match": "ALL", "conditions": [], "actions": []}
        rule_box = QGroupBox()
        rule_layout = QVBoxLayout(rule_box)
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Rule Name:"))
        name_edit = QLineEdit(config.get("name", ""))
        header_layout.addWidget(name_edit)
        delete_rule_btn = QPushButton("Delete Rule")
        header_layout.addWidget(delete_rule_btn)
        rule_layout.addLayout(header_layout)
        conditions_box = QGroupBox("IF")
        conditions_layout = QVBoxLayout(conditions_box)
        match_layout = QHBoxLayout()
        match_layout.addWidget(QLabel("Execute actions if"))
        match_combo = QComboBox()
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
        field_combo = QComboBox()
        field_combo.addItems(self.CONDITION_FIELDS)
        op_combo = QComboBox()
        op_combo.addItems(self.CONDITION_OPERATORS)
        delete_btn = QPushButton("X")

        row_layout.addWidget(field_combo)
        row_layout.addWidget(op_combo)
        # The value widget will be inserted at index 2 by the handler

        field_combo.setCurrentText(config.get("field", self.CONDITION_FIELDS[0]))
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
            new_widget = QComboBox()
            new_widget.addItems([""] + unique_values)  # Add a blank option
            if initial_value and str(initial_value) in unique_values:
                new_widget.setCurrentText(str(initial_value))
        else:
            # Default to QLineEdit
            new_widget = QLineEdit()
            new_widget.setPlaceholderText("Value")
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
        type_combo = QComboBox()
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

    def create_order_rules_tab(self):
        """Creates the 'Order Rules' tab for order-level automation rules.

        Order rules work on entire orders (not line items).
        Useful for tagging, prioritizing, or filtering orders based on order-level criteria.
        """
        tab = QWidget()
        main_layout = QVBoxLayout(tab)

        # Instructions
        instructions = QLabel(
            "Order Rules apply to entire orders (not individual line items).\n"
            "Use these for order-level decisions like tagging, prioritizing, or excluding orders."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: gray; font-style: italic; font-size: 10pt;")
        main_layout.addWidget(instructions)

        # Scroll area for rules
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        scroll_widget = QWidget()
        self.order_rules_layout = QVBoxLayout(scroll_widget)
        scroll.setWidget(scroll_widget)

        main_layout.addWidget(scroll)

        # Add Rule button
        add_rule_btn = QPushButton("+ Add Order Rule")
        add_rule_btn.clicked.connect(lambda: self.add_order_rule_widget())
        main_layout.addWidget(add_rule_btn, 0, Qt.AlignLeft)

        self.tab_widget.addTab(tab, "Order Rules")

        # Populate existing order rules
        for rule_config in self.config_data.get("order_rules", []):
            self.add_order_rule_widget(rule_config)

    def add_order_rule_widget(self, config=None):
        """Adds a new order rule widget.

        Order rules have the same structure as regular rules but work on order level.

        Args:
            config (dict, optional): Existing rule configuration to load
        """
        if not isinstance(config, dict):
            config = {
                "name": "New Order Rule",
                "match": "ALL",
                "conditions": [],
                "actions": []
            }

        # Create rule box
        rule_box = QGroupBox()
        rule_layout = QVBoxLayout(rule_box)

        # Header with name and delete button
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Rule Name:"))

        name_edit = QLineEdit(config.get("name", ""))
        name_edit.setPlaceholderText("E.g., 'High Value Orders', 'Express Shipping'")
        header_layout.addWidget(name_edit, 1)

        delete_rule_btn = QPushButton("Delete Rule")
        delete_rule_btn.setStyleSheet("color: red;")
        header_layout.addWidget(delete_rule_btn)

        rule_layout.addLayout(header_layout)

        # Conditions section
        conditions_box = QGroupBox("IF")
        conditions_layout = QVBoxLayout(conditions_box)

        match_layout = QHBoxLayout()
        match_layout.addWidget(QLabel("Execute actions if"))

        match_combo = QComboBox()
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

        # Actions section
        actions_box = QGroupBox("THEN perform these actions:")
        actions_layout = QVBoxLayout(actions_box)

        actions_rows_layout = QVBoxLayout()
        actions_layout.addLayout(actions_rows_layout)

        add_action_btn = QPushButton("Add Action")
        actions_layout.addWidget(add_action_btn, 0, Qt.AlignLeft)

        rule_layout.addWidget(actions_box)

        # Add to layout
        self.order_rules_layout.addWidget(rule_box)

        # Store widget references
        widget_refs = {
            "group_box": rule_box,
            "name_edit": name_edit,
            "match_combo": match_combo,
            "conditions_layout": conditions_rows_layout,
            "actions_layout": actions_rows_layout,
            "conditions": [],
            "actions": [],
        }
        self.order_rule_widgets.append(widget_refs)

        # Connect buttons
        add_condition_btn.clicked.connect(lambda: self.add_condition_row(widget_refs))
        add_action_btn.clicked.connect(lambda: self.add_action_row(widget_refs))
        delete_rule_btn.clicked.connect(
            lambda: self._delete_widget_from_list(widget_refs, self.order_rule_widgets)
        )

        # Populate existing conditions and actions
        for cond_config in config.get("conditions", []):
            self.add_condition_row(widget_refs, cond_config)
        for act_config in config.get("actions", []):
            self.add_action_row(widget_refs, act_config)

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
        for pl_config in self.config_data.get("packing_lists", []):
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
        field_combo = QComboBox()
        field_combo.addItems(fields)
        op_combo = QComboBox()
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
                new_widget = QComboBox()
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
        for se_config in self.config_data.get("stock_exports", []):
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
        """Creates the 'Mappings' tab for required columns and courier mappings."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)

        # Add scroll area for the entire tab
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # ========================================
        # COLUMN MAPPINGS - Required Columns
        # ========================================
        column_mappings_box = QGroupBox("Required Columns")
        column_mappings_layout = QVBoxLayout(column_mappings_box)

        instructions = QLabel(
            "Specify which columns are required in the CSV files.\n"
            "These columns will be validated when loading files."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: gray; font-style: italic; font-size: 10pt;")
        column_mappings_layout.addWidget(instructions)

        # Orders Required Columns
        orders_box = QGroupBox("Orders CSV - Required Columns")
        orders_layout = QVBoxLayout(orders_box)

        orders_label = QLabel("Enter column names (one per line):")
        orders_layout.addWidget(orders_label)

        self.orders_required_text = QTextEdit()
        self.orders_required_text.setPlaceholderText("Name\nLineitem sku\nLineitem quantity\nShipping Method")
        self.orders_required_text.setMaximumHeight(120)

        # Load existing values
        orders_required = self.config_data.get("column_mappings", {}).get("orders_required", [])
        if orders_required:
            self.orders_required_text.setPlainText("\n".join(orders_required))

        orders_layout.addWidget(self.orders_required_text)
        column_mappings_layout.addWidget(orders_box)

        # Stock Required Columns
        stock_box = QGroupBox("Stock CSV - Required Columns")
        stock_layout = QVBoxLayout(stock_box)

        stock_label = QLabel("Enter column names (one per line):")
        stock_layout.addWidget(stock_label)

        self.stock_required_text = QTextEdit()
        self.stock_required_text.setPlaceholderText("Артикул\nНаличност")
        self.stock_required_text.setMaximumHeight(120)

        # Load existing values
        stock_required = self.config_data.get("column_mappings", {}).get("stock_required", [])
        if stock_required:
            self.stock_required_text.setPlainText("\n".join(stock_required))

        stock_layout.addWidget(self.stock_required_text)
        column_mappings_layout.addWidget(stock_box)

        scroll_layout.addWidget(column_mappings_box)

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

    def save_settings(self):
        """Saves all settings from the UI back into the config dictionary."""
        try:
            # ========================================
            # General Tab - Settings ONLY
            # ========================================
            self.config_data["settings"]["stock_csv_delimiter"] = self.stock_delimiter_edit.text()
            self.config_data["settings"]["low_stock_threshold"] = int(self.low_stock_edit.text())

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
                    "match": rule_w["match_combo"].currentText(),
                    "conditions": conditions,
                    "actions": actions,
                })

            self.config_data["rules"] = new_rules

            # ========================================
            # Order Rules Tab - Order-Level Rules
            # ========================================
            new_order_rules = []
            for rule_w in self.order_rule_widgets:
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

                new_order_rules.append({
                    "name": rule_w["name_edit"].text(),
                    "match": rule_w["match_combo"].currentText(),
                    "conditions": conditions,
                    "actions": actions,
                })

            self.config_data["order_rules"] = new_order_rules

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

                new_packing_lists.append({
                    "name": pl_w["name"].text(),
                    "output_filename": pl_w["filename"].text(),
                    "filters": filters,
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
            # Mappings Tab - Column Mappings
            # ========================================
            self.config_data["column_mappings"] = {
                "orders_required": [],
                "stock_required": []
            }

            # Parse orders required columns
            orders_text = self.orders_required_text.toPlainText().strip()
            if orders_text:
                orders_columns = [
                    line.strip()
                    for line in orders_text.split('\n')
                    if line.strip()
                ]
                self.config_data["column_mappings"]["orders_required"] = orders_columns

            # Parse stock required columns
            stock_text = self.stock_required_text.toPlainText().strip()
            if stock_text:
                stock_columns = [
                    line.strip()
                    for line in stock_text.split('\n')
                    if line.strip()
                ]
                self.config_data["column_mappings"]["stock_required"] = stock_columns

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
                QMessageBox.critical(
                    self,
                    "Save Error",
                    "Failed to save settings to server.\nPlease check server connection."
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
