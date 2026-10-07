from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class TerminalTabWidget(QWidget):
    tab_clicked = Signal()
    close_clicked = Signal()

    def __init__(self, name: str, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.name = name
        self._setup_ui(is_active)

    def _setup_ui(self, is_active: bool):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 5, 2)
        layout.setSpacing(5)
        self.name_label = QLabel(self.name, self)
        self.name_label.setFont(QFont("Segoe UI", 9))
        self.name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.name_label, 1)

        self.close_btn = QPushButton("x", self)
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setToolTip(f"Close {self.name}")
        self.close_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(self.close_btn)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_active(is_active)

    def set_active(self, is_active: bool):
        background = "#37373d" if is_active else "transparent"
        border = "#00aeff" if is_active else "transparent"
        foreground = "#ffffff" if is_active else "#858585"
        self.setStyleSheet(
            f"QWidget {{ background: {background}; border-left: 2px solid {border}; "
            "border-radius: 3px; }"
        )
        self.name_label.setStyleSheet(
            f"color: {foreground}; background: transparent; border: none;"
        )
        self.close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #858585; border: none; } "
            "QPushButton:hover { color: #ff4444; background: #2a2d2e; "
            "border-radius: 9px; }"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.tab_clicked.emit()
        super().mousePressEvent(event)
