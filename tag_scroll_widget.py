from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QScrollArea, QWidget

from tags_service import TagsService


class TagScrollWidget(QWidget):
    tag_clicked = Signal(int, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tags_service = TagsService()
        self.is_hovered = False
        self.scroll_speed = 1.0
        self.set_width = 0

        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._auto_scroll)
        self.animation_timer.start(16)

        self.resume_timer = QTimer()
        self.resume_timer.setSingleShot(True)
        self.resume_timer.timeout.connect(self._resume_scrolling)

        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(60)
        self.setStyleSheet("background-color: #0f0f0f;")
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.tags_container = QWidget()
        self.tags_layout = QHBoxLayout(self.tags_container)
        self.tags_layout.setAlignment(Qt.AlignLeft)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(15)
        self.scroll_area.setWidget(self.tags_container)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll_area)
        self._load_tags()
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self._check_portals)
        QTimer.singleShot(0, self._position_active_zone)

    def enterEvent(self, event):
        self.is_hovered = True
        self.resume_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.resume_timer.start(1000)
        super().leaveEvent(event)

    def _resume_scrolling(self):
        pass

    def _load_tags(self):
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tags = self.tags_service.get_tags()
        active_filters = self.tags_service.get_active_tag_filters()
        for _ in range(3):
            for tag_data in tags:
                self.tags_layout.addWidget(
                    self._create_tag_button(tag_data, tag_data["id"] in active_filters)
                )
        self.tags_layout.addStretch()
        self.set_width = len(tags) * (120 + self.tags_layout.spacing())
        self._position_active_zone()

    def _position_active_zone(self):
        if self.set_width <= 0:
            return
        scrollbar = self.scroll_area.horizontalScrollBar()
        scrollbar.blockSignals(True)
        scrollbar.setValue(min(self.set_width, scrollbar.maximum()))
        scrollbar.blockSignals(False)

    def _create_tag_button(self, tag_data, is_active):
        button = QPushButton(tag_data["tag"])
        button.setFixedHeight(40)
        button.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))

        # Dynamically calculate width to fit the text perfectly with padding
        font_metrics = button.fontMetrics()
        text_width = font_metrics.boundingRect(tag_data["tag"]).width()
        button.setFixedWidth(text_width + 40)  # 40px total padding (20px left + 20px right)

        if is_active:
            button.setStyleSheet(
                "QPushButton { background: #00aeff; color: #000; border: 2px solid #00aeff; border-radius: 20px; }"
                "QPushButton:hover { background: #0088cc; }"
            )
        else:
            button.setStyleSheet(
                "QPushButton { background: #1a1a1a; color: #fff; border: 2px solid #fff; border-radius: 20px; }"
                "QPushButton:hover { border-color: #00aeff; color: #00aeff; }"
                "QPushButton:pressed { padding: 2px 10px 4px 12px; background: #333; }"
            )
        button.clicked.connect(
            lambda checked=False, tag_id=tag_data["id"]: self._on_tag_clicked(tag_id)
        )
        return button

    def _on_tag_clicked(self, tag_id):
        self.tags_service.toggle_tag_filter(tag_id)
        self._load_tags()
        active_filters = self.tags_service.get_active_tag_filters()
        self.tag_clicked.emit(tag_id, active_filters)

    def _on_hover_enter(self):
        self.is_hovered = True
        self.resume_timer.stop()

    def _on_hover_leave(self):
        self.is_hovered = False
        self.resume_timer.start(1000)

    def _auto_scroll(self):
        if not self.is_hovered:
            scrollbar = self.scroll_area.horizontalScrollBar()
            scrollbar.setValue(scrollbar.value() + self.scroll_speed)

    def _check_portals(self):
        scrollbar = self.scroll_area.horizontalScrollBar()
        current = scrollbar.value()
        if self.set_width == 0:
            return
        if current >= self.set_width * 2 or current <= 0:
            scrollbar.blockSignals(True)
            scrollbar.setValue(self.set_width)
            scrollbar.blockSignals(False)

    def keyPressEvent(self, event):
        if self.is_hovered:
            scrollbar = self.scroll_area.horizontalScrollBar()
            if event.key() == Qt.Key_Left:
                scrollbar.setValue(scrollbar.value() - 50)
            elif event.key() == Qt.Key_Right:
                scrollbar.setValue(scrollbar.value() + 50)
