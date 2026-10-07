from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from terminal_instance_widget import TerminalInstanceWidget
from terminal_tab_widget import TerminalTabWidget


class TerminalWidget(QWidget):
    exit_requested = Signal()
    command_logged = Signal(str)
    command_finished = Signal(dict)

    def __init__(self, root_path: str, parent=None):
        super().__init__(parent)
        self.root_path = str(Path(root_path).resolve())
        self.terminals = []
        self.tab_widgets = []
        self.active_terminal_index = -1
        self._next_terminal_number = 1
        self._setup_ui()
        self._create_new_terminal()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setStyleSheet("background: #1e1e1e; border-top: 1px solid #333333;")

        self.terminal_stack = QStackedWidget(self)
        self.terminal_stack.setStyleSheet("background: #1e1e1e; border: none;")
        main_layout.addWidget(self.terminal_stack, 1)

        sidebar = QWidget(self)
        sidebar.setFixedWidth(150)
        sidebar.setStyleSheet(
            "background: #252526; border-left: 1px solid #333333;"
        )
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(5, 5, 5, 5)
        sidebar_layout.setSpacing(5)

        self.terminal_list = QWidget(sidebar)
        self.terminal_list_layout = QVBoxLayout(self.terminal_list)
        self.terminal_list_layout.setContentsMargins(0, 0, 0, 0)
        self.terminal_list_layout.setSpacing(2)

        terminal_scroll = QScrollArea(sidebar)
        terminal_scroll.setWidgetResizable(True)
        terminal_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        terminal_scroll.setWidget(self.terminal_list)
        sidebar_layout.addWidget(terminal_scroll, 1)

        self.add_terminal_btn = QPushButton("+", sidebar)
        self.add_terminal_btn.setFixedHeight(30)
        self.add_terminal_btn.setToolTip("Create a new terminal")
        self.add_terminal_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #ffffff; "
            "border: 1px solid #555555; border-radius: 4px; } "
            "QPushButton:hover { background: #333333; "
            "border-color: #00aeff; color: #00aeff; }"
        )
        self.add_terminal_btn.clicked.connect(self._create_new_terminal)
        sidebar_layout.addWidget(self.add_terminal_btn)
        main_layout.addWidget(sidebar)

    @property
    def command_input(self):
        self.ensure_terminal()
        terminal = self.active_terminal
        return terminal.command_input if terminal else None

    @property
    def active_terminal(self):
        if 0 <= self.active_terminal_index < len(self.terminals):
            return self.terminals[self.active_terminal_index]
        return None

    def ensure_terminal(self):
        if not self.terminals:
            self._create_new_terminal()

    def focus_active_terminal(self):
        self.ensure_terminal()
        if self.command_input:
            self.command_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _create_new_terminal(self):
        name = f"Terminal {self._next_terminal_number}"
        self._next_terminal_number += 1
        terminal = TerminalInstanceWidget(
            self.root_path, name, parent=self.terminal_stack
        )
        terminal.exit_requested.connect(self._close_terminal)
        terminal.command_logged.connect(self.command_logged.emit)
        terminal.command_finished.connect(self.command_finished.emit)
        self.terminal_stack.addWidget(terminal)
        self.terminals.append(terminal)

        tab = TerminalTabWidget(name, parent=self.terminal_list)
        tab.tab_clicked.connect(
            lambda terminal_instance=terminal: self._switch_terminal(
                terminal_instance
            )
        )
        tab.close_clicked.connect(
            lambda terminal_instance=terminal: self._close_terminal(
                terminal_instance
            )
        )
        self.tab_widgets.append(tab)
        self.terminal_list_layout.addWidget(tab)
        self._switch_terminal(terminal)

    def _switch_terminal(self, terminal_or_index):
        if isinstance(terminal_or_index, int):
            if not 0 <= terminal_or_index < len(self.terminals):
                return
            terminal = self.terminals[terminal_or_index]
        else:
            terminal = terminal_or_index
            if terminal not in self.terminals:
                return

        self.active_terminal_index = self.terminals.index(terminal)
        self.terminal_stack.setCurrentWidget(terminal)
        for index, tab in enumerate(self.tab_widgets):
            tab.set_active(index == self.active_terminal_index)

    def _close_terminal(self, terminal_or_index):
        if isinstance(terminal_or_index, int):
            if not 0 <= terminal_or_index < len(self.terminals):
                return
            terminal = self.terminals[terminal_or_index]
        else:
            terminal = terminal_or_index
        if terminal not in self.terminals:
            return
        index = self.terminals.index(terminal)
        tab = self.tab_widgets.pop(index)
        self.terminal_list_layout.removeWidget(tab)
        tab.deleteLater()
        self.terminal_stack.removeWidget(terminal)
        terminal.stop()
        terminal.deleteLater()
        self.terminals.pop(index)

        if not self.terminals:
            self.active_terminal_index = -1
            self.exit_requested.emit()
            return
        active_index = self.active_terminal_index
        if index < active_index:
            active_index -= 1
        elif index == active_index:
            active_index = min(index, len(self.terminals) - 1)
        self._switch_terminal(active_index)

    def closeEvent(self, event):
        for terminal in self.terminals:
            terminal.stop()
        super().closeEvent(event)
