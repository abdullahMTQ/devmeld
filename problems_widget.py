from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class ProblemsWidget(QWidget):
    go_to_line = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setStyleSheet("background: #1e1e1e; border: none;")

        self.header = QLabel("PROBLEMS")
        self.header.setStyleSheet(
            "color: #858585; font-size: 11px; padding: 5px 10px; "
            "background: #252526; border: none;"
        )
        layout.addWidget(self.header)

        self.list = QListWidget(self)
        self.list.setStyleSheet(
            "QListWidget { background: #1e1e1e; color: #cccccc; border: none; } "
            "QListWidget::item { padding: 5px; } "
            "QListWidget::item:hover { background: #2a2d2e; } "
            "QListWidget::item:selected { background: #37373d; }"
        )
        self.list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list, 1)

    def update_errors(self, errors: list):
        self.list.clear()
        for error in errors:
            line_number = error.get("line")
            message = error.get("message", "Syntax error")
            if not isinstance(line_number, int) or line_number < 1:
                continue
            item = QListWidgetItem(f"Line {line_number}: {message}")
            item.setData(Qt.ItemDataRole.UserRole, line_number)
            self.list.addItem(item)
        self.header.setText(f"PROBLEMS ({self.list.count()})")

    def _on_item_clicked(self, item):
        line_number = item.data(Qt.ItemDataRole.UserRole)
        if line_number:
            self.go_to_line.emit(line_number)
