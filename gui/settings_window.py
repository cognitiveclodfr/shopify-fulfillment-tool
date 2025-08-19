import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json

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
        self.tab_view.add("Tagging Rules")
        self.tab_view.add("Packing Lists")
        self.tab_view.add("Stock Exports")

        # Create content for tabs
        self.create_general_tab()
        self.create_tagging_tab()
        self.create_packing_lists_tab()
        self.create_stock_exports_tab()

        # Buttons frame
        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        buttons_frame.grid_columnconfigure((0, 1), weight=1)

        save_button = ctk.CTkButton(buttons_frame, text="Save and Close", command=self.save_settings)
        save_button.grid(row=0, column=0, padx=10, pady=5, sticky="e")

        cancel_button = ctk.CTkButton(buttons_frame, text="Cancel", command=self.destroy, fg_color="gray")
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

            # Update tagging rules
            try:
                self.config_data['tagging_rules']['composite_order_tag'] = self.composite_tag_var.get()
            except Exception:
                # Ensure structure exists
                self.config_data.setdefault('tagging_rules', {})
                self.config_data['tagging_rules']['composite_order_tag'] = getattr(self, 'composite_tag_var', tk.StringVar(value='BOX')).get()

            new_special_tags = {}
            for widgets in getattr(self, 'rule_widgets', []):
                sku = widgets['sku_var'].get()
                tag = widgets['tag_var'].get()
                if sku: # Only save if SKU is not empty
                    new_special_tags[sku] = tag
            self.config_data.setdefault('tagging_rules', {})
            self.config_data['tagging_rules']['special_sku_tags'] = new_special_tags
            # Update packing lists
            new_packing_lists = []
            for widgets in getattr(self, 'packing_list_widgets', []):
                try:
                    # Build the filters dictionary from the dynamic UI
                    filters = {}
                    for row in widgets['filter_rows']:
                        col = row['col_var'].get()
                        op = row['op_var'].get()
                        val = row['val_var'].get()
                        if val: # Only add filter if a value is provided
                            # For 'in'/'not in', the value should be a list
                            if op in ['in', 'not in']:
                                filters[col] = [v.strip() for v in val.split(',')]
                            else:
                                filters[col] = val

                    exclude_skus_str = widgets['exclude_skus_var'].get()
                    exclude_skus = [sku.strip() for sku in exclude_skus_str.split(',') if sku.strip()]

                    new_packing_lists.append({
                        "name": widgets['name_var'].get(),
                        "output_filename": widgets['filename_var'].get(),
                        "filters": filters,
                        "exclude_skus": exclude_skus
                    })
                except json.JSONDecodeError:
                    messagebox.showerror("Validation Error", "Invalid JSON format in Packing List filters.", parent=self)
                    return
            self.config_data['packing_lists'] = new_packing_lists

            # Update stock exports
            new_stock_exports = []
            for widgets in getattr(self, 'stock_export_widgets', []):
                try:
                    filters = json.loads(widgets['filters_var'].get() or '{}')
                    new_stock_exports.append({
                        "name": widgets['name_var'].get(),
                        "template": widgets['template_var'].get(),
                        "filters": filters
                    })
                except json.JSONDecodeError:
                    messagebox.showerror("Validation Error", "Invalid JSON format in Stock Export filters.", parent=self)
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

    def create_tagging_tab(self):
        """Creates widgets for the 'Tagging Rules' tab."""
        tagging_tab = self.tab_view.tab("Tagging Rules")
        tagging_tab.grid_columnconfigure(0, weight=1)

        # --- Composite Tag Section ---
        ctk.CTkLabel(tagging_tab, text="Composite Order Tag", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky="w")

        ctk.CTkLabel(tagging_tab, text="Tag for multi-item orders with a special SKU:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.composite_tag_var = tk.StringVar(value=self.config_data.get('tagging_rules', {}).get('composite_order_tag', 'BOX'))
        ctk.CTkEntry(tagging_tab, textvariable=self.composite_tag_var).grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # --- Special SKU Tags Section ---
        ctk.CTkLabel(tagging_tab, text="Special SKU Tags", font=("Arial", 16, "bold")).grid(row=2, column=0, columnspan=2, pady=(20, 10), padx=10, sticky="w")

        # Frame for the list of rules
        self.rules_frame = ctk.CTkFrame(tagging_tab)
        self.rules_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10)
        self.rules_frame.grid_columnconfigure(0, weight=1)

        # List to keep track of rule entry widgets
        self.rule_widgets = []
        self.populate_tagging_rules()

        # Add new rule button
        add_button = ctk.CTkButton(tagging_tab, text="Add New Rule", command=self.add_rule_entry)
        add_button.grid(row=4, column=0, columnspan=2, pady=10, padx=10, sticky="w")

    def populate_tagging_rules(self):
        """Clears and repopulates the rules frame based on config data."""
        # Clear existing widgets
        for widgets in getattr(self, 'rule_widgets', []):
            widgets['sku_entry'].destroy()
            widgets['tag_entry'].destroy()
            widgets['delete_button'].destroy()
        self.rule_widgets = []

        # Add header
        header_frame = ctk.CTkFrame(self.rules_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=4)
        header_frame.grid_columnconfigure(1, weight=4)
        header_frame.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(header_frame, text="SKU", font=("Arial", 12, "bold")).grid(row=0, column=0, padx=5)
        ctk.CTkLabel(header_frame, text="Tag", font=("Arial", 12, "bold")).grid(row=0, column=1, padx=5)

        # Populate with rules from config
        special_tags = self.config_data.get('tagging_rules', {}).get('special_sku_tags', {})
        for sku, tag in special_tags.items():
            self.add_rule_entry(sku, tag)

    def add_rule_entry(self, sku="", tag=""):
        """Adds a new row of widgets for a single SKU-tag rule."""
        row_index = len(self.rule_widgets) + 1 # +1 for header

        sku_var = tk.StringVar(value=sku)
        tag_var = tk.StringVar(value=tag)

        sku_entry = ctk.CTkEntry(self.rules_frame, textvariable=sku_var)
        sku_entry.grid(row=row_index, column=0, padx=5, pady=5, sticky="ew")

        tag_entry = ctk.CTkEntry(self.rules_frame, textvariable=tag_var)
        tag_entry.grid(row=row_index, column=1, padx=5, pady=5, sticky="ew")

        delete_button = ctk.CTkButton(self.rules_frame, text="Delete", fg_color="red", width=60,
                                      command=lambda r=row_index: self.delete_rule_entry(r))
        delete_button.grid(row=row_index, column=2, padx=5, pady=5)

        self.rule_widgets.append({
            'row': row_index,
            'sku_var': sku_var,
            'tag_var': tag_var,
            'sku_entry': sku_entry,
            'tag_entry': tag_entry,
            'delete_button': delete_button
        })

    def delete_rule_entry(self, row_to_delete):
        """Removes a rule entry from the UI."""
        # Find the widget set by its row index
        widget_to_delete = next((w for w in self.rule_widgets if w['row'] == row_to_delete), None)
        if not widget_to_delete: return

        # Destroy widgets
        widget_to_delete['sku_entry'].destroy()
        widget_to_delete['tag_entry'].destroy()
        widget_to_delete['delete_button'].destroy()

        # Remove from our list
        self.rule_widgets.remove(widget_to_delete)

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

        # Populate existing filters
        existing_filters = config.get('filters', {})
        for col, val in existing_filters.items():
            op = 'in' if isinstance(val, list) else '=='
            val_str = ', '.join(val) if isinstance(val, list) else val
            self._add_filter_rule_row(filters_frame, widget_refs['filter_rows'], col, op, val_str)

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

        ctk.CTkLabel(entry_frame, text="Filters (JSON):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        filters_var = tk.StringVar(value=json.dumps(config.get('filters', {})))
        ctk.CTkEntry(entry_frame, textvariable=filters_var).grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        delete_button = ctk.CTkButton(entry_frame, text="Delete", fg_color="red", width=60,
                                      command=lambda f=entry_frame: self.delete_stock_export_entry(f))
        delete_button.grid(row=3, column=1, padx=5, pady=5, sticky="e")

        self.stock_export_widgets.append({
            'frame': entry_frame, 'name_var': name_var, 'template_var': template_var, 'filters_var': filters_var
        })

    def delete_stock_export_entry(self, frame_to_delete):
        """Removes a stock export entry from the UI."""
        frame_to_delete.destroy()
        self.stock_export_widgets = [w for w in self.stock_export_widgets if w['frame'] is not frame_to_delete]
