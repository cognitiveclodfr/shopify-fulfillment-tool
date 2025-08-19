import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd

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
