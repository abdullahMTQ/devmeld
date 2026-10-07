from PySide6.QtCore import QObject, QPoint, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton, QScrollArea, QVBoxLayout, QWidget

from comment_card_widget import CommentCardWidget
from pfp_manager import PFPManager
from profile_service import ProfileService
from tags_service import TagsService
from threads_service import ThreadsService
from loading_widget import LoadingWidget


class WorkerSignals(QObject):
    finished = Signal(object)


class NetworkWorker(QThread):
    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.function(*self.args, **self.kwargs)
        except Exception as error:
            result = {"__worker_error__": str(error)}
        self.signals.finished.emit(result)


class PostViewScreen(QWidget):
    open_profile = Signal(str)
    post_deleted = Signal()

    def __init__(
        self,
        thread_id,
        user_uid,
        user_token,
        current_username,
        current_pfp,
        scroll_to_comment_id=None,
        parent=None,
    ):
        super().__init__(parent)
        self.thread_id = thread_id
        self.user_uid = user_uid
        self.user_token = user_token
        self.current_username = current_username
        self.current_pfp = current_pfp
        self.scroll_to_comment_id = scroll_to_comment_id
        self.comment_widgets = {}
        self.comments_page_token = None
        self._has_scrolled_to_comment = False
        self.service = ThreadsService()
        self.tags_service = TagsService()
        self.post_data = None
        self.comments = []
        self.last_comment_timestamp = None
        self.has_more_comments = True
        self.is_loading = False
        self._workers = []
        self.setWindowFlags(Qt.WindowType.Window)
        self.loading_overlay = LoadingWidget(self)
        self.loading_overlay.hide()
        self._setup_ui()
        self._load_post()

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()

    def _setup_ui(self):
        self.setWindowTitle("Post - Devmeld")
        self.setStyleSheet("QWidget { background-color: #0f0f0f; color: #ffffff; font-family: 'Segoe UI', Arial, sans-serif; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.main_scroll = QScrollArea()
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_scroll.setStyleSheet("QScrollArea { border: none; background-color: #0f0f0f; }")
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: #0f0f0f;")
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setContentsMargins(40, 40, 40, 40)
        self.content_layout.setSpacing(20)
        self.main_scroll.setWidget(self.scroll_content)
        layout.addWidget(self.main_scroll, 1)

        header = QHBoxLayout()
        self.author_pfp_btn = QPushButton()
        self.author_pfp_btn.setFixedSize(60, 60)
        self.author_pfp_btn.setStyleSheet("QPushButton { border-radius: 30px; border: 3px solid #fff; }")
        header.addWidget(self.author_pfp_btn)
        self.author_username_label = QLabel("@loading...")
        self.author_username_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header.addWidget(self.author_username_label)
        header.addStretch()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("QLabel { color: #00ff88; font-size: 14px; font-weight: bold; }")
        header.addWidget(self.status_label)
        self.menu_btn = QPushButton("...")
        self.menu_btn.setFixedSize(40, 40)
        self.menu_btn.clicked.connect(self._show_menu)
        header.addWidget(self.menu_btn)
        self.content_layout.addLayout(header)

        self.tags_container = QWidget()
        self.tags_layout = QHBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(10)
        self.tags_container.setStyleSheet("background-color: transparent; border: none;")
        self.content_layout.addWidget(self.tags_container)
        self.title_label = QLabel("")
        self.title_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.title_label.setWordWrap(True)
        self.content_layout.addWidget(self.title_label)
        self.body_label = QLabel("")
        self.body_label.setFont(QFont("Segoe UI", 14))
        self.body_label.setWordWrap(True)
        self.body_label.setStyleSheet("color: #ccc;")
        self.content_layout.addWidget(self.body_label)

        comments_header = QLabel("Comments")
        comments_header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        comments_header.setStyleSheet("color: #ffffff; margin-top: 20px; margin-bottom: 10px;")
        self.content_layout.addWidget(comments_header)
        self.comments_container = QWidget()
        self.comments_container.setStyleSheet("background: transparent; border: none;")
        self.comments_list_layout = QVBoxLayout(self.comments_container)
        self.comments_list_layout.setContentsMargins(0, 0, 0, 40)
        self.comments_list_layout.setSpacing(15)
        self.content_layout.addWidget(self.comments_container)
        self.content_layout.addStretch()
        self.main_scroll.verticalScrollBar().valueChanged.connect(self._on_scroll_comments)

        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(80)
        bottom_bar.setStyleSheet("background-color: #0f0f0f; border-top: 1px solid #333;")
        footer = QHBoxLayout(bottom_bar)
        footer.setContentsMargins(40, 15, 40, 15)
        footer.setSpacing(15)
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("add comment")
        self.comment_input.setFixedHeight(50)
        self.comment_input.setStyleSheet(
            "QLineEdit { background: #1a1a1a; color: #fff; border: 3px solid #fff; "
            "border-radius: 25px; padding: 0 20px; font-size: 16px; }"
            "QLineEdit:focus { border: 3px solid #00aeff; }"
        )
        footer.addWidget(self.comment_input)
        self.submit_comment_btn = QPushButton("Post")
        self.submit_comment_btn.setFixedSize(100, 50)
        self.submit_comment_btn.setStyleSheet(
            "QPushButton { background: #00aeff; color: #000; border: none; "
            "border-radius: 25px; font-weight: bold; font-size: 14px; }"
            "QPushButton:hover { background: #0088cc; }"
            "QPushButton:pressed { background: #006699; padding-top: 2px; padding-bottom: 0; }"
        )
        self.submit_comment_btn.clicked.connect(self._on_submit_comment)
        footer.addWidget(self.submit_comment_btn)
        layout.addWidget(bottom_bar)

    def _load_post(self):
        self._show_loading()
        self._start_worker(self._fetch_post_and_author, self._handle_post_load)

    def _fetch_post_and_author(self):
        post = self.service.get_post(self.thread_id, self.user_token)
        if not post.get("success"):
            return {"post": post, "profile": {"success": False}}
        from firebase_rest_adapter import FirebaseRestAdapter

        profile = FirebaseRestAdapter().get_profile_firestore(
            post.get("author_uid", ""), self.user_token
        )
        return {"post": post, "profile": profile}

    def _handle_post_load(self, result):
        self.loading_overlay.hide()
        if isinstance(result, dict) and "__worker_error__" in result:
            print(f"[PostViewScreen] Post load failed: {result['__worker_error__']}")
            result = {"post": {"success": False}, "profile": {"success": False}}
        post = result.get("post", {})
        if not post.get("success"):
            self.title_label.setText("Post unavailable")
            return
        self.post_data = post
        author_uid = post.get("author_uid", "")
        self.author_username_label.setText(author_uid)
        profile = result.get("profile", {})
        if profile.get("success"):
            username = profile.get("username", "@unknown")
            self.author_username_label.setText(username)
            pixmap = PFPManager.get_pfp_pixmap(username, profile.get("pfp_number", 0), 54)
            self.author_pfp_btn.setIcon(QIcon(pixmap))
            self.author_pfp_btn.setIconSize(pixmap.size())
        self.author_pfp_btn.clicked.connect(lambda: self.open_profile.emit(author_uid))
        for value in post.get("tag_ids", []):
            tag_id = int(value.get("integerValue", 0) if isinstance(value, dict) else value)
            tag = next((item for item in self.tags_service.get_tags() if item["id"] == tag_id), None)
            if tag:
                self.tags_layout.addWidget(QLabel(tag["tag"]))
        self.title_label.setText(post.get("title", ""))
        self.body_label.setText(post.get("body", ""))
        self._load_initial_comments()

    def _show_loading(self):
        self._center_loading_overlay()
        self.loading_overlay.show()
        self.loading_overlay.raise_()

    def _start_worker(self, function, callback, *args, **kwargs):
        worker = NetworkWorker(function, *args, **kwargs)
        self._workers.append(worker)
        worker.signals.finished.connect(callback)
        worker.finished.connect(lambda finished_worker=worker: self._release_worker(finished_worker))
        worker.start()

    def _release_worker(self, worker):
        if worker in self._workers:
            self._workers.remove(worker)
        worker.deleteLater()

    def _load_initial_comments(self):
        self._show_loading()
        self.is_loading = True
        self._start_worker(
            self.service.get_comments,
            self._handle_initial_comments,
            self.thread_id,
            20,
            None,
            self.user_token,
        )

    def _handle_initial_comments(self, result):
        self.is_loading = False
        self.loading_overlay.hide()
        if isinstance(result, dict) and "__worker_error__" in result:
            print(f"[PostViewScreen] Comment load failed: {result['__worker_error__']}")
            result = {"comments": [], "has_more": False}
        self.comments = result.get("comments", [])
        self.has_more_comments = result.get("has_more", False)
        self.comments_page_token = result.get("next_page_token")
        self._render_comments()

    def _center_loading_overlay(self):
        self.loading_overlay.move(
            self.rect().center() - self.loading_overlay.rect().center()
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._center_loading_overlay()

    def _render_comments(self):
        while self.comments_list_layout.count():
            item = self.comments_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.comment_widgets = {}
        for comment in self.comments:
            card = CommentCardWidget(comment)
            card.open_profile.connect(self.open_profile.emit)
            self.comments_list_layout.addWidget(card)
            self.comment_widgets[comment.get("id", "")] = card
        if self.scroll_to_comment_id and not self._has_scrolled_to_comment:
            if self.scroll_to_comment_id in self.comment_widgets:
                QTimer.singleShot(0, self._scroll_to_target)
            elif self.has_more_comments and not self.is_loading:
                QTimer.singleShot(0, self._load_more_comments)

    def _on_scroll_comments(self, value):
        bar = self.main_scroll.verticalScrollBar()
        if self.has_more_comments and not self.is_loading and value >= bar.maximum() * 0.8:
            self._load_more_comments()

    def _load_more_comments(self):
        if not self.comments_page_token:
            return
        self.is_loading = True
        self._show_loading()
        self._start_worker(
            self.service.get_comments,
            self._handle_more_comments,
            self.thread_id,
            20,
            self.comments_page_token,
            self.user_token,
        )

    def _handle_more_comments(self, result):
        self.is_loading = False
        self.loading_overlay.hide()
        if isinstance(result, dict) and "__worker_error__" in result:
            print(f"[PostViewScreen] More comments failed: {result['__worker_error__']}")
            return
        self.comments.extend(result.get("comments", []))
        self.comments_page_token = result.get("next_page_token")
        self.has_more_comments = bool(
            result.get("has_more", False) and self.comments_page_token
        )
        self._render_comments()
        self.is_loading = False

    def _scroll_to_target(self):
        target_widget = self.comment_widgets.get(self.scroll_to_comment_id)
        if not target_widget:
            return
        y_pos = target_widget.mapTo(self.scroll_content, QPoint(0, 0)).y()
        self.main_scroll.verticalScrollBar().setValue(y_pos)
        target_widget.setStyleSheet(
            "background-color: #333; border: 2px solid #00aeff; border-radius: 8px;"
        )
        self._has_scrolled_to_comment = True
        QTimer.singleShot(2000, lambda: target_widget.setStyleSheet(""))

    def _on_submit_comment(self):
        body = self.comment_input.text().strip()
        if not body:
            return
        self.submit_comment_btn.setEnabled(False)
        self._show_loading()
        self._start_worker(
            self.service.add_comment,
            self._handle_comment_result,
            self.thread_id,
            body,
            self.user_uid,
            self.current_username,
            self.current_pfp,
            self.user_token,
            self.post_data.get("author_uid", "") if self.post_data else "",
        )

    def _handle_comment_result(self, result):
        self.loading_overlay.hide()
        self.submit_comment_btn.setEnabled(True)
        if isinstance(result, dict) and "__worker_error__" in result:
            print(f"Comment failed: {result['__worker_error__']}")
            return
        if result.get("success"):
            self.comment_input.clear()
            self._load_initial_comments()
        else:
            print(f"Comment failed: {result.get('error', 'Unable to submit comment.')}")

    def _show_menu(self):
        menu = QMenu(self)
        if self.post_data and self.post_data.get("author_uid") == self.user_uid:
            action = menu.addAction("Delete Post")
            action.triggered.connect(self._on_delete_post)
        else:
            action = menu.addAction("Report Author")
            action.triggered.connect(self._on_report_author)
        menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomRight()))

    def _on_delete_post(self):
        self.status_label.setText("deleting...")
        self.status_label.setStyleSheet("QLabel { color: #ffffff; font-size: 14px; font-weight: bold; }")

        self._start_worker(
            self.service.delete_post,
            self._handle_delete_result,
            self.thread_id,
            self.user_token,
        )

    def _handle_delete_result(self, result):
        if isinstance(result, dict) and "__worker_error__" in result:
            self.status_label.setText("failed to delete")
            self.status_label.setStyleSheet("QLabel { color: #ff4444; font-size: 14px; font-weight: bold; }")
            return
        if result.get("success"):
            self.status_label.setText("[post deleted successfully]")
            self.status_label.setStyleSheet("QLabel { color: #00ff88; font-size: 14px; font-weight: bold; }")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1000, lambda: (self.post_deleted.emit(), self.close()))
        else:
            self.status_label.setText("failed to delete")
            self.status_label.setStyleSheet("QLabel { color: #ff4444; font-size: 14px; font-weight: bold; }")

    def _on_report_author(self):
        if not self.post_data:
            return

        from PySide6.QtWidgets import QMessageBox

        confirm = QMessageBox.question(
            self,
            "Confirm Report",
            "Warning: You are about to report this user.\n\n"
            "False reports may result in restrictions on your own account.\n\n"
            "Do you want to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.status_label.setText("reporting...")
        self.status_label.setStyleSheet("QLabel { color: #ffffff; font-size: 14px; font-weight: bold; }")

        self._start_worker(
            ProfileService().report,
            self._handle_report_result,
            self.user_uid,
            self.post_data.get("author_uid", ""),
            self.user_token,
        )

    def _handle_report_result(self, result):
        from PySide6.QtCore import QTimer

        if isinstance(result, dict) and "__worker_error__" in result:
            self.status_label.setText("report failed")
            self.status_label.setStyleSheet("QLabel { color: #ff4444; font-size: 14px; font-weight: bold; }")
            QTimer.singleShot(3000, lambda: self.status_label.clear())
            return

        if result.get("success"):
            self.status_label.setText("[reported]")
            self.status_label.setStyleSheet("QLabel { color: #00ff88; font-size: 14px; font-weight: bold; }")
        else:
            error_msg = result.get("error", "").lower()
            if "already reported" in error_msg:
                self.status_label.setText("[you already reported this person]")
            else:
                self.status_label.setText("report failed")
            self.status_label.setStyleSheet("QLabel { color: #ff4444; font-size: 14px; font-weight: bold; }")

        QTimer.singleShot(3000, lambda: self.status_label.clear())
