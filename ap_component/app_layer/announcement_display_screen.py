# Domain: announcement, Purpose: display, Layer: app (UI)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame)
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QPixmap
from ap_component.service_layer.announcement_fetch_service import AnnouncementFetchService

class AnnouncementLoaderThread(QThread):
    def __init__(self, service):
        super().__init__()
        self._service = service

    def run(self):
        # Triggers the INPUT CABLE
        self._service.request_announcements()

class AnnouncementDisplayScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AP Component Test")
        self.resize(600, 800)
        self._service = AnnouncementFetchService()
        self._loader = None
        self._init_ui()
        self._connect_cables()
        self._load_data()

    def _init_ui(self):
        self.setStyleSheet(
            """
            QWidget {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QScrollArea {
                border: 1px solid #333333;
                background-color: #1a1a1a;
            }
            """
        )
        main_layout = QVBoxLayout(self)
        self.header_label = QLabel("Announcements")
        self.header_label.setStyleSheet(
            "color: #ffffff; font-size: 24px; font-weight: bold; margin-bottom: 10px;"
        )
        main_layout.addWidget(self.header_label)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)

    def _connect_cables(self):
        # Listening to the OUTPUT CABLES
        self._service.signals.announcements_ready.connect(self._on_data_ready)
        self._service.signals.announcements_failed.connect(self._on_data_failed)

    def _load_data(self):
        self._clear_content()
        self._loader = AnnouncementLoaderThread(self._service)
        self._loader.start()

    def _on_data_ready(self, announcements):
        if not announcements:
            self._show_message("No announcements available.")
            return
        for ann in announcements:
            self._render_announcement_card(ann)

    def _on_data_failed(self, message):
        self._show_error(message)

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_error(self, message):
        label = QLabel(message)
        label.setStyleSheet("color: #ff6b6b; font-size: 16px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(label)

    def _show_message(self, message):
        label = QLabel(message)
        label.setStyleSheet("color: #cccccc; font-size: 16px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(label)

    def _add_image_placeholder(self, layout, text):
        placeholder = QLabel(text)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setFixedHeight(120)
        placeholder.setStyleSheet(
            "background-color: #1a1a1a; color: #cccccc; border: 1px solid #333333; "
            "margin-top: 5px; border-radius: 4px;"
        )
        layout.addWidget(placeholder)

    def _render_announcement_card(self, ann):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            "QFrame { background-color: #252526; color: #d4d4d4; "
            "border: 1px solid #333333; border-radius: 8px; padding: 15px; "
            "margin-bottom: 10px; }"
        )
        card_layout = QVBoxLayout(card)
        
        header = QLabel(ann.get("header", "No Header"))
        header.setStyleSheet("color: #00aeff; font-size: 18px; font-weight: bold;")
        card_layout.addWidget(header)
        
        body = QLabel(ann.get("body", "No Body"))
        body.setWordWrap(True)
        body.setStyleSheet("color: #d4d4d4; font-size: 14px; margin-top: 5px;")
        card_layout.addWidget(body)
        
        links = ann.get("links", [])
        if isinstance(links, dict):
            links = list(links.values())
        if links:
            links_html = "<br>".join(
                [
                    f'<a href="{link}" style="color: #00aeff;">{link}</a>'
                    for link in links
                ]
            )
            links_label = QLabel(links_html)
            links_label.setStyleSheet(
                "color: #00aeff; font-size: 12px; margin-top: 5px;"
            )
            links_label.setOpenExternalLinks(True)
            card_layout.addWidget(links_label)
            
        processed_images = ann.get("processed_images", [])
        for img in processed_images:
            if img["status"] == "success" and img["bytes"]:
                pixmap = QPixmap()
                if pixmap.loadFromData(img["bytes"]):
                    if pixmap.width() > 420:
                        pixmap = pixmap.scaledToWidth(420, Qt.TransformationMode.SmoothTransformation)
                    img_label = QLabel()
                    img_label.setPixmap(pixmap)
                    img_label.setStyleSheet(
                        "background-color: #1a1a1a; border: 1px solid #333333; "
                        "margin-top: 5px;"
                    )
                    card_layout.addWidget(img_label)
                else:
                    self._add_image_placeholder(card_layout, "Image unavailable (decode failed)")
            else:
                self._add_image_placeholder(card_layout, "Image unavailable (download failed)")
                
        self.content_layout.addWidget(card)

    def closeEvent(self, event):
        if hasattr(self, '_loader') and self._loader and self._loader.isRunning():
            self._loader.wait(7000)
        super().closeEvent(event)
