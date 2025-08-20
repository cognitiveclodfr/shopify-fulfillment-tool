import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import logging
from collections import deque
import time

class TreeViewLogHandler(logging.Handler):
    """A custom logging handler that sends records to a queue."""
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        # Add the actual record object to the queue
        self.queue.append(record)

class LogViewer(ctk.CTkFrame):
    """A widget for displaying and filtering logs from the Python logging module."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.log_queue = deque(maxlen=1000) # Store up to 1000 log records
        self.log_handler = TreeViewLogHandler(self.log_queue)

        # Configure the logger to use our handler
        # A specific logger name can be used, or the root logger
        logger = logging.getLogger('ShopifyToolLogger')
        logger.addHandler(self.log_handler)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_widgets()
        self._process_log_queue()

    def _create_widgets(self):
        # --- Controls Frame ---
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        controls_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(controls_frame, text="Filter by Level:").grid(row=0, column=0, padx=(0, 5))
        self.level_filter_var = tk.StringVar(value="ALL")
        self.level_filter_menu = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.level_filter_var,
            values=["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            command=self._apply_filters
        )
        self.level_filter_menu.grid(row=0, column=1, padx=5)

        ctk.CTkLabel(controls_frame, text="Search:").grid(row=0, column=2, padx=(10, 5), sticky="e")
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(controls_frame, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=3, padx=5, sticky="ew")
        self.search_var.trace_add("write", self._apply_filters)

        # --- Treeview for Logs ---
        self.tree = ttk.Treeview(self, columns=("Time", "Level", "Message"), show="headings")
        self.tree.grid(row=1, column=0, sticky="nsew")

        self.tree.heading("Time", text="Time")
        self.tree.heading("Level", text="Level")
        self.tree.heading("Message", text="Message")

        self.tree.column("Time", width=160, anchor='w', stretch=tk.NO)
        self.tree.column("Level", width=80, anchor='w', stretch=tk.NO)
        self.tree.column("Message", width=600, anchor='w')

        # --- Scrollbar ---
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        vsb.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)

        # --- Tags for color-coding ---
        self.tree.tag_configure('DEBUG', foreground='gray')
        self.tree.tag_configure('INFO', foreground='white')
        self.tree.tag_configure('WARNING', foreground='#F97316') # Orange
        self.tree.tag_configure('ERROR', foreground='#EF4444') # Red
        self.tree.tag_configure('CRITICAL', background='#EF4444', foreground='white')

    def _process_log_queue(self):
        """Periodically check the queue for new log messages and add them to the tree."""
        while self.log_queue:
            message = self.log_queue.popleft()
            self._add_log_entry(message)

        # Poll every 100ms
        self.after(100, self._process_log_queue)

    def _add_log_entry(self, record):
        """Adds a single log entry to the Treeview from a LogRecord object."""
        try:
            log_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
            level = record.levelname
            message = record.getMessage()

            # Insert at the top
            item_id = self.tree.insert("", 0, values=(log_time, level, message), tags=(level,))

            # Re-apply filters to the new item
            self._filter_item(item_id)

        except Exception as e:
            # Use logger to report errors in the logger itself
            logging.getLogger('ShopifyToolLogger').error(f"Error adding log entry to GUI: {e}")

    def _apply_filters(self, *args):
        """Apply the current level and search filters to all items in the tree."""
        for item_id in self.tree.get_children():
            self._filter_item(item_id)

    def _filter_item(self, item_id):
        """Show or hide a single item based on the current filters."""
        values = self.tree.item(item_id, 'values')
        level_filter = self.level_filter_var.get()
        search_term = self.search_var.get().lower()

        level_match = (level_filter == "ALL") or (values[1] == level_filter)
        search_match = (search_term == "") or (search_term in values[2].lower())

        if level_match and search_match:
            # Re-attach the item if it was hidden
            parent = self.tree.parent(item_id)
            if parent: # If it's a top-level item, parent is '', otherwise it's a child
                 self.tree.move(item_id, '', self.tree.index(item_id))
        else:
            # Detach the item to hide it
            self.tree.detach(item_id)
