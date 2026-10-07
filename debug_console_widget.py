from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget


class DebugConsoleWidget(QWidget):
    expression_logged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.namespace = {"__name__": "__devmeld_debug_console__"}
        self._setup_ui()
        self._append_text("Devmeld Debug Console (Python)", "#00aeff")
        self._append_text("Enter Python expressions or statements.", "#858585")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        self.setStyleSheet("background: #1e1e1e; border: none;")

        self.output_area = QPlainTextEdit(self)
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet(
            "QPlainTextEdit { background: #1e1e1e; color: #cccccc; border: none; "
            "font-family: Consolas; font-size: 12px; }"
        )
        layout.addWidget(self.output_area, 1)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        self.prompt_label = QLineEdit(self)
        self.prompt_label.setReadOnly(True)
        self.prompt_label.setFixedWidth(48)
        self.prompt_label.setText(">>> ")
        self.prompt_label.setStyleSheet(
            "QLineEdit { background: #1e1e1e; color: #00aeff; border: none; "
            "font-family: Consolas; font-size: 12px; font-weight: bold; }"
        )
        input_layout.addWidget(self.prompt_label)

        self.command_input = QLineEdit(self)
        self.command_input.setPlaceholderText("Python expression or statement")
        self.command_input.setStyleSheet(
            "QLineEdit { background: #1e1e1e; color: #ffffff; border: none; "
            "font-family: Consolas; font-size: 12px; }"
        )
        self.command_input.returnPressed.connect(self._on_enter_pressed)
        input_layout.addWidget(self.command_input, 1)
        layout.addLayout(input_layout)

    def _append_text(self, text: str, color: str = "#cccccc"):
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        cursor.insertText(text + "\n", text_format)
        self.output_area.setTextCursor(cursor)
        scrollbar = self.output_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_enter_pressed(self):
        command = self.command_input.text().strip()
        if not command:
            return
        self._append_text(f">>> {command}", "#00aeff")
        self.command_input.clear()
        self.expression_logged.emit(f"[Debug Console] {command}")

        try:
            compiled = compile(command, "<debug-console>", "eval")
        except SyntaxError:
            try:
                compiled = compile(command, "<debug-console>", "exec")
                exec(compiled, self.namespace, self.namespace)
                self.expression_logged.emit("Executed successfully.")
            except Exception as error:
                error_text = f"Error: {error}"
                self._append_text(error_text, "#ff4444")
                self.expression_logged.emit(error_text)
        except Exception as error:
            error_text = f"Error: {error}"
            self._append_text(error_text, "#ff4444")
            self.expression_logged.emit(error_text)
        else:
            try:
                result = eval(compiled, self.namespace, self.namespace)
                if result is not None:
                    self._append_text(repr(result), "#4ec9b0")
                    self.expression_logged.emit(repr(result))
            except Exception as error:
                error_text = f"Error: {error}"
                self._append_text(error_text, "#ff4444")
                self.expression_logged.emit(error_text)
