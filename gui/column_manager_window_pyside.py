from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QDialogButtonBox, QListWidgetItem, QAbstractItemView
)

class ColumnManagerWindow(QDialog):
    def __init__(self, all_columns, visible_columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Columns")
        self.setMinimumSize(500, 400)

        # The final list of visible columns in the desired order
        self.new_visible_columns = visible_columns[:]

        hidden_columns = sorted([c for c in all_columns if c not in visible_columns])

        # --- Main Layout ---
        main_layout = QHBoxLayout(self)

        # --- Visible Columns List ---
        visible_layout = QVBoxLayout()
        self.visible_list = QListWidget()
        self.visible_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.visible_list.addItems(visible_columns)
        visible_layout.addWidget(self.visible_list)
        main_layout.addLayout(visible_layout)

        # --- Control Buttons ---
        controls_layout = QVBoxLayout()
        add_btn = QPushButton(" < ")
        remove_btn = QPushButton(" > ")
        move_up_btn = QPushButton("Up")
        move_down_btn = QPushButton("Down")
        controls_layout.addStretch()
        controls_layout.addWidget(add_btn)
        controls_layout.addWidget(remove_btn)
        controls_layout.addSpacing(20)
        controls_layout.addWidget(move_up_btn)
        controls_layout.addWidget(move_down_btn)
        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)

        # --- Hidden Columns List ---
        hidden_layout = QVBoxLayout()
        self.hidden_list = QListWidget()
        self.hidden_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.hidden_list.addItems(hidden_columns)
        hidden_layout.addWidget(self.hidden_list)
        main_layout.addLayout(hidden_layout)

        # Add main layout to a container widget for the dialog button box
        container_widget = QWidget()
        container_widget.setLayout(main_layout)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.addWidget(container_widget)

        # --- Dialog Buttons ---
        button_box = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Cancel)
        dialog_layout.addWidget(button_box)

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
        # Keep the hidden list sorted for easier browsing
        self.hidden_list.sortItems()

    def move_up(self):
        for item in self.visible_list.selectedItems():
            row = self.visible_list.row(item)
            if row > 0:
                self.visible_list.takeItem(row)
                self.visible_list.insertItem(row - 1, item)
                self.visible_list.setCurrentItem(item)

    def move_down(self):
        for i in reversed(range(self.visible_list.count())):
            item = self.visible_list.item(i)
            if item.isSelected():
                row = self.visible_list.row(item)
                if row < self.visible_list.count() - 1:
                    self.visible_list.takeItem(row)
                    self.visible_list.insertItem(row + 1, item)
                    self.visible_list.setCurrentItem(item)

    def apply_changes(self):
        self.new_visible_columns = [self.visible_list.item(i).text() for i in range(self.visible_list.count())]
        self.accept()
