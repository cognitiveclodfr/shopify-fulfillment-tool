import customtkinter as ctk
import tkinter as tk

class ColumnManagerWindow(ctk.CTkToplevel):
    """A Toplevel window for managing Treeview columns."""

    def __init__(self, parent, all_columns, visible_columns):
        super().__init__(parent)
        self.parent_app = parent
        self.all_columns = all_columns

        # The order of visible_columns matters
        self.visible_columns_list = visible_columns
        self.hidden_columns_list = sorted([c for c in all_columns if c not in visible_columns])

        self.title("Manage Columns")
        self.geometry("600x450")
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure((0, 2), weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._create_widgets()
        self.wait_window(self)

    def _create_widgets(self):
        # --- Visible Columns Listbox ---
        visible_frame = ctk.CTkFrame(self)
        visible_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        visible_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(visible_frame, text="Visible Columns").grid(row=0, column=0, padx=5, pady=5)
        self.visible_listbox = tk.Listbox(visible_frame, selectmode="extended")
        self.visible_listbox.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        for col in self.visible_columns_list:
            self.visible_listbox.insert(tk.END, col)

        # --- Control Buttons Frame ---
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.grid(row=0, column=1, padx=5, pady=10, sticky="ns")

        add_btn = ctk.CTkButton(controls_frame, text="<", width=40, command=self._move_to_visible)
        add_btn.pack(pady=5)
        remove_btn = ctk.CTkButton(controls_frame, text=">", width=40, command=self._move_to_hidden)
        remove_btn.pack(pady=5)

        # --- Hidden Columns Listbox ---
        hidden_frame = ctk.CTkFrame(self)
        hidden_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        hidden_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(hidden_frame, text="Hidden Columns").grid(row=0, column=0, padx=5, pady=5)
        self.hidden_listbox = tk.Listbox(hidden_frame, selectmode="extended")
        self.hidden_listbox.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        for col in self.hidden_columns_list:
            self.hidden_listbox.insert(tk.END, col)

        # --- Reordering Buttons ---
        reorder_frame = ctk.CTkFrame(self, fg_color="transparent")
        reorder_frame.grid(row=0, column=1, sticky="s", pady=(0, 100))
        move_up_btn = ctk.CTkButton(reorder_frame, text="Up", width=60, command=self._move_up)
        move_up_btn.pack(pady=5)
        move_down_btn = ctk.CTkButton(reorder_frame, text="Down", width=60, command=self._move_down)
        move_down_btn.pack(pady=5)

        # --- Bottom Buttons ---
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        bottom_frame.grid_columnconfigure((0, 1), weight=1)

        ok_button = ctk.CTkButton(bottom_frame, text="Apply", command=self._apply_changes, fg_color=self.parent_app.STYLE['color_accent'])
        ok_button.grid(row=0, column=0, padx=10, pady=5, sticky="e")
        cancel_button = ctk.CTkButton(bottom_frame, text="Cancel", command=self.destroy, fg_color=self.parent_app.STYLE['color_gray'])
        cancel_button.grid(row=0, column=1, padx=10, pady=5, sticky="w")

    def _move_to_visible(self):
        """Move selected items from hidden to visible."""
        selected_indices = self.hidden_listbox.curselection()
        for i in reversed(selected_indices):
            item = self.hidden_listbox.get(i)
            self.visible_listbox.insert(tk.END, item)
            self.hidden_listbox.delete(i)

    def _move_to_hidden(self):
        """Move selected items from visible to hidden."""
        selected_indices = self.visible_listbox.curselection()
        for i in reversed(selected_indices):
            item = self.visible_listbox.get(i)
            self.hidden_listbox.insert(tk.END, item)
            self.visible_listbox.delete(i)
        # Keep hidden list sorted
        items = list(self.hidden_listbox.get(0, tk.END))
        self.hidden_listbox.delete(0, tk.END)
        for item in sorted(items):
            self.hidden_listbox.insert(tk.END, item)

    def _move_up(self):
        """Move selected item up in the visible list."""
        selected_indices = self.visible_listbox.curselection()
        for i in selected_indices:
            if i > 0:
                item = self.visible_listbox.get(i)
                self.visible_listbox.delete(i)
                self.visible_listbox.insert(i - 1, item)
                self.visible_listbox.selection_set(i - 1)

    def _move_down(self):
        """Move selected item down in the visible list."""
        selected_indices = self.visible_listbox.curselection()
        for i in reversed(selected_indices):
            if i < self.visible_listbox.size() - 1:
                item = self.visible_listbox.get(i)
                self.visible_listbox.delete(i)
                self.visible_listbox.insert(i + 1, item)
                self.visible_listbox.selection_set(i + 1)

    def _apply_changes(self):
        """Apply the new column visibility and order."""
        new_visible_order = list(self.visible_listbox.get(0, tk.END))
        self.parent_app.update_tree_columns(new_visible_order)
        self.destroy()
