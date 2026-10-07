import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout
)
from PySide6.QtGui import QClipboard
from PySide6.QtCore import Qt

IMAGE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp',
    '.ico', '.svg', '.webp', '.tiff', '.tif'
}

SKIP_DIRS = {
    '__pycache__', '.git', 'venv', '.venv',
    'env', 'node_modules', '.idea', '.vscode'
}

SKIP_FILES = {'GUI.py'}


def scan_folder(base_path):
    files = []
    for root, dirs, filenames in os.walk(base_path):
        dirs[:] = sorted([d for d in dirs if d not in SKIP_DIRS])
        for fname in sorted(filenames):
            if fname in SKIP_FILES:
                continue
            if fname.endswith('.pyc'):
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, base_path)
            ext = os.path.splitext(fname)[1].lower()
            files.append((rel_path, full_path, ext))
    return files


def read_file_content(full_path, ext):
    if ext in IMAGE_EXTENSIONS:
        return "[IMAGE FILE]"
    try:
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception:
        return "[COULD NOT READ FILE]"


def build_chunks(files, num_chunks=4):
    entries = []
    for rel_path, full_path, ext in files:
        content = read_file_content(full_path, ext)
        entry = f"{rel_path}\n\n{content}"
        entries.append(entry)

    if not entries:
        return ["(no files found)"] * num_chunks

    chunk_size = max(1, len(entries) // num_chunks)
    chunks = []

    for i in range(num_chunks):
        start = i * chunk_size
        if i == num_chunks - 1:
            chunk_entries = entries[start:]
        else:
            chunk_entries = entries[start:start + chunk_size]

        if not chunk_entries:
            chunks.append("(empty)")
        else:
            chunk_text = "--------\n" + "\n_____\n".join(chunk_entries) + "\n_____"
            chunks.append(chunk_text)

    return chunks


class ChunkTab(QWidget):
    def __init__(self, chunk_text, file_count):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        top_bar = QHBoxLayout()
        info_label = QLabel(f"📄 {file_count} file(s) in this chunk")
        info_label.setStyleSheet("color: #888; font-size: 12px;")
        top_bar.addWidget(info_label)
        top_bar.addStretch()

        copy_btn = QPushButton("📋 Copy This Chunk")
        copy_btn.setFixedWidth(160)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: #2d7ff9;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background: #1a6fe8; }
            QPushButton:pressed { background: #0f5fd4; }
        """)
        copy_btn.clicked.connect(lambda: self.copy_chunk(chunk_text, copy_btn))
        top_bar.addWidget(copy_btn)
        layout.addLayout(top_bar)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(chunk_text)
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
                background: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.text_edit)

    def copy_chunk(self, text, btn):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        btn.setText("✅ Copied!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: btn.setText("📋 Copy This Chunk"))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DevMeld — Codebase Viewer")
        self.resize(950, 720)

        base_path = os.path.dirname(os.path.abspath(__file__))
        files = scan_folder(base_path)
        chunks = build_chunks(files)

        chunk_size = max(1, len(files) // 4)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 8px 18px;
                font-size: 13px;
            }
        """)

        for i, chunk in enumerate(chunks):
            start = i * chunk_size
            if i == 3:
                count = len(files) - start
            else:
                count = min(chunk_size, len(files) - start)
            count = max(0, count)

            tab = ChunkTab(chunk, count)
            tabs.addTab(tab, f"Chunk {i + 1}")

        self.setCentralWidget(tabs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    app.exec()