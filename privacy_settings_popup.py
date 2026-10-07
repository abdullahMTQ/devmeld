from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QCheckBox, QDialog, QLabel, QVBoxLayout

from local_settings import (
    get_hide_strangers_setting,
    save_hide_strangers_setting,
)


class PrivacySettingsPopup(QDialog):
    setting_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Privacy Settings")
        self.setFixedSize(350, 150)
        self.setStyleSheet(
            "QDialog { background-color: #0f0f0f; color: #ffffff; "
            "border: 2px solid #ffffff; border-radius: 12px; } "
            "QLabel { font-size: 14px; padding: 10px; } "
            "QCheckBox { font-size: 14px; spacing: 10px; padding: 10px; } "
            "QCheckBox::indicator { width: 20px; height: 20px; "
            "border: 2px solid #ffffff; border-radius: 10px; background: #000000; } "
            "QCheckBox::indicator:checked { background: #00aeff; "
            "border: 2px solid #00aeff; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("DM Privacy")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.toggle = QCheckBox("Hide chats unless I've sent a message")
        self.toggle.setChecked(get_hide_strangers_setting())
        self.toggle.toggled.connect(self._on_toggle_changed)
        layout.addWidget(self.toggle)

    def _on_toggle_changed(self, enabled: bool):
        save_hide_strangers_setting(enabled)
        self.setting_changed.emit(enabled)