from PySide6.QtCore import QObject, QThread, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QTextEdit, QVBoxLayout, QWidget

from create_post_service import CreatePostService
from tags_service import TagsService
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
            result = {"success": False, "error": f"System error: {error}"}
        self.signals.finished.emit(result)


class CreatePostScreen(QWidget):
    post_created = Signal()

    def __init__(self, user_uid: str, user_token: str, parent=None):
        super().__init__(parent)
        self.user_uid = user_uid
        self.user_token = user_token
        self.service = CreatePostService()
        self.tags_service = TagsService()
        self.selected_tag_ids = []
        self.all_tags = self.tags_service.get_tags()
        self._workers = []
        self.setWindowFlags(Qt.WindowType.Window)
        self._setup_ui()
        self.loading_overlay = LoadingWidget(self)
        self.loading_overlay.hide()

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()
        self._center_loading_overlay()

    def _center_loading_overlay(self):
        self.loading_overlay.move(self.rect().center() - self.loading_overlay.rect().center())

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "loading_overlay"):
            self._center_loading_overlay()

    def _setup_ui(self):
        self.setWindowTitle("Create Post - Devmeld")
        self.setStyleSheet("QWidget { background: #0f0f0f; color: #fff; font-family: 'Segoe UI'; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        header = QHBoxLayout()
        header.addStretch()
        self.post_btn = QPushButton("post")
        self.post_btn.setFixedSize(120, 45)
        self.post_btn.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.post_btn.setStyleSheet("QPushButton { background: transparent; color: #00ff88; border: 2px solid #00ff88; border-radius: 22px; } QPushButton:hover { background: #00ff88; color: #000; } QPushButton:disabled { color: #555; border-color: #555; } QPushButton:pressed { padding: 2px 10px 4px 12px; }")
        self.post_btn.clicked.connect(self._on_post_clicked)
        header.addWidget(self.post_btn)
        layout.addLayout(header)

        self.tag_caption = QLabel("choose at least one tag")
        self.tag_caption.setStyleSheet("QLabel { color: #ff4444; font-size: 12px; font-weight: bold; }")
        layout.addWidget(self.tag_caption)

        self.tag_search_input = QLineEdit()
        self.tag_search_input.setPlaceholderText("tag search")
        self.tag_search_input.setFixedHeight(50)
        self.tag_search_input.setFont(QFont("Segoe UI", 16))
        self.tag_search_input.setStyleSheet(
            "QLineEdit { background: #1a1a1a; color: #ffffff; border: 3px solid #ffffff; "
            "border-radius: 25px; padding: 0 20px; }"
            "QLineEdit:focus { border: 3px solid #00aeff; }"
        )
        self.tag_search_input.textChanged.connect(self._on_tag_search_changed)
        layout.addWidget(self.tag_search_input)
        self.tag_suggestions = QListWidget()
        self.tag_suggestions.setFixedHeight(150)
        self.tag_suggestions.itemClicked.connect(self._on_tag_suggestion_clicked)
        self.tag_suggestions.hide()
        layout.addWidget(self.tag_suggestions)
        self.selected_tags_layout = QHBoxLayout()
        layout.addLayout(self.selected_tags_layout)

        title_label = QLabel("title:")
        title_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        layout.addWidget(title_label)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Write your title...")
        self.title_input.setFixedHeight(50)
        self.title_input.setFont(QFont("Segoe UI", 16))
        self.title_input.setMaxLength(350)
        self.title_input.setStyleSheet(self._get_title_style("#ffffff"))
        self.title_input.textChanged.connect(self._check_title_limit)
        layout.addWidget(self.title_input)

        body_label = QLabel("body:")
        body_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        layout.addWidget(body_label)
        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText("Share your thoughts...")
        self.body_input.setFont(QFont("Segoe UI", 14))
        self.body_input.setMaximumHeight(3000)
        self.body_input.setStyleSheet(self._get_body_style("#ffffff"))
        self.body_input.textChanged.connect(self._check_body_limit)
        layout.addWidget(self.body_input, 1)

        self.limit_warning_label = QLabel("")
        self.limit_warning_label.setStyleSheet("QLabel { color: #ff4444; font-size: 14px; font-weight: bold; padding: 5px; }")
        self.limit_warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.limit_warning_label)
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("QLabel { color: #ff4444; font-size: 14px; padding: 10px; }")
        self.warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.warning_label)
        self._validate_form()

    def _get_title_style(self, color):
        return f"QLineEdit {{ background: #1a1a1a; color: #fff; border: 2px solid {color}; border-radius: 8px; padding: 0 15px; }} QLineEdit:focus {{ border: 2px solid #00aeff; }}"

    def _get_body_style(self, color):
        return f"QTextEdit {{ background: #1a1a1a; color: #fff; border: 2px solid {color}; border-radius: 8px; padding: 15px; }} QTextEdit:focus {{ border: 2px solid #00aeff; }}"

    def _check_title_limit(self):
        length = len(self.title_input.text())
        if length >= 350:
            self.title_input.setStyleSheet(self._get_title_style("#ff4444"))
            self.limit_warning_label.setText("[reached the limit]")
        elif length >= 300:
            self.title_input.setStyleSheet(self._get_title_style("#ff4444"))
            self.limit_warning_label.clear()
        elif length >= 150:
            self.title_input.setStyleSheet(self._get_title_style("#ffd700"))
            self.limit_warning_label.clear()
        else:
            self.title_input.setStyleSheet(self._get_title_style("#ffffff"))
            self.limit_warning_label.clear()
        self._validate_form()

    def _check_body_limit(self):
        length = len(self.body_input.toPlainText())
        if length > 3000:
            self.body_input.blockSignals(True)
            self.body_input.setPlainText(self.body_input.toPlainText()[:3000])
            self.body_input.blockSignals(False)
            length = 3000
        if length >= 3000:
            self.body_input.setStyleSheet(self._get_body_style("#ff4444"))
            self.limit_warning_label.setText("[reached the limit]")
        elif length >= 2500:
            self.body_input.setStyleSheet(self._get_body_style("#ff4444"))
            self.limit_warning_label.clear()
        elif length >= 1500:
            self.body_input.setStyleSheet(self._get_body_style("#ffd700"))
            self.limit_warning_label.clear()
        else:
            self.body_input.setStyleSheet(self._get_body_style("#ffffff"))
            self.limit_warning_label.clear()
        self._validate_form()

    def _on_tag_search_changed(self, text):
        self.tag_suggestions.clear()
        if not text.strip() or len(self.selected_tag_ids) >= 3:
            self.tag_suggestions.hide()
            return
        matches = [
            tag for tag in self.tags_service.search_tags(text)
            if tag["id"] not in self.selected_tag_ids
        ]
        for tag in matches[:5]:
            item = QListWidgetItem(tag["tag"])
            item.setData(Qt.ItemDataRole.UserRole, tag["id"])
            self.tag_suggestions.addItem(item)
        self.tag_suggestions.setVisible(bool(matches))

    def _on_tag_suggestion_clicked(self, item):
        tag_id = item.data(Qt.ItemDataRole.UserRole)
        if tag_id not in self.selected_tag_ids and len(self.selected_tag_ids) < 3:
            self.selected_tag_ids.append(tag_id)
            self.tag_search_input.clear()
            self.tag_suggestions.hide()
            self._render_selected_tags()
            self._validate_form()

    def _render_selected_tags(self):
        while self.selected_tags_layout.count():
            item = self.selected_tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for tag_id in self.selected_tag_ids:
            tag = next((value for value in self.all_tags if value["id"] == tag_id), {"tag": "#unknown"})
            button = QPushButton(tag["tag"])
            button.setFixedSize(100, 35)
            button.clicked.connect(lambda checked=False, selected=tag_id: self._remove_tag(selected))
            self.selected_tags_layout.addWidget(button)
        self.selected_tags_layout.addStretch()

    def _remove_tag(self, tag_id):
        self.selected_tag_ids.remove(tag_id)
        self._render_selected_tags()
        self._validate_form()

    def _validate_form(self):
        valid = bool(self.title_input.text().strip() and self.body_input.toPlainText().strip() and 1 <= len(self.selected_tag_ids) <= 3)
        self.post_btn.setEnabled(valid)
        if valid:
            self.warning_label.clear()

    def _on_post_clicked(self):
        title = self.title_input.text().strip()
        body = self.body_input.toPlainText().strip()
        if not title or not body or not (1 <= len(self.selected_tag_ids) <= 3):
            self._validate_form()
            return
        self.post_btn.setEnabled(False)
        self.warning_label.setText("Posting...")
        self._show_loading()
        self._start_worker(
            self.service.submit_post,
            self._handle_post_publish,
            title,
            body,
            list(self.selected_tag_ids),
            self.user_uid,
            self.user_token,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "loading_overlay"):
            self._center_loading_overlay()

    def _handle_post_publish(self, result):
        self.loading_overlay.hide()
        self.post_btn.setEnabled(True)
        if isinstance(result, dict) and "__worker_error__" in result:
            result = {"success": False, "error": result["__worker_error__"]}
        if result.get("success"):
            self.warning_label.setStyleSheet("QLabel { color: #00ff88; font-size: 14px; font-weight: bold; }")
            self.warning_label.setText("Posted successfully!")
            QTimer.singleShot(700, self._on_success)
        else:
            self.warning_label.setStyleSheet("QLabel { color: #ff4444; font-size: 14px; font-weight: bold; }")
            self.warning_label.setText(result.get("error", "Failed to create post."))

    def _on_success(self):
        print("[CreatePostScreen] Emitting post_created signal")
        self.post_created.emit()
        self.close()
