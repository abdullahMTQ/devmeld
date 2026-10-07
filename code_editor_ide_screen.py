from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget


class CodeEditorIDEScreen(QWidget):
    def __init__(self, folder_path: str, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle(f"Code Editor - {folder_path}")
        self.setStyleSheet("QWidget { background-color: #000000; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.isMaximized():
            self.showMaximized()
