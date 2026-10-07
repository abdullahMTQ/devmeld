from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class CollaboratorChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background: #1a1a1a; border-left: 1px solid #333333;"
        )

        label = QLabel("Collaborator Chat\nComing Soon")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFont(QFont("Segoe UI", 12))
        label.setStyleSheet(
            "color: #888888; background: transparent; border: none;"
        )
        layout.addWidget(label)
