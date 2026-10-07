from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from code_editor_adapter import format_size


class CodeEditorEntryPillWidget(QWidget):
    open_folder = Signal(str)
    remove_folder = Signal(str)

    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.folder_path = entry.get("path", "")
        self._setup_ui()

    def _setup_ui(self):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(70)
        self.setStyleSheet(
            "QWidget { background: #000000; border: 3px solid #ffffff; "
            "border-radius: 30px; } "
            "QWidget:hover { border: 3px solid #00aeff; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 10, 8)
        layout.setSpacing(15)

        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(2)

        folder_name = QLabel(self.entry.get("folder_name", "Unknown"))
        folder_name.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        folder_name.setStyleSheet(
            "color: #ffffff; background: transparent; border: none;"
        )
        folder_name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        details_layout.addWidget(folder_name)

        size_text = format_size(self.entry.get("size_mb", 0.0))
        info_label = QLabel(f"{self.folder_path}  |  {size_text}")
        info_label.setFont(QFont("Segoe UI", 11))
        info_label.setStyleSheet(
            "color: #aaaaaa; background: transparent; border: none;"
        )
        info_label.setWordWrap(False)
        info_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        details_layout.addWidget(info_label)
        layout.addLayout(details_layout, 1)

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(36, 36)
        remove_btn.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        remove_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #ff4444; "
            "border: none; border-radius: 18px; } "
            "QPushButton:hover { background: #ff4444; color: #ffffff; }"
        )
        remove_btn.clicked.connect(
            lambda checked=False: self.remove_folder.emit(self.folder_path)
        )
        layout.addWidget(remove_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_folder.emit(self.folder_path)
        super().mousePressEvent(event)
