from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pfp_manager import PFPManager


class CommentCardWidget(QWidget):
    open_profile = Signal(str)

    def __init__(self, comment_data: dict, parent=None):
        super().__init__(parent)
        self.comment_data = comment_data
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(15)
        username = self.comment_data.get("author_username", "@unknown")
        pfp = PFPManager.get_pfp_pixmap(username, self.comment_data.get("author_pfp_number", 0), 36)
        pfp_button = QPushButton()
        pfp_button.setFixedSize(40, 40)
        pfp_button.setIcon(QIcon(pfp))
        pfp_button.setIconSize(pfp.size())
        pfp_button.setStyleSheet("QPushButton { border-radius: 20px; border: 2px solid #fff; background: #1a1a1a; }")
        pfp_button.clicked.connect(lambda: self.open_profile.emit(self.comment_data.get("author_uid", "")))
        layout.addWidget(pfp_button)

        content = QVBoxLayout()
        username_label = QLabel(username)
        username_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        username_label.setStyleSheet("color: #00aeff;")
        content.addWidget(username_label)
        from content_filter_service import ContentFilterService

        censored_body = ContentFilterService().censor_text(
            self.comment_data.get("body", "")
        )
        body = QLabel(censored_body)
        body.setWordWrap(True)
        body.setStyleSheet("color: #fff;")
        content.addWidget(body)
        layout.addLayout(content)
        layout.addStretch()
