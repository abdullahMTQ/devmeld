from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from code_editor_entry_pill_widget import CodeEditorEntryPillWidget
from code_editor_service import CodeEditorService
from impobj_utils import logger


class CodeEditorHomeScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = CodeEditorService()
        self.setWindowFlags(Qt.WindowType.Window)
        self._setup_ui()
        self._load_entries()

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()

    def _setup_ui(self):
        self.setWindowTitle("Code Editor - Devmeld")
        self.setStyleSheet(
            "QWidget { background-color: #000000; color: #ffffff; "
            "font-family: 'Segoe UI'; }"
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(30)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(20)
        caption = QLabel("code editor")
        caption.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        caption.setStyleSheet(
            "color: #ffffff; background: transparent; border: none;"
        )
        top_bar.addWidget(caption)
        top_bar.addStretch()

        self.select_folder_btn = QPushButton("select folder")
        self.select_folder_btn.setFixedHeight(50)
        self.select_folder_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.select_folder_btn.setStyleSheet(
            "QPushButton { background: #000000; color: #ffffff; "
            "border: 3px solid #ffffff; border-radius: 25px; padding: 0 25px; } "
            "QPushButton:hover { border: 3px solid #00aeff; color: #00aeff; } "
            "QPushButton:pressed { background: #00aeff; color: #000000; }"
        )
        self.select_folder_btn.clicked.connect(self._on_select_folder)
        top_bar.addWidget(self.select_folder_btn)
        main_layout.addLayout(top_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )
        self.entries_container = QWidget()
        self.entries_container.setStyleSheet(
            "background: transparent; border: none;"
        )
        self.entries_layout = QVBoxLayout(self.entries_container)
        self.entries_layout.setContentsMargins(0, 0, 0, 0)
        self.entries_layout.setSpacing(15)
        self.entries_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.entries_container)
        main_layout.addWidget(self.scroll_area, 1)

    def _load_entries(self):
        while self.entries_layout.count():
            item = self.entries_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        entries = self.service.get_quick_entries()
        if not entries:
            empty_label = QLabel("No recent folders. Select a folder to begin.")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setFont(QFont("Segoe UI", 14))
            empty_label.setStyleSheet(
                "QLabel { color: #888888; background: transparent; border: none; "
                "padding: 50px; }"
            )
            self.entries_layout.addWidget(empty_label)
            self.entries_layout.addStretch()
            return

        for entry in entries:
            pill = CodeEditorEntryPillWidget(entry, self.entries_container)
            pill.open_folder.connect(self._on_open_folder)
            pill.remove_folder.connect(self._on_remove_folder)
            self.entries_layout.addWidget(pill)
        self.entries_layout.addStretch()

    def _on_select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Project Folder", ""
        )
        if folder_path:
            self._launch_ide(folder_path)

    def _on_open_folder(self, folder_path: str):
        self._launch_ide(folder_path)

    def _on_remove_folder(self, folder_path: str):
        result = self.service.remove_quick_entry(folder_path)
        if result.get("success"):
            logger.info("Code editor: removed quick entry for %s", folder_path)
            self._load_entries()
        else:
            logger.warning(
                "Code editor: failed to remove entry: %s", result.get("error")
            )

    def _launch_ide(self, folder_path: str):
        """Save a quick entry and open the project workspace."""
        result = self.service.open_folder(folder_path)
        if not result.get("success"):
            logger.error(
                "Code editor: failed to open folder: %s", result.get("error")
            )
            return
        self._load_entries()
        from code_editor_workspace_screen import CodeEditorWorkspaceScreen

        self.workspace_screen = CodeEditorWorkspaceScreen(
            folder_path, parent=self
        )
        self.workspace_screen.show()
