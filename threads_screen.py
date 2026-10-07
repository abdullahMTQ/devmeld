from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QLabel, QHBoxLayout, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget

from pfp_manager import PFPManager
from post_card_widget import PostCardWidget
from tag_scroll_widget import TagScrollWidget
from tags_service import TagsService
from threads_service import ThreadsService
from loading_widget import LoadingWidget


class WorkerSignals(QObject):
    finished = Signal(object)


class NetworkWorker(QThread):
    """Run a callable off the GUI thread and return its result."""

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
        except Exception as error:
            result = {"__worker_error__": str(error)}
        self.signals.finished.emit(result)


class ThreadsScreen(QWidget):
    back_requested = Signal()
    profile_requested = Signal()
    create_post_requested = Signal()
    post_open_requested = Signal(str)

    def __init__(self, user_uid, user_token, parent=None):
        super().__init__(parent)
        self.user_uid = user_uid
        self.user_token = user_token
        self.current_username = "@user"
        self.current_pfp_number = 0
        self.current_active_filters = []
        self.threads_service = ThreadsService()
        from notification_service import NotificationService

        self.notification_service = NotificationService()
        self.tags_service = TagsService()
        self.posts = []
        self.all_posts = []
        self.last_visible = None
        self.has_more = True
        self.is_loading = False
        self.is_searching = False
        self.current_search_query = ""
        self.search_results = []
        self.search_rendered_count = 0
        self.search_has_more = True
        self.search_cursor = None
        self._network_workers = []
        self.setWindowFlags(Qt.WindowType.Window)
        self.loading_overlay = LoadingWidget(self)
        self.loading_overlay.hide()
        self._setup_ui()
        self._load_initial_posts()

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()
        self._center_loading_overlay()

    def _center_loading_overlay(self):
        self.loading_overlay.move(
            self.rect().center() - self.loading_overlay.rect().center()
        )

    def _show_loading(self):
        self._center_loading_overlay()
        self.loading_overlay.show()
        self.loading_overlay.raise_()
        QApplication.processEvents()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._center_loading_overlay()

    def _setup_ui(self):
        self.setWindowTitle("Threads - Devmeld")
        self.setStyleSheet("QWidget { background: #0f0f0f; color: #fff; font-family: 'Segoe UI'; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        header = QHBoxLayout()
        header.setSpacing(15)
        header.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        search_container = QWidget()
        search_container.setFixedHeight(50)
        search_container.setStyleSheet("background-color: #1a1a1a; border: 2px solid #ffffff; border-radius: 22px;")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(15, 0, 10, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("search")
        self.search_input.setStyleSheet("QLineEdit { background: transparent; color: #fff; border: none; font-size: 16px; padding: 5px; }")
        self.search_input.returnPressed.connect(self._on_search)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_input, 1)
        self.clear_search_btn = QPushButton("×")
        self.clear_search_btn.setFixedSize(30, 30)
        self.clear_search_btn.setStyleSheet("QPushButton { background: transparent; color: #ff4444; border: none; font-size: 24px; font-weight: bold; margin-top: -5px; } QPushButton:hover { color: #ff0000; } QPushButton:pressed { font-size: 22px; }")
        self.clear_search_btn.clicked.connect(self._clear_search)
        self.clear_search_btn.hide()
        search_layout.addWidget(self.clear_search_btn)
        header.addWidget(search_container, 1)
        self.create_post_btn = QPushButton("+")
        self.create_post_btn.setFixedSize(50, 50)
        self.create_post_btn.setStyleSheet("QPushButton { background: transparent; color: #00ff88; border: none; font-size: 42px; font-weight: bold; padding: 0; margin-top: -5px; } QPushButton:hover { color: #00dd77; } QPushButton:pressed { font-size: 40px; }")
        self.create_post_btn.clicked.connect(self._open_create_post)
        header.addWidget(self.create_post_btn)
        self.bell_btn = QPushButton("🔔")
        self.bell_btn.setFixedSize(50, 50)
        self.bell_btn.setToolTip("Notifications")
        self.bell_btn.setFont(QFont("Segoe UI", 16))
        self.bell_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #fff; border: none; } "
            "QPushButton:hover { color: #00aeff; }"
        )
        self.bell_btn.clicked.connect(self._on_bell_clicked)
        self.bell_badge = QLabel("")
        self.bell_badge.setFixedSize(14, 14)
        self.bell_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bell_badge.setStyleSheet(
            "QLabel { background-color: #ff4444; border-radius: 7px; "
            "border: 2px solid #0f0f0f; }"
        )
        self.bell_badge.hide()
        bell_container = QWidget()
        bell_container.setStyleSheet("background: transparent; border: none;")
        bell_layout = QHBoxLayout(bell_container)
        bell_layout.setContentsMargins(0, 0, 0, 0)
        bell_layout.setSpacing(0)
        bell_layout.addWidget(self.bell_btn)
        bell_layout.addWidget(self.bell_badge)
        header.addWidget(bell_container)
        self.profile_btn = QPushButton()
        self.profile_btn.setFixedSize(50, 50)
        self.profile_btn.setStyleSheet("QPushButton { border-radius: 25px; border: 3px solid #ffffff; background-color: #1a1a1a; } QPushButton:hover { border: 3px solid #00aeff; }")
        self.profile_btn.clicked.connect(self._on_profile_clicked)
        header.addWidget(self.profile_btn)
        layout.addLayout(header)
        self.tag_scroll = TagScrollWidget()
        self.tag_scroll.tag_clicked.connect(self._on_tag_filter)
        layout.addWidget(self.tag_scroll)
        self.posts_scroll = QScrollArea()
        self.posts_scroll.setWidgetResizable(True)
        self.posts_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.posts_scroll.setStyleSheet("QScrollArea { border: none; background: #0f0f0f; }")
        self.posts_container = QWidget()
        self.posts_layout = QVBoxLayout(self.posts_container)
        self.posts_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.posts_layout.setSpacing(20)
        self.posts_scroll.setWidget(self.posts_container)
        self.posts_scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)
        layout.addWidget(self.posts_scroll, 1)

    def _on_search_text_changed(self, text):
        self.clear_search_btn.setVisible(bool(text.strip()))

    def _clear_search(self):
        self.search_input.clear()
        self.clear_search_btn.hide()
        self.is_searching = False
        self.current_search_query = ""
        self.search_results = []
        self.search_rendered_count = 0
        self.search_has_more = True
        self.search_cursor = None
        self._fetch_posts(reset=True)

    def _on_profile_clicked(self):
        from profile_screen import ProfileScreen

        self.profile_screen = ProfileScreen(self.user_uid, self.user_token, self.user_uid, parent=self)
        self.profile_screen.pfp_updated.connect(self._on_pfp_updated)
        self.profile_screen.show()

    def _open_create_post(self):
        from create_post_screen import CreatePostScreen

        self.create_post_screen = CreatePostScreen(
            self.user_uid, self.user_token, parent=self
        )
        self.create_post_screen.post_created.connect(self._on_post_created)
        self.create_post_screen.show()

    def _on_post_created(self):
        print("[ThreadsScreen] Post created signal received!")
        print(f"[ThreadsScreen] Current posts count: {len(self.posts)}")
        self.posts = []
        self.last_visible = None
        self.has_more = True
        self._load_initial_posts()
        print("[ThreadsScreen] Feed reloaded")

    def _load_initial_posts(self):
        print("[ThreadsScreen] >>> STARTING INITIAL POST LOAD <<<")
        self._fetch_posts(reset=True)

    def _execute_initial_load(self, result):
        self._handle_posts_result(result, reset=True)
        print(f"[ThreadsScreen] Total posts to render: {len(self.posts)}")
        print("[ThreadsScreen] >>> INITIAL POST LOAD COMPLETE <<<")

    def _track_worker(self, worker):
        self._network_workers.append(worker)
        worker.finished.connect(lambda completed=worker: self._release_worker(completed))
        worker.start()

    def _release_worker(self, worker):
        if worker in self._network_workers:
            self._network_workers.remove(worker)
        worker.deleteLater()

    def _on_tag_filter(self, tag_id: int, active_filters: list):
        """Handle filter changes received directly from TagScrollWidget."""
        self.current_active_filters = active_filters
        print(f"[ThreadsScreen] >>> RECEIVED FILTERS FROM BELT: {active_filters} <<<")
        self._render_posts()

    def _on_pfp_updated(self, pfp_number: int):
        pixmap = PFPManager.get_pfp_pixmap(self.current_username, pfp_number, 44)
        self.profile_btn.setIcon(QIcon(pixmap))
        self.profile_btn.setIconSize(pixmap.size())

    def _fetch_posts(self, reset=False):
        if self.is_loading:
            return
        self.is_loading = True
        cursor = None if reset else self.last_visible
        self._show_loading()
        worker = NetworkWorker(
            self.threads_service.get_posts,
            page_size=10,
            start_after=cursor,
            tag_filters=self.tags_service.get_active_tag_filters(),
            id_token=self.user_token,
        )
        if reset:
            worker.signals.finished.connect(self._execute_initial_posts_result)
        else:
            worker.signals.finished.connect(lambda result: self._handle_posts_result(result, reset=False))
        self._track_worker(worker)

    def _execute_initial_posts_result(self, result):
        self._execute_initial_post_result(result, reset=True)

    def _handle_posts_result(self, result, reset=False):
        self._execute_initial_post_result(result, reset)

    def _execute_initial_post_result(self, result, reset):
        self.is_loading = False
        self.loading_overlay.hide()
        if isinstance(result, dict) and "__worker_error__" in result:
            print(f"[ThreadsScreen] Feed request failed: {result['__worker_error__']}")
            self._check_unread_notifications()
            return
        if reset:
            self.all_posts = []
        self.all_posts.extend(result.get("posts", []))
        self.posts = self.all_posts.copy()
        self.last_visible = result.get("next_page_token")
        self.has_more = bool(result.get("has_more", False) and self.last_visible)
        self._render_posts()
        self.is_loading = False
        self._check_unread_notifications()

    def _render_posts(self):
        while self.posts_layout.count():
            item = self.posts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        active_filters = self.current_active_filters
        print(f"[ThreadsScreen] Rendering posts. Active filters: {active_filters}")
        for post in self.all_posts:
            card = PostCardWidget(post, self.tags_service)
            card.post_clicked.connect(self._open_post_view)
            if active_filters:
                post_tag_ids = []
                for tag_value in post.get("tag_ids", post.get("tag_numbers", [])):
                    try:
                        value = tag_value.get("integerValue") if isinstance(tag_value, dict) else tag_value
                        post_tag_ids.append(int(value))
                    except (TypeError, ValueError):
                        continue
                if not any(tag_id in post_tag_ids for tag_id in active_filters):
                    continue
            self.posts_layout.addWidget(card)
        self.posts_layout.addStretch()

    def _on_scroll(self, value):
        bar = self.posts_scroll.verticalScrollBar()
        if self.is_loading or value < bar.maximum() * 0.8:
            return
        if self.is_searching and self.search_has_more:
            self._fetch_search_results(reset=False)
        elif not self.is_searching and self.has_more:
            self._fetch_posts(reset=False)

    def _on_search(self):
        query = self.search_input.text().strip()
        print(f"[ThreadsScreen] >>> SEARCHING FOR: '{query}' <<<")
        if not query:
            self.is_searching = False
            self._fetch_posts(reset=True)
            return
        self.is_searching = True
        self.current_search_query = query
        self.search_results = []
        self.search_rendered_count = 0
        self.search_has_more = True
        self.search_cursor = None
        self._fetch_search_results(reset=True)

    def _fetch_search_results(self, reset=False):
        if self.is_loading or not self.search_has_more:
            return
        self.is_loading = True
        self._show_loading()
        start_after = None if reset else self.search_cursor
        worker = NetworkWorker(
            self.threads_service.search,
            self.current_search_query,
            start_after,
            self.user_token,
        )
        callback = self._handle_search_results if reset else self._handle_search_results_append
        worker.signals.finished.connect(callback)
        self._track_worker(worker)

    def _handle_search_results(self, results):
        self.is_loading = False
        self.loading_overlay.hide()
        if isinstance(results, dict) and "__worker_error__" in results:
            results = {"results": [], "next_page_token": None}
        self.search_results = results.get("results", [])
        self.search_cursor = results.get("next_page_token")
        self.search_has_more = bool(self.search_cursor)
        print(f"[ThreadsScreen] Search returned {len(self.search_results)} results")
        self._render_search_results(reset=True)

    def _handle_search_results_append(self, results):
        self.is_loading = False
        self.loading_overlay.hide()
        if isinstance(results, dict) and "__worker_error__" in results:
            results = {"results": [], "next_page_token": None}
        self.search_results.extend(results.get("results", []))
        self.search_cursor = results.get("next_page_token")
        self.search_has_more = bool(self.search_cursor)
        self._render_search_results(reset=False)

    def _render_search_results(self, reset=True):
        if reset:
            while self.posts_layout.count():
                item = self.posts_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.search_rendered_count = 0
        elif self.posts_layout.count() and self.posts_layout.itemAt(
            self.posts_layout.count() - 1
        ).spacerItem():
            self.posts_layout.takeAt(self.posts_layout.count() - 1)

        items_to_render = self.search_results[
            self.search_rendered_count : self.search_rendered_count + 10
        ]
        if not items_to_render and reset and not self.search_has_more:
            no_results = QLabel("No results found")
            no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_results.setStyleSheet("QLabel { color: #888; font-size: 18px; padding: 50px; }")
            self.posts_layout.addWidget(no_results)
            return

        for result in items_to_render:
            if result.get("type") == "user":
                self.posts_layout.addWidget(self._create_user_result_card(result))
            elif result.get("type") == "post":
                post_data = dict(result)
                post_data["tag_numbers"] = post_data.get("tag_ids", post_data.get("tag_numbers", []))
                card = PostCardWidget(post_data, self.tags_service)
                post_id = result["id"]
                card.post_clicked.connect(lambda _clicked_id, pid=post_id: self._open_post_view(pid))
                self.posts_layout.addWidget(card)
        self.search_rendered_count += len(items_to_render)
        self.posts_layout.addStretch()

    def _create_user_result_card(self, user_data):
        card = QWidget()
        card.setStyleSheet("QWidget { background: #1a1a1a; border: 2px solid #fff; border-radius: 10px; padding: 15px; } QWidget:hover { border-color: #00aeff; }")
        layout = QHBoxLayout(card)
        layout.setSpacing(15)
        pfp_btn = QPushButton()
        pfp_btn.setFixedSize(50, 50)
        pfp_btn.setStyleSheet("QPushButton { border-radius: 25px; border: 3px solid #fff; }")
        username = user_data.get("username") or "@unknown"
        pixmap = PFPManager.get_pfp_pixmap(username, 0, 44)
        pfp_btn.setIcon(QIcon(pixmap))
        pfp_btn.setIconSize(pixmap.size())
        layout.addWidget(pfp_btn)
        username_label = QLabel(user_data.get("username", "@unknown"))
        username_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        username_label.setStyleSheet("color: #fff;")
        layout.addWidget(username_label)
        layout.addStretch()
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        def open_profile():
            from profile_screen import ProfileScreen

            self.profile_screen = ProfileScreen(self.user_uid, self.user_token, user_data["uid"], parent=self)
            self.profile_screen.show()

        card.mousePressEvent = lambda event: open_profile()
        return card

    def update_profile_pfp(self, pfp_number, username):
        self.current_pfp_number = pfp_number
        self.current_username = username or "@unknown"
        pixmap = PFPManager.get_pfp_pixmap(username or "@unknown", pfp_number, 44)
        self.profile_btn.setIcon(QIcon(pixmap))
        self.profile_btn.setIconSize(pixmap.size())

    def _open_post_view(self, thread_id: str, scroll_to_comment_id: str = None):
        from post_view_screen import PostViewScreen

        self.post_view_screen = PostViewScreen(
            thread_id,
            self.user_uid,
            self.user_token,
            self.current_username,
            self.current_pfp_number,
            scroll_to_comment_id=scroll_to_comment_id,
            parent=self,
        )
        self.post_view_screen.open_profile.connect(self._on_open_profile_from_post)
        self.post_view_screen.post_deleted.connect(self._on_post_deleted)
        self.post_view_screen.show()

    def _on_bell_clicked(self):
        self.bell_badge.hide()

        worker = NetworkWorker(
            self.notification_service.cleanup_read_notifications,
            self.user_uid,
            self.user_token,
        )
        worker.signals.finished.connect(
            lambda result: print(
                f"[ThreadsScreen] Cleaned up notifications: {result}"
            )
        )
        self._track_worker(worker)

        from notification_screen import NotificationScreen

        self.notif_screen = NotificationScreen(
            self.user_uid, self.user_token, parent=self
        )
        self.notif_screen.open_post.connect(self._open_post_from_notification)
        self.notif_screen.show()

    def _check_unread_notifications(self):
        from notification_service import NotificationService

        worker = NetworkWorker(
            NotificationService().get_unread_count,
            self.user_uid,
            self.user_token,
        )
        worker.signals.finished.connect(self._handle_unread_count)
        self._track_worker(worker)

    def _handle_unread_count(self, count):
        print(f"[ThreadsScreen] >>> Unread count received: {count} (Type: {type(count)}) <<<")

        if isinstance(count, int) and count > 0:
            print("[ThreadsScreen] >>> Showing red dot! <<<")
            self.bell_badge.show()
        else:
            print("[ThreadsScreen] >>> Hiding red dot. <<<")
            self.bell_badge.hide()

    def _open_post_from_notification(self, thread_id, comment_id):
        self._open_post_view(thread_id, scroll_to_comment_id=comment_id)

    def _on_open_profile_from_post(self, uid: str):
        from profile_screen import ProfileScreen

        self.profile_screen = ProfileScreen(
            self.user_uid, self.user_token, uid, parent=self
        )
        self.profile_screen.show()

    def _on_post_deleted(self):
        self._load_initial_posts()
