import json

from PySide6.QtCore import QObject, QSize, QThread, Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from conversation_screen import ConversationScreen
from dm_service import DMService
from impobj_utils import get_impobj_path, logger
from local_settings import get_hide_strangers_setting
from pfp_manager import PFPManager
from profile_service import ProfileService


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


class DmsUserRowWidget(QWidget):
    """UI component for a single conversation row."""

    open_conversation = Signal(str)

    def __init__(self, user_data: dict, parent=None, user_token=None):
        super().__init__(parent)
        self.user_data = user_data
        self.user_token = user_token
        self._pfp_worker = None
        self._setup_ui()
        screen = self.parentWidget()
        while screen and not hasattr(screen, "pfp_cache"):
            screen = screen.parentWidget()
        cached_pixmap = (
            screen.pfp_cache.get(self.user_data.get("uid")) if screen else None
        )
        if cached_pixmap and not cached_pixmap.isNull():
            self._set_pfp_icon(cached_pixmap)
        self._load_pfp()

    def _setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.row_frame = QFrame()
        self.row_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        self.row_frame.setStyleSheet(
            "QFrame { background: #1a1a1a; border: 1px solid #333; "
            "border-radius: 8px; } "
            "QFrame:hover { border: 1px solid #00aeff; background: #252525; } "
            "QLabel { background: transparent; border: none; color: #ffffff; }"
        )
        self.row_frame.mousePressEvent = self._on_row_mouse_press
        outer_layout.addWidget(self.row_frame)

        layout = QHBoxLayout(self.row_frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        self.menu_btn = QToolButton()
        self.menu_btn.setText("⋮")
        self.menu_btn.setFixedSize(30, 30)
        self.menu_btn.setStyleSheet(
            "QToolButton { background: transparent; color: #ffffff; border: none; "
            "font-size: 22px; font-weight: bold; } "
            "QToolButton:hover { background: #333333; border-radius: 15px; }"
        )
        self.menu = QMenu(self)
        block_action = self.menu.addAction("Block this user")
        block_action.triggered.connect(self._on_block_user)
        self.menu_btn.setMenu(self.menu)
        self.menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        layout.addWidget(self.menu_btn)

        self.avatar_btn = QPushButton()
        self.avatar_btn.setFixedSize(45, 45)
        self.avatar_btn.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.avatar_btn.setStyleSheet(
            "QPushButton { border-radius: 22px; border: 2px solid #ffffff; "
            "background: #000000; }"
        )
        layout.addWidget(self.avatar_btn)

        self.username_label = QLabel(self.user_data.get("username", "@unknown"))
        self.username_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(self.username_label)
        self.red_dot = QLabel("●")
        self.red_dot.setFixedSize(16, 20)
        self.red_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.red_dot.setStyleSheet(
            "color: #ff4444; font-size: 16px; background: transparent; border: none;"
        )
        self.red_dot.hide()
        layout.addWidget(self.red_dot)
        layout.addStretch()

    def set_unread(self, is_unread: bool):
        self.red_dot.setVisible(is_unread)

    def _on_block_user(self):
        from dm_adapter import get_blocked_chats
        from PySide6.QtWidgets import QMessageBox

        chat_id = self.user_data.get("chat_id")
        other_uid = self.user_data.get("uid")
        if not chat_id or not other_uid:
            QMessageBox.warning(self, "Block failed", "Chat details are missing.")
            return
        if chat_id in get_blocked_chats():
            QMessageBox.information(
                self, "Already Blocked", "This user is already blocked."
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Block",
            "Are you sure you want to block this user?\n\n"
            "This will permanently delete all messages and attachments in this chat.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        screen = self.parentWidget()
        while screen and not hasattr(screen, "user_uid"):
            screen = screen.parentWidget()
        if not screen:
            QMessageBox.warning(self, "Block failed", "Could not find the DM screen.")
            return

        self.menu_btn.setEnabled(False)
        worker = NetworkWorker(
            screen.dm_service.block_user_and_delete_chat,
            screen.user_uid,
            other_uid,
            chat_id,
            screen.user_token,
        )
        worker.signals.finished.connect(
            lambda result: self._handle_block_result(result, chat_id, screen)
        )
        worker.finished.connect(
            lambda completed=worker: screen._release_worker(completed)
        )
        screen._workers.append(worker)
        worker.start()

    def _handle_block_result(self, result, chat_id, screen):
        from PySide6.QtWidgets import QMessageBox

        if isinstance(result, dict) and result.get("success"):
            logger.info("[DmsUserRowWidget] Blocked chat %s.", chat_id)
            screen.preloaded_chats.discard(chat_id)
            screen.unread_status.pop(chat_id, None)
            screen._read_chat_ids.discard(chat_id)
            screen._all_chats = [
                chat for chat in screen._all_chats
                if chat.get("chat_id") != chat_id
            ]
            screen._render_chat_list(screen._all_chats)
            return

        self.menu_btn.setEnabled(True)
        error = result.get("error", "Unknown error") if isinstance(result, dict) else str(result)
        QMessageBox.warning(self, "Block Failed", f"Could not block user: {error}")

    def _load_pfp(self):
        """Fetch the user's saved PFP number and apply the avatar."""
        username = self.user_data.get("username", "@unknown")
        logger.info("[DmsUserRowWidget] Loading PFP for: %s", username)
        target_uid = self.user_data.get("uid")
        if not target_uid or not self.user_token:
            self._apply_pfp({"username": username, "pfp_number": 0})
            return
        worker = NetworkWorker(
            ProfileService().get_profile, target_uid, self.user_token
        )
        self._pfp_worker = worker
        worker.setParent(self.window())
        worker.signals.finished.connect(self._apply_pfp)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _apply_pfp(self, profile):
        if isinstance(profile, dict) and "__worker_error__" in profile:
            logger.error(
                "[DmsUserRowWidget] PFP fetch error: %s",
                profile["__worker_error__"],
            )
            profile = {}
        if not profile.get("success", True):
            logger.warning(
                "[DmsUserRowWidget] Could not fetch PFP profile for %s",
                self.user_data.get("uid"),
            )
        username = profile.get("username") or self.user_data.get(
            "username", "@unknown"
        )
        pfp_number = profile.get("pfp_number", 0)
        try:
            pixmap = PFPManager.get_pfp_pixmap(username, pfp_number, 41)
            if pixmap and not pixmap.isNull():
                self._set_pfp_icon(pixmap)

                online_status = ProfileService().get_online_status(username)
                ring_color = "#00ff88" if online_status == 1 else "#ff4444"
                self.avatar_btn.setStyleSheet(
                    f"QPushButton {{ border-radius: 22px; "
                    f"border: 3px solid {ring_color}; background-color: #000000; }} "
                    f"QPushButton:hover {{ border: 3px solid #00aeff; }}"
                )

                screen = self.parentWidget()
                while screen and not hasattr(screen, "pfp_cache"):
                    screen = screen.parentWidget()
                if screen:
                    screen.pfp_cache[self.user_data.get("uid")] = pixmap
                logger.info(
                    "[DmsUserRowWidget] PFP #%s loaded for %s (Online: %s)",
                    pfp_number,
                    username,
                    "Yes" if online_status == 1 else "No",
                )
        except Exception as error:
            logger.exception("[DmsUserRowWidget] PFP load error: %s", error)

    def _set_pfp_icon(self, pixmap):
        self.avatar_btn.setIcon(QIcon(pixmap))
        self.avatar_btn.setIconSize(QSize(41, 41))
        self.avatar_btn.setStyleSheet(
            "QPushButton { border-radius: 22px; "
            "border: 2px solid #ffffff; background-color: transparent; } "
            "QPushButton:hover { border: 2px solid #00aeff; }"
        )

    def _on_row_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_conversation.emit(self.user_data.get("uid", ""))
        event.accept()


class DmsScreen(QWidget):
    """Local-only main UI for the Direct Messages section."""

    back_requested = Signal()

    def __init__(
        self,
        user_uid: str,
        user_token: str,
        target_uid: str = None,
        target_username: str = None,
        current_username: str = "@unknown",
        parent=None,
    ):
        super().__init__(parent)
        self.user_uid = user_uid
        self.user_token = user_token
        self.target_uid = target_uid
        self.target_username = target_username or "@unknown"
        self.current_username = current_username or "@unknown"
        self.dm_service = DMService()
        self._target_chat_initialized = False
        self._workers = []
        self._all_chats = []
        self.pfp_cache = {}
        self.conversations = []
        self.chat_row_widgets = {}
        self.unread_status = {}
        self._read_chat_ids = set()
        self.preloaded_chats = set()
        self._preload_in_flight = set()
        self.filtered_conversations = []
        self._search_query = ""

        self.setWindowFlags(Qt.WindowType.Window)
        self._setup_ui()
        self._load_user_chats()

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()
        if self.target_uid and not self._target_chat_initialized:
            self._target_chat_initialized = True
            self._initialize_chat_with_user(self.target_uid)

    def _initialize_chat_with_user(self, target_uid: str, target_username=None):
        """Open the conversation view for a target user."""
        logger.info("[DmsScreen] Initializing chat with target_uid: %s", target_uid)
        chat_id = "_".join(sorted((self.user_uid, target_uid)))
        self._mark_chat_read(chat_id)
        from dm_adapter import get_blocked_chats, remove_blocked_chat

        if chat_id in get_blocked_chats():
            logger.info(
                "[DmsScreen] Profile DM requested for blocked chat; unblocking %s.",
                chat_id,
            )
            remove_blocked_chat(chat_id)

        target_username = target_username or self.target_username
        if target_username == "@unknown":
            target_username = f"User_{target_uid[:4]}"
        current_username = self.current_username or "@current_user"
        logger.info("[DmsScreen] Opening ConversationScreen for %s", target_uid)
        self.conversation_screen = ConversationScreen(
            user_uid=self.user_uid,
            user_token=self.user_token,
            target_uid=target_uid,
            target_username=target_username,
            current_username=current_username,
            parent=self,
        )
        self.conversation_screen.open_profile.connect(self._open_profile)
        self.conversation_screen.show()

    def _load_user_chats(self):
        logger.info("[DmsScreen] Fetching chats for user: %s", self.user_uid)
        worker = NetworkWorker(
            self.dm_service.get_user_chats, self.user_uid, self.user_token
        )
        worker.signals.finished.connect(self._handle_chats_loaded)
        worker.finished.connect(
            lambda completed=worker: self._release_worker(completed)
        )
        self._workers.append(worker)
        worker.start()

    def _handle_chats_loaded(self, result):
        if isinstance(result, dict) and "__worker_error__" in result:
            logger.error(
                "[DmsScreen] Failed to load chats: %s",
                result["__worker_error__"],
            )
            return
        if not result.get("success"):
            logger.error("[DmsScreen] Chat list request failed: %s", result.get("error"))
            return
        self._render_chat_list(result.get("chats", []))

    def _release_worker(self, worker):
        if worker in self._workers:
            self._workers.remove(worker)
        worker.deleteLater()

    def _setup_ui(self):
        self.setWindowTitle("DMs - Devmeld")
        self.setStyleSheet("QWidget { background-color: #0f0f0f; color: #ffffff; font-family: 'Segoe UI'; }")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        # --- TOP BAR (Settings + Search) ---
        top_bar = QHBoxLayout()
        top_bar.setSpacing(15)
        top_bar.addStretch()

        # Settings Icon (Placed BEFORE search bar)
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(50, 50)
        self.settings_btn.setFont(QFont("Segoe UI", 16))
        self.settings_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #ffffff; border: 2px solid #ffffff; border-radius: 25px; } "
            "QPushButton:hover { border: 2px solid #00aeff; color: #00aeff; } "
            "QPushButton:pressed { background: #00aeff; color: #000000; }"
        )
        self.settings_btn.clicked.connect(self._open_settings)
        top_bar.addWidget(self.settings_btn)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("search conversations")
        self.search_input.setFixedHeight(50)
        self.search_input.setFont(QFont("Segoe UI", 14))
        self.search_input.setStyleSheet(
            "QLineEdit { background-color: #1a1a1a; color: #ffffff; border: 2px solid #ffffff; "
            "border-radius: 25px; padding: 0 20px; } "
            "QLineEdit:focus { border: 2px solid #00aeff; }"
        )
        self.search_input.textChanged.connect(self._on_search_changed)
        top_bar.addWidget(self.search_input, 1)
        main_layout.addLayout(top_bar)

        # --- CONVERSATIONS LIST ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent; border: none;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area, 1)

        # Empty State Label
        self.empty_state_label = QLabel()
        self.empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_label.setStyleSheet("QLabel { color: #888888; font-size: 18px; padding: 50px; }")
        self._render_conversations(self.conversations)

    def set_conversations(self, conversations):
        """Set local conversation data and reapply the current search."""
        self.conversations = list(conversations)
        self._apply_search(self._search_query)

    def _on_search_changed(self, text):
        self._apply_search(text)

    def _apply_search(self, text):
        self._search_query = text.strip().casefold()
        if self._search_query:
            self.filtered_conversations = [
                conversation
                for conversation in self.conversations
                if self._search_query
                in conversation.get("username", "").casefold()
            ]
        else:
            self.filtered_conversations = list(self.conversations)
        self._render_conversations(self.filtered_conversations)

    def _render_conversations(self, data_list):
        while self.list_layout.count():
            self.list_layout.takeAt(0)

        if not data_list:
            self.empty_state_label.setText(
                "No matching conversations"
                if self._search_query
                else "No conversations yet"
            )
            for row in self.chat_row_widgets.values():
                row.hide()
            self.list_layout.addWidget(self.empty_state_label)
            self.empty_state_label.show()
            self.list_layout.addStretch()
            return

        self.empty_state_label.hide()
        visible_chat_ids = set()
        for user_data in data_list:
            chat_id = user_data.get("chat_id")
            row = self.chat_row_widgets.get(chat_id)
            if row is None:
                row = DmsUserRowWidget(
                    user_data,
                    self.list_container,
                    user_token=self.user_token,
                )
                row.open_conversation.connect(self._on_open_conversation)
            else:
                row.user_data = user_data
                row.username_label.setText(user_data.get("username", "@unknown"))
            if chat_id:
                visible_chat_ids.add(chat_id)
                self.chat_row_widgets[chat_id] = row
                row.set_unread(
                    self.unread_status.get(chat_id, False)
                    and chat_id not in self._read_chat_ids
                )
            row.show()
            self.list_layout.addWidget(row)
        for chat_id, row in self.chat_row_widgets.items():
            if chat_id not in visible_chat_ids:
                row.hide()
        self.list_layout.addStretch()

    def _render_chat_list(self, chats):
        from dm_adapter import get_blocked_chats

        self._all_chats = list(chats)
        blocked_chats = set(get_blocked_chats())
        active_chats = [
            chat for chat in self._all_chats
            if chat.get("chat_id") not in blocked_chats
        ]

        if get_hide_strangers_setting():
            chat_msg_dir = get_impobj_path() / "chatMSG"
            filtered_chats = []
            for chat in active_chats:
                chat_file = chat_msg_dir / f"{chat.get('chat_id', '')}.json"
                try:
                    with chat_file.open("r", encoding="utf-8") as file:
                        messages = json.load(file)
                    if isinstance(messages, list) and any(
                        isinstance(message, dict)
                        and message.get("author_uid") == self.user_uid
                        for message in messages
                    ):
                        filtered_chats.append(chat)
                except (OSError, ValueError):
                    continue
            active_chats = filtered_chats

        self.conversations = [
            {
                **chat,
                "uid": chat.get("target_uid", ""),
                "username": chat.get("target_username", "@unknown"),
            }
            for chat in active_chats
        ]
        self._apply_search(self._search_query)
        current_chat_ids = {
            chat.get("chat_id") for chat in self.conversations if chat.get("chat_id")
        }
        for chat_id in list(self.chat_row_widgets):
            if chat_id not in current_chat_ids:
                row = self.chat_row_widgets.pop(chat_id)
                self.list_layout.removeWidget(row)
                row.deleteLater()

        chats_to_preload = [
            chat_id
            for chat_id in current_chat_ids
            if chat_id not in self.preloaded_chats
            and chat_id not in self._preload_in_flight
        ]
        if chats_to_preload:
            self._preload_in_flight.update(chats_to_preload)
            logger.info(
                "[DmsScreen] Preloading %d newly allowed chats.",
                len(chats_to_preload),
            )
            worker = NetworkWorker(
                self.dm_service.preload_allowed_chats,
                self.user_uid,
                chats_to_preload,
                self.user_token,
            )
            worker.signals.finished.connect(
                lambda result, requested=tuple(chats_to_preload):
                self._handle_preload_result(result, requested)
            )
            worker.finished.connect(
                lambda completed=worker: self._release_worker(completed)
            )
            self._workers.append(worker)
            worker.start()

    def _handle_preload_result(self, result, requested_chat_ids):
        self._preload_in_flight.difference_update(requested_chat_ids)
        if not isinstance(result, dict) or not result.get("success"):
            logger.warning("[DmsScreen] Chat preload failed: %s", result)
            return
        unread_status = result.get("unread_status", {})
        self.preloaded_chats.update(unread_status)
        self.unread_status.update(unread_status)
        for chat_id, is_unread in unread_status.items():
            row = self.chat_row_widgets.get(chat_id)
            if row:
                row.set_unread(bool(is_unread) and chat_id not in self._read_chat_ids)

    def _mark_chat_read(self, chat_id: str):
        self._read_chat_ids.add(chat_id)
        self.unread_status[chat_id] = False
        row = self.chat_row_widgets.get(chat_id)
        if row:
            row.set_unread(False)

    def _open_settings(self):
        from privacy_settings_popup import PrivacySettingsPopup

        popup = PrivacySettingsPopup(self)
        popup.setting_changed.connect(
            lambda _enabled: self._render_chat_list(self._all_chats)
        )
        popup.exec()

    def _on_open_conversation(self, target_uid):
        target = next(
            (item for item in self.conversations if item.get("uid") == target_uid),
            {},
        )
        if not target_uid:
            logger.warning("[DmsScreen] Cannot open chat: target UID is missing")
            return
        self._initialize_chat_with_user(
            target_uid,
            target.get("target_username", target.get("username", "@unknown")),
        )

    def _open_profile(self, target_uid):
        from profile_screen import ProfileScreen

        self.profile_screen = ProfileScreen(
            self.user_uid, self.user_token, target_uid, parent=self
        )
        self.profile_screen.show()
