from datetime import datetime

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class OutputWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setStyleSheet("background: #1e1e1e; border: none;")

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 5, 10, 5)
        self.header_label = QLabel("OUTPUT")
        self.header_label.setStyleSheet(
            "color: #858585; font-size: 11px; background: transparent; border: none;"
        )
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setToolTip("Clear output")
        self.clear_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #858585; border: none; "
            "font-size: 11px; padding: 3px 8px; } "
            "QPushButton:hover { color: #ffffff; }"
        )
        self.clear_btn.clicked.connect(self._clear)
        header_layout.addWidget(self.clear_btn)
        layout.addLayout(header_layout)

        self.output_area = QPlainTextEdit(self)
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet(
            "QPlainTextEdit { background: #1e1e1e; color: #cccccc; border: none; "
            "font-family: Consolas; font-size: 12px; }"
        )
        layout.addWidget(self.output_area, 1)
        self.log("Devmeld Code Editor Output initialized.")

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output_area.appendPlainText(f"[{timestamp}] {message}")
        scrollbar = self.output_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _clear(self):
        self.output_area.clear()
