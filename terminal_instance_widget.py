from pathlib import Path
import platform

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from terminal_adapter import TerminalAdapter


class _CommandWorker(QThread):
    result_ready = Signal(dict)

    def __init__(self, adapter, command: str, cwd: str, parent=None):
        super().__init__(parent)
        self.adapter = adapter
        self.command = command
        self.cwd = cwd

    def run(self):
        self.result_ready.emit(self.adapter.execute_command(self.command, self.cwd))


class TerminalInstanceWidget(QWidget):
    command_finished = Signal(dict)
    command_logged = Signal(str)
    exit_requested = Signal(object)

    def __init__(self, root_path: str, terminal_name: str, parent=None):
        super().__init__(parent)
        self.root_path = Path(root_path).resolve()
        self.current_dir = self.root_path
        self.terminal_name = terminal_name
        self.adapter = TerminalAdapter()
        self._worker = None
        self._setup_ui()
        self._print_welcome()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        self.setStyleSheet("background: #1e1e1e; border: none;")

        self.output_area = QPlainTextEdit(self)
        self.output_area.setReadOnly(True)
        self.output_area.setFont(QFont("Consolas", 10))
        self.output_area.setStyleSheet(
            "QPlainTextEdit { background: #1e1e1e; color: #cccccc; border: none; }"
        )
        layout.addWidget(self.output_area, 1)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        self.prompt_label = QLabel()
        self.prompt_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.prompt_label.setStyleSheet(
            "color: #00aeff; background: transparent; border: none;"
        )
        self._update_prompt()
        input_layout.addWidget(self.prompt_label)

        self.command_input = QLineEdit(self)
        self.command_input.setFont(QFont("Consolas", 10))
        self.command_input.setPlaceholderText("Enter command")
        self.command_input.setStyleSheet(
            "QLineEdit { background: #1e1e1e; color: #ffffff; border: none; }"
            "QLineEdit:focus { border: none; }"
        )
        self.command_input.returnPressed.connect(self._on_enter_pressed)
        input_layout.addWidget(self.command_input, 1)
        layout.addLayout(input_layout)

    def _prompt_text(self):
        if platform.system() == "Windows":
            return f"PS {self.current_dir}> "
        return f"{self.current_dir}$ "

    def _update_prompt(self):
        self.prompt_label.setText(self._prompt_text())

    def _print_welcome(self):
        self._append_text(f"Devmeld Terminal - {self.terminal_name}")
        self._append_text("Type 'help' for available commands.")

    def _append_text(self, text: str, color: str = "#cccccc"):
        if text:
            cursor = self.output_area.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            text_format = QTextCharFormat()
            text_format.setForeground(QColor(color))
            cursor.insertText(text.rstrip("\n") + "\n", text_format)
            self.output_area.setTextCursor(cursor)
        scrollbar = self.output_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_enter_pressed(self):
        command = self.command_input.text().strip()
        if not command or self._worker is not None:
            return
        self._append_text(f"{self._prompt_text()}{command}", "#00aeff")
        self.command_input.clear()
        self.command_logged.emit(f"[{self.terminal_name}] {command}")

        normalized = command.casefold()
        if normalized == "help":
            message = "Available commands: help, clear, exit, and shell commands."
            self._append_text(message)
            self.command_logged.emit(message)
            return
        if normalized in {"clear", "cls"}:
            self.output_area.clear()
            return
        if normalized == "cd" or normalized.startswith("cd "):
            self._change_directory(command[2:].strip())
            return
        if normalized == "exit":
            self.exit_requested.emit(self)
            return

        self.command_input.setEnabled(False)
        worker = _CommandWorker(
            self.adapter, command, str(self.current_dir), parent=self
        )
        self._worker = worker
        worker.result_ready.connect(self._on_command_finished)
        worker.finished.connect(
            lambda completed=worker: self._release_worker(completed)
        )
        worker.start()

    def _change_directory(self, target: str):
        target = target.strip()
        if len(target) >= 2 and target[0] == target[-1] and target[0] in "\"'":
            target = target[1:-1]
        if not target or target == "~":
            destination = Path.home()
        else:
            destination = Path(target).expanduser()
            if not destination.is_absolute():
                destination = self.current_dir / destination
        try:
            destination = destination.resolve(strict=True)
        except OSError:
            message = f"cd: no such directory: {target or Path.home()}"
            self._append_text(message, "#ff4444")
            self.command_logged.emit(f"ERROR: {message}")
            return
        if not destination.is_dir():
            message = f"cd: not a directory: {destination}"
            self._append_text(message, "#ff4444")
            self.command_logged.emit(f"ERROR: {message}")
            return
        self.current_dir = destination
        self._update_prompt()
        self.command_logged.emit(f"Changed directory to {destination}")

    def _on_command_finished(self, result: dict):
        self._worker = None
        output = result.get("output", "") or "Command completed."
        self._append_text(output, "#cccccc" if result.get("success") else "#ff4444")
        if output:
            self.command_logged.emit(
                output if result.get("success") else f"ERROR: {output}"
            )
        self.command_input.setEnabled(True)
        self.command_input.setFocus(Qt.FocusReason.OtherFocusReason)
        self.command_finished.emit(result)

    def _release_worker(self, worker):
        if self._worker is worker:
            self._worker = None
        worker.deleteLater()

    def stop(self):
        worker = self._worker
        if worker and worker.isRunning():
            worker.wait(TerminalAdapter.TIMEOUT_SECONDS * 1000 + 1000)
