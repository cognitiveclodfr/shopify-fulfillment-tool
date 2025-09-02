import sys
import json
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QVBoxLayout, QTabWidget,
    QWidget, QFormLayout, QLabel, QLineEdit, QMessageBox, QScrollArea,
    QGroupBox, QHBoxLayout, QPushButton, QComboBox, QFrame
)
from PySide6.QtCore import Qt

class SettingsWindow(QDialog):
    # Constants for builders
    FILTERABLE_COLUMNS = [
        'Order_Number', 'Order_Type', 'SKU', 'Product_Name', 'Stock_Alert',
        'Order_Fulfillment_Status', 'Shipping_Provider', 'Destination_Country',
        'Tags', 'System_note', 'Status_Note', 'Total Price'
    ]
    FILTER_OPERATORS = ['==', '!=', 'in', 'not in']
    CONDITION_FIELDS = FILTERABLE_COLUMNS
    CONDITION_OPERATORS = [
        'equals', 'does not equal', 'contains', 'does not contain',
        'is greater than', 'is less than', 'starts with', 'ends with',
        'is empty', 'is not empty'
    ]
    ACTION_TYPES = [
        'ADD_TAG', 'SET_STATUS', 'SET_PRIORITY',
        'EXCLUDE_FROM_REPORT', 'EXCLUDE_SKU'
    ]

    def __init__(self, parent, config):
        super().__init__(parent)
        self.parent = parent
        self.config_data = json.loads(json.dumps(config))
        self.rule_widgets = []
        self.packing_list_widgets = []
        self.stock_export_widgets = []

        self.setWindowTitle("Application Settings")
        self.setMinimumSize(800, 700)
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.create_general_tab()
        self.create_rules_tab()
        self.create_packing_lists_tab()
        self.create_stock_exports_tab()

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    # Generic helper to delete a widget and its reference from a list
    def _delete_widget_from_list(self, widget_refs, ref_list):
        widget_refs['group_box'].deleteLater()
        ref_list.remove(widget_refs)

    # Generic helper to delete a row widget and its reference from a list
    def _delete_row_from_list(self, row_widget, ref_list, ref_dict):
        row_widget.deleteLater()
        ref_list.remove(ref_dict)

    def create_general_tab(self):
        tab = QWidget(); layout = QFormLayout(tab)
        self.stock_delimiter_edit = QLineEdit(); self.low_stock_edit = QLineEdit()
        self.templates_path_edit = QLineEdit(); self.stock_output_path_edit = QLineEdit()
        layout.addRow(QLabel("Stock CSV Delimiter:"), self.stock_delimiter_edit)
        layout.addRow(QLabel("Low Stock Threshold:"), self.low_stock_edit)
        layout.addRow(QLabel("Templates Directory:"), self.templates_path_edit)
        layout.addRow(QLabel("Stock Export Output Directory:"), self.stock_output_path_edit)
        settings = self.config_data.get('settings', {}); paths = self.config_data.get('paths', {})
        self.stock_delimiter_edit.setText(settings.get('stock_csv_delimiter', ';'))
        self.low_stock_edit.setText(str(settings.get('low_stock_threshold', 10)))
        self.templates_path_edit.setText(paths.get('templates', ''))
        self.stock_output_path_edit.setText(paths.get('output_dir_stock', ''))
        self.tab_widget.addTab(tab, "General & Paths")

    def create_rules_tab(self):
        tab = QWidget(); main_layout = QVBoxLayout(tab)
        add_rule_btn = QPushButton("Add New Rule"); add_rule_btn.clicked.connect(self.add_rule_widget)
        main_layout.addWidget(add_rule_btn, 0, Qt.AlignLeft)
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True); main_layout.addWidget(scroll_area)
        scroll_content = QWidget(); self.rules_layout = QVBoxLayout(scroll_content)
        self.rules_layout.setAlignment(Qt.AlignTop); scroll_area.setWidget(scroll_content)
        self.tab_widget.addTab(tab, "Rules")
        for rule_config in self.config_data.get('rules', []):
            self.add_rule_widget(rule_config)

    def add_rule_widget(self, config=None):
        if config is None: config = {"name": "New Rule", "match": "ALL", "conditions": [], "actions": []}
        rule_box = QGroupBox(); rule_layout = QVBoxLayout(rule_box)
        header_layout = QHBoxLayout(); header_layout.addWidget(QLabel("Rule Name:"))
        name_edit = QLineEdit(config.get('name', '')); header_layout.addWidget(name_edit)
        delete_rule_btn = QPushButton("Delete Rule"); header_layout.addWidget(delete_rule_btn)
        rule_layout.addLayout(header_layout)
        conditions_box = QGroupBox("IF"); conditions_layout = QVBoxLayout(conditions_box)
        match_layout = QHBoxLayout(); match_layout.addWidget(QLabel("Execute actions if"))
        match_combo = QComboBox(); match_combo.addItems(["ALL", "ANY"]); match_combo.setCurrentText(config.get('match', 'ALL'))
        match_layout.addWidget(match_combo); match_layout.addWidget(QLabel("of the following conditions are met:")); match_layout.addStretch()
        conditions_layout.addLayout(match_layout)
        conditions_rows_layout = QVBoxLayout(); conditions_layout.addLayout(conditions_rows_layout)
        add_condition_btn = QPushButton("Add Condition"); conditions_layout.addWidget(add_condition_btn, 0, Qt.AlignLeft)
        rule_layout.addWidget(conditions_box)
        actions_box = QGroupBox("THEN perform these actions:"); actions_layout = QVBoxLayout(actions_box)
        actions_rows_layout = QVBoxLayout(); actions_layout.addLayout(actions_rows_layout)
        add_action_btn = QPushButton("Add Action"); actions_layout.addWidget(add_action_btn, 0, Qt.AlignLeft)
        rule_layout.addWidget(actions_box)
        self.rules_layout.addWidget(rule_box)
        widget_refs = {'group_box': rule_box, 'name_edit': name_edit, 'match_combo': match_combo, 'conditions_layout': conditions_rows_layout, 'actions_layout': actions_rows_layout, 'conditions': [], 'actions': []}
        self.rule_widgets.append(widget_refs)
        add_condition_btn.clicked.connect(lambda: self.add_condition_row(widget_refs))
        add_action_btn.clicked.connect(lambda: self.add_action_row(widget_refs))
        delete_rule_btn.clicked.connect(lambda: self._delete_widget_from_list(widget_refs, self.rule_widgets))
        for cond_config in config.get('conditions', []): self.add_condition_row(widget_refs, cond_config)
        for act_config in config.get('actions', []): self.add_action_row(widget_refs, act_config)

    def add_condition_row(self, rule_widget_refs, config=None):
        if config is None: config = {}
        row_layout = QHBoxLayout(); field_combo = QComboBox(); field_combo.addItems(self.CONDITION_FIELDS)
        op_combo = QComboBox(); op_combo.addItems(self.CONDITION_OPERATORS); value_edit = QLineEdit(); delete_btn = QPushButton("X")
        row_layout.addWidget(field_combo); row_layout.addWidget(op_combo); row_layout.addWidget(value_edit, 1); row_layout.addWidget(delete_btn)
        field_combo.setCurrentText(config.get('field', self.CONDITION_FIELDS[0])); op_combo.setCurrentText(config.get('operator', self.CONDITION_OPERATORS[0])); value_edit.setText(config.get('value', ''))
        row_widget = QWidget(); row_widget.setLayout(row_layout); rule_widget_refs['conditions_layout'].addWidget(row_widget)
        condition_refs = {'widget': row_widget, 'field': field_combo, 'op': op_combo, 'value': value_edit}
        rule_widget_refs['conditions'].append(condition_refs)
        delete_btn.clicked.connect(lambda: self._delete_row_from_list(row_widget, rule_widget_refs['conditions'], condition_refs))

    def add_action_row(self, rule_widget_refs, config=None):
        if config is None: config = {}
        row_layout = QHBoxLayout(); type_combo = QComboBox(); type_combo.addItems(self.ACTION_TYPES)
        value_edit = QLineEdit(); delete_btn = QPushButton("X")
        row_layout.addWidget(type_combo); row_layout.addWidget(value_edit, 1); row_layout.addWidget(delete_btn)
        type_combo.setCurrentText(config.get('type', self.ACTION_TYPES[0])); value_edit.setText(config.get('value', ''))
        row_widget = QWidget(); row_widget.setLayout(row_layout); rule_widget_refs['actions_layout'].addWidget(row_widget)
        action_refs = {'widget': row_widget, 'type': type_combo, 'value': value_edit}
        rule_widget_refs['actions'].append(action_refs)
        delete_btn.clicked.connect(lambda: self._delete_row_from_list(row_widget, rule_widget_refs['actions'], action_refs))

    def create_packing_lists_tab(self):
        tab = QWidget(); main_layout = QVBoxLayout(tab)
        add_btn = QPushButton("Add New Packing List"); add_btn.clicked.connect(self.add_packing_list_widget)
        main_layout.addWidget(add_btn, 0, Qt.AlignLeft)
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True); main_layout.addWidget(scroll_area)
        scroll_content = QWidget(); self.packing_lists_layout = QVBoxLayout(scroll_content)
        self.packing_lists_layout.setAlignment(Qt.AlignTop); scroll_area.setWidget(scroll_content)
        self.tab_widget.addTab(tab, "Packing Lists")
        for pl_config in self.config_data.get('packing_lists', []):
            self.add_packing_list_widget(pl_config)

    def add_packing_list_widget(self, config=None):
        if config is None: config = {"name": "", "output_filename": "", "filters": [], "exclude_skus": []}
        pl_box = QGroupBox(); pl_layout = QVBoxLayout(pl_box)
        form_layout = QFormLayout()
        name_edit = QLineEdit(config.get('name', '')); filename_edit = QLineEdit(config.get('output_filename', ''))
        exclude_skus_edit = QLineEdit(",".join(config.get('exclude_skus', [])))
        form_layout.addRow("Name:", name_edit); form_layout.addRow("Output Filename:", filename_edit)
        form_layout.addRow("Exclude SKUs (comma-separated):", exclude_skus_edit)
        pl_layout.addLayout(form_layout)
        filters_box = QGroupBox("Filters"); filters_layout = QVBoxLayout(filters_box)
        filters_rows_layout = QVBoxLayout(); filters_layout.addLayout(filters_rows_layout)
        add_filter_btn = QPushButton("Add Filter"); filters_layout.addWidget(add_filter_btn, 0, Qt.AlignLeft)
        pl_layout.addWidget(filters_box)
        delete_btn = QPushButton("Delete Packing List"); pl_layout.addWidget(delete_btn, 0, Qt.AlignRight)
        self.packing_lists_layout.addWidget(pl_box)
        widget_refs = {'group_box': pl_box, 'name': name_edit, 'filename': filename_edit, 'exclude_skus': exclude_skus_edit, 'filters_layout': filters_rows_layout, 'filters': []}
        self.packing_list_widgets.append(widget_refs)
        add_filter_btn.clicked.connect(lambda: self.add_filter_row(widget_refs, self.FILTERABLE_COLUMNS, self.FILTER_OPERATORS))
        delete_btn.clicked.connect(lambda: self._delete_widget_from_list(widget_refs, self.packing_list_widgets))
        for f_config in config.get('filters', []): self.add_filter_row(widget_refs, self.FILTERABLE_COLUMNS, self.FILTER_OPERATORS, f_config)

    def add_filter_row(self, parent_widget_refs, fields, operators, config=None):
        if config is None: config = {}
        row_layout = QHBoxLayout(); field_combo = QComboBox(); field_combo.addItems(fields)
        op_combo = QComboBox(); op_combo.addItems(operators); value_edit = QLineEdit(); delete_btn = QPushButton("X")
        row_layout.addWidget(field_combo); row_layout.addWidget(op_combo); row_layout.addWidget(value_edit, 1); row_layout.addWidget(delete_btn)
        field_combo.setCurrentText(config.get('field', fields[0])); op_combo.setCurrentText(config.get('operator', operators[0]))
        val = config.get('value', '')
        value_edit.setText(",".join(val) if isinstance(val, list) else val)
        row_widget = QWidget(); row_widget.setLayout(row_layout); parent_widget_refs['filters_layout'].addWidget(row_widget)
        filter_refs = {'widget': row_widget, 'field': field_combo, 'op': op_combo, 'value': value_edit}
        parent_widget_refs['filters'].append(filter_refs)
        delete_btn.clicked.connect(lambda: self._delete_row_from_list(row_widget, parent_widget_refs['filters'], filter_refs))

    def create_stock_exports_tab(self):
        tab = QWidget(); main_layout = QVBoxLayout(tab)
        add_btn = QPushButton("Add New Stock Export"); add_btn.clicked.connect(self.add_stock_export_widget)
        main_layout.addWidget(add_btn, 0, Qt.AlignLeft)
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True); main_layout.addWidget(scroll_area)
        scroll_content = QWidget(); self.stock_exports_layout = QVBoxLayout(scroll_content)
        self.stock_exports_layout.setAlignment(Qt.AlignTop); scroll_area.setWidget(scroll_content)
        self.tab_widget.addTab(tab, "Stock Exports")
        for se_config in self.config_data.get('stock_exports', []):
            self.add_stock_export_widget(se_config)

    def add_stock_export_widget(self, config=None):
        if config is None: config = {"name": "", "template": "", "filters": []}
        se_box = QGroupBox(); se_layout = QVBoxLayout(se_box)
        form_layout = QFormLayout()
        name_edit = QLineEdit(config.get('name', '')); template_edit = QLineEdit(config.get('template', ''))
        form_layout.addRow("Name:", name_edit); form_layout.addRow("Template Filename:", template_edit)
        se_layout.addLayout(form_layout)
        filters_box = QGroupBox("Filters"); filters_layout = QVBoxLayout(filters_box)
        filters_rows_layout = QVBoxLayout(); filters_layout.addLayout(filters_rows_layout)
        add_filter_btn = QPushButton("Add Filter"); filters_layout.addWidget(add_filter_btn, 0, Qt.AlignLeft)
        se_layout.addWidget(filters_box)
        delete_btn = QPushButton("Delete Stock Export"); se_layout.addWidget(delete_btn, 0, Qt.AlignRight)
        self.stock_exports_layout.addWidget(se_box)
        widget_refs = {'group_box': se_box, 'name': name_edit, 'template': template_edit, 'filters_layout': filters_rows_layout, 'filters': []}
        self.stock_export_widgets.append(widget_refs)
        add_filter_btn.clicked.connect(lambda: self.add_filter_row(widget_refs, self.FILTERABLE_COLUMNS, self.FILTER_OPERATORS))
        delete_btn.clicked.connect(lambda: self._delete_widget_from_list(widget_refs, self.stock_export_widgets))
        for f_config in config.get('filters', []): self.add_filter_row(widget_refs, self.FILTERABLE_COLUMNS, self.FILTER_OPERATORS, f_config)

    def save_settings(self):
        try:
            # General Tab
            self.config_data['settings']['stock_csv_delimiter'] = self.stock_delimiter_edit.text()
            self.config_data['settings']['low_stock_threshold'] = int(self.low_stock_edit.text())
            self.config_data['paths']['templates'] = self.templates_path_edit.text()
            self.config_data['paths']['output_dir_stock'] = self.stock_output_path_edit.text()

            # Rules Tab
            new_rules = []
            for rule_w in self.rule_widgets:
                conditions = [{'field': c['field'].currentText(), 'operator': c['op'].currentText(), 'value': c['value'].text()} for c in rule_w['conditions']]
                actions = [{'type': a['type'].currentText(), 'value': a['value'].text()} for a in rule_w['actions']]
                new_rules.append({'name': rule_w['name_edit'].text(), 'match': rule_w['match_combo'].currentText(), 'conditions': conditions, 'actions': actions})
            self.config_data['rules'] = new_rules

            # Packing Lists Tab
            new_pls = []
            for pl_w in self.packing_list_widgets:
                filters = []
                for f in pl_w['filters']:
                    val = f['value'].text(); op = f['op'].currentText()
                    filters.append({'field': f['field'].currentText(), 'operator': op, 'value': [v.strip() for v in val.split(',')] if op in ['in', 'not in'] else val})
                exclude_skus = [sku.strip() for sku in pl_w['exclude_skus'].text().split(',') if sku.strip()]
                new_pls.append({'name': pl_w['name'].text(), 'output_filename': pl_w['filename'].text(), 'filters': filters, 'exclude_skus': exclude_skus})
            self.config_data['packing_lists'] = new_pls

            # Stock Exports Tab
            new_ses = []
            for se_w in self.stock_export_widgets:
                filters = []
                for f in se_w['filters']:
                    val = f['value'].text(); op = f['op'].currentText()
                    filters.append({'field': f['field'].currentText(), 'operator': op, 'value': [v.strip() for v in val.split(',')] if op in ['in', 'not in'] else val})
                new_ses.append({'name': se_w['name'].text(), 'template': se_w['template'].text(), 'filters': filters})
            self.config_data['stock_exports'] = new_ses

            self.accept()
        except ValueError:
            QMessageBox.critical(self, "Validation Error", "Low Stock Threshold must be a valid number.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dummy_config = {
        "settings": {"stock_csv_delimiter": ";", "low_stock_threshold": 5},
        "paths": {"templates": "data/templates", "output_dir_stock": "data/output"},
        "rules": [{"name": "Test Rule", "match": "ANY", "conditions": [{"field": "SKU", "operator": "contains", "value": "TEST"}], "actions": [{"type": "ADD_TAG", "value": "auto_tagged"}]}],
        "packing_lists": [{"name": "Test PL", "output_filename": "test.xlsx", "filters": [{"field": "Order_Type", "operator": "==", "value": "Single"}], "exclude_skus": ["SKU1"]}],
        "stock_exports": [{"name": "Test SE", "template": "template.xls", "filters": [{"field": "Shipping_Provider", "operator": "==", "value": "DHL"}]}]
    }
    dialog = SettingsWindow(None, dummy_config)
    if dialog.exec():
        print("Settings saved:", json.dumps(dialog.config_data, indent=2))
    else:
        print("Cancelled.")
    sys.exit(0)
