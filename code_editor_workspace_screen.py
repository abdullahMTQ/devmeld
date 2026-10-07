from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from collaborator_chat_widget import CollaboratorChatWidget
from file_tree_widget import FileTreeWidget
from file_viewer_widget import FileViewerWidget
from tools_bar_widget import ToolsBarWidget
from file_watcher_service import FileWatcherService
from impobj_utils import logger
from terminal_widget import TerminalWidget
from problems_widget import ProblemsWidget
from output_widget import OutputWidget
from debug_console_widget import DebugConsoleWidget
from file_system_service import FileSystemService
from editor_settings_adapter import load_editor_settings
from todo_widget import TodoWindow


class CodeEditorWorkspaceScreen(QWidget):
    def __init__(self, folder_path: str, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.file_service = FileSystemService()
        self.watcher_service = FileWatcherService()
        self.todo_window = None
        self._editor_dirty = False
        self.auto_save_enabled = False
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle(f"Devmeld Code Editor - {folder_path}")
        self._setup_ui()
        self._start_watcher()

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()

    def _setup_ui(self):
        self.setStyleSheet("QWidget { background: #1e1e1e; color: #d4d4d4; }")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)
        splitter.setStyleSheet("QSplitter::handle { background: #333333; }")

        self.file_tree = FileTreeWidget(self.folder_path)
        self.file_tree.setMinimumWidth(150)
        self.file_tree.setMaximumWidth(420)
        splitter.addWidget(self.file_tree)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        self.tools_bar = ToolsBarWidget(center, self.folder_path)
        self.tools_bar.tool_requested.connect(self._on_tool_requested)
        self.tools_bar.checkpoint_requested.connect(self._on_checkpoint_requested)
        self.tools_bar.save_requested.connect(self._on_save_requested)
        self.tools_bar.close_editor_requested.connect(self._on_close_editor)
        self.tools_bar.auto_save_toggled.connect(self._on_auto_save_toggled)
        self.tools_bar.file_selected.connect(self._on_search_result_selected)
        self.tools_bar.new_file_requested.connect(
            lambda: self.file_tree._create_item("file", self.folder_path)
        )
        self.tools_bar.new_folder_requested.connect(
            lambda: self.file_tree._create_item("folder", self.folder_path)
        )
        self.tools_bar.open_folder_requested.connect(self._on_open_new_folder)
        self.tools_bar.exit_requested.connect(self.close)
        self.tools_bar.setFixedHeight(35)
        center_layout.addWidget(self.tools_bar)

        self.file_viewer = FileViewerWidget(center)
        self.file_viewer.set_auto_save_enabled(False)
        self.file_viewer.setMinimumHeight(100)
        self.file_viewer.file_saved.connect(self._on_file_saved)
        self.file_viewer.unsaved_changes.connect(
            self._on_unsaved_changes_changed
        )
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.setInterval(2000)
        self.auto_save_timer.timeout.connect(self._perform_auto_save)
        self.auto_save_enabled = bool(
            load_editor_settings().get("auto_save", True)
        )

        self.terminal_panel = TerminalWidget(self.folder_path, center)
        self.terminal_panel.hide()
        self.terminal_panel.exit_requested.connect(self._hide_terminal)
        self.problems_panel = ProblemsWidget(center)
        self.problems_panel.go_to_line.connect(self._go_to_problem_line)
        self.output_panel = OutputWidget(center)
        self.debug_panel = DebugConsoleWidget(center)
        self.terminal_panel.command_logged.connect(self.output_panel.log)
        self.debug_panel.expression_logged.connect(self.output_panel.log)

        self.bottom_panels = QStackedWidget(center)
        for panel in (
            self.terminal_panel,
            self.problems_panel,
            self.output_panel,
            self.debug_panel,
        ):
            self.bottom_panels.addWidget(panel)
        self.bottom_panels.setCurrentWidget(self.terminal_panel)
        self.bottom_panels.hide()
        self.file_viewer.errors_changed.connect(self.problems_panel.update_errors)

        center_splitter = QSplitter(Qt.Orientation.Vertical)
        center_splitter.addWidget(self.file_viewer)
        center_splitter.addWidget(self.bottom_panels)
        center_splitter.setStretchFactor(0, 0)
        center_splitter.setStretchFactor(1, 1)
        center_splitter.setCollapsible(0, False)
        center_splitter.setCollapsible(1, True)
        center_splitter.setSizes([800, 0])
        center_layout.addWidget(center_splitter, 1)
        self.center_splitter = center_splitter
        splitter.addWidget(center)

        self.chat_widget = CollaboratorChatWidget()
        self.chat_widget.setMinimumWidth(150)
        self.chat_widget.setMaximumWidth(420)
        splitter.addWidget(self.chat_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([250, 800, 250])
        self.file_tree.file_selected.connect(self._on_file_selected)
        main_layout.addWidget(splitter)

        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.save_shortcut.activated.connect(self._on_save_requested)

    def _start_watcher(self):
        try:
            signals = self.watcher_service.start_watching(self.folder_path)
            signals.directory_changed.connect(self.file_tree.refresh)
        except (OSError, RuntimeError) as error:
            logger.warning("Code editor: could not watch project folder: %s", error)

    def _on_file_selected(self, file_path: str):
        self.auto_save_timer.stop()
        if self.file_viewer.open_file(file_path):
            self.output_panel.log(f"File opened: {file_path}")
        elif self.auto_save_enabled and self._editor_dirty:
            self.auto_save_timer.start()

    def _on_save_requested(self):
        self.auto_save_timer.stop()
        if not self.file_viewer.save_current_file() and self._editor_dirty:
            self.auto_save_timer.start()

    def _on_tool_requested(self, tool_name: str):
        if tool_name == "TODOs":
            if self.todo_window is None:
                self.todo_window = TodoWindow(self)
            self.todo_window.show()
            self.todo_window.raise_()
            self.todo_window.activateWindow()
            return
        panel_indexes = {
            "Terminal": 0,
            "Problems": 1,
            "Output": 2,
            "Debug Console": 3,
        }
        panel_index = panel_indexes.get(tool_name)
        if panel_index is None:
            return
        if tool_name == "Terminal":
            self.terminal_panel.ensure_terminal()
            self.terminal_panel.focus_active_terminal()
        self.bottom_panels.setCurrentIndex(panel_index)
        self.bottom_panels.show()
        total_height = max(self.center_splitter.height(), 300)
        self.center_splitter.setSizes(
            [int(total_height * 0.67), int(total_height * 0.33)]
        )

    def _on_auto_save_toggled(self, enabled: bool):
        self.auto_save_enabled = enabled
        if enabled and self._editor_dirty:
            self.auto_save_timer.start()
        elif not enabled:
            self.auto_save_timer.stop()

    def _on_unsaved_changes_changed(self, is_dirty: bool):
        self._editor_dirty = is_dirty
        if is_dirty and self.auto_save_enabled:
            self.auto_save_timer.start()
        elif not is_dirty:
            self.auto_save_timer.stop()

    def _perform_auto_save(self):
        if (
            not self.auto_save_enabled
            or not self._editor_dirty
            or not self.file_viewer.current_file_path
        ):
            return
        if not self.file_viewer.save_current_file():
            self.auto_save_timer.start()

    def _on_close_editor(self):
        self.auto_save_timer.stop()
        if self.file_viewer.clear_view():
            logger.info("[CodeEditor] Editor cleared.")
        elif self.auto_save_enabled and self._editor_dirty:
            self.auto_save_timer.start()

    def _on_search_result_selected(self, file_path: str, line_number: int):
        full_path = str(Path(self.folder_path) / file_path)
        self._on_file_selected(full_path)
        if line_number > 0 and self.file_viewer.current_file_path == full_path:
            QTimer.singleShot(
                100,
                lambda target_line=line_number: self._go_to_problem_line(target_line),
            )

    def _hide_terminal(self):
        self.bottom_panels.hide()
        self.center_splitter.setSizes([max(self.center_splitter.height(), 1), 0])

    def _go_to_problem_line(self, line_number: int):
        block = self.file_viewer.code_editor.document().findBlockByNumber(
            line_number - 1
        )
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        self.file_viewer.code_editor.setTextCursor(cursor)
        self.file_viewer.code_editor.setFocus()
        self.file_viewer.code_editor.ensureCursorVisible()

    def _on_file_saved(self, success: bool, file_path: str):
        if success:
            logger.info("[CodeEditor] Saved: %s", file_path)
            self.output_panel.log(f"Saved: {file_path}")
        else:
            logger.error("[CodeEditor] Failed to save: %s", file_path)
            self.output_panel.log(f"Failed to save: {file_path}")

    def _on_checkpoint_requested(self):
        folder_name = Path(self.folder_path).name or self.folder_path
        answer = QMessageBox.question(
            self,
            "Save Checkpoint",
            "Save a numbered copy of this project in your Downloads folder?\n\n"
            f"Name: {folder_name}_checkpoint_<number>",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.output_panel.log("Creating project checkpoint...")
        result = self.file_service.create_checkpoint(self.folder_path)
        if result.get("success"):
            destination = result.get("path", "")
            self.output_panel.log(f"Checkpoint saved: {destination}")
            QMessageBox.information(
                self,
                "Checkpoint Saved",
                f"Project checkpoint saved to:\n{destination}",
            )
        else:
            error = result.get("error", "Unknown error")
            self.output_panel.log(f"Checkpoint failed: {error}")
            QMessageBox.warning(
                self, "Checkpoint Failed", f"Could not create checkpoint:\n{error}"
            )

    def _on_open_new_folder(self):
        new_folder = QFileDialog.getExistingDirectory(
            self, "Open Project Folder", str(Path(self.folder_path).parent)
        )
        if not new_folder:
            return
        if Path(new_folder).resolve() == Path(self.folder_path).resolve():
            return
        self.new_workspace = CodeEditorWorkspaceScreen(new_folder)
        self.new_workspace.show()

    def closeEvent(self, event):
        self.auto_save_timer.stop()
        if not self.file_viewer.confirm_save_changes("closing the editor"):
            event.ignore()
            if self.auto_save_enabled and self._editor_dirty:
                self.auto_save_timer.start()
            return
        self.watcher_service.stop_watching()
        super().closeEvent(event)
