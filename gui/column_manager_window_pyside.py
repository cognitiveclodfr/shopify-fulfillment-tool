from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QDialogButtonBox,
    QLabel,
    QAbstractItemView,
    QWidget,
)


class ColumnManagerWindow(QDialog):
    def __init__(self, all_columns, visible_columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Columns")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        # This will hold the final list of visible columns in the correct order
        self.new_visible_columns = visible_columns[:]
        hidden_columns = sorted([c for c in all_columns if c not in visible_columns])

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)

        # --- Lists Layout ---
        lists_layout = QHBoxLayout()

        # Visible Columns
        visible_widget = QWidget()
        visible_v_layout = QVBoxLayout(visible_widget)
        visible_v_layout.addWidget(QLabel("Visible Columns"))
        self.visible_list = QListWidget()
        self.visible_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.visible_list.addItems(visible_columns)
        visible_v_layout.addWidget(self.visible_list)
        lists_layout.addWidget(visible_widget)

        # Control Buttons
        controls_layout = QVBoxLayout()
        controls_layout.addStretch()
        add_btn = QPushButton(" < ")
        add_btn.setToolTip("Show selected column(s)")
        remove_btn = QPushButton(" > ")
        remove_btn.setToolTip("Hide selected column(s)")
        controls_layout.addWidget(add_btn)
        controls_layout.addWidget(remove_btn)
        controls_layout.addStretch()
        lists_layout.addLayout(controls_layout)

        # Hidden Columns
        hidden_widget = QWidget()
        hidden_v_layout = QVBoxLayout(hidden_widget)
        hidden_v_layout.addWidget(QLabel("Hidden Columns"))
        self.hidden_list = QListWidget()
        self.hidden_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.hidden_list.addItems(hidden_columns)
        hidden_v_layout.addWidget(self.hidden_list)
        lists_layout.addWidget(hidden_widget)

        # Reordering buttons for the visible list
        reorder_layout = QVBoxLayout()
        reorder_layout.addStretch()
        move_up_btn = QPushButton("Up")
        move_down_btn = QPushButton("Down")
        reorder_layout.addWidget(move_up_btn)
        reorder_layout.addWidget(move_down_btn)
        reorder_layout.addStretch()
        lists_layout.addLayout(reorder_layout)

        main_layout.addLayout(lists_layout)

        # --- Dialog Buttons ---
        button_box = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Cancel)
        main_layout.addWidget(button_box)

        # --- Connect Signals ---
        add_btn.clicked.connect(self.move_to_visible)
        remove_btn.clicked.connect(self.move_to_hidden)
        move_up_btn.clicked.connect(self.move_up)
        move_down_btn.clicked.connect(self.move_down)
        button_box.accepted.connect(self.apply_changes)
        button_box.rejected.connect(self.reject)

    def move_to_visible(self):
        for item in self.hidden_list.selectedItems():
            self.hidden_list.takeItem(self.hidden_list.row(item))
            self.visible_list.addItem(item)

    def move_to_hidden(self):
        for item in self.visible_list.selectedItems():
            self.visible_list.takeItem(self.visible_list.row(item))
            self.hidden_list.addItem(item)
        self.hidden_list.sortItems()

    def move_up(self):
        selected_rows = sorted([self.visible_list.row(item) for item in self.visible_list.selectedItems()])
        for row in selected_rows:
            if row > 0:
                item = self.visible_list.takeItem(row)
                self.visible_list.insertItem(row - 1, item)
                item.setSelected(True)

    def move_down(self):
        selected_rows = sorted(
            [self.visible_list.row(item) for item in self.visible_list.selectedItems()], reverse=True
        )
        for row in selected_rows:
            if row < self.visible_list.count() - 1:
                item = self.visible_list.takeItem(row)
                self.visible_list.insertItem(row + 1, item)
                item.setSelected(True)

    def apply_changes(self):
        self.new_visible_columns = [self.visible_list.item(i).text() for i in range(self.visible_list.count())]
        self.accept()
