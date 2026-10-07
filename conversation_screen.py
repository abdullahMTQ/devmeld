from datetime import datetime, timezone
import json
import os
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal, QThread, QSize, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from dm_service import DMService
from impobj_utils import get_impobj_path, logger
from loading_widget import LoadingWidget
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


class MessageCardWidget(QFrame):
    delete_requested = Signal(str)
    download_requested = Signal(str, str)

    def __init__(self, message_data: dict, is_own_message: bool, parent=None):
        super().__init__(parent)
        self.message_data = message_data
        self.is_own_message = is_own_message
        self.message_id = message_data.get("id", "")
        self._setup_ui()

    def _setup_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QFrame { background: transparent; border: none; }")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(10)

        content_widget = QWidget()
        content_widget.setMaximumWidth(680)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 10, 15, 10)
        content_layout.setSpacing(5)
        self.content_label = QLabel()
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet(
            "color: #ffffff; background: transparent; border: none;"
        )

        storage_path = self.message_data.get("storage_path")
        if storage_path:
            file_name = self.message_data.get("file_name") or Path(storage_path).name
            if self.message_data.get("is_uploading"):
                self.content_label.setText(f"Uploading {file_name}...")
            else:
                self.content_label.setText(f"📂 {file_name}\n[attachment]")
            self.content_label.setStyleSheet(
                "color: #00ff88; background: transparent; border: none; "
                "font-weight: bold;"
            )
            if not self.message_data.get("is_uploading"):
                content_widget.setCursor(Qt.CursorShape.PointingHandCursor)
                content_widget.mousePressEvent = self._on_attachment_click
        else:
            from content_filter_service import ContentFilterService

            censored_content = ContentFilterService().censor_text(
                self.message_data.get("content", "")
            )
            self.content_label.setText(censored_content)
        content_layout.addWidget(self.content_label)

        timestamp_label = QLabel(
            self._format_timestamp(self.message_data.get("timestamp", ""))
        )
        timestamp_label.setStyleSheet(
            "color: #888888; font-size: 11px; background: transparent; border: none;"
        )
        content_layout.addWidget(timestamp_label)

        if self.is_own_message:
            content_widget.setStyleSheet(
                "QWidget { background-color: #ffffff; border-radius: 15px; }"
            )
            self.content_label.setStyleSheet(
                "color: #111111; background: transparent; border: none;"
            )
            timestamp_label.setStyleSheet(
                "color: #555555; font-size: 11px; "
                "background: transparent; border: none;"
            )
            layout.addStretch()
            layout.addWidget(content_widget, 0, Qt.AlignmentFlag.AlignRight)
        else:
            content_widget.setStyleSheet(
                "QWidget { background-color: #1a1a1a; border: 2px solid #ffffff; "
                "border-radius: 15px; }"
            )
            layout.addWidget(content_widget, 0, Qt.AlignmentFlag.AlignLeft)
            layout.addStretch()

        self.delete_btn = None
        if self.is_own_message:
            self.delete_btn = QPushButton("🗑️")
            self.delete_btn.setFixedSize(30, 30)
            self.delete_btn.setToolTip("Delete message")
            self.delete_btn.setStyleSheet(
                "QPushButton { background: transparent; color: #ff4444; "
                "border: none; font-size: 16px; } "
                "QPushButton:hover { background: #ff4444; color: #fff; }"
            )
            self.delete_btn.hide()
            self.delete_btn.clicked.connect(
                lambda: self.delete_requested.emit(self.message_id)
            )
            layout.addWidget(self.delete_btn)
        self.setMouseTracking(True)

    @staticmethod
    def _format_timestamp(timestamp: str) -> str:
        if not timestamp:
            return ""
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return parsed.strftime("%I:%M %p")
        except (TypeError, ValueError):
            return ""

    def enterEvent(self, event):
        if self.delete_btn:
            self.delete_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.delete_btn:
            self.delete_btn.hide()
        super().leaveEvent(event)

    def _on_attachment_click(self, event):
        if self.message_data.get("is_uploading"):
            event.accept()
            return
        storage_path = self.message_data.get("storage_path")
        file_name = Path(
            self.message_data.get("file_name") or Path(storage_path).name
        ).name or "downloaded_file"
        message = QMessageBox(self)
        message.setWindowTitle("Download Attachment")
        message.setText("Are you sure you want to download this file?")
        message.setInformativeText(
            "We cannot verify whether this file contains malware. "
            "Download it only if you trust the sender."
        )
        message.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        message.setDefaultButton(QMessageBox.StandardButton.No)
        if message.exec() == QMessageBox.StandardButton.Yes:
            downloads_dir = Path.home() / "Downloads"
            downloads_dir.mkdir(parents=True, exist_ok=True)
            destination = downloads_dir / file_name
            self.download_requested.emit(
                storage_path, str(destination)
            )
        event.accept()


class ConversationScreen(QWidget):
    open_profile = Signal(str)

    def __init__(
        self,
        user_uid: str,
        user_token: str,
        target_uid: str,
        target_username: str,
        current_username: str = "@unknown",
        parent=None,
    ):
        super().__init__(parent)
        self.user_uid = user_uid
        self.user_token = user_token
        self.target_uid = target_uid
        self.target_username = target_username or "@unknown"
        self.current_username = current_username or "@unknown"
        sorted_uids = sorted([user_uid, target_uid])
        self.chat_id = f"{sorted_uids[0]}_{sorted_uids[1]}"
        self.dm_service = DMService()
        self.local_messages = []
        self._workers = []
        self._chat_ready = False
        self._messages_fetching = False
        self.selected_file_path = None
        self.file_name = None
        self.file_size = None
        self.is_temp_zip = False
        self.is_temp_zip = False

        logger.info(
            "[ConversationScreen] Initialized. chat_id: %s, target: %s",
            self.chat_id,
            self.target_username,
        )
        self.setWindowFlags(Qt.WindowType.Window)
        self._setup_ui()
        from dm_adapter import get_blocked_chats

        if self.chat_id in get_blocked_chats():
            logger.warning(
                "[ConversationScreen] Attempted to open blocked chat %s; deleting and closing.",
                self.chat_id,
            )
            self._run_worker(
                self.dm_service.block_user_and_delete_chat,
                lambda result: logger.info(
                    "[ConversationScreen] Blocked-chat cleanup result: %s", result
                ),
                self.user_uid,
                self.target_uid,
                self.chat_id,
                self.user_token,
            )
            self.close()
            return

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(30000)
        self.refresh_timer.timeout.connect(self._refresh_messages)
        self._load_target_pfp()
        self._load_chat_data()

    def _load_target_pfp(self):
        """Fetch the saved avatar number and load the target user's PFP."""
        logger.info(
            "[ConversationScreen] Fetching PFP number for: %s",
            self.target_username,
        )
        self._run_worker(
            self._fetch_target_profile,
            self._apply_target_pfp,
            self.target_uid,
        )

    def _fetch_target_profile(self, target_uid):
        result = ProfileService().get_profile(target_uid, self.user_token)
        if not result.get("success"):
            logger.warning(
                "[ConversationScreen] Could not fetch target profile: %s",
                result.get("error"),
            )
            return {"pfp_number": 0, "username": self.target_username}
        return result

    def _apply_target_pfp(self, user_data):
        if isinstance(user_data, dict) and "__worker_error__" in user_data:
            logger.error(
                "[ConversationScreen] PFP profile fetch failed: %s",
                user_data["__worker_error__"],
            )
            user_data = {"pfp_number": 0, "username": self.target_username}
        pfp_number = user_data.get("pfp_number", 0)
        username = user_data.get("username") or self.target_username
        logger.info(
            "[ConversationScreen] Loading PFP #%s for %s",
            pfp_number,
            username,
        )
        try:
            pixmap = PFPManager.get_pfp_pixmap(username, pfp_number, 54)
            if pixmap and not pixmap.isNull():
                self.target_pfp_btn.setIcon(QIcon(pixmap))
                self.target_pfp_btn.setIconSize(QSize(54, 54))
                online_status = ProfileService().get_online_status(username)
                ring_color = "#00ff88" if online_status == 1 else "#ff4444"
                self.target_pfp_btn.setStyleSheet(
                    f"QPushButton {{ border-radius: 30px; "
                    f"border: 3px solid {ring_color}; background-color: transparent; }} "
                    f"QPushButton:hover {{ border: 3px solid #00aeff; }}"
                )
                logger.info(
                    "[ConversationScreen] PFP #%s loaded successfully for %s "
                    "(Online: %s)",
                    pfp_number,
                    username,
                    "Yes" if online_status == 1 else "No",
                )
            else:
                logger.warning(
                    "[ConversationScreen] PFPManager returned null pixmap "
                    "for PFP #%s",
                    pfp_number,
                )
        except Exception as error:
            logger.exception("[ConversationScreen] Failed to apply PFP: %s", error)

    def _setup_ui(self):
        self.setWindowTitle(f"DM - {self.target_username}")
        self.setStyleSheet(
            "QWidget { background-color: #0f0f0f; color: #ffffff; "
            "font-family: 'Segoe UI'; }"
        )
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_bar = QFrame()
        top_bar.setStyleSheet(
            "QFrame { background-color: #1a1a1a; border-bottom: 1px solid #555; }"
        )
        top_bar.setFixedHeight(80)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 10, 20, 10)
        top_layout.setSpacing(15)

        self.target_pfp_btn = QPushButton()
        self.target_pfp_btn.setFixedSize(60, 60)
        self.target_pfp_btn.setStyleSheet(
            "QPushButton { border-radius: 30px; border: 3px solid #ffffff; "
            "background-color: #000000; } "
            "QPushButton:hover { border-color: #00aeff; }"
        )
        self.target_pfp_btn.clicked.connect(
            lambda: self.open_profile.emit(self.target_uid)
        )
        top_layout.addWidget(self.target_pfp_btn)

        username_label = QLabel(self.target_username)
        username_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        username_label.setStyleSheet(
            "color: #ffffff; background: transparent; border: none;"
        )
        top_layout.addWidget(username_label)
        top_layout.addStretch()
        main_layout.addWidget(top_bar)

        self.messages_scroll = QScrollArea()
        self.messages_scroll.setWidgetResizable(True)
        self.messages_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.messages_scroll.setStyleSheet(
            "QScrollArea { border: none; background-color: #0f0f0f; }"
        )
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(20, 20, 20, 20)
        self.messages_layout.setSpacing(8)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_scroll.setWidget(self.messages_container)
        main_layout.addWidget(self.messages_scroll, 1)

        bottom_bar = QFrame()
        bottom_bar.setStyleSheet(
            "QFrame { background-color: #1a1a1a; border-top: 1px solid #555; }"
        )
        bottom_bar.setFixedHeight(80)
        bottom_layout = QVBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(20, 12, 20, 12)
        bottom_layout.setSpacing(10)

        self.file_selection_row = QWidget()
        file_selection_layout = QHBoxLayout(self.file_selection_row)
        file_selection_layout.setContentsMargins(0, 0, 0, 0)
        file_selection_layout.setSpacing(15)

        self.file_pill_widget = QFrame()
        self.file_pill_widget.setStyleSheet(
            "QFrame { background: #000000; border: 3px solid #ffffff; "
            "border-radius: 28px; }"
        )
        self.file_pill_widget.setFixedHeight(56)
        self.file_pill_widget.setMinimumWidth(300)
        file_pill_layout = QHBoxLayout(self.file_pill_widget)
        file_pill_layout.setContentsMargins(15, 10, 15, 10)
        file_pill_layout.setSpacing(12)
        self.file_icon_label = QLabel("📁")
        self.file_icon_label.setStyleSheet(
            "font-size: 24px; background: transparent; border: none;"
        )
        self.file_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        file_pill_layout.addWidget(self.file_icon_label)

        file_info_layout = QVBoxLayout()
        file_info_layout.setSpacing(2)
        file_info_layout.setContentsMargins(0, 0, 0, 0)
        self.file_name_label = QLabel("")
        self.file_name_label.setStyleSheet(
            "color: #ffffff; font-size: 13px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        file_info_layout.addWidget(self.file_name_label)
        self.file_size_label = QLabel("")
        self.file_size_label.setStyleSheet(
            "color: #888888; font-size: 11px; background: transparent; border: none;"
        )
        file_info_layout.addWidget(self.file_size_label)
        file_pill_layout.addLayout(file_info_layout, 1)

        self.remove_file_btn = QPushButton("✕")
        self.remove_file_btn.setFixedSize(28, 28)
        self.remove_file_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #ff4444; "
            "border: none; font-size: 18px; font-weight: bold; } "
            "QPushButton:hover { background: #ff4444; color: #fff; }"
        )
        self.remove_file_btn.clicked.connect(self._clear_selected_file)
        file_pill_layout.addWidget(self.remove_file_btn)
        self.file_pill_widget.hide()
        file_selection_layout.addWidget(self.file_pill_widget)

        self.send_btn = QPushButton("→")
        self.send_btn.setFixedSize(50, 50)
        self.send_btn.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.send_btn.setStyleSheet(
            "QPushButton { background-color: #00aeff; color: #000000; "
            "border: none; border-radius: 25px; } "
            "QPushButton:hover { background-color: #0088cc; } "
            "QPushButton:pressed { padding: 2px 10px 4px 12px; }"
        )
        self.send_btn.clicked.connect(self._on_send_clicked)
        file_selection_layout.addWidget(self.send_btn)
        file_selection_layout.addStretch()
        self.file_selection_row.hide()
        bottom_layout.addWidget(self.file_selection_row)

        self.text_input_row = QWidget()
        text_input_layout = QHBoxLayout(self.text_input_row)
        text_input_layout.setContentsMargins(0, 0, 0, 0)
        text_input_layout.setSpacing(15)
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.setFixedHeight(50)
        self.message_input.setFont(QFont("Segoe UI", 14))
        self.message_input.setStyleSheet(
            "QLineEdit { background-color: #000000; color: #ffffff; "
            "border: 3px solid #ffffff; border-radius: 25px; padding: 0 20px; } "
            "QLineEdit:focus { border: 3px solid #00aeff; }"
        )
        self.message_input.returnPressed.connect(self._on_send_clicked)
        text_input_layout.addWidget(self.message_input, 1)

        self.attach_btn = QPushButton("📁")
        self.attach_btn.setFixedSize(50, 50)
        self.attach_btn.setFont(QFont("Segoe UI", 20))
        self.attach_btn.setStyleSheet(
            "QPushButton { background-color: #ffffff; border: 3px solid #ffffff; "
            "border-radius: 25px; } "
            "QPushButton:hover { background-color: #e0e0e0; "
            "border: 3px solid #00aeff; }"
        )
        self.attach_btn.clicked.connect(self._on_attach_clicked)
        text_input_layout.addWidget(self.attach_btn)

        self.send_btn_input = QPushButton("→")
        self.send_btn_input.setFixedSize(50, 50)
        self.send_btn_input.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.send_btn_input.setStyleSheet(
            "QPushButton { background-color: #00aeff; color: #000000; "
            "border: none; border-radius: 25px; } "
            "QPushButton:hover { background-color: #0088cc; }"
        )
        self.send_btn_input.clicked.connect(self._on_send_clicked)
        text_input_layout.addWidget(self.send_btn_input)
        self.text_input_row.show()
        bottom_layout.addWidget(self.text_input_row)
        main_layout.addWidget(bottom_bar)

        self.loading_overlay = LoadingWidget(self)
        self.loading_overlay.hide()

    def _run_worker(self, function, callback, *args, **kwargs):
        worker = NetworkWorker(function, *args, **kwargs)
        self._workers.append(worker)
        worker.signals.finished.connect(callback)
        worker.finished.connect(
            lambda completed=worker: self._release_worker(completed)
        )
        worker.start()

    def _release_worker(self, worker):
        if worker in self._workers:
            self._workers.remove(worker)
        worker.deleteLater()

    def _set_send_buttons_enabled(self, enabled):
        self.send_btn.setEnabled(enabled)
        self.send_btn_input.setEnabled(enabled)

    def _load_chat_data(self):
        self._show_loading_messages()
        self._load_local_messages()
        self._initialize_chat()

    def _show_loading_messages(self):
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        loading_label = QLabel("Loading messages...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet(
            "QLabel { color: #888888; font-size: 14px; padding: 20px; }"
        )
        self.messages_layout.addWidget(loading_label)
        self.messages_layout.addStretch()

    def _initialize_chat(self):
        logger.info(
            "[ConversationScreen] Initializing chat with target UID: %s",
            self.target_uid,
        )
        self._run_worker(
            self.dm_service.initialize_chat,
            self._handle_chat_initialized,
            self.user_uid,
            self.target_uid,
            self.current_username,
            self.target_username,
            self.user_token,
        )

    def _handle_chat_initialized(self, result):
        logger.info("[ConversationScreen] Chat initialization result: %s", result)
        if isinstance(result, dict) and "__worker_error__" in result:
            logger.error(
                "[ConversationScreen] Chat initialization failed: %s",
                result["__worker_error__"],
            )
            QMessageBox.warning(self, "Direct messages", result["__worker_error__"])
            return
        if not result.get("success"):
            logger.error(
                "[ConversationScreen] Chat initialization rejected: %s",
                result.get("error"),
            )
            QMessageBox.warning(
                self,
                "Direct messages",
                result.get("error", "Could not open this conversation."),
            )
            return
        self.chat_id = result.get("chat_id", self.chat_id)
        self._chat_ready = True
        logger.info("[ConversationScreen] Chat ready: %s", self.chat_id)
        self._fetch_messages_from_firebase()

    def _local_chat_file(self) -> Path:
        return get_impobj_path() / "chatMSG" / f"{self.chat_id}.json"

    def _load_local_messages(self):
        chat_file = self._local_chat_file()
        if not chat_file.exists():
            logger.info("[ConversationScreen] No local cache at %s", chat_file)
            self._render_messages()
            return
        try:
            with chat_file.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
            self.local_messages = loaded if isinstance(loaded, list) else []
            logger.info(
                "[ConversationScreen] Loaded %d cached messages from %s",
                len(self.local_messages),
                chat_file,
            )
        except (OSError, ValueError) as error:
            logger.exception("[ConversationScreen] Failed to load local messages: %s", error)
            self.local_messages = []
        self._render_messages()

    def _save_all_local_messages(self):
        chat_file = self._local_chat_file()
        try:
            chat_file.parent.mkdir(parents=True, exist_ok=True)
            with chat_file.open("w", encoding="utf-8") as file:
                json.dump(
                    sorted(self.local_messages, key=self._message_timestamp_key),
                    file,
                    indent=2,
                )
        except OSError as error:
            logger.exception("[ConversationScreen] Failed to save local messages: %s", error)

    @staticmethod
    def _message_timestamp_key(message):
        timestamp = message.get("timestamp", "")
        if not timestamp:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (AttributeError, TypeError, ValueError):
            return datetime.min.replace(tzinfo=timezone.utc)

    def _render_messages(self):
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        messages = sorted(
            self.local_messages, key=self._message_timestamp_key
        )
        if not messages:
            empty_label = QLabel("No messages yet")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(
                "QLabel { color: #888888; font-size: 18px; padding: 50px; }"
            )
            self.messages_layout.addWidget(empty_label)
            self.messages_layout.addStretch()
            return
        for message in messages:
            author_uid = message.get("author_uid")
            author = message.get("author", "")
            is_own = author_uid == self.user_uid or (
                author.casefold() == self.current_username.casefold()
            )
            card = MessageCardWidget(message, is_own, self.messages_container)
            card.delete_requested.connect(self._on_delete_message)
            card.download_requested.connect(self._on_attachment_download)
            self.messages_layout.addWidget(card)
        self.messages_layout.addStretch()
        scrollbar = self.messages_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _fetch_messages_from_firebase(self, show_loading=True):
        if self._messages_fetching:
            logger.info(
                "[ConversationScreen] Skipping message fetch; previous fetch is active."
            )
            return
        self._messages_fetching = True
        logger.info(
            "[ConversationScreen] Fetching messages for chat_id: %s",
            self.chat_id,
        )
        if show_loading:
            self.loading_overlay.move(
                self.rect().center() - self.loading_overlay.rect().center()
            )
            self.loading_overlay.show()
            self.loading_overlay.raise_()
        self._run_worker(
            self.dm_service.get_messages,
            lambda result: self._handle_firebase_messages(
                result, hide_loading=show_loading
            ),
            self.user_uid,
            self.chat_id,
            self.user_token,
            50,
            None,
        )

    def _handle_firebase_messages(self, result, hide_loading=True):
        self._messages_fetching = False
        if hide_loading:
            self.loading_overlay.hide()
        if isinstance(result, dict) and "__worker_error__" in result:
            logger.error(
                "[ConversationScreen] Failed to fetch messages: %s",
                result["__worker_error__"],
            )
            return
        if not isinstance(result, dict):
            logger.error(
                "[ConversationScreen] Unexpected message fetch result: %r", result
            )
            return

        messages = result.get("messages", [])
        logger.info(
            "[ConversationScreen] Fetched %d messages from Firebase.",
            len(messages),
        )
        if messages:
            logger.info(
                "[ConversationScreen] Sample fetched message keys: %s",
                list(messages[0].keys()),
            )
            logger.info(
                "[ConversationScreen] Sample fetched message author_uid: %s",
                messages[0].get("author_uid"),
            )

        known_ids = {message.get("id") for message in self.local_messages}
        new_messages = [
            message for message in messages
            if message.get("id") not in known_ids
        ]
        logger.info(
            "[ConversationScreen] Found %d NEW messages to process locally.",
            len(new_messages),
        )
        if new_messages:
            self.local_messages.extend(new_messages)
            self._save_all_local_messages()
            self._render_messages()


        text_messages_to_delete = []
        for message in messages:
            has_storage = bool(message.get("storage_path"))
            author_uid = message.get("author_uid")
            is_other_user = author_uid != self.user_uid
            logger.info(
                "[ConversationScreen] Evaluating fetched msg %s: "
                "has_storage=%s, author_uid=%s, is_other_user=%s",
                message.get("id"),
                has_storage,
                author_uid,
                is_other_user,
            )
            if (
                not has_storage
                and is_other_user
                and author_uid
                and message.get("id")
            ):
                text_messages_to_delete.append(
                    {"msg_id": message["id"], "author_uid": author_uid}
                )

        logger.info(
            "[ConversationScreen] Identified %d fetched text messages from other "
            "users for Firestore cleanup.",
            len(text_messages_to_delete),
        )
        author_uids = {
            message["author_uid"] for message in text_messages_to_delete
        }
        for author_uid in author_uids:
            message_ids = [
                message["msg_id"]
                for message in text_messages_to_delete
                if message["author_uid"] == author_uid
            ]
            logger.info(
                "[ConversationScreen] Triggering dual Firestore cleanup for %d "
                "text messages from folders: %s",
                len(message_ids),
                [author_uid, self.user_uid],
            )
            target_uids = list(dict.fromkeys([author_uid, self.user_uid]))
            self._run_worker(
                self.dm_service.delete_text_messages,
                lambda cleanup_result: logger.info(
                    "[ConversationScreen] Firestore cleanup result: %s",
                    cleanup_result,
                ),
                target_uids,
                self.chat_id,
                message_ids,
                self.user_token,
            )

    def _on_send_clicked(self):
        if self.selected_file_path:
            self._send_attachment()
            return
        content = self.message_input.text().strip()
        logger.info(
            "[ConversationScreen] Send clicked. Content length: %d",
            len(content),
        )
        if not content:
            logger.warning("[ConversationScreen] Send aborted: Empty content.")
            return
        if not self._chat_ready:
            logger.warning(
                "[ConversationScreen] Send aborted: chat is not initialized."
            )
            return
        self.message_input.clear()
        timestamp = datetime.now().astimezone().isoformat()
        temp_id = f"temp_{datetime.now().timestamp()}"
        optimistic_message = {
            "id": temp_id,
            "author": self.current_username,
            "author_uid": self.user_uid,
            "content": content,
            "timestamp": timestamp,
            "storage_path": None,
        }
        logger.info(
            "[ConversationScreen] Adding optimistic message %s to local storage.",
            temp_id,
        )
        self.local_messages.append(optimistic_message)
        self._save_all_local_messages()
        self._render_messages()
        self._set_send_buttons_enabled(False)
        logger.info(
            "[ConversationScreen] Dispatching background worker to send message."
        )
        self._run_worker(
            self.dm_service.send_message,
            lambda result, message_id=temp_id: self._handle_send_result(
                message_id, result
            ),
            self.user_uid,
            self.chat_id,
            content,
            self.current_username,
            self.user_token,
            None,
        )

    def _handle_send_result(self, temp_id, result):
        logger.info("[ConversationScreen] Send result received: %s", result)
        self._set_send_buttons_enabled(True)
        if isinstance(result, dict) and "__worker_error__" in result:
            logger.error(
                "[ConversationScreen] FAILED to send message: %s",
                result["__worker_error__"],
            )
            result = {"success": False, "error": result["__worker_error__"]}
        if not result.get("success"):
            logger.error(
                "[ConversationScreen] Firebase rejected message: %s",
                result.get("error"),
            )
            self.local_messages = [
                message for message in self.local_messages if message.get("id") != temp_id
            ]
            self._save_all_local_messages()
            self._render_messages()
            QMessageBox.warning(
                self, "Message not sent", result.get("error", "Please try again.")
            )
            return
        real_id = result.get("message_id")
        logger.info(
            "[ConversationScreen] Message sent successfully. Real ID: %s",
            real_id,
        )
        for message in self.local_messages:
            if message.get("id") == temp_id:
                message["id"] = real_id
                break
        self._save_all_local_messages()
        self._render_messages()

    def _on_attach_clicked(self):
        choice_dialog = QMessageBox(self)
        choice_dialog.setWindowTitle("Select Attachment")
        choice_dialog.setText("Do you want to send files or a folder?")
        files_button = choice_dialog.addButton(
            "Files", QMessageBox.ButtonRole.AcceptRole
        )
        folder_button = choice_dialog.addButton(
            "Folder", QMessageBox.ButtonRole.AcceptRole
        )
        choice_dialog.addButton(QMessageBox.StandardButton.Cancel)
        choice_dialog.exec()
        choice = choice_dialog.clickedButton()

        if choice == files_button:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "Select Files",
                str(Path.home()),
                "All Files (*);;Images (*.png *.jpg *.jpeg);;"
                "Documents (*.pdf *.docx *.txt)",
            )
            if file_paths:
                self._process_selected_file(file_paths[0], is_temp_zip=False)
            return

        if choice != folder_button:
            logger.info("[ConversationScreen] Attachment selection cancelled.")
            return

        directory_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", str(Path.home())
        )
        if not directory_path:
            logger.info("[ConversationScreen] Folder selection cancelled.")
            return
        try:
            import shutil
            import tempfile

            archive_name = (
                f"{Path(directory_path).name}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            archive_base = os.path.join(tempfile.gettempdir(), archive_name)
            archive_path = shutil.make_archive(
                archive_base, "zip", root_dir=directory_path
            )
            self._process_selected_file(archive_path, is_temp_zip=True)
        except (OSError, shutil.Error) as error:
            logger.exception("[ConversationScreen] Failed to zip folder: %s", error)
            QMessageBox.warning(self, "Folder unavailable", str(error))

    def _process_selected_file(self, file_path: str, is_temp_zip: bool = False):
        """Validate and prepare a selected file or zipped folder for sending."""
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        except OSError as error:
            logger.error("[ConversationScreen] Failed to inspect file: %s", error)
            if is_temp_zip and os.path.exists(file_path):
                os.remove(file_path)
            QMessageBox.warning(self, "File unavailable", str(error))
            return
        if file_size_mb > 35:
            QMessageBox.warning(
                self,
                "File Too Large",
                f"Size ({file_size_mb:.2f} MB) exceeds the 35 MB limit.",
            )
            if is_temp_zip and os.path.exists(file_path):
                os.remove(file_path)
            return
        self.selected_file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.file_size = file_size_mb
        self.is_temp_zip = is_temp_zip
        self.file_name_label.setText(self.file_name)
        self.file_size_label.setText(f"{file_size_mb:.2f} MB")
        self.text_input_row.hide()
        self.file_pill_widget.show()
        self.file_selection_row.show()
        self.message_input.setEnabled(False)
        self.message_input.clear()
        logger.info(
            "[ConversationScreen] File selected: %s (%.2f MB)",
            self.file_name,
            file_size_mb,
        )

    def _clear_selected_file(self, delete_temp_zip=True):
        if (
            delete_temp_zip
            and self.is_temp_zip
            and self.selected_file_path
            and os.path.exists(self.selected_file_path)
        ):
            try:
                os.remove(self.selected_file_path)
                logger.info(
                    "[ConversationScreen] Cleaned up temp zip: %s",
                    self.selected_file_path,
                )
            except OSError as error:
                logger.error(
                    "[ConversationScreen] Failed to delete temp zip: %s", error
                )
        self.selected_file_path = None
        self.file_name = None
        self.file_size = None
        self.is_temp_zip = False
        self.file_selection_row.hide()
        self.file_pill_widget.hide()
        self.text_input_row.show()
        self.message_input.clear()
        self.message_input.setEnabled(True)
        self.message_input.setFocus()

    def _send_attachment(self):
        if not self.selected_file_path or not self._chat_ready:
            logger.warning("[ConversationScreen] Attachment send aborted: chat is not ready.")
            return
        file_path = self.selected_file_path
        file_name = self.file_name or os.path.basename(file_path)
        temp_zip_path = file_path if self.is_temp_zip else None
        self.message_input.clear()
        self._clear_selected_file(delete_temp_zip=False)

        temp_id = f"temp_attach_{datetime.now().timestamp()}"
        optimistic_message = {
            "id": temp_id,
            "author": self.current_username,
            "author_uid": self.user_uid,
            "content": "",
            "storage_path": f"uploading.../{file_name}",
            "file_name": file_name,
            "timestamp": datetime.now().astimezone().isoformat(),
            "is_uploading": True,
        }
        self.local_messages.append(optimistic_message)
        self._save_all_local_messages()
        self._render_messages()
        self._set_send_buttons_enabled(False)
        logger.info(
            "[ConversationScreen] Uploading attachment %s for message %s",
            file_name,
            temp_id,
        )
        self._run_worker(
            self.dm_service.upload_file,
            lambda result: self._handle_upload_result(
                temp_id, result, temp_zip_path
            ),
            self.chat_id,
            temp_id,
            file_path,
            self.user_token,
        )

    def _handle_upload_result(self, temp_id, result, temp_zip_path=None):
        logger.info("[ConversationScreen] Attachment upload result: %s", result)
        if temp_zip_path and os.path.exists(temp_zip_path):
            try:
                os.remove(temp_zip_path)
                logger.info(
                    "[ConversationScreen] Cleaned up uploaded temp zip: %s",
                    temp_zip_path,
                )
            except OSError as error:
                logger.error(
                    "[ConversationScreen] Failed to delete uploaded temp zip: %s",
                    error,
                )
        if isinstance(result, dict) and "__worker_error__" in result:
            result = {"success": False, "error": result["__worker_error__"]}
        if not result.get("success"):
            logger.error(
                "[ConversationScreen] Attachment upload failed: %s",
                result.get("error"),
            )
            self.local_messages = [
                message for message in self.local_messages
                if message.get("id") != temp_id
            ]
            self._save_all_local_messages()
            self._render_messages()
            self._set_send_buttons_enabled(True)
            QMessageBox.warning(
                self, "Upload failed", result.get("error", "Could not upload file.")
            )
            return

        storage_path = result["storage_path"]
        optimistic_message = next(
            (
                message
                for message in self.local_messages
                if message.get("id") == temp_id
            ),
            {},
        )
        file_name = optimistic_message.get("file_name", "")
        logger.info(
            "[ConversationScreen] Upload successful, persisting to Firestore "
            "with path: %s",
            storage_path,
        )
        for message in self.local_messages:
            if message.get("id") == temp_id:
                message["storage_path"] = storage_path
                message["is_uploading"] = False
                break
        self._save_all_local_messages()
        self._render_messages()
        self._run_worker(
            self.dm_service.send_message,
            lambda firestore_result: self._handle_firestore_persist(
                temp_id, firestore_result
            ),
            self.user_uid,
            self.chat_id,
            "",
            self.current_username,
            self.user_token,
            storage_path,
            file_name,
        )

    def _handle_firestore_persist(self, temp_id, result):
        """Handle the Firestore result for an uploaded attachment message."""
        logger.info("[ConversationScreen] Attachment message result: %s", result)
        self._set_send_buttons_enabled(True)
        if isinstance(result, dict) and "__worker_error__" in result:
            result = {"success": False, "error": result["__worker_error__"]}
        if not result.get("success"):
            logger.error(
                "[ConversationScreen] Failed to persist attachment message: %s",
                result.get("error"),
            )
            self.local_messages = [
                message for message in self.local_messages
                if message.get("id") != temp_id
            ]
            self._save_all_local_messages()
            self._render_messages()
            QMessageBox.warning(
                self,
                "Message not sent",
                result.get("error", "Could not send attachment."),
            )
            return
        real_id = result.get("message_id")
        for message in self.local_messages:
            if message.get("id") == temp_id:
                message["id"] = real_id
                message["is_uploading"] = False
                break
        self._save_all_local_messages()
        self._render_messages()

    def _on_attachment_download(self, storage_path, destination_path):
        if not storage_path:
            logger.warning("[ConversationScreen] Download aborted: storage path is missing.")
            return
        logger.info("[ConversationScreen] Attachment download requested: %s", storage_path)
        self.loading_overlay.move(
            self.rect().center() - self.loading_overlay.rect().center()
        )
        self.loading_overlay.show()
        self.loading_overlay.raise_()
        self._run_worker(
            self.dm_service.download_file,
            lambda result: self._handle_download_result(result, destination_path),
            storage_path,
            destination_path,
            self.user_token,
        )

    def _handle_download_result(self, result, destination_path):
        self.loading_overlay.hide()
        logger.info("[ConversationScreen] Attachment download result: %s", result)
        if isinstance(result, dict) and result.get("success"):
            QMessageBox.information(
                self,
                "Download complete",
                f"File saved to:\n{destination_path}",
            )
        else:
            error = result.get("error", "Download failed.") if isinstance(result, dict) else "Download failed."
            QMessageBox.warning(self, "Download failed", error)

    def _on_delete_message(self, message_id: str):
        logger.info(
            "[ConversationScreen] Delete requested for message_id: %s",
            message_id,
        )
        original_index = next(
            (
                index
                for index, message in enumerate(self.local_messages)
                if message.get("id") == message_id
            ),
            None,
        )
        if original_index is None:
            logger.warning(
                "[ConversationScreen] Message %s is not in the local list.",
                message_id,
            )
            return
        original_message = self.local_messages.pop(original_index)
        self._save_all_local_messages()
        self._render_messages()
        self._run_worker(
            self.dm_service.delete_message,
            lambda result: self._handle_delete_result(
                message_id, original_message, original_index, result
            ),
            self.user_uid,
            self.chat_id,
            message_id,
            self.user_token,
        )

    def _handle_delete_result(self, message_id, original_message, original_index, result):
        logger.info(
            "[ConversationScreen] Delete result for %s: %s",
            message_id,
            result,
        )
        if isinstance(result, dict) and "__worker_error__" in result:
            result = {"success": False, "error": result["__worker_error__"]}
        if result.get("success"):
            logger.info(
                "[ConversationScreen] Message %s deleted locally.", message_id
            )
            return
        logger.error(
            "[ConversationScreen] Failed to delete message %s: %s",
            message_id,
            result.get("error"),
        )
        if not any(
            message.get("id") == message_id for message in self.local_messages
        ):
            self.local_messages.insert(
                min(original_index, len(self.local_messages)), original_message
            )
            self._save_all_local_messages()
            self._render_messages()
        QMessageBox.warning(
            self, "Delete failed", result.get("error", "Could not delete message.")
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()
        if not self.refresh_timer.isActive():
            self.refresh_timer.start()
            logger.info("[ConversationScreen] Auto-refresh timer started (30s).")

    def hideEvent(self, event):
        self.refresh_timer.stop()
        logger.info("[ConversationScreen] Auto-refresh timer stopped.")
        super().hideEvent(event)

    def _refresh_messages(self):
        if self.isVisible():
            self._fetch_messages_from_firebase(show_loading=False)
