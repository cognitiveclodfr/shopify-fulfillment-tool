import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import sys
import os
import pandas as pd
import json
from datetime import datetime

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
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from shopify_tool import analysis, packing_lists, stock_export

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Shopify Fulfillment Tool v4.1")
        self.geometry("900x750")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.analysis_results_df = None
        self.config_path = resource_path('config.json')
        self.config = self.load_config()
        self.log_file_path = resource_path('app_history.log')

        self.create_widgets()

    def load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            messagebox.showerror("Configuration Error", f"Failed to load config.json: {e}")
            self.after(100, self.destroy)
        return None

    def create_widgets(self):
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
        actions_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.run_analysis_button = ctk.CTkButton(actions_frame, text="Run Analysis", state="disabled", command=self.start_analysis_thread)
        self.run_analysis_button.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
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

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_view.add("Execution Log")
        self.tab_view.add("Analysis Data")

        self.log_area = ctk.CTkTextbox(self.tab_view.tab("Execution Log"), wrap=tk.WORD)
        self.log_area.pack(fill="both", expand=True)
        self.log_area.configure(state='disabled')
        sys.stdout = TextRedirector(self.log_area, self.log_file_path)
        
        self.data_viewer_frame = ctk.CTkFrame(self.tab_view.tab("Analysis Data"))
        self.data_viewer_frame.pack(fill="both", expand=True)
        self.create_data_viewer()

    def create_data_viewer(self):
        style = ttk.Style()
        style.theme_use("default")
        # Base style
        style.configure("Treeview", background="#2B2B2B", foreground="white", fieldbackground="#2B2B2B", borderwidth=0)
        style.map('Treeview', background=[('selected', '#22559b')])
        # Heading style
        style.configure("Treeview.Heading", background="#565b5e", foreground="white", relief="flat")
        style.map("Treeview.Heading", background=[('active', '#3484F0')])
        
        # ⭐ NEW: Tag styles for row coloring
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
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(df.columns)
        self.tree["show"] = "headings"
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor='w')
        
        # ⭐ NEW: Apply tags based on status
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
        if "not selected" not in self.orders_file_path.get() and "not selected" not in self.stock_file_path.get():
            self.run_analysis_button.configure(state="normal")
            print("Both files loaded. Ready for analysis.")

    def start_analysis_thread(self):
        self.run_analysis_button.configure(state="disabled")
        self.packing_list_button.configure(state="disabled")
        self.stock_export_button.configure(state="disabled")
        self.report_builder_button.configure(state="disabled")
        print("\n--- Starting Analysis ---")
        threading.Thread(target=self.run_analysis_logic, daemon=True).start()

    def run_analysis_logic(self):
        try:
            stock_path = self.stock_file_path.get()
            orders_path = self.orders_file_path.get()
            output_dir = self.config['paths']['output_dir_stock']
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            output_path = os.path.join(output_dir, "fulfillment_analysis.xlsx")
            analysis.run_analysis(stock_path, orders_path, output_path)
            self.after(0, self.on_analysis_complete, True, output_path)
        except Exception as e:
            self.after(0, self.on_analysis_complete, False, str(e))

    def on_analysis_complete(self, success, result):
        if success:
            print(f"--- Analysis Completed Successfully! ---")
            messagebox.showinfo("Success", f"Analysis complete. Report saved to:\n{result}")
            self.analysis_results_df = pd.read_excel(result, sheet_name='fulfillment_analysis')
            self.update_data_viewer(self.analysis_results_df)
            self.packing_list_button.configure(state="normal")
            self.stock_export_button.configure(state="normal")
            self.report_builder_button.configure(state="normal")
            self.tab_view.set("Analysis Data")
        else:
            print(f"ERROR: {result}")
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

    # ⭐ RESTORED: Full report selection window functionality
    def create_report_window(self, report_type, title):
        window = ctk.CTkToplevel(self)
        window.title(title)
        window.geometry("400x300")
        
        reports = self.config.get(report_type, [])
        if not reports:
            ctk.CTkLabel(window, text="No reports configured in config.json.").pack(pady=20, padx=10)
            return

        for report_config in reports:
            btn = ctk.CTkButton(
                window,
                text=report_config.get('name', 'Unknown Report'),
                command=lambda rc=report_config, rt=report_type, win=window: self.start_report_thread(rc, rt, win)
            )
            btn.pack(pady=5, padx=10, fill="x")

    def start_report_thread(self, report_config, report_type, window):
        window.destroy()
        threading.Thread(target=self.run_report_logic, args=(report_config, report_type), daemon=True).start()

    def run_report_logic(self, report_config, report_type):
        try:
            # ⭐ RESTORED: Full report generation logic
            if report_type == "packing_lists":
                output_file = report_config['output_filename']
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                packing_lists.create_packing_list(
                    analysis_df=self.analysis_results_df,
                    output_file=output_file,
                    report_name=report_config['name'],
                    filters=report_config.get('filters')
                )
            elif report_type == "stock_exports":
                templates_path = resource_path(self.config['paths']['templates'])
                output_path = self.config['paths']['output_dir_stock']
                template_name = report_config['template']
                template_full_path = os.path.join(templates_path, template_name)
                
                datestamp = datetime.now().strftime("%Y-%m-%d")
                name, ext = os.path.splitext(template_name)
                output_filename = f"{name}_{datestamp}{ext}"
                
                os.makedirs(output_path, exist_ok=True)
                output_full_path = os.path.join(output_path, output_filename)

                stock_export.create_stock_export(
                    analysis_df=self.analysis_results_df,
                    template_file=template_full_path,
                    output_file=output_full_path,
                    report_name=report_config['name'],
                    filters=report_config.get('filters')
                )
            self.after(0, messagebox.showinfo, "Success", f"Report '{report_config['name']}' created successfully.")
        except Exception as e:
            self.after(0, messagebox.showerror, "Error", f"Failed to create report '{report_config['name']}':\n{e}")


class ReportBuilderWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Report Builder")
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_widgets()

    def create_widgets(self):
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        controls_frame.grid_columnconfigure(0, weight=1)

        # --- Columns Selection ---
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

        # --- Filter Section ---
        filter_frame = ctk.CTkFrame(controls_frame)
        filter_frame.grid(row=1, column=0, padx=5, pady=10, sticky="ew")
        ctk.CTkLabel(filter_frame, text="Step 2: Add a Filter (Optional)", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0,5))
        
        self.filter_column_var = ctk.StringVar(value=all_columns[0])
        self.filter_operator_var = ctk.StringVar(value="==")
        self.filter_value_var = ctk.StringVar()

        ctk.CTkComboBox(filter_frame, values=list(all_columns), variable=self.filter_column_var).pack(side="left", padx=5)
        ctk.CTkComboBox(filter_frame, values=["==", "!=", ">", "<", "contains"], variable=self.filter_operator_var).pack(side="left", padx=5)
        ctk.CTkEntry(filter_frame, placeholder_text="Value", textvariable=self.filter_value_var).pack(side="left", padx=5, fill="x", expand=True)

        # --- Generate Button ---
        generate_btn = ctk.CTkButton(self, text="Step 3: Generate and Save Custom Report", command=self.generate_custom_report, height=40)
        generate_btn.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

    def generate_custom_report(self):
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
            messagebox.showinfo("Success", f"Custom report saved successfully to:\n{save_path}", parent=self)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save the report:\n{e}", parent=self)


class TextRedirector:
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

if __name__ == "__main__":
    app = App()
    app.mainloop()

