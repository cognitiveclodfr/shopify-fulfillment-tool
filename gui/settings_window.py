import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json

class RuleBuilderFrame(ctk.CTkScrollableFrame):
    """A custom frame for building and managing a list of rules."""

    # Define constants based on user feedback and backend implementation
    CONDITION_FIELDS = [
        'Order_Number', 'Order_Type', 'SKU', 'Product_Name', 'Stock_Alert',
        'Order_Fulfillment_Status', 'Shipping_Provider', 'Destination_Country',
        'Tags', 'Status_Note', 'Total_Price' # Added Total_Price from example
    ]
    CONDITION_OPERATORS = [
        'equals', 'does not equal', 'contains', 'does not contain',
        'is greater than', 'is less than', 'starts with', 'ends with',
        'is empty', 'is not empty'
    ]
    ACTION_TYPES = [
        'ADD_TAG', 'SET_STATUS', 'SET_PRIORITY',
        'EXCLUDE_FROM_REPORT', 'EXCLUDE_SKU'
    ]

    def __init__(self, master, rules_data, style, **kwargs):
        super().__init__(master, **kwargs)
        self.rules_data = rules_data
        self.style = style
        self.rule_widgets = []
        self.grid_columnconfigure(0, weight=1)
        self.populate_rules()

    def populate_rules(self):
        """Clears and repopulates the frame with rule widgets."""
        for widgets in self.rule_widgets:
            widgets['frame'].destroy()
        self.rule_widgets = []

        for rule_config in self.rules_data:
            self.add_rule_entry(rule_config)

    def add_rule_entry(self, config=None):
        """Adds a UI block for a single rule."""
        if config is None:
            config = {
                "name": "New Rule",
                "match": "ALL",
                "conditions": [],
                "actions": []
            }

        rule_frame = ctk.CTkFrame(self, border_width=1)
        rule_frame.grid(padx=5, pady=(5, 10), sticky="ew")
        rule_frame.grid_columnconfigure(1, weight=1)

        # --- Rule Header ---
        header_frame = ctk.CTkFrame(rule_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        header_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header_frame, text="Rule Name:").grid(row=0, column=0, padx=(0,5))
        name_var = tk.StringVar(value=config.get('name', ''))
        ctk.CTkEntry(header_frame, textvariable=name_var).grid(row=0, column=1, sticky="ew")

        delete_rule_btn = ctk.CTkButton(header_frame, text="Delete Rule", fg_color=self.style['color_destructive'], width=100,
                                        command=lambda f=rule_frame: self.delete_rule_ui(f))
        delete_rule_btn.grid(row=0, column=2, padx=(10, 0))

        # --- Conditions (IF) ---
        conditions_frame = ctk.CTkFrame(rule_frame)
        conditions_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        conditions_frame.grid_columnconfigure(0, weight=1)

        match_var = tk.StringVar(value=config.get('match', 'ALL'))
        match_menu = ctk.CTkOptionMenu(conditions_frame, variable=match_var, values=["ALL", "ANY"])
        ctk.CTkLabel(conditions_frame, text="Execute actions if").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        match_menu.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(conditions_frame, text="of the following conditions are met:").grid(row=0, column=2, padx=5, pady=5, sticky="w")

        conditions_list_frame = ctk.CTkFrame(conditions_frame, fg_color="transparent")
        conditions_list_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5)

        # --- Actions (THEN) ---
        actions_frame = ctk.CTkFrame(rule_frame)
        actions_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        actions_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(actions_frame, text="Then, perform these actions:").grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        actions_list_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        actions_list_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5)

        widget_refs = {
            'frame': rule_frame,
            'name_var': name_var,
            'match_var': match_var,
            'conditions': [], # List of dicts for condition rows
            'actions': [] # List of dicts for action rows
        }

        # --- Add Buttons ---
        add_condition_btn = ctk.CTkButton(conditions_frame, text="Add Condition", width=120,
                                           command=lambda: self.add_condition_row(conditions_list_frame, widget_refs['conditions']))
        add_condition_btn.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        add_action_btn = ctk.CTkButton(actions_frame, text="Add Action", width=120,
                                       command=lambda: self.add_action_row(actions_list_frame, widget_refs['actions']))
        add_action_btn.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # Populate existing conditions and actions
        for cond in config.get('conditions', []):
            self.add_condition_row(conditions_list_frame, widget_refs['conditions'], cond)
        for act in config.get('actions', []):
            self.add_action_row(actions_list_frame, widget_refs['actions'], act)

        self.rule_widgets.append(widget_refs)

    def add_condition_row(self, parent, conditions_list, config=None):
        """Adds a UI row for a single condition."""
        if config is None: config = {}
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)

        field_var = tk.StringVar(value=config.get('field', self.CONDITION_FIELDS[0]))
        op_var = tk.StringVar(value=config.get('operator', self.CONDITION_OPERATORS[0]))
        val_var = tk.StringVar(value=config.get('value', ''))

        ctk.CTkComboBox(row_frame, values=self.CONDITION_FIELDS, variable=field_var).pack(side="left", padx=5)
        ctk.CTkComboBox(row_frame, values=self.CONDITION_OPERATORS, variable=op_var, width=150).pack(side="left", padx=5)
        ctk.CTkEntry(row_frame, textvariable=val_var, placeholder_text="Value").pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(row_frame, text="X", width=30, fg_color=self.style['color_destructive'],
                      command=lambda: self.delete_row(row_frame, conditions_list, condition_widgets)).pack(side="left", padx=5)

        condition_widgets = {'frame': row_frame, 'field_var': field_var, 'op_var': op_var, 'val_var': val_var}
        conditions_list.append(condition_widgets)

    def add_action_row(self, parent, actions_list, config=None):
        """Adds a UI row for a single action."""
        if config is None: config = {}
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)

        type_var = tk.StringVar(value=config.get('type', self.ACTION_TYPES[0]))
        val_var = tk.StringVar(value=config.get('value', ''))

        ctk.CTkComboBox(row_frame, values=self.ACTION_TYPES, variable=type_var).pack(side="left", padx=5)
        ctk.CTkEntry(row_frame, textvariable=val_var, placeholder_text="Value").pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(row_frame, text="X", width=30, fg_color=self.style['color_destructive'],
                      command=lambda: self.delete_row(row_frame, actions_list, action_widgets)).pack(side="left", padx=5)

        action_widgets = {'frame': row_frame, 'type_var': type_var, 'val_var': val_var}
        actions_list.append(action_widgets)

    def delete_row(self, frame, widget_list, widget_dict):
        frame.destroy()
        widget_list.remove(widget_dict)

    def delete_rule_ui(self, frame):
        frame.destroy()
        self.rule_widgets = [w for w in self.rule_widgets if w['frame'] is not frame]

    def get_rules_config(self):
        """Constructs and returns the rules configuration from the UI state."""
        new_rules = []
        for rule_w in self.rule_widgets:
            conditions = []
            for cond_w in rule_w['conditions']:
                conditions.append({
                    "field": cond_w['field_var'].get(),
                    "operator": cond_w['op_var'].get(),
                    "value": cond_w['val_var'].get()
                })

            actions = []
            for act_w in rule_w['actions']:
                actions.append({
                    "type": act_w['type_var'].get(),
                    "value": act_w['val_var'].get()
                })

            new_rules.append({
                "name": rule_w['name_var'].get(),
                "match": rule_w['match_var'].get(),
                "conditions": conditions,
                "actions": actions
            })
        return new_rules


class SettingsWindow(ctk.CTkToplevel):
    """
    A Toplevel window for managing application settings from config.json.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Application Settings")
        self.geometry("800x800")

        # Define constants for the filter builder
        self.FILTERABLE_COLUMNS = [
            'Order_Type', 'Shipping_Provider', 'Order_Fulfillment_Status',
            'Tags', 'Status_Note', 'Destination_Country'
        ]
        self.OPERATORS = ['==', '!=', 'in', 'not in']

        # Make a deep copy of the config to edit, so we can cancel without side effects
        self.config_data = json.loads(json.dumps(self.parent.config))

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.transient(parent)
        self.grab_set()

        self.create_widgets()

        self.parent.wait_window(self)

    def create_widgets(self):
        """Creates all widgets for the settings window."""
        # Main container frame
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        # Tab view for different settings categories
        self.tab_view = ctk.CTkTabview(main_frame)
        self.tab_view.grid(row=0, column=0, sticky="nsew")

        self.tab_view.add("General & Paths")
        self.tab_view.add("Rules")
        self.tab_view.add("Packing Lists")
        self.tab_view.add("Stock Exports")

        # Create content for tabs
        self.create_general_tab()
        # self.create_tagging_tab() # This will be replaced
        self.create_rules_tab()
        self.create_packing_lists_tab()
        self.create_stock_exports_tab()

        # Buttons frame
        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        buttons_frame.grid_columnconfigure((0, 1), weight=1)

        save_button = ctk.CTkButton(buttons_frame, text="Save and Close", command=self.save_settings, fg_color=self.parent.STYLE['color_accent'])
        save_button.grid(row=0, column=0, padx=10, pady=5, sticky="e")

        cancel_button = ctk.CTkButton(buttons_frame, text="Cancel", command=self.destroy, fg_color=self.parent.STYLE['color_gray'])
        cancel_button.grid(row=0, column=1, padx=10, pady=5, sticky="w")

    def create_general_tab(self):
        """Creates widgets for the 'General & Paths' tab."""
        general_tab = self.tab_view.tab("General & Paths")
        general_tab.grid_columnconfigure(1, weight=1)

        # --- Settings Section ---
        ctk.CTkLabel(general_tab, text="General Settings", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky="w")

        ctk.CTkLabel(general_tab, text="Stock CSV Delimiter:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.stock_delimiter_var = tk.StringVar(value=self.config_data.get('settings', {}).get('stock_csv_delimiter', ';'))
        ctk.CTkEntry(general_tab, textvariable=self.stock_delimiter_var).grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(general_tab, text="Low Stock Threshold:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.low_stock_var = tk.StringVar(value=self.config_data.get('settings', {}).get('low_stock_threshold', 10))
        ctk.CTkEntry(general_tab, textvariable=self.low_stock_var).grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # --- Paths Section ---
        ctk.CTkLabel(general_tab, text="File Paths", font=("Arial", 16, "bold")).grid(row=3, column=0, columnspan=2, pady=(20, 10), padx=10, sticky="w")

        ctk.CTkLabel(general_tab, text="Templates Directory:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.templates_path_var = tk.StringVar(value=self.config_data.get('paths', {}).get('templates', ''))
        ctk.CTkEntry(general_tab, textvariable=self.templates_path_var).grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(general_tab, text="Stock Export Output Directory:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.stock_output_path_var = tk.StringVar(value=self.config_data.get('paths', {}).get('output_dir_stock', ''))
        ctk.CTkEntry(general_tab, textvariable=self.stock_output_path_var).grid(row=5, column=1, padx=10, pady=5, sticky="ew")

    def save_settings(self):
        """Saves the current settings back to the config object and file."""
        try:
            # Update settings
            self.config_data['settings']['stock_csv_delimiter'] = self.stock_delimiter_var.get()
            self.config_data['settings']['low_stock_threshold'] = int(self.low_stock_var.get())

            # Update paths
            self.config_data['paths']['templates'] = self.templates_path_var.get()
            self.config_data['paths']['output_dir_stock'] = self.stock_output_path_var.get()

            # Get the new rules configuration from the builder
            self.config_data['rules'] = self.rule_builder.get_rules_config()

            # Update packing lists
            new_packing_lists = []
            for widgets in getattr(self, 'packing_list_widgets', []):
                try:
                    # Build the filters list from the dynamic UI
                    new_filters = []
                    for row in widgets['filter_rows']:
                        col = row['col_var'].get()
                        op = row['op_var'].get()
                        val_str = row['val_var'].get()
                        if val_str:
                            val = [v.strip() for v in val_str.split(',')] if op in ['in', 'not in'] else val_str
                            new_filters.append({"field": col, "operator": op, "value": val})

                    exclude_skus_str = widgets['exclude_skus_var'].get()
                    exclude_skus = [sku.strip() for sku in exclude_skus_str.split(',') if sku.strip()]

                    new_packing_lists.append({
                        "name": widgets['name_var'].get(),
                        "output_filename": widgets['filename_var'].get(),
                        "filters": new_filters,
                        "exclude_skus": exclude_skus
                    })
                except Exception as e:
                    messagebox.showerror("Save Error", f"Could not save Packing List '{widgets['name_var'].get()}'.\nError: {e}", parent=self)
                    return
            self.config_data['packing_lists'] = new_packing_lists

            # Update stock exports
            new_stock_exports = []
            for widgets in getattr(self, 'stock_export_widgets', []):
                try:
                    # Build the filters list from the dynamic UI
                    new_filters = []
                    for row in widgets['filter_rows']:
                        col = row['col_var'].get()
                        op = row['op_var'].get()
                        val_str = row['val_var'].get()
                        if val_str:
                            val = [v.strip() for v in val_str.split(',')] if op in ['in', 'not in'] else val_str
                            new_filters.append({"field": col, "operator": op, "value": val})

                    new_stock_exports.append({
                        "name": widgets['name_var'].get(),
                        "template": widgets['template_var'].get(),
                        "filters": new_filters
                    })
                except Exception as e:
                    messagebox.showerror("Save Error", f"Could not save Stock Export '{widgets['name_var'].get()}'.\nError: {e}", parent=self)
                    return
            self.config_data['stock_exports'] = new_stock_exports

            # Write to the parent's config object and save to file
            self.parent.config = self.config_data
            with open(self.parent.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.parent.config, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("Success", "Settings saved successfully.", parent=self)
            self.destroy()

        except ValueError:
            messagebox.showerror("Validation Error", "Low Stock Threshold must be a valid number.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}", parent=self)

    def create_rules_tab(self):
        """Creates widgets for the 'Rules' tab."""
        rules_tab = self.tab_view.tab("Rules")
        rules_tab.grid_columnconfigure(0, weight=1)
        rules_tab.grid_rowconfigure(1, weight=1)

        # Main frame for the rule builder
        builder_main_frame = ctk.CTkFrame(rules_tab, fg_color="transparent")
        builder_main_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        builder_main_frame.grid_columnconfigure(0, weight=1)

        add_rule_button = ctk.CTkButton(builder_main_frame, text="Add New Rule",
                                        command=lambda: self.rule_builder.add_rule_entry())
        add_rule_button.pack(anchor="w")

        # Create the scrollable frame for the rules
        self.rule_builder = RuleBuilderFrame(
            master=rules_tab,
            rules_data=self.config_data.get('rules', []),
            style=self.parent.STYLE,
            label_text="Automation Rules"
        )
        self.rule_builder.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def create_packing_lists_tab(self):
        """Creates widgets for the 'Packing Lists' tab."""
        tab = self.tab_view.tab("Packing Lists")
        tab.grid_columnconfigure(0, weight=1)

        self.packing_lists_frame = ctk.CTkScrollableFrame(tab, label_text="Configured Packing Lists")
        self.packing_lists_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.packing_lists_frame.grid_columnconfigure(0, weight=1)

        self.packing_list_widgets = []
        self.populate_packing_lists()

        add_button = ctk.CTkButton(tab, text="Add New Packing List", command=self.add_packing_list_entry)
        add_button.grid(row=1, column=0, pady=10, padx=10, sticky="w")

    def populate_packing_lists(self):
        """Populates the UI with packing list configurations."""
        for widgets in getattr(self, 'packing_list_widgets', []):
            widgets['frame'].destroy()
        self.packing_list_widgets = []

        for report_config in self.config_data.get('packing_lists', []):
            self.add_packing_list_entry(report_config)

    def add_packing_list_entry(self, config=None):
        """Adds a new entry for a packing list configuration."""
        if config is None:
            config = {"name": "New Packing List", "output_filename": "data/output/new_list.xlsx", "filters": {}, "exclude_skus": []}

        entry_frame = ctk.CTkFrame(self.packing_lists_frame, border_width=1)
        entry_frame.pack(fill="x", expand=True, padx=5, pady=5)
        entry_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(entry_frame, text="Name:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        name_var = tk.StringVar(value=config.get('name', ''))
        ctk.CTkEntry(entry_frame, textvariable=name_var).grid(row=0, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        ctk.CTkLabel(entry_frame, text="Output Filename:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        filename_var = tk.StringVar(value=config.get('output_filename', ''))
        ctk.CTkEntry(entry_frame, textvariable=filename_var).grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        # --- Filter Builder UI ---
        ctk.CTkLabel(entry_frame, text="Filters:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        filters_frame = ctk.CTkFrame(entry_frame)
        filters_frame.grid(row=2, column=1, sticky="ew")

        add_filter_button = ctk.CTkButton(entry_frame, text="Add Filter", width=80)
        add_filter_button.grid(row=3, column=1, padx=5, pady=(0, 5), sticky="w")

        # --- Exclude SKUs ---
        ctk.CTkLabel(entry_frame, text="Exclude SKUs (comma-separated):").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        exclude_skus_var = tk.StringVar(value=", ".join(config.get('exclude_skus', [])))
        ctk.CTkEntry(entry_frame, textvariable=exclude_skus_var).grid(row=4, column=1, sticky="ew")

        # --- Delete Button ---
        delete_button = ctk.CTkButton(entry_frame, text="Delete", fg_color="red", width=60,
                                      command=lambda f=entry_frame: self.delete_packing_list_entry(f))
        delete_button.grid(row=5, column=1, padx=5, pady=5, sticky="e")

        widget_refs = {
            'frame': entry_frame,
            'name_var': name_var,
            'filename_var': filename_var,
            'exclude_skus_var': exclude_skus_var,
            'filters_frame': filters_frame, # Reference to the container for filter rows
            'filter_rows': [] # List to hold widgets for each filter rule
        }

        add_filter_button.configure(command=lambda: self._add_filter_rule_row(filters_frame, widget_refs['filter_rows']))

        self.packing_list_widgets.append(widget_refs)

        # Populate existing filters from the new list-based structure
        existing_filters = config.get('filters', [])
        for f in existing_filters:
            val = f.get('value')
            val_str = ', '.join(map(str, val)) if isinstance(val, list) else str(val)
            self._add_filter_rule_row(
                parent_frame=filters_frame,
                rows_list=widget_refs['filter_rows'],
                col=f.get('field', ''),
                op=f.get('operator', '=='),
                val=val_str
            )

    def delete_packing_list_entry(self, frame_to_delete):
        """Removes a packing list entry from the UI."""
        frame_to_delete.destroy()
        self.packing_list_widgets = [w for w in self.packing_list_widgets if w['frame'] is not frame_to_delete]

    def _add_filter_rule_row(self, parent_frame, rows_list, col="", op="", val=""):
        """Dynamically adds a new row of widgets for creating a filter rule."""
        row_frame = ctk.CTkFrame(parent_frame)
        row_frame.grid(sticky="ew", pady=2)
        row_frame.grid_columnconfigure(2, weight=1) # Allow the value entry to expand

        col_var = tk.StringVar(value=col or self.FILTERABLE_COLUMNS[0])
        op_var = tk.StringVar(value=op or self.OPERATORS[0])
        val_var = tk.StringVar(value=val)

        col_combo = ctk.CTkComboBox(row_frame, values=self.FILTERABLE_COLUMNS, variable=col_var, width=150)
        col_combo.grid(row=0, column=0, padx=5, pady=5)

        op_combo = ctk.CTkComboBox(row_frame, values=self.OPERATORS, variable=op_var, width=80)
        op_combo.grid(row=0, column=1, padx=5, pady=5)

        val_entry = ctk.CTkEntry(row_frame, textvariable=val_var, placeholder_text="Value")
        val_entry.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        row_widgets = {
            "frame": row_frame,
            "col_var": col_var,
            "op_var": op_var,
            "val_var": val_var,
            "value_widget": val_entry # Keep a reference to the current value widget
        }

        # Add commands to trigger the dynamic widget update
        col_combo.configure(command=lambda choice, rw=row_widgets: self._on_filter_criteria_changed(rw))
        op_combo.configure(command=lambda choice, rw=row_widgets: self._on_filter_criteria_changed(rw))

        delete_button = ctk.CTkButton(row_frame, text="X", fg_color="red", width=30,
                                      command=lambda: self._delete_filter_rule_row(row_widgets, rows_list))
        delete_button.grid(row=0, column=3, padx=5, pady=5)

        rows_list.append(row_widgets)

    def _delete_filter_rule_row(self, row_widgets, rows_list):
        """Destroys the widgets in a filter rule row and removes it from the list."""
        row_widgets['frame'].destroy()
        rows_list.remove(row_widgets)

    def _on_filter_criteria_changed(self, row_widgets):
        """
        Handles changes in the column or operator dropdowns for a filter rule,
        dynamically updating the value widget.
        """
        col = row_widgets['col_var'].get()
        op = row_widgets['op_var'].get()
        val_var = row_widgets['val_var']
        row_frame = row_widgets['frame']

        # Destroy the old value widget
        if row_widgets['value_widget']:
            row_widgets['value_widget'].destroy()

        # Decide whether to show a ComboBox or an Entry
        use_combobox = op not in ['in', 'not in'] and self.parent.analysis_results_df is not None and col in self.parent.analysis_results_df.columns

        if use_combobox:
            try:
                unique_values = self.parent.analysis_results_df[col].dropna().unique().tolist()
                unique_values.sort()
            except Exception:
                unique_values = [] # Fallback in case of error

            new_widget = ctk.CTkComboBox(row_frame, values=unique_values, variable=val_var)
        else:
            new_widget = ctk.CTkEntry(row_frame, textvariable=val_var, placeholder_text="Value(s), comma-separated for 'in'")

        new_widget.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        row_widgets['value_widget'] = new_widget

    def create_stock_exports_tab(self):
        """Creates widgets for the 'Stock Exports' tab."""
        tab = self.tab_view.tab("Stock Exports")
        tab.grid_columnconfigure(0, weight=1)

        self.stock_exports_frame = ctk.CTkScrollableFrame(tab, label_text="Configured Stock Exports")
        self.stock_exports_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.stock_exports_frame.grid_columnconfigure(0, weight=1)

        self.stock_export_widgets = []
        self.populate_stock_exports()

        add_button = ctk.CTkButton(tab, text="Add New Stock Export", command=self.add_stock_export_entry)
        add_button.grid(row=1, column=0, pady=10, padx=10, sticky="w")

    def populate_stock_exports(self):
        """Populates the UI with stock export configurations."""
        for widgets in getattr(self, 'stock_export_widgets', []):
            widgets['frame'].destroy()
        self.stock_export_widgets = []

        for report_config in self.config_data.get('stock_exports', []):
            self.add_stock_export_entry(report_config)

    def add_stock_export_entry(self, config=None):
        """Adds a new entry for a stock export configuration."""
        if config is None:
            config = {"name": "New Stock Export", "template": "template.xls", "filters": {}}

        entry_frame = ctk.CTkFrame(self.stock_exports_frame, border_width=1)
        entry_frame.pack(fill="x", expand=True, padx=5, pady=5)
        entry_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(entry_frame, text="Name:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        name_var = tk.StringVar(value=config.get('name', ''))
        ctk.CTkEntry(entry_frame, textvariable=name_var).grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ctk.CTkLabel(entry_frame, text="Template Filename:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        template_var = tk.StringVar(value=config.get('template', ''))
        ctk.CTkEntry(entry_frame, textvariable=template_var).grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        # --- Filter Builder UI ---
        ctk.CTkLabel(entry_frame, text="Filters:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        filters_frame = ctk.CTkFrame(entry_frame)
        filters_frame.grid(row=2, column=1, sticky="ew")

        add_filter_button = ctk.CTkButton(entry_frame, text="Add Filter", width=80)
        add_filter_button.grid(row=3, column=1, padx=5, pady=(0, 5), sticky="w")

        # --- Delete Button ---
        delete_button = ctk.CTkButton(entry_frame, text="Delete", fg_color="red", width=60,
                                      command=lambda f=entry_frame: self.delete_stock_export_entry(f))
        delete_button.grid(row=4, column=1, padx=5, pady=5, sticky="e")

        widget_refs = {
            'frame': entry_frame,
            'name_var': name_var,
            'template_var': template_var,
            'filters_frame': filters_frame,
            'filter_rows': []
        }

        add_filter_button.configure(command=lambda: self._add_filter_rule_row(filters_frame, widget_refs['filter_rows']))

        self.stock_export_widgets.append(widget_refs)

        # Populate existing filters from the new list-based structure
        existing_filters = config.get('filters', [])
        for f in existing_filters:
            val = f.get('value')
            val_str = ', '.join(map(str, val)) if isinstance(val, list) else str(val)
            self._add_filter_rule_row(
                parent_frame=filters_frame,
                rows_list=widget_refs['filter_rows'],
                col=f.get('field', ''),
                op=f.get('operator', '=='),
                val=val_str
            )

    def delete_stock_export_entry(self, frame_to_delete):
        """Removes a stock export entry from the UI."""
        frame_to_delete.destroy()
        self.stock_export_widgets = [w for w in self.stock_export_widgets if w['frame'] is not frame_to_delete]
