from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from global_search_service import GlobalSearchService


class SuggestionsPopup(QListWidget):
    """Floating results list that does not activate or take input focus."""

    item_chosen = Signal(dict)

    def __init__(self, target_input, parent=None):
        super().__init__(parent)
        self.target_input = target_input
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedHeight(350)
        self.setFixedWidth(600)
        self.setStyleSheet(
            "QListWidget { background: #252526; color: #fff; border: 1px solid #333; "
            "border-radius: 4px; }"
            "QListWidget::item { padding: 8px 10px; border-bottom: 1px solid #333; "
            "font-size: 12px; }"
            "QListWidget::item:hover { background: #37373d; }"
            "QListWidget::item:selected { background: #007acc; }"
        )
        self.itemClicked.connect(self._on_item_clicked)

    def show_under_widget(self, widget):
        """Show the popup directly below the supplied widget."""
        bottom_left = widget.mapToGlobal(QPoint(0, widget.height()))
        self.move(bottom_left.x(), bottom_left.y() + 5)
        self.show()
        QTimer.singleShot(0, self._restore_target_focus)

    def _restore_target_focus(self):
        target_window = self.target_input.window()
        target_window.activateWindow()
        self.target_input.setFocus()

    def _on_item_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            self.item_chosen.emit(data)
            self.hide()
            QTimer.singleShot(0, self._restore_target_focus)


class GlobalSearchWidget(QWidget):
    file_selected = Signal(str, int)
    search_query_changed = Signal(str)

    def __init__(self, root_path: str, parent=None):
        super().__init__(parent)
        self.root_path = str(Path(root_path))
        self.service = GlobalSearchService()
        self._setup_ui()

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        search_container = QWidget()
        search_container.setFixedHeight(35)
        search_container.setStyleSheet(
            "background: #252526; border: 1px solid #333; border-radius: 4px;"
        )

        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(5, 2, 5, 2)
        search_layout.setSpacing(5)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search files and code...")
        self.search_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.search_input.setStyleSheet(
            "QLineEdit { background: transparent; color: #fff; border: none; "
            "padding: 0 10px; font-size: 13px; }"
            "QLineEdit:focus { border: none; }"
        )
        self.search_input.textChanged.connect(self._on_text_changed)
        search_layout.addWidget(self.search_input, 1)

        self.clear_search_btn = QPushButton("✕")
        self.clear_search_btn.setFixedSize(24, 24)
        self.clear_search_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.clear_search_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #ff4444; border: none; "
            "border-radius: 12px; padding: 0; }"
            "QPushButton:hover { color: #ff0000; background: #37373d; }"
        )
        self.clear_search_btn.clicked.connect(self._clear_search)
        self.clear_search_btn.hide()
        search_layout.addWidget(self.clear_search_btn)
        layout.addWidget(search_container)

        self.popup = SuggestionsPopup(self.search_input, self)
        self.popup.item_chosen.connect(self._on_popup_item_chosen)

    def _on_text_changed(self, text: str):
        self.clear_search_btn.setVisible(bool(text.strip()))
        self.search_query_changed.emit(text)
        if len(text.strip()) < 2:
            self.search_timer.stop()
            self.popup.hide()
            return
        self.search_timer.start(300)

    def _clear_search(self):
        self.search_timer.stop()
        self.search_input.clear()
        self.popup.hide()
        self.search_input.setFocus()

    def _perform_search(self):
        query = self.search_input.text().strip()
        results = self.service.search(self.root_path, query)
        self._render_results(results)

    def _render_results(self, results: list):
        self.popup.clear()
        if not results:
            self.popup.hide()
            return

        for result in results:
            item = QListWidgetItem()
            if result["type"] == "file":
                item.setText(f" {result['path']}")
            else:
                item.setText(
                    f" {result['path']}:{result['line']} — {result['content']}"
                )
            item.setData(Qt.ItemDataRole.UserRole, result)
            self.popup.addItem(item)

        self.popup.show_under_widget(self.search_input)

    def _on_popup_item_chosen(self, data: dict):
        self.file_selected.emit(data["path"], data["line"])
        self.search_input.clear()
        self.popup.hide()
        self.search_input.setFocus()
