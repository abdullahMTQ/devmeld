from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMenu,
    QMessageBox,
    QPushButton,
    QWidget,
)

from editor_settings_adapter import load_editor_settings, save_editor_settings
from global_search_widget import GlobalSearchWidget
from impobj_utils import logger


class ToolsBarWidget(QWidget):
    tool_requested = Signal(str)
    checkpoint_requested = Signal()
    new_file_requested = Signal()
    new_folder_requested = Signal()
    open_folder_requested = Signal()
    exit_requested = Signal()
    save_requested = Signal()
    close_editor_requested = Signal()
    auto_save_toggled = Signal(bool)
    search_query_changed = Signal(str)
    file_selected = Signal(str, int)

    def __init__(self, parent=None, root_path="."):
        super().__init__(parent)
        self.root_path = root_path
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)
        self.setStyleSheet(
            "background: #252526; border-bottom: 1px solid #333333;"
        )

        self.file_btn = QPushButton("File")
        self.file_btn.setFixedHeight(35)
        self.file_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.file_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #858585; border: none; "
            "border-bottom: 2px solid transparent; padding: 0 15px; } "
            "QPushButton:hover { color: #ffffff; background: #2a2d2e; } "
            "QPushButton:pressed { color: #ffffff; background: #37373d; }"
        )
        self.file_menu = QMenu(self.file_btn)
        self.file_menu.setStyleSheet(
            "QMenu { background: #252526; color: #ffffff; border: 1px solid #333333; } "
            "QMenu::item { padding: 6px 20px; } "
            "QMenu::item:selected { background: #007acc; } "
            "QMenu::item:disabled { color: #666666; }"
        )
        self.file_menu.addAction("New File").triggered.connect(
            self.new_file_requested.emit
        )
        self.file_menu.addAction("New Folder").triggered.connect(
            self.new_folder_requested.emit
        )
        self.file_menu.addAction("Open Folder").triggered.connect(
            self.open_folder_requested.emit
        )
        self.file_menu.addSeparator()
        self.auto_save_action = self.file_menu.addAction("Auto Save")
        self.auto_save_action.setCheckable(True)
        settings = load_editor_settings()
        self.auto_save_action.setChecked(bool(settings.get("auto_save", True)))
        self.auto_save_action.toggled.connect(self._on_auto_save_toggled)

        self.save_action = self.file_menu.addAction("Save")
        self.save_action.triggered.connect(self.save_requested.emit)
        self._update_save_button_state()
        self.file_menu.addSeparator()
        self.file_menu.addAction("Save Checkpoint").triggered.connect(
            self.checkpoint_requested.emit
        )
        self.file_menu.addSeparator()
        self.file_menu.addAction("Close Editor").triggered.connect(
            self.close_editor_requested.emit
        )
        self.file_menu.addSeparator()
        self.file_menu.addAction("Exit").triggered.connect(
            self.exit_requested.emit
        )
        self.file_btn.setMenu(self.file_menu)
        layout.addWidget(self.file_btn)

        self.global_search_widget = GlobalSearchWidget(self.root_path, self)
        self.global_search_widget.search_query_changed.connect(
            self.search_query_changed.emit
        )
        self.global_search_widget.file_selected.connect(self.file_selected.emit)
        layout.addWidget(self.global_search_widget)

        self.buttons = {}
        tools = ("Terminal", "Problems", "Output", "Debug Console", "TODOs")
        for tool_name in tools:
            button = QPushButton(tool_name)
            button.setFixedHeight(35)
            button.setFont(QFont("Segoe UI", 10))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                "QPushButton { background: transparent; color: #858585; "
                "border: none; border-bottom: 2px solid transparent; padding: 0 15px; } "
                "QPushButton:hover { color: #ffffff; background: #2a2d2e; } "
                "QPushButton:pressed { color: #ffffff; background: #37373d; }"
            )
            button.setProperty("tool_name", tool_name)
            button.clicked.connect(self._on_tool_button_clicked)
            layout.addWidget(button)
            self.buttons[tool_name] = button
        layout.addStretch()

    def _on_tool_button_clicked(self):
        button = self.sender()
        if not isinstance(button, QPushButton):
            return
        tool_name = button.property("tool_name")
        if isinstance(tool_name, str):
            self.tool_requested.emit(tool_name)

    def _on_auto_save_toggled(self, checked: bool):
        if not checked:
            answer = QMessageBox.warning(
                self,
                "Disable Auto Save?",
                "Changes will no longer be saved automatically. "
                "You will need to use Save, and unsaved changes will prompt "
                "before files are closed.\n\n"
                "Are you sure you want to disable Auto Save?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.auto_save_action.blockSignals(True)
                self.auto_save_action.setChecked(True)
                self.auto_save_action.blockSignals(False)
                return

        settings = load_editor_settings()
        settings["auto_save"] = checked
        if not save_editor_settings(settings):
            logger.error("Could not persist the editor auto-save setting")
        self._update_save_button_state()
        self.auto_save_toggled.emit(checked)

    def _update_save_button_state(self):
        auto_save_enabled = self.auto_save_action.isChecked()
        self.save_action.setText(
            "Save (Auto Save On)" if auto_save_enabled else "Save"
        )
        self.save_action.setEnabled(not auto_save_enabled)
