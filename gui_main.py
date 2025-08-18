import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import sys
import os
import pandas as pd
import json
import logging
from shopify_tool.logger_config import setup_logging
from datetime import datetime

# configure logging early so other modules get the handlers
setup_logging()
logger = logging.getLogger('ShopifyToolLogger')
# --- Helper classes and functions ---

class ToolTip:
    """
    Create a tooltip for a given widget.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                      background="#FFFFE0", relief='solid', borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from shopify_tool import core

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Shopify Fulfillment Tool v5.1")
        self.geometry("900x750")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.analysis_results_df = None
        self.analysis_stats = None # To store the stats dictionary
        self.config_path = resource_path('config.json')
        self.config = self.load_config()
        self.log_file_path = resource_path('app_history.log')

        self.create_widgets()
    def load_config(self):
        """ Loads the main configuration file. """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            messagebox.showerror("Configuration Error", f"Failed to load config.json: {e}")
            self.after(100, self.destroy)
        return None

    def create_widgets(self):
        """ Creates all the widgets for the main application window. """
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        files_frame = ctk.CTkFrame(self)
        files_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        files_frame.grid_columnconfigure(1, weight=1)

        self.orders_file_path = tk.StringVar(value="Orders file not selected")
        self.stock_file_path = tk.StringVar(value="Stock file not selected")

        load_orders_btn = ctk.CTkButton(files_frame, text="Load Orders File (.csv)", command=self.select_orders_file)
        load_orders_btn.grid(row=0, column=0, padx=10, pady=5)
        ToolTip(load_orders_btn, "Select the orders_export.csv file from Shopify.")
        
        ctk.CTkLabel(files_frame, textvariable=self.orders_file_path).grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        load_stock_btn = ctk.CTkButton(files_frame, text="Load Stock File (.csv)", command=self.select_stock_file)
        load_stock_btn.grid(row=1, column=0, padx=10, pady=5)
        ToolTip(load_stock_btn, "Select the inventory/stock CSV file.")

        ctk.CTkLabel(files_frame, textvariable=self.stock_file_path).grid(row=1, column=1, padx=10, pady=5, sticky="w")

        actions_frame = ctk.CTkFrame(self)
        actions_frame.grid(row=1, column=0, padx=10, pady=0, sticky="ew")
        # Reserve middle column to expand so buttons on the right stay aligned
        actions_frame.grid_columnconfigure(1, weight=1)

        self.run_analysis_button = ctk.CTkButton(actions_frame, text="Run Analysis", state="disabled", command=self.start_analysis_thread)
        # Span only two columns so a Settings button can be placed on the right
        self.run_analysis_button.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        ToolTip(self.run_analysis_button, "Start the fulfillment analysis based on the loaded files.")

        self.packing_list_button = ctk.CTkButton(actions_frame, text="Create Packing List", state="disabled", command=self.open_packing_list_window)
        self.packing_list_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ToolTip(self.packing_list_button, "Generate packing lists based on pre-defined filters.")

        self.stock_export_button = ctk.CTkButton(actions_frame, text="Create Stock Export", state="disabled", command=self.open_stock_export_window)
        self.stock_export_button.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ToolTip(self.stock_export_button, "Generate stock export files for couriers.")

        self.report_builder_button = ctk.CTkButton(actions_frame, text="Report Builder", state="disabled", command=self.open_report_builder_window)
        self.report_builder_button.grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        ToolTip(self.report_builder_button, "Create a custom report with your own filters and columns.")
        
        # Settings button (opens the Settings window)
        self.settings_button = ctk.CTkButton(actions_frame, text="Settings", command=self.open_settings_window)
        self.settings_button.grid(row=0, column=2, padx=10, pady=10, sticky="e")
        ToolTip(self.settings_button, "Open the application settings window.")

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_view.add("Execution Log")
        self.tab_view.add("Activity Log")
        self.tab_view.add("Analysis Data")
        self.tab_view.add("Statistics")

        # --- Setup Tabs ---
        self.log_area = ctk.CTkTextbox(self.tab_view.tab("Execution Log"), wrap=tk.WORD)
        self.log_area.pack(fill="both", expand=True)
        self.log_area.configure(state='disabled')
        sys.stdout = TextRedirector(self.log_area, self.log_file_path)
            
        self.activity_log_frame = ctk.CTkFrame(self.tab_view.tab("Activity Log"))
        self.activity_log_frame.pack(fill="both", expand=True)
        self.create_activity_log()

        self.stats_frame = ctk.CTkFrame(self.tab_view.tab("Statistics"))
        self.stats_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.create_statistics_tab()

        self.data_viewer_frame = ctk.CTkFrame(self.tab_view.tab("Analysis Data"))
        self.data_viewer_frame.pack(fill="both", expand=True)
        self.create_data_viewer()

    def create_statistics_tab(self):
        """ Creates the UI elements for the Statistics tab. """
        # Configure column weights for stability
        self.stats_frame.grid_columnconfigure(0, weight=0) # Column for labels
        self.stats_frame.grid_columnconfigure(1, weight=1) # Column for values (expands)

        self.stats_labels = {}
        stat_keys = {
            "total_orders_completed": "Total Orders Completed:",
            "total_orders_not_completed": "Total Orders Not Completed:",
            "total_items_to_write_off": "Total Items to Write Off:",
            "total_items_not_to_write_off": "Total Items Not to Write Off:",
        }
        
        row_counter = 0
        for key, text in stat_keys.items():
            label = ctk.CTkLabel(self.stats_frame, text=text, font=("Arial", 14, "bold"), anchor="w")
            label.grid(row=row_counter, column=0, sticky="ew", padx=10, pady=5)
            value_label = ctk.CTkLabel(self.stats_frame, text="-", font=("Arial", 14), anchor="w")
            value_label.grid(row=row_counter, column=1, sticky="ew", padx=10, pady=5)
            self.stats_labels[key] = value_label
            row_counter += 1
            
        courier_header = ctk.CTkLabel(self.stats_frame, text="Couriers Stats:", font=("Arial", 14, "bold"), anchor="w")
        courier_header.grid(row=row_counter, column=0, columnspan=2, sticky="ew", padx=10, pady=(15, 5))
        row_counter += 1
        
        self.courier_stats_frame = ctk.CTkFrame(self.stats_frame)
        self.courier_stats_frame.grid(row=row_counter, column=0, columnspan=2, sticky="ew", padx=10)
        # Configure courier frame columns for stability
        self.courier_stats_frame.grid_columnconfigure(0, weight=1)
        self.courier_stats_frame.grid_columnconfigure(1, weight=1)
        self.courier_stats_frame.grid_columnconfigure(2, weight=1)


    def update_statistics_tab(self):
        """ Populates the Statistics tab with data from self.analysis_stats. """
        if not self.analysis_stats:
            return

        for key, label in self.stats_labels.items():
            value = self.analysis_stats.get(key, "N/A")
            label.configure(text=str(value))

        for widget in self.courier_stats_frame.winfo_children():
            widget.destroy()

        courier_stats = self.analysis_stats.get('couriers_stats')
        if courier_stats:
            # Create headers with anchor
            ctk.CTkLabel(self.courier_stats_frame, text="Courier ID", font=("Arial", 12, "bold"), anchor="w").grid(row=0, column=0, padx=5, pady=2, sticky="ew")
            ctk.CTkLabel(self.courier_stats_frame, text="Orders Assigned", font=("Arial", 12, "bold"), anchor="w").grid(row=0, column=1, padx=5, pady=2, sticky="ew")
            ctk.CTkLabel(self.courier_stats_frame, text="Repeated Orders", font=("Arial", 12, "bold"), anchor="w").grid(row=0, column=2, padx=5, pady=2, sticky="ew")

            for i, stats in enumerate(courier_stats, start=1):
                ctk.CTkLabel(self.courier_stats_frame, text=stats.get('courier_id', 'N/A'), anchor="w").grid(row=i, column=0, padx=5, pady=2, sticky="ew")
                ctk.CTkLabel(self.courier_stats_frame, text=stats.get('orders_assigned', 'N/A'), anchor="w").grid(row=i, column=1, padx=5, pady=2, sticky="ew")
                ctk.CTkLabel(self.courier_stats_frame, text=stats.get('repeated_orders_found', 'N/A'), anchor="w").grid(row=i, column=2, padx=5, pady=2, sticky="ew")
        else:
            ctk.CTkLabel(self.courier_stats_frame, text="No courier stats available.").pack(pady=10)

    def create_activity_log(self):
        """ Creates the Treeview widget for displaying user-facing activity logs. """
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Activity.Treeview", background="#2B2B2B", foreground="white", fieldbackground="#2B2B2B", borderwidth=0)
        style.map('Activity.Treeview', background=[('selected', '#22559b')])
        style.configure("Activity.Treeview.Heading", background="#565b5e", foreground="white", relief="flat")
        style.map("Activity.Treeview.Heading", background=[('active', '#3484F0')])

        self.activity_log_tree = ttk.Treeview(self.activity_log_frame, style="Activity.Treeview", columns=("Time", "Operation", "Description"), show="headings")
        self.activity_log_tree.pack(side="left", fill="both", expand=True)

        self.activity_log_tree.heading("Time", text="Time")
        self.activity_log_tree.heading("Operation", text="Operation")
        self.activity_log_tree.heading("Description", text="Description")

        self.activity_log_tree.column("Time", width=150, anchor='w', stretch=tk.NO)
        self.activity_log_tree.column("Operation", width=200, anchor='w', stretch=tk.NO)
        self.activity_log_tree.column("Description", width=500, anchor='w')

        vsb = ttk.Scrollbar(self.activity_log_frame, orient="vertical", command=self.activity_log_tree.yview)
        vsb.pack(side='right', fill='y')
        self.activity_log_tree.configure(yscrollcommand=vsb.set)

    def log_activity(self, operation_type, description):
        """ Adds a new entry to the Activity Log tab. """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.activity_log_tree.insert("", 0, values=(current_time, operation_type, description))
        self.tab_view.set("Activity Log")

    def create_data_viewer(self):
        """ Creates the Treeview widget for displaying analysis data. """
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2B2B2B", foreground="white", fieldbackground="#2B2B2B", borderwidth=0)
        style.map('Treeview', background=[('selected', '#22559b')])
        style.configure("Treeview.Heading", background="#565b5e", foreground="white", relief="flat")
        style.map("Treeview.Heading", background=[('active', '#3484F0')])
        
        style.configure("Fulfillable.Treeview", background="#0A380A", foreground="white")
        style.configure("NotFulfillable.Treeview", background="#4A1A1A", foreground="white")

        self.tree = ttk.Treeview(self.data_viewer_frame, style="Treeview")
        self.tree.pack(side="left", fill="both", expand=True)
        
        vsb = ttk.Scrollbar(self.data_viewer_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=vsb.set)

        hsb = ttk.Scrollbar(self.data_viewer_frame, orient="horizontal", command=self.tree.xview)
        hsb.pack(side='bottom', fill='x')
        self.tree.configure(xscrollcommand=hsb.set)

    def update_data_viewer(self, df):
        """ Clears and repopulates the Treeview with new DataFrame data. """
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(df.columns)
        self.tree["show"] = "headings"
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor='w')
        
        self.tree.tag_configure("Fulfillable", background="#2E4B2E", foreground="lightgreen")
        self.tree.tag_configure("NotFulfillable", background="#5A2E2E", foreground="#FFB0B0")

        for index, row in df.iterrows():
            status = row.get("Order_Fulfillment_Status", "")
            tag = ""
            if status == "Fulfillable":
                tag = "Fulfillable"
            elif status == "Not Fulfillable":
                tag = "NotFulfillable"
            self.tree.insert("", "end", values=list(row), tags=(tag,))

    def select_orders_file(self):
        filepath = filedialog.askopenfilename(title="Select Orders File", filetypes=[("CSV files", "*.csv")])
        if filepath:
            self.orders_file_path.set(filepath)
            print(f"Orders file selected: {filepath}")
            self.check_files_selected()

    def select_stock_file(self):
        filepath = filedialog.askopenfilename(title="Select Stock File", filetypes=[("CSV files", "*.csv")])
        if filepath:
            self.stock_file_path.set(filepath)
            print(f"Stock file selected: {filepath}")
            self.check_files_selected()

    def check_files_selected(self):
        """ Enables the 'Run Analysis' button if both files are selected. """
        if "not selected" not in self.orders_file_path.get() and "not selected" not in self.stock_file_path.get():
            self.run_analysis_button.configure(state="normal")
            print("Both files loaded. Ready for analysis.")

    def start_analysis_thread(self):
        """ Starts the analysis process in a separate thread to avoid freezing the GUI. """
        self.run_analysis_button.configure(state="disabled")
        self.packing_list_button.configure(state="disabled")
        self.stock_export_button.configure(state="disabled")
        self.report_builder_button.configure(state="disabled")
        
        threading.Thread(target=self.run_analysis_logic, daemon=True).start()

    def run_analysis_logic(self):
        """
        Wrapper function that calls the core analysis function and handles the result.
        """
        stock_path = self.stock_file_path.get()
        orders_path = self.orders_file_path.get()
        output_dir = self.config['paths']['output']['analysis_file']
        stock_delimiter = self.config['settings']['stock_csv_delimiter']

        try:
            success, result, df, stats = core.run_full_analysis(
                stock_path,
                orders_path,
                os.path.dirname(output_dir),
                stock_delimiter,
                self.config
            )
        except Exception as e:
            # Forward exception to GUI thread handler
            self.after(0, self.on_analysis_complete, False, str(e), None, None)
            return

        self.after(0, self.on_analysis_complete, success, result, df, stats)

    def on_analysis_complete(self, success, result, df, stats):
        """
        Handles the completion of the analysis, updating the GUI accordingly.
        """
        if success:
            self.log_activity("Analysis", f"Analysis complete. Report saved to: {result}")
            self.analysis_results_df = df
            self.analysis_stats = stats
            
            self.update_data_viewer(self.analysis_results_df)
            self.update_statistics_tab()
            
            self.packing_list_button.configure(state="normal")
            self.stock_export_button.configure(state="normal")
            self.report_builder_button.configure(state="normal")
            self.tab_view.set("Statistics")
        else:
            messagebox.showerror("Analysis Error", f"An error occurred during analysis:\n{result}")
        
        self.run_analysis_button.configure(state="normal")

    def open_packing_list_window(self):
        self.create_report_window("packing_lists", "Create Packing Lists")

    def open_stock_export_window(self):
        self.create_report_window("stock_exports", "Create Stock Exports")

    def open_report_builder_window(self):
        if self.analysis_results_df is None:
            messagebox.showwarning("Warning", "Please run the analysis first.")
            return
        ReportBuilderWindow(self)

    def open_settings_window(self):
        SettingsWindow(self)

    def create_report_window(self, report_type, title):
        """ Creates a new modal window for report selection. """
        window = ctk.CTkToplevel(self)
        window.title(title)
        window.geometry("400x300")
        
        window.transient(self)
        window.grab_set()
        
        reports = self.config.get(report_type, [])
        if not reports:
            ctk.CTkLabel(window, text="No reports configured in config.json.").pack(pady=20, padx=10)
            self.wait_window(window)
            return

        for report_config in reports:
            btn = ctk.CTkButton(
                window,
                text=report_config.get('name', 'Unknown Report'),
                command=lambda rc=report_config, rt=report_type, win=window: self.start_report_thread(rc, rt, win)
            )
            btn.pack(pady=5, padx=10, fill="x")

        self.wait_window(window)

    def start_report_thread(self, report_config, report_type, window):
        """ Starts a report generation process in a separate thread. """
        window.destroy()
        threading.Thread(target=self.run_report_logic, args=(report_config, report_type), daemon=True).start()

    def run_report_logic(self, report_config, report_type):
        """
        Wrapper function that calls the appropriate core report function.
        """
        if report_type == "packing_lists":
            success, message = core.create_packing_list_report(
                analysis_df=self.analysis_results_df,
                report_config=report_config
            )
        elif report_type == "stock_exports":
            templates_path = resource_path(self.config['paths']['templates'])
            output_path = self.config['paths']['output_dir_stock']
            success, message = core.create_stock_export_report(
                analysis_df=self.analysis_results_df,
                report_config=report_config,
                templates_path=templates_path,
                output_path=output_path
            )
        else:
            success = False
            message = "Unknown report type."

        if success:
            self.after(0, self.log_activity, "Report Generation", message)
        else:
            self.after(0, messagebox.showerror, "Error", message)


class ReportBuilderWindow(ctk.CTkToplevel):
    """
    A Toplevel window for creating custom reports.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Report Builder")
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.transient(parent)
        self.grab_set()

        self.create_widgets()
        self.parent.wait_window(self)


    def create_widgets(self):
        """ Creates all widgets for the report builder window. """
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        controls_frame.grid_columnconfigure(0, weight=1)

        columns_frame = ctk.CTkFrame(controls_frame)
        columns_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(columns_frame, text="Step 1: Select Columns to Include", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0,5))

        self.column_vars = {}
        scrollable_frame = ctk.CTkScrollableFrame(columns_frame, height=150)
        scrollable_frame.pack(fill="x", expand=True)
        
        all_columns = self.parent.analysis_results_df.columns
        for col in all_columns:
            self.column_vars[col] = tk.BooleanVar(value=True)
            ctk.CTkCheckBox(scrollable_frame, text=col, variable=self.column_vars[col]).pack(anchor="w", padx=10)

        filter_frame = ctk.CTkFrame(controls_frame)
        filter_frame.grid(row=1, column=0, padx=5, pady=10, sticky="ew")
        ctk.CTkLabel(filter_frame, text="Step 2: Add a Filter (Optional)", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0,5))
        
        self.filter_column_var = ctk.StringVar(value=all_columns[0])
        self.filter_operator_var = ctk.StringVar(value="==")
        self.filter_value_var = ctk.StringVar()

        ctk.CTkComboBox(filter_frame, values=list(all_columns), variable=self.filter_column_var).pack(side="left", padx=5)
        ctk.CTkComboBox(filter_frame, values=["==", "!=", ">", "<", "contains"], variable=self.filter_operator_var).pack(side="left", padx=5)
        ctk.CTkEntry(filter_frame, placeholder_text="Value", textvariable=self.filter_value_var).pack(side="left", padx=5, fill="x", expand=True)

        generate_btn = ctk.CTkButton(self, text="Step 3: Generate and Save Custom Report", command=self.generate_custom_report, height=40)
        generate_btn.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

    def generate_custom_report(self):
        """ Filters and saves the custom report based on user selections. """
        selected_columns = [col for col, var in self.column_vars.items() if var.get()]
        if not selected_columns:
            messagebox.showerror("Error", "Please select at least one column.", parent=self)
            return

        df = self.parent.analysis_results_df.copy()
        filter_col = self.filter_column_var.get()
        operator = self.filter_operator_var.get()
        value = self.filter_value_var.get()

        if value:
            try:
                numeric_value = pd.to_numeric(value, errors='coerce')
                if not pd.isna(numeric_value):
                    value = numeric_value
                    df[filter_col] = pd.to_numeric(df[filter_col], errors='coerce')

                if operator == "==": df = df[df[filter_col] == value]
                elif operator == "!=": df = df[df[filter_col] != value]
                elif operator == ">": df = df[df[filter_col] > value]
                elif operator == "<": df = df[df[filter_col] < value]
                elif operator == "contains": df = df[df[filter_col].astype(str).str.contains(value, case=False, na=False)]
            except Exception as e:
                messagebox.showerror("Filter Error", f"Could not apply filter:\n{e}", parent=self)
                return
        
        report_df = df[selected_columns]

        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
            title="Save Custom Report"
        )
        if not save_path: return

        try:
            report_df.to_excel(save_path, index=False)
            self.parent.log_activity("Custom Report", f"Custom report saved successfully to: {save_path}")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save the report:\n{e}", parent=self)


class TextRedirector:
    """ A class to redirect stdout to a Tkinter Text widget and a log file. """
    def __init__(self, widget, file_path):
        self.widget = widget
        self.file = open(file_path, "a", encoding="utf-8")
    def write(self, s):
        self.widget.configure(state='normal')
        self.widget.insert(tk.END, s)
        self.widget.configure(state='disabled')
        self.widget.see(tk.END)
        self.file.write(s)
    def flush(self):
        self.file.flush()


class SettingsWindow(ctk.CTkToplevel):
    """
    A Toplevel window for managing application settings from config.json.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Application Settings")
        self.geometry("800x600")

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
                    filters = json.loads(widgets['filters_var'].get() or '{}')
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

        ctk.CTkLabel(entry_frame, text="Filters (JSON):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        filters_var = tk.StringVar(value=json.dumps(config.get('filters', {})))
        ctk.CTkEntry(entry_frame, textvariable=filters_var).grid(row=2, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        ctk.CTkLabel(entry_frame, text="Exclude SKUs (comma-separated):").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        exclude_skus_var = tk.StringVar(value=", ".join(config.get('exclude_skus', [])))
        ctk.CTkEntry(entry_frame, textvariable=exclude_skus_var).grid(row=3, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        delete_button = ctk.CTkButton(entry_frame, text="Delete", fg_color="red", width=60,
                                      command=lambda f=entry_frame: self.delete_packing_list_entry(f))
        delete_button.grid(row=4, column=2, padx=5, pady=5, sticky="e")

        self.packing_list_widgets.append({
            'frame': entry_frame, 'name_var': name_var, 'filename_var': filename_var,
            'filters_var': filters_var, 'exclude_skus_var': exclude_skus_var
        })
        
    def delete_packing_list_entry(self, frame_to_delete):
        """Removes a packing list entry from the UI."""
        frame_to_delete.destroy()
        self.packing_list_widgets = [w for w in self.packing_list_widgets if w['frame'] is not frame_to_delete]

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
        ctk.CTkEntry(entry_frame, textvariable=name_var).grid(row=0, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        ctk.CTkLabel(entry_frame, text="Template Filename:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        template_var = tk.StringVar(value=config.get('template', ''))
        ctk.CTkEntry(entry_frame, textvariable=template_var).grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        ctk.CTkLabel(entry_frame, text="Filters (JSON):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        filters_var = tk.StringVar(value=json.dumps(config.get('filters', {})))
        ctk.CTkEntry(entry_frame, textvariable=filters_var).grid(row=2, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        delete_button = ctk.CTkButton(entry_frame, text="Delete", fg_color="red", width=60,
                                      command=lambda f=entry_frame: self.delete_stock_export_entry(f))
        delete_button.grid(row=3, column=2, padx=5, pady=5, sticky="e")

        self.stock_export_widgets.append({
            'frame': entry_frame, 'name_var': name_var, 'template_var': template_var, 'filters_var': filters_var
        })
        
    def delete_stock_export_entry(self, frame_to_delete):
        """Removes a stock export entry from the UI."""
        frame_to_delete.destroy()
        self.stock_export_widgets = [w for w in self.stock_export_widgets if w['frame'] is not frame_to_delete]

if __name__ == "__main__":
    app = App()
    app.mainloop()
