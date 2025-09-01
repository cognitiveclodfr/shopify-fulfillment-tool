import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import sys
import os
import pandas as pd
import json
import logging
import pickle
import shutil
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

    def update_text(self, new_text):
        self.text = new_text

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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from shopify_tool import core
from shopify_tool.utils import get_persistent_data_path, resource_path
from shopify_tool.analysis import recalculate_statistics, toggle_order_fulfillment
from gui.report_builder_window import ReportBuilderWindow
from gui.settings_window import SettingsWindow
from gui.column_manager_window import ColumnManagerWindow
from gui.log_viewer import LogViewer


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.is_syncing = False
        self.title("Shopify Fulfillment Tool v8.0.0")
        self.geometry("950x800")
        ctk.set_appearance_mode("Dark")
        self.configure(fg_color="#111827") # Set main background color

        # --- Style Configuration ---
        self.STYLE = {
            "font_family": ("Segoe UI",),
            "font_normal": (("Segoe UI", 12)),
            "font_bold": (("Segoe UI", 12, "bold")),
            "font_table_header": (("Segoe UI", 10)),
            "font_h1": (("Segoe UI", 18, "bold")),
            "font_h2": (("Segoe UI", 14, "bold")),
            "color_accent": "#4b36e3",
            "color_destructive": "#5E2E2E",
            "color_success": "#2A4B3A",
            "color_warning": "#756B0D",
            "color_gray": "#6B7280",
            "color_border": "#374151",      # Gray-700
            "color_bg_main": "#111827",     # Gray-900
            "color_bg_frame": "#1F2937",    # Gray-800
            "color_text": "#D1D5DB",        # Gray-300
            "corner_radius": 8,
            "padding_outer": 10,
            "padding_inner": 5
        }

        self.analysis_results_df = None
        self.all_columns = []
        self.visible_columns = []
        self.analysis_stats = None # To store the stats dictionary
        self.session_path = None

        # Initialize and load configuration
        self.config = None
        self.config_path = None # Will be set by _init_and_load_config
        self._init_and_load_config()

        # Use persistent path for log file and session file
        self.log_file_path = get_persistent_data_path('app_history.log')
        self.session_file = get_persistent_data_path('session_data.pkl')

        self.create_widgets()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.load_session()

    def on_closing(self):
        """Handle the event of the window closing by automatically saving the session."""
        if self.analysis_results_df is not None and not self.analysis_results_df.empty:
            logger.info(f"Attempting to save session to {self.session_file}")
            try:
                session_data = {
                    'dataframe': self.analysis_results_df,
                    'visible_columns': self.visible_columns
                }
                with open(self.session_file, 'wb') as f:
                    pickle.dump(session_data, f)
                logger.info(f"Session saved successfully to {self.session_file}")
            except Exception as e:
                logger.error(f"Error saving session automatically: {e}", exc_info=True)
        else:
            logger.info("No data to save, skipping session save.")
        self.destroy()

    def load_session(self):
        """Check for and load a previous session file."""
        logger.info(f"Checking for session file at {self.session_file}...")
        if os.path.exists(self.session_file):
            logger.info("Session file found.")
            if messagebox.askyesno("Restore Session", "A previous session was found. Do you want to restore it?", parent=self):
                logger.info("User chose to restore session.")
                try:
                    with open(self.session_file, 'rb') as f:
                        session_data = pickle.load(f)

                    self.analysis_results_df = session_data.get('dataframe')
                    self.visible_columns = session_data.get('visible_columns', list(self.analysis_results_df.columns))

                    logger.info("Session data loaded. Updating UI.")
                    # Manually trigger the post-analysis UI updates
                    self.analysis_stats = recalculate_statistics(self.analysis_results_df)
                    self._post_analysis_ui_update()
                    self.log_activity("Session", "Restored previous session.")
                    logger.info("UI updated with restored session data.")

                except Exception as e:
                    logger.error(f"Failed to load session file: {e}", exc_info=True)
                    messagebox.showerror("Load Error", f"Failed to load session file: {e}", parent=self)
            else:
                logger.info("User chose not to restore session.")

            # Always remove the file after checking to prevent re-loading the same session
            try:
                os.remove(self.session_file)
                logger.info(f"Session file {self.session_file} removed.")
            except Exception as e:
                logger.error(f"Failed to remove session file: {e}", exc_info=True)
        else:
            logger.info("No session file found.")

    def _init_and_load_config(self):
        """
        Initializes the configuration by ensuring a user-specific config file exists,
        copying a default if it doesn't, and then loading it.
        """
        persistent_config_path = get_persistent_data_path('config.json')
        default_config_path = resource_path('config.json')

        # If a user config doesn't exist, create one from the default.
        if not os.path.exists(persistent_config_path):
            logger.info(f"User config not found at {persistent_config_path}. Copying default config.")
            try:
                shutil.copy(default_config_path, persistent_config_path)
            except Exception as e:
                messagebox.showerror("Fatal Error", f"Could not create user configuration file: {e}")
                self.after(100, self.destroy)
                return

        # Now, use the persistent path for all operations.
        self.config_path = persistent_config_path

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            messagebox.showerror("Configuration Error", f"Failed to load config.json: {e}")
            self.after(100, self.destroy)

    def create_widgets(self):
        """ Creates all the widgets for the main application window. """
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # --- Session Control Frame ---
        session_frame = ctk.CTkFrame(self)
        session_frame.grid(row=0, column=0, padx=self.STYLE['padding_outer'], pady=self.STYLE['padding_outer'], sticky="ew")
        session_frame.grid_columnconfigure(1, weight=1)

        new_session_btn = ctk.CTkButton(session_frame, text="Create New Session", command=self._create_new_session, fg_color=self.STYLE['color_accent'])
        new_session_btn.grid(row=0, column=0, padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'])

        self.session_path_label = ctk.CTkLabel(session_frame, text="No session started.", text_color=self.STYLE['color_gray'], font=self.STYLE['font_normal'])
        self.session_path_label.grid(row=0, column=1, padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'], sticky="w")

        # --- File Loading Frame ---
        files_frame = ctk.CTkFrame(self)
        files_frame.grid(row=1, column=0, padx=self.STYLE['padding_outer'], pady=(0, self.STYLE['padding_outer']), sticky="ew")
        files_frame.grid_columnconfigure(1, weight=1)

        self.orders_file_path = tk.StringVar(value="Orders file not selected")
        self.stock_file_path = tk.StringVar(value="Stock file not selected")

        self.load_orders_btn = ctk.CTkButton(files_frame, text="Load Orders File (.csv)", command=self.select_orders_file, state=tk.DISABLED)
        self.load_orders_btn.grid(row=0, column=0, padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'])
        ToolTip(self.load_orders_btn, "Select the orders_export.csv file from Shopify.")

        ctk.CTkLabel(files_frame, textvariable=self.orders_file_path, font=self.STYLE['font_normal']).grid(row=0, column=1, padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'], sticky="w")
        self.orders_file_status_label = ctk.CTkLabel(files_frame, text="", width=20)
        self.orders_file_status_label.grid(row=0, column=2, padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'], sticky="w")
        self.orders_file_tooltip = ToolTip(self.orders_file_status_label, "")

        self.load_stock_btn = ctk.CTkButton(files_frame, text="Load Stock File (.csv)", command=self.select_stock_file, state=tk.DISABLED)
        self.load_stock_btn.grid(row=1, column=0, padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'])
        ToolTip(self.load_stock_btn, "Select the inventory/stock CSV file.")

        ctk.CTkLabel(files_frame, textvariable=self.stock_file_path, font=self.STYLE['font_normal']).grid(row=1, column=1, padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'], sticky="w")
        self.stock_file_status_label = ctk.CTkLabel(files_frame, text="", width=20)
        self.stock_file_status_label.grid(row=1, column=2, padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'], sticky="w")
        self.stock_file_tooltip = ToolTip(self.stock_file_status_label, "")

        actions_frame = ctk.CTkFrame(self)
        actions_frame.grid(row=2, column=0, padx=self.STYLE['padding_outer'], pady=0, sticky="ew")
        actions_frame.grid_columnconfigure(1, weight=3) # Give the main action column more weight
        actions_frame.grid_columnconfigure(0, weight=1)

        # --- Reports Frame (Left Column) ---
        reports_frame = ctk.CTkFrame(actions_frame)
        reports_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'])
        reports_frame.grid_columnconfigure(0, weight=1)

        self.packing_list_button = ctk.CTkButton(reports_frame, text="Create Packing List", state="disabled", command=self.open_packing_list_window, corner_radius=self.STYLE['corner_radius'])
        self.packing_list_button.grid(row=0, column=0, padx=self.STYLE['padding_inner'], pady=(self.STYLE['padding_inner'], 2), sticky="ew")
        ToolTip(self.packing_list_button, "Generate packing lists based on pre-defined filters.")

        self.stock_export_button = ctk.CTkButton(reports_frame, text="Create Stock Export", state="disabled", command=self.open_stock_export_window, corner_radius=self.STYLE['corner_radius'])
        self.stock_export_button.grid(row=1, column=0, padx=self.STYLE['padding_inner'], pady=2, sticky="ew")
        ToolTip(self.stock_export_button, "Generate stock export files for couriers.")

        self.report_builder_button = ctk.CTkButton(reports_frame, text="Report Builder", state="disabled", command=self.open_report_builder_window, corner_radius=self.STYLE['corner_radius'])
        self.report_builder_button.grid(row=2, column=0, padx=self.STYLE['padding_inner'], pady=(2, self.STYLE['padding_inner']), sticky="ew")
        ToolTip(self.report_builder_button, "Create a custom report with your own filters and columns.")

        # --- Main Actions (Right Column) ---
        main_actions_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        main_actions_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")
        main_actions_frame.grid_columnconfigure(0, weight=1)
        main_actions_frame.grid_rowconfigure(0, weight=1)

        self.run_analysis_button = ctk.CTkButton(main_actions_frame, text="Run Analysis", state="disabled", command=self.start_analysis_thread, fg_color=self.STYLE['color_accent'], height=60, corner_radius=self.STYLE['corner_radius'])
        self.run_analysis_button.grid(row=0, column=0, padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'], sticky="nsew")
        ToolTip(self.run_analysis_button, "Start the fulfillment analysis based on the loaded files.")

        self.settings_button = ctk.CTkButton(main_actions_frame, text="⚙️", command=self.open_settings_window, fg_color=self.STYLE['color_gray'], width=40, height=40, corner_radius=self.STYLE['corner_radius'])
        self.settings_button.grid(row=1, column=0, padx=self.STYLE['padding_inner'], pady=(0, self.STYLE['padding_inner']), sticky="se")
        ToolTip(self.settings_button, "Open the application settings window.")

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=3, column=0, padx=self.STYLE['padding_outer'], pady=self.STYLE['padding_outer'], sticky="nsew")
        self.tab_view.add("Execution Log")
        self.tab_view.add("Activity Log")
        self.tab_view.add("Analysis Data")
        self.tab_view.add("Statistics")

        # --- Setup Tabs ---
        log_viewer_frame = self.tab_view.tab("Execution Log")
        # The LogViewer is a complex widget, we add a containing frame for the border
        log_container = ctk.CTkFrame(log_viewer_frame, border_width=1, border_color=self.STYLE['color_border'])
        log_container.pack(fill="both", expand=True, padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'])
        self.log_viewer = LogViewer(log_container)
        self.log_viewer.pack(fill="both", expand=True)

        self.activity_log_frame = ctk.CTkFrame(self.tab_view.tab("Activity Log"), border_width=1, border_color=self.STYLE['color_border'])
        self.activity_log_frame.pack(fill="both", expand=True, padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'])
        self.create_activity_log()

        self.stats_frame = ctk.CTkFrame(self.tab_view.tab("Statistics"), border_width=1, border_color=self.STYLE['color_border'])
        self.stats_frame.pack(fill="both", expand=True, padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'])
        self.create_statistics_tab()

        self.data_viewer_frame = ctk.CTkFrame(self.tab_view.tab("Analysis Data"), border_width=1, border_color=self.STYLE['color_border'])
        self.data_viewer_frame.pack(fill="both", expand=True, padx=self.STYLE['padding_inner'], pady=self.STYLE['padding_inner'])
        self.create_data_viewer()

    def create_statistics_tab(self):
        """ Creates the UI elements for the Statistics tab. """
        # Configure column weights for stability
        self.stats_frame.grid_columnconfigure(0, weight=0)
        self.stats_frame.grid_columnconfigure(1, weight=1)

        self.stats_labels = {}
        stat_keys = {
            "total_orders_completed": "Total Orders Completed:",
            "total_orders_not_completed": "Total Orders Not Completed:",
            "total_items_to_write_off": "Total Items to Write Off:",
            "total_items_not_to_write_off": "Total Items Not to Write Off:",
        }

        row_counter = 0
        for key, text in stat_keys.items():
            label = ctk.CTkLabel(self.stats_frame, text=text, font=self.STYLE['font_h2'], anchor="w")
            label.grid(row=row_counter, column=0, sticky="ew", padx=self.STYLE['padding_outer'], pady=self.STYLE['padding_inner'])
            value_label = ctk.CTkLabel(self.stats_frame, text="-", font=self.STYLE['font_h2'], anchor="w")
            value_label.grid(row=row_counter, column=1, sticky="ew", padx=self.STYLE['padding_outer'], pady=self.STYLE['padding_inner'])
            self.stats_labels[key] = value_label
            row_counter += 1

        courier_header = ctk.CTkLabel(self.stats_frame, text="Couriers Stats:", font=self.STYLE['font_h2'], anchor="w")
        courier_header.grid(row=row_counter, column=0, columnspan=2, sticky="ew", padx=self.STYLE['padding_outer'], pady=(15, self.STYLE['padding_inner']))
        row_counter += 1

        self.courier_stats_frame = ctk.CTkFrame(self.stats_frame)
        self.courier_stats_frame.grid(row=row_counter, column=0, columnspan=2, sticky="ew", padx=self.STYLE['padding_outer'])
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

    def _sync_treeview_y_scroll(self, *args):
        """Callback to synchronize the y-scroll of both treeviews."""
        self.frozen_tree.yview(*args)
        self.main_tree.yview(*args)

    def _sync_treeview_selection(self, event, tree_from, tree_to):
        """Callback to synchronize selection between the two treeviews."""
        selection = tree_from.selection()

        # If the selection is already the same, do nothing. This is the key to preventing loops.
        if selection == tree_to.selection():
            return

        # The is_syncing flag is a secondary guard against potential race conditions.
        if self.is_syncing:
            return

        self.is_syncing = True
        logger.debug(f"Syncing selection from {tree_from} to {tree_to}. Selection: {selection}")
        tree_to.selection_set(selection)
        if selection:
            tree_to.focus(selection[0])
        self.is_syncing = False

    def create_data_viewer(self):
        """ Creates the Treeview widget for displaying analysis data. """
        # Configure the grid
        self.data_viewer_frame.grid_rowconfigure(1, weight=1)
        self.data_viewer_frame.grid_columnconfigure(1, weight=1) # Main tree gets weight

        # Top bar for controls
        top_bar = ctk.CTkFrame(self.data_viewer_frame, fg_color="transparent")
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        self.column_manager_button = ctk.CTkButton(top_bar, text="Manage Columns", command=self.open_column_manager, state="disabled")
        self.column_manager_button.pack(side="left")

        # Treeview frame
        tree_frame = ctk.CTkFrame(self.data_viewer_frame, fg_color="transparent")
        tree_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(1, weight=1) # Main tree container gets weight

        style = ttk.Style()
        style.theme_use("default")

        # --- Base Treeview Style ---
        # Increased row height for better spacing and readability.
        style.configure("Treeview",
                        background=self.STYLE['color_bg_frame'],
                        foreground=self.STYLE['color_text'],
                        fieldbackground=self.STYLE['color_bg_frame'],
                        borderwidth=0,
                        rowheight=28) # Increased row height
        style.map('Treeview', background=[('selected', self.STYLE['color_accent'])])

        # --- Heading Style ---
        # Using fonts and colors from the central STYLE dictionary.
        style.configure("Treeview.Heading",
                        background=self.STYLE['color_bg_main'],
                        foreground=self.STYLE['color_text'],
                        relief="flat",
                        font=self.STYLE['font_table_header'])
        style.map("Treeview.Heading", background=[('active', self.STYLE['color_border'])])

        # The Fulfillable/NotFulfillable styles are now defined by tags, not a separate Treeview style.
        # This simplifies the logic in update_data_viewer.

        # --- Frozen Tree (for Order_Number) ---
        self.frozen_tree = ttk.Treeview(tree_frame, style="Treeview", show="headings")
        self.frozen_tree.grid(row=0, column=0, sticky="nsew")

        # --- Main Tree (for all other columns) ---
        self.main_tree = ttk.Treeview(tree_frame, style="Treeview", show="headings")
        self.main_tree.grid(row=0, column=1, sticky="nsew")

        # --- Scrollbars ---
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._sync_treeview_y_scroll)
        vsb.grid(row=0, column=2, sticky="ns")
        self.frozen_tree.configure(yscrollcommand=vsb.set)
        self.main_tree.configure(yscrollcommand=vsb.set)

        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.main_tree.xview)
        hsb.grid(row=1, column=1, sticky="ew") # Only for the main tree
        self.main_tree.configure(xscrollcommand=hsb.set)

        # --- Bindings ---
        self.frozen_tree.bind("<Double-1>", self._on_order_double_click)
        self.main_tree.bind("<Double-1>", self._on_order_double_click)
        self.frozen_tree.bind("<Button-3>", self._show_context_menu)
        self.main_tree.bind("<Button-3>", self._show_context_menu)
        self.frozen_tree.bind("<<TreeviewSelect>>", lambda e: self._sync_treeview_selection(e, self.frozen_tree, self.main_tree))
        self.main_tree.bind("<<TreeviewSelect>>", lambda e: self._sync_treeview_selection(e, self.main_tree, self.frozen_tree))
        self.frozen_tree.bind("<MouseWheel>", self._on_mousewheel)
        self.main_tree.bind("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        """Synchronize mouse wheel scrolling between the two trees."""
        # The delta value is different on different platforms, so we normalize it
        # to a simple up/down direction. The number of units can be adjusted for speed.
        if event.num == 5 or event.delta < 0:
            delta = 2
        else:
            delta = -2

        self.frozen_tree.yview_scroll(delta, "units")
        self.main_tree.yview_scroll(delta, "units")
        return "break" # Prevents the event from propagating further

    def _show_context_menu(self, event):
        """Creates and displays a context menu for the clicked treeview item."""
        tree = event.widget
        item_id = tree.identify_row(event.y)
        if not item_id:
            return

        # The user's click already sets the focus.
        # Programmatically setting selection here caused a recursive loop.
        # We just need to identify the item under the cursor.

        try:
            order_number = self.frozen_tree.item(item_id, 'values')[0]
            # SKU is in the main tree. Find its index.
            sku_index = self.main_tree['columns'].index('SKU')
            sku = self.main_tree.item(item_id, 'values')[sku_index]
        except (ValueError, IndexError):
            return # Clicked on a non-data row or something went wrong

        menu = tk.Menu(self, tearoff=0)

        menu.add_command(label="Change Status", command=lambda: self.toggle_fulfillment_status(order_number))
        menu.add_command(label="Copy Order Number", command=lambda: self._copy_to_clipboard(order_number))
        menu.add_command(label="Copy SKU", command=lambda: self._copy_to_clipboard(sku))
        menu.add_command(label="Add Tag Manually...", command=lambda: self._add_tag_manually(item_id))
        menu.add_separator()
        menu.add_command(label="Remove This Item from Order", command=lambda: self._remove_item_from_order(item_id, order_number, sku))
        menu.add_command(label="Remove Entire Order", command=lambda: self._remove_entire_order(order_number))

        menu.tk_popup(event.x_root, event.y_root)

    def _copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.log_activity("Clipboard", f"Copied '{text}' to clipboard.")

    def _add_tag_manually(self, item_id):
        dialog = ctk.CTkInputDialog(text="Enter tag to add:", title="Add Manual Tag")
        tag_to_add = dialog.get_input()

        if tag_to_add:
            # Find all rows for this order to apply the tag consistently
            order_number = self.frozen_tree.item(item_id, 'values')[0]
            order_rows_indices = self.analysis_results_df[self.analysis_results_df['Order_Number'] == order_number].index

            # Ensure the Status_Note column exists
            if 'Status_Note' not in self.analysis_results_df.columns:
                self.analysis_results_df['Status_Note'] = ''

            for index in order_rows_indices:
                current_notes = self.analysis_results_df.loc[index, 'Status_Note']
                if pd.isna(current_notes) or current_notes == '':
                    new_notes = tag_to_add
                elif tag_to_add not in current_notes.split(','):
                    new_notes = f"{current_notes}, {tag_to_add}"
                else:
                    new_notes = current_notes
                self.analysis_results_df.loc[index, 'Status_Note'] = new_notes

            self.update_data_viewer(self.analysis_results_df)
            self.log_activity("Manual Tag", f"Added note '{tag_to_add}' to order {order_number}.")

    def _remove_item_from_order(self, item_id, order_number, sku):
        if not messagebox.askyesno("Confirm", f"Are you sure you want to remove item {sku} from order {order_number}?\nThis cannot be undone.", parent=self):
            return

        # We need the original index from the dataframe to remove it
        # This is a bit tricky since tree iid is not the df index.
        # We can find the unique row by combining order number and sku, and assuming no duplicate skus in an order in the raw file.
        # A more robust way would be to store df index in the tree, but for now this should work.

        # Find the specific row in the DataFrame to remove
        df_indices = self.analysis_results_df[
            (self.analysis_results_df['Order_Number'] == order_number) &
            (self.analysis_results_df['SKU'] == sku)
        ].index

        if not df_indices.empty:
            # For now, remove the first match if there are duplicates
            self.analysis_results_df.drop(df_indices[0], inplace=True)
            self.analysis_results_df.reset_index(drop=True, inplace=True)

            self.update_data_viewer(self.analysis_results_df)
            self.analysis_stats = recalculate_statistics(self.analysis_results_df)
            self.update_statistics_tab()
            self.log_activity("Data Edit", f"Removed item {sku} from order {order_number}.")

    def _remove_entire_order(self, order_number):
        if not messagebox.askyesno("Confirm", f"Are you sure you want to remove the entire order {order_number}?\nThis cannot be undone.", parent=self):
            return

        self.analysis_results_df = self.analysis_results_df[
            self.analysis_results_df['Order_Number'] != order_number
        ].reset_index(drop=True)

        self.update_data_viewer(self.analysis_results_df)
        self.analysis_stats = recalculate_statistics(self.analysis_results_df)
        self.update_statistics_tab()
        self.log_activity("Data Edit", f"Removed order {order_number}.")

    def _on_order_double_click(self, event):
        """Event handler for double-clicking an order in the Analysis Data table."""
        if self.analysis_results_df is None: return

        # Identify which tree received the click
        tree = event.widget
        item_id = tree.focus()
        if not item_id: return

        try:
            # Always get the order number from the frozen tree, it's reliable
            order_number = self.frozen_tree.item(item_id, 'values')[0]
            self.toggle_fulfillment_status(order_number)
        except (ValueError, IndexError) as e:
            logger.warning(f"Could not process double-click, likely on a non-data row: {e}")

    def update_data_viewer(self, df):
        """ Clears and repopulates both Treeviews with new DataFrame data. """
        self.frozen_tree.delete(*self.frozen_tree.get_children())
        self.main_tree.delete(*self.main_tree.get_children())

        if df is None or df.empty:
            self.all_columns = []
            self.visible_columns = []
            self.column_manager_button.configure(state="disabled")
            return

        # First time loading data, initialize column lists
        if not self.all_columns:
            self.all_columns = list(df.columns)
            # Ensure Order_Number is not in the list of columns to be managed
            if 'Order_Number' in self.all_columns:
                self.all_columns.remove('Order_Number')
            self.visible_columns = self.all_columns[:] # Initially all are visible

        # Configure Frozen Tree
        self.frozen_tree["columns"] = ['Order_Number']
        self.frozen_tree.heading('Order_Number', text='Order_Number')
        self.frozen_tree.column('Order_Number', width=120, anchor='w')

        # Configure Main Tree
        self.main_tree["columns"] = self.all_columns
        self.main_tree["displaycolumns"] = self.visible_columns
        for col in self.all_columns:
            self.main_tree.heading(col, text=col)
            self.main_tree.column(col, width=100, anchor='w')

        # Common tag configurations
        for tree in [self.frozen_tree, self.main_tree]:
            # Configure tags for fulfillment status with colors from the STYLE dict
            tree.tag_configure("Fulfillable", background=self.STYLE['color_success'], foreground=self.STYLE['color_text'])
            tree.tag_configure("NotFulfillable", background=self.STYLE['color_destructive'], foreground=self.STYLE['color_text'])

            # Zebra-striping is being removed. The base background is set in the main "Treeview" style.

            # New tag for highlighting rows with system notes (e.g., 'Repeat')
            tree.tag_configure("SystemNoteHighlight", background=self.STYLE['color_warning'], foreground=self.STYLE['color_text']) # Light text for contrast

            # New tag to create a visual separator line after an order
            tree.tag_configure("order_separator", background=self.STYLE['color_border'])

        # Pre-calculate which rows are the last item of an order for the separator line
        is_last_item = df['Order_Number'] != df['Order_Number'].shift(-1)

        # Inserting data
        for index, row in df.iterrows():
            tags = []

            # First, determine the primary background color tag based on status.
            system_note = row.get("System_note", "")
            if pd.notna(system_note) and system_note != '':
                tags.append("SystemNoteHighlight")
            else:
                status = row.get("Order_Fulfillment_Status", "")
                if status == "Fulfillable":
                    tags.append("Fulfillable")
                elif status == "Not Fulfillable":
                    tags.append("NotFulfillable")
                # If no status, it will have the default background.

            # Separately, if this is the last item of an order, add the separator tag.
            # The Treeview will use the background from the last tag in the list,
            # so this will override the status color for this specific row.
            if is_last_item[index]:
                tags.append("order_separator")

            # Insert into frozen tree
            order_number_val = (row['Order_Number'],)
            frozen_iid = self.frozen_tree.insert("", "end", values=order_number_val, tags=tuple(tags))

            # Insert into main tree with the same iid
            main_values = list(row.drop('Order_Number'))
            self.main_tree.insert("", "end", iid=frozen_iid, values=main_values, tags=tuple(tags))

        self.column_manager_button.configure(state="normal")

    def open_column_manager(self):
        """Opens the column management window."""
        if not self.all_columns:
            messagebox.showwarning("No Data", "Please run an analysis to load data first.", parent=self)
            return
        # Pass the list of non-frozen columns to the manager
        ColumnManagerWindow(self, self.all_columns, self.visible_columns)

    def update_tree_columns(self, new_visible_columns):
        """Callback function from the ColumnManagerWindow to update the main tree."""
        self.visible_columns = new_visible_columns
        self.main_tree["displaycolumns"] = self.visible_columns

    def select_orders_file(self):
        filepath = filedialog.askopenfilename(title="Select Orders File", filetypes=[("CSV files", "*.csv")])
        if filepath:
            self.orders_file_path.set(filepath)
            logger.info(f"Orders file selected: {filepath}")
            self.start_validation_thread(filepath, 'orders')
            self.check_files_selected()

    def select_stock_file(self):
        filepath = filedialog.askopenfilename(title="Select Stock File", filetypes=[("CSV files", "*.csv")])
        if filepath:
            self.stock_file_path.set(filepath)
            logger.info(f"Stock file selected: {filepath}")
            self.start_validation_thread(filepath, 'stock')
            self.check_files_selected()

    def check_files_selected(self):
        """ Enables the 'Run Analysis' button if both files are selected. """
        if "not selected" not in self.orders_file_path.get() and "not selected" not in self.stock_file_path.get():
            self.run_analysis_button.configure(state="normal")
            logger.info("Both files loaded. Ready for analysis.")

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
        if not self.session_path:
            self.after(0, messagebox.showerror, "Session Error", "Please create a new session before running an analysis.")
            return

        stock_path = self.stock_file_path.get()
        orders_path = self.orders_file_path.get()
        stock_delimiter = self.config['settings']['stock_csv_delimiter']

        try:
            success, result, df, stats = core.run_full_analysis(
                stock_path,
                orders_path,
                self.session_path, # Use the session path as the output directory
                stock_delimiter,
                self.config
            )
        except Exception as e:
            # Forward exception to GUI thread handler
            logger.error(f"An exception occurred in the analysis thread: {e}", exc_info=True)
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
            self._post_analysis_ui_update()
        else:
            messagebox.showerror("Analysis Error", f"An error occurred during analysis:\n{result}")

        self.run_analysis_button.configure(state="normal")

    def _post_analysis_ui_update(self):
        """Centralized method to update UI elements after analysis or session load."""
        self.update_data_viewer(self.analysis_results_df)
        self.update_statistics_tab()

        self.packing_list_button.configure(state="normal")
        self.stock_export_button.configure(state="normal")
        self.report_builder_button.configure(state="normal")
        self.tab_view.set("Statistics")

    def start_validation_thread(self, file_path, file_type):
        """Starts a new thread to validate the CSV headers."""
        threading.Thread(target=self.run_validation_logic, args=(file_path, file_type), daemon=True).start()

    def run_validation_logic(self, file_path, file_type):
        """The logic that runs in a separate thread to validate a file."""
        if file_type == 'orders':
            required_cols = self.config.get('column_mappings', {}).get('orders_required', [])
            delimiter = ','
        else: # stock
            required_cols = self.config.get('column_mappings', {}).get('stock_required', [])
            delimiter = self.config.get('settings', {}).get('stock_csv_delimiter', ';')

        is_valid, missing_cols = core.validate_csv_headers(file_path, required_cols, delimiter)

        # Schedule the UI update on the main thread
        self.after(0, self.on_validation_complete, file_type, is_valid, missing_cols)

    def on_validation_complete(self, file_type, is_valid, missing_cols):
        """Handles the result of the validation and updates the UI."""
        if file_type == 'orders':
            label = self.orders_file_status_label
            tooltip = self.orders_file_tooltip
        else: # stock
            label = self.stock_file_status_label
            tooltip = self.stock_file_tooltip

        if is_valid:
            label.configure(text="✓", text_color="green", font=("Arial", 16, "bold"))
            tooltip.update_text("File is valid.")
        else:
            label.configure(text="✗", text_color="red", font=("Arial", 16, "bold"))
            error_message = f"Missing columns: {', '.join(missing_cols)}"
            tooltip.update_text(error_message)

    def _create_new_session(self):
        """Creates a new session by creating a unique dated folder for outputs."""
        try:
            base_output_dir = self.config['paths'].get('output_dir_stock', 'data/output')
            date_str = datetime.now().strftime('%Y-%m-%d')

            session_id = 1
            while True:
                session_path = os.path.join(base_output_dir, f"{date_str}_session_{session_id}")
                if not os.path.exists(session_path):
                    break
                session_id += 1

            os.makedirs(session_path, exist_ok=True)
            self.session_path = session_path

            self.session_path_label.configure(text=f"Current Session: {os.path.basename(self.session_path)}", text_color="white")
            self.log_activity("Session", f"New session started. Output will be saved to: {self.session_path}")

            # Enable file loading buttons
            self.load_orders_btn.configure(state=tk.NORMAL)
            self.load_stock_btn.configure(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("Session Error", f"Could not create a new session folder.\nError: {e}")


    def _on_order_double_click(self, event):
        """Event handler for double-clicking an order in the Analysis Data table."""
        if self.analysis_results_df is None:
            return  # Don't do anything if no data is loaded

        item_id = self.tree.focus()
        if not item_id:
            return

        try:
            values = self.tree.item(item_id, 'values')
            order_number_index = self.tree["columns"].index('Order_Number')
            order_number = values[order_number_index]

            # Call the refactored method
            self.toggle_fulfillment_status(order_number)

        except (ValueError, IndexError) as e:
            print(f"Could not process double-click: {e}")

    def toggle_fulfillment_status(self, order_number):
        """
        UI-facing method to handle toggling fulfillment status.
        Calls the core logic, and then updates the UI.
        """
        success, result, updated_df = toggle_order_fulfillment(self.analysis_results_df, order_number)

        if success:
            self.analysis_results_df = updated_df
            # Recalculate stats and update the UI
            self.analysis_stats = recalculate_statistics(self.analysis_results_df)
            self.update_data_viewer(self.analysis_results_df)
            self.update_statistics_tab()

            # Log the successful action
            new_status = self.analysis_results_df.loc[self.analysis_results_df['Order_Number'] == order_number, 'Order_Fulfillment_Status'].iloc[0]
            self.log_activity("Manual Edit", f"Order {order_number} status changed to '{new_status}'.")
        else:
            # Show an error message if the toggle failed
            messagebox.showerror("Error", result)


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
        if not self.session_path:
            self.after(0, messagebox.showerror, "Session Error", "Please create a new session before generating reports.")
            return

        if report_type == "packing_lists":
            # The filename from config is now relative to the session path
            relative_path = report_config.get('output_filename', 'default_packing_list.xlsx')
            output_file = os.path.join(self.session_path, os.path.basename(relative_path))

            # Update the report_config with the new full path for the core function
            report_config_copy = report_config.copy()
            report_config_copy['output_filename'] = output_file

            success, message = core.create_packing_list_report(
                analysis_df=self.analysis_results_df,
                report_config=report_config_copy
            )
        elif report_type == "stock_exports":
            templates_path = resource_path(self.config['paths']['templates'])
            # The output_path is now the session path, not the one from config
            success, message = core.create_stock_export_report(
                analysis_df=self.analysis_results_df,
                report_config=report_config,
                templates_path=templates_path,
                output_path=self.session_path
            )
        else:
            success = False
            message = "Unknown report type."

        if success:
            self.after(0, self.log_activity, "Report Generation", message)
        else:
            self.after(0, messagebox.showerror, "Error", message)


if __name__ == "__main__":
    app = App()
    app.mainloop()
