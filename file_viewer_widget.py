from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPixmap,
    QTextCursor,
    QTextFormat,
    QTextOption,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from syntax_checker_adapter import SyntaxCheckerAdapter
from syntax_highlighter import CodeHighlighter


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.paint_line_number_area(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.setFont(QFont("Consolas", 11))
        self.setStyleSheet(
            "QPlainTextEdit { background: #1e1e1e; color: #d4d4d4; "
            "border: none; padding: 5px; selection-background-color: #264f78; }"
        )
        self.highlighter = CodeHighlighter(self.document())
        self.error_selections = []
        self.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.highlight_current_line()

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        content_rect = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(
                content_rect.left(),
                content_rect.top(),
                self.line_number_area_width(),
                content_rect.height(),
            )
        )

    def paint_line_number_area(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#252526"))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#858585"))
                painter.drawText(
                    0,
                    int(top),
                    self.line_number_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            if block.isValid():
                bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def highlight_current_line(self):
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#252526"))
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection, *self.error_selections])

    def show_error_lines(self, line_numbers: list):
        """Highlight multiple one-based source lines without moving the cursor."""
        self.clear_error_highlights()
        for line_number in line_numbers:
            if line_number < 1:
                continue
            block = self.document().findBlockByNumber(line_number - 1)
            if not block.isValid():
                continue
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor(255, 0, 0, 60))
            selection.format.setProperty(
                QTextFormat.Property.FullWidthSelection, True
            )
            selection.cursor = QTextCursor(block)
            self.error_selections.append(selection)
        self.highlight_current_line()

    def clear_error_highlights(self):
        self.error_selections.clear()
        self.highlight_current_line()


class FileViewerWidget(QWidget):
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}
    MAX_TEXT_BYTES = 2 * 1024 * 1024
    file_saved = Signal(bool, str)
    errors_changed = Signal(list)
    unsaved_changes = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image = None
        self.current_file_path = None
        self.auto_save_enabled = True
        self.has_unsaved_changes = False
        self._saved_content = None
        self.syntax_checker = SyntaxCheckerAdapter()
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.setInterval(1000)
        self._auto_save_timer.timeout.connect(self._perform_auto_save)
        self._syntax_error_line = None
        self._setup_ui()

    def _setup_ui(self):
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background: #1e1e1e; border: none;")

        self.error_dot = QLabel("●")
        self.error_dot.setToolTip("Python syntax error detected")
        self.error_dot.setStyleSheet(
            "QLabel { color: #ff4444; font-size: 18px; background: transparent; }"
        )
        self.error_dot.hide()
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 2, 10, 2)
        self.unsaved_label = QLabel("")
        self.unsaved_label.setStyleSheet(
            "QLabel { color: #ffd700; font-size: 12px; "
            "background: transparent; border: none; }"
        )
        header_layout.addWidget(self.unsaved_label)
        header_layout.addStretch()
        header_layout.addWidget(self.error_dot)
        self.content_layout.addWidget(header)

        self.placeholder = QLabel("Select a file to view its contents")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet(
            "color: #888888; font-size: 15px; background: transparent;"
        )
        self.content_layout.addWidget(self.placeholder)

        self.code_editor = CodeEditor()
        self.text_editor = self.code_editor
        self.code_editor.textChanged.connect(self._on_text_changed)
        self.text_editor.hide()
        self.content_layout.addWidget(self.text_editor)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background: transparent; border: none;")
        self.image_label.hide()
        self.content_layout.addWidget(self.image_label)

    def open_file(self, file_path: str):
        if file_path == self.current_file_path:
            return True
        if not self.confirm_save_changes("opening another file"):
            return False
        self._auto_save_timer.stop()
        self.current_file_path = file_path
        self.text_editor.hide()
        self.image_label.hide()
        self.placeholder.hide()
        self.current_image = None
        self._syntax_error_line = None
        self.error_dot.hide()
        self.code_editor.clear_error_highlights()

        path = Path(file_path)
        if path.suffix.casefold() in self.IMAGE_EXTENSIONS:
            self._show_image(path)
        else:
            self._show_text(path)
        self._check_syntax()
        self._saved_content = (
            self.code_editor.toPlainText()
            if not self.code_editor.isHidden()
            else None
        )
        self._set_unsaved_changes(False)
        return True

    def save_current_file(self):
        if not self.current_file_path or self.code_editor.isHidden():
            return False
        self._auto_save_timer.stop()
        from file_system_service import FileSystemService

        content = self.code_editor.toPlainText()
        result = FileSystemService().save_file(self.current_file_path, content)
        success = bool(result.get("success"))
        if success:
            self._saved_content = content
            self._set_unsaved_changes(False)
        self.file_saved.emit(success, self.current_file_path)
        return success

    def set_auto_save_enabled(self, enabled: bool):
        self.auto_save_enabled = enabled
        if not enabled:
            self._auto_save_timer.stop()

    def clear_view(self):
        """Clear the current file from the editor."""
        if not self.confirm_save_changes("closing the current file"):
            return False
        self.current_file_path = None
        self._auto_save_timer.stop()
        self._saved_content = None
        self._set_unsaved_changes(False)
        self.code_editor.clear()
        self.code_editor.hide()
        self.image_label.hide()
        self.placeholder.setText("Select a file to view or edit")
        self.placeholder.show()
        self.error_dot.hide()
        self.code_editor.clear_error_highlights()
        self.current_image = None
        self._syntax_error_line = None
        self.errors_changed.emit([])
        return True

    def _on_text_changed(self):
        if not self.current_file_path or self.code_editor.isHidden():
            return
        is_dirty = self.code_editor.toPlainText() != self._saved_content
        self._set_unsaved_changes(is_dirty)
        if self.auto_save_enabled and is_dirty:
            self._auto_save_timer.start()
        elif not is_dirty:
            self._auto_save_timer.stop()
        self._check_syntax()

    def _perform_auto_save(self):
        if not self.auto_save_enabled or not self.has_unsaved_changes:
            return False
        return self.save_current_file()

    def _set_unsaved_changes(self, has_changes: bool):
        if self.has_unsaved_changes == has_changes:
            return
        self.has_unsaved_changes = has_changes
        self.unsaved_label.setText("● unsaved" if has_changes else "")
        self.unsaved_changes.emit(has_changes)

    def confirm_save_changes(self, action: str) -> bool:
        if not self.has_unsaved_changes or not self.current_file_path:
            return True

        answer = QMessageBox.question(
            self,
            "Unsaved Changes",
            f"Save changes to '{Path(self.current_file_path).name}' before "
            f"{action}?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return self.save_current_file()
        return True

    def _check_syntax(self):
        """Find Python syntax and unfinished-structure errors."""
        if not self.current_file_path or Path(self.current_file_path).suffix.casefold() != ".py":
            self._syntax_error_line = None
            self.error_dot.hide()
            self.code_editor.clear_error_highlights()
            self.errors_changed.emit([])
            return

        errors = self.syntax_checker.check_syntax(
            self.code_editor.toPlainText()
        )
        if errors:
            error_lines = [error["line"] for error in errors]
            self._syntax_error_line = error_lines[0]
            self.error_dot.show()
            self.code_editor.show_error_lines(error_lines)
        else:
            self._syntax_error_line = None
            self.error_dot.hide()
            self.code_editor.clear_error_highlights()
        self.errors_changed.emit(errors)

    def _show_text(self, path: Path):
        try:
            with path.open("rb") as file:
                content = file.read(self.MAX_TEXT_BYTES + 1)
            if b"\x00" in content[:8192]:
                self._show_message("Binary file preview is not available")
                return
            truncated = len(content) > self.MAX_TEXT_BYTES
            text = content[:self.MAX_TEXT_BYTES].decode("utf-8", errors="replace")
            if truncated:
                text += "\n\n[Preview truncated at 2 MB]"
            self.text_editor.setPlainText(text)
            self.text_editor.show()
        except OSError as error:
            self._show_message(f"Could not read file: {error}")

    def _show_image(self, path: Path):
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._show_message("Could not load image")
            return
        self.current_image = pixmap
        self._update_image_preview()

    def _show_message(self, text: str):
        self.placeholder.setText(text)
        self.placeholder.show()

    def _update_image_preview(self):
        if self.current_image is None:
            return
        scaled = self.current_image.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)
        self.image_label.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_image is not None:
            self._update_image_preview()
