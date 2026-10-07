from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget

from pfp_manager import PFPManager
from pfp_selector_screen import PFPSelectorScreen
from profile_service import ProfileService
from loading_widget import LoadingWidget
from hardware_id_adapter import HardwareIdAdapter


class PFPViewerDialog(QDialog):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Profile Picture")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet("QDialog { background-color: #0f0f0f; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel()
        scaled_pixmap = pixmap.scaled(
            512,
            512,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(scaled_pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("background: transparent; border: none;")

        layout.addWidget(label)
        self.adjustSize()


class WorkerSignals(QObject):
    finished = Signal(object)


class NetworkWorker(QThread):
    """Execute a blocking profile network operation outside the UI thread."""

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


class ProfileScreen(QWidget):
    pfp_updated = Signal(int)

    def __init__(self, current_user_uid: str, current_user_token: str, target_uid: str, parent=None):
        super().__init__(parent)
        self.current_uid = current_user_uid
        self.current_token = current_user_token
        self.target_uid = target_uid
        self.is_own_profile = current_user_uid == target_uid
        self.service = ProfileService()
        self.current_hw_id = HardwareIdAdapter().get_machine_id()
        self.profile_data = None
        self._network_workers = []
        self.setWindowFlags(Qt.WindowType.Window)
        self.loading_overlay = LoadingWidget(self)
        self.loading_overlay.hide()
        self._setup_ui()
        self._load_profile()

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()

    def _setup_ui(self):
        self.setWindowTitle("Profile")
        self.setStyleSheet("QWidget { background-color: #0f0f0f; color: #ffffff; font-family: 'Segoe UI'; }")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        header_layout = QHBoxLayout()
        header_layout.addStretch()
        if not self.is_own_profile:
            self.report_btn = QPushButton("REPORT")
            self.report_btn.setFixedSize(120, 40)
            self.report_btn.setStyleSheet("QPushButton { color: #ff4444; border: 2px solid #ff4444; border-radius: 20px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #ff4444; color: #fff; } QPushButton:disabled { color: #888; border-color: #888; }")
            self.report_btn.clicked.connect(self._on_report)
            header_layout.addWidget(self.report_btn)
        else:
            self.logout_btn = QPushButton("logout")
            self.logout_btn.setFixedSize(120, 40)
            self.logout_btn.setStyleSheet(
                "QPushButton { color: #ff4444; border: 2px solid #ff4444; "
                "border-radius: 20px; font-weight: bold; font-size: 14px; "
                "background-color: transparent; }"
                "QPushButton:hover { background-color: #ff4444; color: #fff; }"
            )
            self.logout_btn.clicked.connect(self._on_logout)
            header_layout.addWidget(self.logout_btn)
        main_layout.addLayout(header_layout)

        info_layout = QHBoxLayout()
        info_layout.setSpacing(30)
        self.pfp_btn = QPushButton()
        self.pfp_btn.setFixedSize(120, 120)
        self.pfp_btn.setStyleSheet("QPushButton { border-radius: 60px; border: 4px solid #ffffff; background-color: #1a1a1a; }")
        self.pfp_btn.clicked.connect(self._on_pfp_clicked)
        info_layout.addWidget(self.pfp_btn)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(15)
        self.username_label = QLabel("@loading...")
        self.username_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        text_layout.addWidget(self.username_label)
        self.action_btn = QPushButton("change pfp" if self.is_own_profile else "DM")
        self.action_btn.setFixedSize(160, 45)
        self.action_btn.setStyleSheet("QPushButton { color: #00aeff; border: 2px solid #00aeff; border-radius: 22px; font-size: 16px; font-weight: bold; background-color: transparent; } QPushButton:hover { background-color: #00aeff; color: #000; }")
        self.action_btn.clicked.connect(self._open_pfp_selector if self.is_own_profile else self._on_dm)
        text_layout.addWidget(self.action_btn)
        text_layout.addStretch()
        info_layout.addLayout(text_layout)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #ffffff; margin: 10px 0;")
        main_layout.addWidget(divider)

        self.user_posts_scroll = QScrollArea()
        self.user_posts_scroll.setWidgetResizable(True)
        self.user_posts_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.user_posts_scroll.setStyleSheet("QScrollArea { border: none; background-color: #0f0f0f; }")
        self.user_posts_container = QWidget()
        self.user_posts_layout = QVBoxLayout(self.user_posts_container)
        self.user_posts_layout.setSpacing(15)
        self.user_posts_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.user_posts_scroll.setWidget(self.user_posts_container)
        main_layout.addWidget(self.user_posts_scroll, 1)
        self._load_user_posts()

    def _show_loading(self):
        self.loading_overlay.move(
            self.rect().center() - self.loading_overlay.rect().center()
        )
        self.loading_overlay.show()
        self.loading_overlay.raise_()
        QApplication.processEvents()

    def _start_network_worker(self, function, callback, *args, **kwargs):
        worker = NetworkWorker(function, *args, **kwargs)
        self._network_workers.append(worker)
        worker.signals.finished.connect(callback)
        worker.finished.connect(lambda completed=worker: self._release_network_worker(completed))
        worker.start()

    def _release_network_worker(self, worker):
        if worker in self._network_workers:
            self._network_workers.remove(worker)
        worker.deleteLater()

    def _load_profile(self):
        self._show_loading()
        self._start_network_worker(
            self.service.get_profile,
            self._handle_profile_load,
            self.target_uid,
            self.current_token,
        )

    def _handle_profile_load(self, result):
        self.loading_overlay.hide()
        if isinstance(result, dict) and "__worker_error__" in result:
            print(f"[ProfileScreen] Profile load worker failed: {result['__worker_error__']}")
            result = {"success": False}
        if not result.get("success"):
            self.username_label.setText("@profile unavailable")
            return
        self.profile_data = result
        try:
            report_count = int(result.get("report_count", 0) or 0)
        except (TypeError, ValueError):
            report_count = 0
        if self.is_own_profile and report_count >= 50:
            self._trigger_auto_ban()
            return
        username = result.get("username") or "@unknown"
        self.username_label.setText(username)
        self._set_pfp(username, result.get("pfp_number", 0))

    def _set_pfp(self, username: str, pfp_number: int):
        pixmap = PFPManager.get_pfp_pixmap(username or "@unknown", pfp_number, 112)
        self.pfp_btn.setIcon(QIcon(pixmap))
        self.pfp_btn.setIconSize(pixmap.size())

    def _on_pfp_clicked(self):
        """Open a dialog to view the profile picture in full size."""
        if not self.profile_data:
            return
        pfp_number = self.profile_data.get("pfp_number", 0)
        username = self.profile_data.get("username") or "@unknown"

        # Load the original full-size image from IMPOBJ
        from impobj_utils import get_impobj_path

        pfp_path = get_impobj_path() / "avatars" / f"{pfp_number}.png"

        if pfp_path.exists():
            pixmap = QPixmap(str(pfp_path))
        else:
            # Fallback to the generated letter avatar if image is missing
            from pfp_manager import PFPManager

            pixmap = PFPManager.get_pfp_pixmap(username, pfp_number, size=256)

        if not pixmap.isNull():
            viewer = PFPViewerDialog(pixmap, self)
            viewer.exec()

    def _open_pfp_selector(self):
        self.selector = PFPSelectorScreen(self)
        self.selector.pfp_selected.connect(self._on_pfp_selected)
        self.selector.show()

    def _on_pfp_selected(self, pfp_number: int):
        result = self.service.update_pfp(self.current_uid, pfp_number, self.current_token)
        if result.get("success") and self.profile_data:
            self.profile_data["pfp_number"] = pfp_number
            self._set_pfp(self.profile_data.get("username") or "@unknown", pfp_number)
            self.pfp_updated.emit(pfp_number)
        elif not result.get("success"):
            QMessageBox.warning(self, "Profile picture", "Unable to update your profile picture.")

    def _on_dm(self):
        if self.profile_data:
            target_username = self.profile_data.get("username", "@unknown")
            target_uid = self.target_uid
            print(
                f"[ProfileScreen] Opening DM for {target_username} "
                f"(UID: {target_uid})"
            )

            from dms_screen import DmsScreen

            current_username = "@unknown"
            parent_screen = self.parentWidget()
            if parent_screen is not None:
                current_username = getattr(
                    parent_screen, "current_username", current_username
                )
                current_user_data = getattr(
                    parent_screen, "current_user_data", None
                )
                if current_user_data:
                    current_username = current_user_data.get(
                        "username", current_username
                    )

            self.dm_screen = DmsScreen(
                self.current_uid,
                self.current_token,
                target_uid=target_uid,
                target_username=target_username,
                current_username=current_username,
                parent=self,
            )
            self.dm_screen.show()

    def _on_report(self):
        if self.is_own_profile:
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

        self.report_btn.setEnabled(False)
        self._show_loading()
        self._start_network_worker(
            self.service.report_user,
            self._handle_report_result,
            self.target_uid,
            self.current_hw_id,
            self.current_token,
            reporter_uid=self.current_uid,
        )

    def _handle_report_result(self, result):
        self.loading_overlay.hide()
        if isinstance(result, dict) and "__worker_error__" in result:
            result = {"success": False, "error": result["__worker_error__"]}
        if result.get("success"):
            self.report_btn.setText("[reported]")
            self.report_btn.setEnabled(False)
            self.report_btn.setStyleSheet("QPushButton { color: #00ff88; border: 2px solid #00ff88; border-radius: 20px; font-weight: bold; font-size: 14px; background: transparent; }")
            return

        error_msg = result.get("error", "").lower()
        if "already reported" in error_msg:
            self.report_btn.setText("[you already reported this person]")
            self.report_btn.setEnabled(False)
            self.report_btn.setStyleSheet("QPushButton { color: #ff4444; border: 2px solid #ff4444; border-radius: 20px; font-weight: bold; font-size: 12px; background: transparent; }")
        else:
            self.report_btn.setText("REPORT")
            self.report_btn.setEnabled(True)
            QMessageBox.warning(self, "Report failed", result.get("error", "Report failed."))

    def _on_logout(self):
        from PySide6.QtWidgets import QMessageBox
        from session_service import SessionService

        reply = QMessageBox.question(
            self,
            "Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        SessionService().logout_user()
        self.close()
        parent = self.parentWidget()
        if parent is not None and parent.__class__.__name__ == "ThreadsScreen":
            threads_parent = parent.parentWidget()
            parent.close()
            parent = threads_parent
        if parent is not None:
            parent.is_logged_in = False
            parent.current_user_data = None
            parent.set_login_state(False)

    def _load_user_posts(self):
        self._start_network_worker(self._fetch_user_posts_data, self._render_user_posts)

    def _fetch_user_posts_data(self):
        try:
            import requests
            from firebase_rest_adapter import FirebaseRestAdapter

            firebase = FirebaseRestAdapter()
            response = requests.get(
                f"{firebase.firestore_url}/threads",
                params={"key": firebase.api_key, "orderBy": "timestamp desc", "pageSize": "100"},
                headers={"Authorization": f"Bearer {self.current_token}"},
                timeout=15,
            )
            posts = []
            if response.status_code == 200:
                for document in response.json().get("documents", []):
                    fields = document.get("fields", {})
                    if fields.get("author_uid", {}).get("stringValue", "") != self.target_uid:
                        continue
                    posts.append({
                        "id": document.get("name", "").rsplit("/", 1)[-1],
                        "title": fields.get("title", {}).get("stringValue", ""),
                        "tag_ids": fields.get("tag_ids", {}).get("arrayValue", {}).get("values", []),
                    })
            return posts
        except Exception as error:
            print(f"[ProfileScreen] Failed to load user posts: {error}")
            return []

    def _render_user_posts(self, posts):
        if isinstance(posts, dict) and "__worker_error__" in posts:
            print(f"[ProfileScreen] User posts worker failed: {posts['__worker_error__']}")
            posts = []
        from post_card_widget import PostCardWidget
        from tags_service import TagsService

        for post in posts:
            card = PostCardWidget(post, TagsService())
            card.post_clicked.connect(self._open_post)
            self.user_posts_layout.addWidget(card)
        if not posts:
            placeholder = QLabel("(start posting to see them here)")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("QLabel { color: #888; font-size: 18px; padding: 50px; }")
            self.user_posts_layout.addWidget(placeholder)

    def _open_post(self, thread_id):
        from post_view_screen import PostViewScreen
        self.post_view = PostViewScreen(
            thread_id, self.current_uid, self.current_token,
            self.profile_data.get("username", "@user") if self.profile_data else "@user",
            self.profile_data.get("pfp_number", 0) if self.profile_data else 0,
            parent=None,
        )
        self.post_view.show()

    def _trigger_auto_ban(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QMessageBox

        message = QMessageBox(self)
        message.setWindowTitle("Account Banned")
        message.setText(
            "You are permanently banned from this platform due to breaking the rules."
        )
        message.setStyleSheet(
            "QMessageBox { background-color: #0f0f0f; color: #ff4444; font-size: 16px; }"
        )
        message.exec()
        QTimer.singleShot(5000, self._perform_auto_ban)

    def _perform_auto_ban(self):
        from session_service import SessionService

        result = SessionService().ban_user_permanently(
            self.current_uid, self.current_token
        )
        if result.get("success"):
            self.close()
            parent = self.parentWidget()
            if parent is not None:
                parent.set_login_state(False)
