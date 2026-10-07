from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from todo_service import TodoService


class NoteCardWidget(QWidget):
    delete_requested = Signal(int)

    def __init__(self, todo_data: dict, parent=None):
        super().__init__(parent)
        self.todo_id = todo_data.get("id")
        self._setup_ui(todo_data.get("content", ""))

    def _setup_ui(self, content: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.setStyleSheet(
            "QWidget { background: #252526; border: 1px solid #333; "
            "border-radius: 6px; }"
        )

        self.text_label = QLabel(content)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet(
            "color: #fff; background: transparent; border: none; font-size: 13px;"
        )
        layout.addWidget(self.text_label, 1)

        self.delete_btn = QPushButton("✕")
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #ff4444; border: none; "
            "font-weight: bold; }"
            "QPushButton:hover { color: #ff0000; background: #333; "
            "border-radius: 12px; }"
        )
        self.delete_btn.clicked.connect(
            lambda: self.delete_requested.emit(self.todo_id)
        )
        layout.addWidget(self.delete_btn)


class TodoWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = TodoService()
        self.setWindowTitle("TODOs")
        self.setFixedSize(400, 500)
        self.setStyleSheet(
            "QDialog { background: #1e1e1e; color: #fff; border: 1px solid #333; }"
        )
        self._setup_ui()
        self._load_notes()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        self.create_input = QLineEdit()
        self.create_input.setPlaceholderText("Write a note...")
        self.create_input.setStyleSheet(
            "QLineEdit { background: #252526; color: #fff; border: 1px solid #333; "
            "border-radius: 4px; padding: 8px; }"
            "QLineEdit:focus { border: 1px solid #00aeff; }"
        )
        self.create_input.returnPressed.connect(self._on_create)
        header_layout.addWidget(self.create_input, 1)

        self.create_btn = QPushButton("Create Note")
        self.create_btn.setFixedHeight(35)
        self.create_btn.setStyleSheet(
            "QPushButton { background: #0e639c; color: #fff; border: none; "
            "border-radius: 4px; padding: 0 15px; }"
            "QPushButton:hover { background: #1177bb; }"
        )
        self.create_btn.clicked.connect(self._on_create)
        header_layout.addWidget(self.create_btn)
        layout.addLayout(header_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        self.notes_container = QWidget()
        self.notes_layout = QVBoxLayout(self.notes_container)
        self.notes_layout.setContentsMargins(0, 0, 0, 0)
        self.notes_layout.setSpacing(8)
        self.notes_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.notes_container)
        layout.addWidget(self.scroll_area, 1)

    def _load_notes(self):
        while self.notes_layout.count():
            item = self.notes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        todos = self.service.get_todos()
        if not todos:
            empty = QLabel("No TODOs yet. Create one above!")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #888; font-size: 14px; padding: 20px;")
            self.notes_layout.addWidget(empty)
        else:
            for todo in todos:
                if not isinstance(todo, dict):
                    continue
                card = NoteCardWidget(todo)
                card.delete_requested.connect(self._on_delete)
                self.notes_layout.addWidget(card)
        self.notes_layout.addStretch()

    def _on_create(self):
        result = self.service.add_todo(self.create_input.text())
        if result.get("success"):
            self.create_input.clear()
            self._load_notes()
        else:
            QMessageBox.warning(
                self, "Could not create note", result.get("error", "Failed to save.")
            )

    def _on_delete(self, todo_id: int):
        result = self.service.delete_todo(todo_id)
        if result.get("success"):
            self._load_notes()
        else:
            QMessageBox.warning(
                self, "Could not delete note", result.get("error", "Failed to save.")
            )
