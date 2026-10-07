import json
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot, QThread, QTimer
from PySide6.QtGui import QCursor, QFont, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from signin_screen import SignUpScreen
from pfp_manager import PFPManager
from session_service import SessionService

# AP Component Imports (assuming the folder is named 'ap_component')
try:
    from ap_component import AnnouncementDisplayScreen
except ImportError:
    AnnouncementDisplayScreen = None

from impobj_utils import get_impobj_path, logger


class DMUnreadWorker(QThread):
    """Background worker to fetch DM unread status without blocking the UI."""

    result_ready = Signal(dict)

    def __init__(self, uid: str, token: str, parent=None):
        super().__init__(parent)
        self.uid = uid
        self.token = token

    def run(self):
        try:
            from dm_service import DMService

            service = DMService()
            chats_result = service.get_user_chats(self.uid, self.token)
            if chats_result.get("success"):
                chat_ids = [
                    chat.get("chat_id")
                    for chat in chats_result.get("chats", [])
                    if chat.get("chat_id")
                ]
                if chat_ids:
                    preload_result = service.preload_allowed_chats(
                        self.uid, chat_ids, self.token
                    )
                    if preload_result.get("success"):
                        self.result_ready.emit(
                            preload_result.get("unread_status", {})
                        )
                        return
            self.result_ready.emit({})
        except Exception as error:
            self.result_ready.emit({"error": str(error)})


class HomeScreen(QWidget):
    """Main home screen with navigation to Threads, DMs, and Code Editor."""

    threads_requested = Signal()
    dms_requested = Signal()
    code_editor_requested = Signal()
    profile_requested = Signal()
    signin_requested = Signal()

    def __init__(self):
        super().__init__()
        self.session_service = SessionService()
        self.is_logged_in = False
        self.current_user_avatar = None
        self.current_user_data = None

        self._setup_ui()
        self._connect_signals()
        self._restore_session()
        self._check_auto_open_announcement()

    def showEvent(self, event):
        """Ensure the home screen always opens maximized."""
        super().showEvent(event)
        self.showMaximized()

    def _restore_session(self):
        """Restore and validate the previous session during startup."""
        result = self.session_service.restore_session()
        if not result.get("success"):
            print("[HomeScreen] No saved session found")
            return

        user_data = result["user_data"]
        print(f"[HomeScreen] Session restored for {user_data.get('username')}")
        username = user_data.get("username", "")
        token = user_data.get("token", "")
        if username and token:
            from firebase_rest_adapter import FirebaseRestAdapter

            status_result = FirebaseRestAdapter().set_online_status(
                username, True, token
            )
            if not status_result.get("success"):
                logger.warning(
                    "[HomeScreen] Failed to set online status for %s: %s",
                    username,
                    status_result.get("error", "RTDB request failed"),
                )
        ban_check = self.session_service.check_and_enforce_ban(
            user_data["uid"], user_data["token"]
        )
        if ban_check.get("banned"):
            print("[HomeScreen] User is banned, executing permanent ban")
            self._execute_ban_workflow(user_data)
        else:
            self._on_login_success(user_data)
            QTimer.singleShot(2000, self._check_unread_dms)

    def _get_tracker_path(self) -> Path:
        """Get the path to the local announcement tracker in IMPOBJ."""
        return get_impobj_path() / "announcement_tracker.json"

    def _check_auto_open_announcement(self):
        """Check if it's Tuesday and auto-open the announcement window if not opened yet this week."""
        try:
            today = datetime.now(timezone.utc)
            if today.weekday() == 1:  # 1 is Tuesday
                tracker_path = self._get_tracker_path()
                last_opened = None
                if tracker_path.exists():
                    try:
                        with tracker_path.open("r", encoding="utf-8") as f:
                            data = json.load(f)
                            last_opened = data.get("last_opened_tuesday")
                    except Exception:
                        pass

                today_str = today.strftime("%Y-%m-%d")
                if last_opened != today_str:
                    self._open_announcement_window(update_tracker=True)
        except Exception as e:
            print(f"[HomeScreen] Auto-open announcement check failed: {e}")

    def _on_announcement_clicked(self):
        """Handle manual click on the announcement bell icon."""
        self._open_announcement_window(update_tracker=True)

    def _open_announcement_window(self, update_tracker: bool = False):
        """Open the announcement window and optionally update the Tuesday tracker."""
        try:
            from ap_component import AnnouncementDisplayScreen
        except ImportError:
            print("[HomeScreen] AP Component not found. Cannot open announcements.")
            return

        try:
            self.ap_display = AnnouncementDisplayScreen()
            self.ap_display.show()

            if update_tracker:
                tracker_path = self._get_tracker_path()
                tracker_path.parent.mkdir(parents=True, exist_ok=True)
                today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                with tracker_path.open("w", encoding="utf-8") as f:
                    json.dump({"last_opened_tuesday": today_str}, f, indent=2)
        except Exception as e:
            print(f"[HomeScreen] Failed to open announcement window: {e}")

    def closeEvent(self, event):
        """Set online status to 0 when the application closes."""
        if self.is_logged_in and self.current_user_data:
            username = self.current_user_data.get("username", "")
            token = self.current_user_data.get("token", "")
            if username and token:
                from firebase_rest_adapter import FirebaseRestAdapter

                status_result = FirebaseRestAdapter().set_online_status(
                    username, False, token
                )
                if not status_result.get("success"):
                    logger.warning(
                        "[HomeScreen] Failed to clear online status for %s: %s",
                        username,
                        status_result.get("error", "RTDB request failed"),
                    )
        super().closeEvent(event)

    def _execute_ban_workflow(self, user_data):
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtCore import QTimer

        message = QMessageBox(self)
        message.setWindowTitle("Account Banned")
        message.setText(
            "You are permanently banned from this platform due to breaking the rules."
        )
        message.setStyleSheet(
            "QMessageBox { background-color: #0f0f0f; color: #ff4444; font-size: 16px; }"
            "QPushButton { background-color: #ff4444; color: white; padding: 10px 20px; border-radius: 5px; }"
        )
        message.exec()
        QTimer.singleShot(5000, lambda: self._perform_ban(user_data))

    def _perform_ban(self, user_data):
        result = self.session_service.ban_user_permanently(
            user_data["uid"], user_data["token"]
        )
        if result.get("success"):
            print("[HomeScreen] Permanent ban executed successfully")
            self.set_login_state(False)

    def _setup_ui(self):
        self.setWindowTitle("Devmeld - Developer Collaboration Platform")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #0f0f0f;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            """
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        # Announcement Bell Icon
        self.announcement_btn = QPushButton("🔔")
        self.announcement_btn.setFixedSize(60, 60)
        self.announcement_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.announcement_btn.setToolTip("Check Announcements")
        self.announcement_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #ffffff; border: none; font-size: 28px; }"
            "QPushButton:hover { color: #00aeff; }"
        )
        self.announcement_btn.clicked.connect(self._on_announcement_clicked)
        header_layout.addWidget(self.announcement_btn)

        self.profile_btn = QPushButton()
        self.profile_btn.setFixedSize(60, 60)
        self.profile_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        header_layout.addWidget(self.profile_btn)
        main_layout.addLayout(header_layout)

        main_layout.addStretch(1)

        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setSpacing(25)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.threads_btn = self._create_nav_button("THREADS")
        self.threads_caption = self._create_caption("requires account to proceed")
        center_layout.addLayout(self._create_button_wrapper(self.threads_btn, self.threads_caption))

        self.dms_btn = self._create_nav_button("DMs")
        self.dms_caption = self._create_caption("requires account to proceed")

        # Clean container for DM button and red dot badge
        dms_container = QWidget()
        dms_container.setStyleSheet("background: transparent; border: none;")
        dms_layout = QVBoxLayout(dms_container)
        dms_layout.setContentsMargins(0, 0, 0, 0)
        dms_layout.setSpacing(5)
        dms_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.addWidget(self.dms_btn)

        self.dms_badge = QLabel("●")
        self.dms_badge.setFixedSize(12, 12)
        self.dms_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dms_badge.setStyleSheet(
            "color: #ff4444; font-size: 14px; background: transparent; border: none;"
        )
        self.dms_badge.hide()
        btn_row.addWidget(self.dms_badge)

        dms_layout.addLayout(btn_row)
        dms_layout.addWidget(self.dms_caption)
        center_layout.addWidget(dms_container)

        self.code_editor_btn = self._create_nav_button("CODE EDITOR", enabled=True)
        center_layout.addWidget(self.code_editor_btn)

        main_layout.addWidget(center_container)
        main_layout.addStretch(1)
        self._update_login_controls()

    def _create_button_wrapper(self, button, caption):
        wrapper = QVBoxLayout()
        wrapper.addWidget(button)
        wrapper.addWidget(caption)
        wrapper.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wrapper.setSpacing(5)
        return wrapper

    def _create_nav_button(self, text, enabled=False):
        button = QPushButton(text)
        button.setFixedSize(400, 80)
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        button.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        button.setEnabled(enabled)
        return button

    def _create_caption(self, text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFont(QFont("Segoe UI", 10))
        label.setStyleSheet(
            """
            QLabel {
                color: rgba(255, 80, 80, 0.8);
                background-color: transparent;
                padding: 2px 10px;
                font-size: 10px;
            }
            """
        )
        label.setVisible(False)
        return label

    def _set_nav_button_style(self, button, enabled):
        if enabled:
            button.setStyleSheet(
                """
                QPushButton {
                    background-color: #1a1a1a;
                    color: #ffffff;
                    border: 3px solid #ffffff;
                    border-radius: 40px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #252525;
                    border: 3px solid #00aeff;
                    color: #00aeff;
                }
                QPushButton:pressed {
                    background-color: #00aeff;
                    color: #000000;
                    padding: 2px 10px 4px 12px;
                }
                """
            )
        else:
            button.setStyleSheet(
                """
                QPushButton {
                    background-color: #0a0a0a;
                    color: #404040;
                    border: 3px solid #303030;
                    border-radius: 40px;
                    font-weight: bold;
                }
                """
            )

    def _update_profile_button(self):
        if self.is_logged_in and self.current_user_avatar:
            self.profile_btn.setText("")
            if isinstance(self.current_user_avatar, dict):
                username = self.current_user_avatar.get("username") or "@unknown"
                pfp_number = self.current_user_avatar.get("pfp_number", 0)
                pixmap = PFPManager.get_pfp_pixmap(username, pfp_number, size=54)
                self.profile_btn.setIcon(QIcon(pixmap))
                self.profile_btn.setIconSize(pixmap.size())
            self.profile_btn.setStyleSheet(
                """
                QPushButton {
                    border-radius: 30px;
                    border: 3px solid #00aeff;
                    background-color: #252525;
                }
                QPushButton:hover { border: 3px solid #ffffff; }
                """
            )
        else:
            self.profile_btn.setIcon(QIcon())
            self.profile_btn.setText("SIGN IN")
            self.profile_btn.setStyleSheet(
                """
                QPushButton {
                    border-radius: 30px;
                    border: 3px solid #ffffff;
                    background-color: #1a1a1a;
                    color: #888888;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    border: 3px solid #00aeff;
                    background-color: #252525;
                    color: #00aeff;
                }
                """
            )

    def _update_login_controls(self):
        self._update_profile_button()
        for button, caption in (
            (self.threads_btn, self.threads_caption),
            (self.dms_btn, self.dms_caption),
        ):
            button.setEnabled(self.is_logged_in)
            caption.setVisible(not self.is_logged_in)
            self._set_nav_button_style(button, self.is_logged_in)

    def _connect_signals(self):
        self.profile_btn.clicked.connect(self._on_profile_clicked)
        self.threads_btn.clicked.connect(self._on_threads_clicked)
        self.dms_btn.clicked.connect(self._on_dms_clicked)
        self.code_editor_btn.clicked.connect(self._on_code_editor_clicked)

    @Slot()
    def _on_profile_clicked(self):
        """Handle profile/signin button click."""
        if self.is_logged_in:
            if self.current_user_data:
                from profile_screen import ProfileScreen

                uid = self.current_user_data.get("uid")
                token = self.current_user_data.get("token")
                if uid and token:
                    self.profile_screen = ProfileScreen(uid, token, uid, parent=self)
                    self.profile_screen.pfp_updated.connect(self._on_home_pfp_updated)
                    self.profile_screen.show()
                    return
            self.profile_requested.emit()
            print("[HomeScreen] Profile requested (profile data unavailable)")
        else:
            self.signin_requested.emit()
            print("[HomeScreen] Opening Sign Up screen")
            self.signup_screen = SignUpScreen(parent=self)
            self.signup_screen.login_successful.connect(self._on_login_success)
            self.signup_screen.show()

    @Slot(int)
    def _on_home_pfp_updated(self, new_pfp_number: int):
        """Update the home avatar after a profile picture change."""
        print(f"[HomeScreen] Syncing PFP to number: {new_pfp_number}")
        if not self.current_user_data:
            return
        self.current_user_data["pfp_number"] = new_pfp_number
        username = self.current_user_data.get("username") or "@unknown"
        pixmap = PFPManager.get_pfp_pixmap(username, new_pfp_number, size=54)
        self.profile_btn.setIcon(QIcon(pixmap))
        self.profile_btn.setIconSize(pixmap.size())
        self.profile_btn.setText("")

    @Slot(dict)
    def _on_login_success(self, user_data):
        """Apply authenticated user data immediately after sign-up or sign-in."""
        self.session_service.login_user(user_data)
        print(f"[HomeScreen] Login successful: {user_data}")
        print(f"[HomeScreen] Username from login: {user_data.get('username', 'MISSING')}")
        print(f"[HomeScreen] PFP number: {user_data.get('pfp_number', 'MISSING')}")
        self.current_user_data = user_data
        self.is_logged_in = True
        if not user_data.get("username"):
            print("[HomeScreen] ERROR: No username in user_data!")
        self.set_login_state(True, user_data)
        QTimer.singleShot(2000, self._check_unread_dms)

    @Slot()
    def _on_threads_clicked(self):
        if self.is_logged_in:
            if self.current_user_data:
                from threads_screen import ThreadsScreen

                uid = self.current_user_data.get("uid")
                token = self.current_user_data.get("token")
                if uid and token:
                    self.threads_screen = ThreadsScreen(uid, token, parent=self)
                    self.threads_screen.profile_requested.connect(self._on_profile_from_threads)
                    self.threads_screen.post_open_requested.connect(self._on_post_open)
                    self.threads_screen.show()
                    self.threads_screen.update_profile_pfp(
                        self.current_user_data.get("pfp_number", 0),
                        self.current_user_data.get("username", "@unknown"),
                    )
                    self.threads_screen.current_username = self.current_user_data.get(
                        "username", "@unknown"
                    )
                    return
            self.threads_requested.emit()

    def _on_profile_from_threads(self):
        print("[HomeScreen] Profile requested from threads")
        if hasattr(self, "threads_screen"):
            self.threads_screen.close()
        self._on_profile_clicked()

    def _on_post_open(self, post_id: str):
        print(f"[HomeScreen] Opening post: {post_id}")

    @Slot()
    def _on_dms_clicked(self):
        if self.is_logged_in:
            if self.current_user_data:
                from dms_screen import DmsScreen

                uid = self.current_user_data.get("uid")
                token = self.current_user_data.get("token")
                if uid and token:
                    self.dms_screen = DmsScreen(
                        uid,
                        token,
                        current_username=self.current_user_data.get(
                            "username", "@unknown"
                        ),
                        parent=self,
                    )
                    self.dms_screen.show()

    def _check_unread_dms(self):
        """Trigger background check for unread DMs."""
        if not self.is_logged_in or not self.current_user_data:
            return
        uid = self.current_user_data.get("uid")
        token = self.current_user_data.get("token")
        if uid and token:
            # Prevent multiple workers from running at the same time
            if hasattr(self, "dm_unread_worker") and self.dm_unread_worker.isRunning():
                return
            self.dm_unread_worker = DMUnreadWorker(uid, token, self)
            self.dm_unread_worker.result_ready.connect(
                self._handle_dm_unread_result
            )
            self.dm_unread_worker.start()

    def _handle_dm_unread_result(self, unread_status: dict):
        """Update the DM badge based on the background worker's result."""
        if "error" in unread_status:
            print(f"[HomeScreen] DM preload error: {unread_status['error']}")
            return
        has_unread = any(unread_status.values())
        self.dms_badge.setVisible(has_unread)

    @Slot()
    def _on_code_editor_clicked(self):
        from code_editor_home_screen import CodeEditorHomeScreen

        self.code_editor_screen = CodeEditorHomeScreen(parent=self)
        self.code_editor_screen.show()

    def set_login_state(self, is_logged_in: bool, user_data: dict = None):
        """Update the UI for an authenticated or unauthenticated user."""
        self.is_logged_in = is_logged_in
        self.current_user_data = user_data if is_logged_in else None
        self.current_user_avatar = user_data if is_logged_in else None
        if is_logged_in and user_data:
            username = user_data.get("username") or "@unknown"
            pfp_number = user_data.get("pfp_number", 0)
            print(f"[HomeScreen] Setting PFP for user: {username}, pfp_num: {pfp_number}")
            pixmap = PFPManager.get_pfp_pixmap(username, pfp_number, size=54)
            self.profile_btn.setIcon(QIcon(pixmap))
            self.profile_btn.setIconSize(pixmap.size())
            self.profile_btn.setText("")
        self._update_login_controls()
