from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class PostCardWidget(QFrame):
    post_clicked = Signal(str)

    def __init__(self, post_data: dict, tags_service, parent=None):
        super().__init__(parent)
        self.post_id = post_data["id"]
        self.tags_service = tags_service
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._setup_ui(post_data)

    def _setup_ui(self, post_data: dict):
        self.setStyleSheet(
            """
            QFrame {
                background-color: #1a1a1a;
                border: 2px solid #ffffff;
                border-radius: 8px;
            }
            QFrame:hover { border: 2px solid #00aeff; }
            """
        )
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        from content_filter_service import ContentFilterService

        censored_title = ContentFilterService().censor_text(post_data["title"])
        title_label = QLabel(censored_title)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #ffffff; background: transparent; border: none;")
        title_label.setWordWrap(True)
        main_layout.addWidget(title_label)
        main_layout.addStretch()

        tags_container = QWidget()
        tags_container.setStyleSheet("background: transparent; border: none;")
        tags_layout = QHBoxLayout(tags_container)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        tags_layout.setSpacing(8)
        tags_layout.addStretch()

        for tag_value in post_data.get("tag_ids", []):
            try:
                tag_id = int(
                    tag_value["integerValue"]
                    if isinstance(tag_value, dict) and "integerValue" in tag_value
                    else tag_value
                )
                for tag_data in self.tags_service.get_tags():
                    if tag_data["id"] == tag_id:
                        tag_button = QPushButton(tag_data["tag"])
                        tag_button.setFixedSize(90, 28)
                        tag_button.setStyleSheet(
                            """
                            QPushButton {
                                background-color: transparent;
                                color: #00aeff;
                                border: 1px solid #00aeff;
                                border-radius: 14px;
                                font-size: 11px;
                                font-weight: bold;
                            }
                            """
                        )
                        tags_layout.addWidget(tag_button)
                        break
            except (ValueError, TypeError):
                continue

        main_layout.addWidget(tags_container)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.post_clicked.emit(self.post_id)
        super().mousePressEvent(event)
