from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from loading_widget import LoadingWidget
from notification_service import NotificationService


class NotificationWorker(QThread):
    result_ready = Signal(object)

    def __init__(self, uid, token, parent=None):
        super().__init__(parent)
        self.uid = uid
        self.token = token

    def run(self):
        try:
            result = NotificationService().get_unread(self.uid, self.token)
        except Exception as error:
            result = {"__worker_error__": str(error)}
        self.result_ready.emit(result)


class NotificationReadWorker(QThread):
    def __init__(self, uid, notification_id, token, parent=None):
        super().__init__(parent)
        self.uid = uid
        self.notification_id = notification_id
        self.token = token

    def run(self):
        NotificationService().mark_read(
            self.uid, self.notification_id, self.token
        )


class NotificationCard(QFrame):
    clicked_signal = Signal(str, str, str)

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.notification_id = data["id"]
        self.is_unread = not data.get("is_read", True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        self.user_label = QLabel(data.get("commenter_username", "@unknown"))
        layout.addWidget(self.user_label)

        snippet = data.get("comment_snippet", "")
        self.snippet_label = QLabel(f'commented: "{snippet}..."')
        self.snippet_label.setWordWrap(True)
        layout.addWidget(self.snippet_label)
        self._apply_style()

    def mousePressEvent(self, event):
        self.clicked_signal.emit(
            self.notification_id,
            self.data.get("thread_id", ""),
            self.data.get("comment_id", ""),
        )
        super().mousePressEvent(event)

    def _apply_style(self):
        if self.is_unread:
            self.setStyleSheet(
                "QFrame { background: #1a1a1a; border: 2px solid #00aeff; "
                "border-radius: 8px; padding: 15px; } "
                "QFrame:hover { border: 2px solid #00d4ff; background: #252525; }"
            )
            self.user_label.setStyleSheet(
                "font-weight: bold; font-size: 14px; color: #00aeff; "
                "background: transparent; border: none;"
            )
            self.snippet_label.setStyleSheet(
                "color: #ffffff; background: transparent; border: none;"
            )
        else:
            self.setStyleSheet(
                "QFrame { background: #1a1a1a; border: 1px solid #333; "
                "border-radius: 8px; padding: 15px; } "
                "QFrame:hover { border: 1px solid #00aeff; background: #252525; }"
            )
            self.user_label.setStyleSheet(
                "font-weight: bold; font-size: 14px; color: #aaaaaa; "
                "background: transparent; border: none;"
            )
            self.snippet_label.setStyleSheet(
                "color: #888888; background: transparent; border: none;"
            )

    def mark_read_locally(self):
        if self.is_unread:
            self.is_unread = False
            self.data["is_read"] = True
            self._apply_style()


class NotificationScreen(QWidget):
    open_post = Signal(str, str)

    def __init__(self, uid, token, parent=None):
        super().__init__(parent)
        self.uid = uid
        self.token = token
        self._worker = None
        self._read_workers = []
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle("Notifications")
        self.setStyleSheet("QWidget { background: #0f0f0f; color: #fff; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        title = QLabel("Notifications")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll.setStyleSheet(
            "QScrollArea { border: none; background: #0f0f0f; }"
        )
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setSpacing(10)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, 1)

        self.loading = LoadingWidget(self)
        self.loading.hide()
        self._load()

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()
        self._center_loading()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._center_loading()

    def _center_loading(self):
        self.loading.move(self.rect().center() - self.loading.rect().center())

    def _load(self):
        self._center_loading()
        self.loading.show()
        self.loading.raise_()
        self._worker = NotificationWorker(self.uid, self.token, self)
        self._worker.result_ready.connect(self._handle_load)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _handle_load(self, data):
        self.loading.hide()
        if isinstance(data, dict) and "__worker_error__" in data:
            data = []
        if not data:
            empty = QLabel("No new notifications")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #888; font-size: 16px; padding: 50px;")
            self.container_layout.addWidget(empty)
            return

        for item in data:
            card = NotificationCard(item)
            card.clicked_signal.connect(self._handle_card_click)
            self.container_layout.addWidget(card)

    def _handle_card_click(self, notification_id, thread_id, comment_id):
        card = self.sender()
        if isinstance(card, NotificationCard) and card.is_unread:
            card.mark_read_locally()
            worker = NotificationReadWorker(
                self.uid, notification_id, self.token, self
            )
            self._read_workers.append(worker)
            worker.finished.connect(
                lambda finished_worker=worker: self._release_read_worker(
                    finished_worker
                )
            )
            worker.start()
        self.open_post.emit(thread_id, comment_id)

    def _release_read_worker(self, worker):
        if worker in self._read_workers:
            self._read_workers.remove(worker)
        worker.deleteLater()
