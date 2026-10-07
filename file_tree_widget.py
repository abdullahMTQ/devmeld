from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from file_system_service import FileSystemService


class FileTreeWidget(QWidget):
    file_selected = Signal(str)
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}

    def __init__(self, root_path: str, parent=None):
        super().__init__(parent)
        self.root_path = Path(root_path)
        self.service = FileSystemService()
        self.clipboard = {"path": None, "action": None}
        self._setup_ui()
        self._load_tree()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 10, 10, 5)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("search")
        self.search_input.setToolTip("Filter files and folders")
        self.search_input.setStyleSheet(
            "QLineEdit { background: #1a1a1a; color: #fff; border: 2px solid #fff; "
            "border-radius: 15px; padding: 5px 15px; font-size: 14px; } "
            "QLineEdit:focus { border: 2px solid #00aeff; }"
        )
        self.search_input.textChanged.connect(self._filter_tree)
        header_layout.addWidget(self.search_input, 1)

        self.clear_search_btn = QPushButton("✕")
        self.clear_search_btn.setFixedSize(30, 30)
        self.clear_search_btn.setToolTip("Clear search")
        self.clear_search_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #ff4444; border: none; "
            "font-size: 18px; font-weight: bold; } "
            "QPushButton:hover { color: #ff0000; }"
        )
        self.clear_search_btn.clicked.connect(self.search_input.clear)
        header_layout.addWidget(self.clear_search_btn)

        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(30, 30)
        self.add_btn.setToolTip("Create or import a project item")
        self.add_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #00ff88; border: none; "
            "font-size: 24px; font-weight: bold; padding: 0; } "
            "QPushButton:hover { color: #00dd77; }"
        )
        self.add_btn.clicked.connect(self._show_add_menu)
        header_layout.addWidget(self.add_btn)
        layout.addLayout(header_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(25)
        self.tree.setAnimated(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setFont(QFont("Segoe UI", 12))
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setStyleSheet(
            "QTreeWidget { background: #1a1a1a; color: #ffffff; border: none; }"
            "QTreeWidget::item { padding: 4px 0; }"
            "QTreeWidget::item:hover { background: #2a2d2e; }"
            "QTreeWidget::item:selected { background: #37373d; }"
        )
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

    def _load_tree(self):
        self.tree.clear()
        relative_paths = self.service.get_project_files(str(self.root_path))
        tree_data = {}
        for relative_path in relative_paths:
            branch = tree_data
            for part in relative_path.parts:
                branch = branch.setdefault(part, {})
        self._populate_branch(
            self.tree.invisibleRootItem(), tree_data, self.root_path
        )
        if self.search_input.text():
            self._filter_tree(self.search_input.text())

    def refresh(self):
        """Rescan the project directory, preserving the current search."""
        self._load_tree()

    def _populate_branch(self, parent_item, data, current_path):
        for name in sorted(data, key=str.casefold):
            item = QTreeWidgetItem(parent_item)
            item_path = current_path / name
            item.setData(0, Qt.ItemDataRole.UserRole, str(item_path))
            if item_path.is_dir():
                item.setText(0, f"📁 {name}")
                item.setFont(0, QFont("Segoe UI", 12, QFont.Weight.Bold))
                self._populate_branch(item, data[name], item_path)
            elif item_path.suffix.casefold() in self.IMAGE_EXTENSIONS:
                item.setText(0, f"🖼️ {name}")
            else:
                item.setText(0, f"📄 {name}")

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        item_path = item.data(0, Qt.ItemDataRole.UserRole)
        if item_path and Path(item_path).is_file():
            self.file_selected.emit(item_path)

    def _filter_tree(self, query: str):
        query = query.strip().casefold()
        root = self.tree.invisibleRootItem()
        for index in range(root.childCount()):
            self._filter_item(root.child(index), query)

    def _filter_item(self, item: QTreeWidgetItem, query: str) -> bool:
        item_name = Path(item.data(0, Qt.ItemDataRole.UserRole)).name.casefold()
        has_match = query in item_name
        for index in range(item.childCount()):
            has_match = self._filter_item(item.child(index), query) or has_match
        item.setHidden(not has_match)
        if query and has_match:
            item.setExpanded(True)
        return has_match

    def _show_add_menu(self):
        menu = QMenu(self)
        self._style_menu(menu)
        import_action = menu.addAction("Import File/Folder")
        menu.addSeparator()
        folder_action = menu.addAction("Create Folder")
        file_action = menu.addAction("Create File")
        action = menu.exec(
            self.add_btn.mapToGlobal(self.add_btn.rect().bottomRight())
        )
        if action == import_action:
            self._import_from_drive(self.root_path)
        elif action == folder_action:
            self._create_item("folder", self.root_path)
        elif action == file_action:
            self._create_item("file", self.root_path)

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if item:
            self.tree.setCurrentItem(item)
        menu = QMenu(self.tree)
        self._style_menu(menu)

        if item:
            item_path = Path(item.data(0, Qt.ItemDataRole.UserRole))
            if item_path.is_dir():
                new_file = menu.addAction("New File")
                new_folder = menu.addAction("New Folder")
                import_action = menu.addAction("Import File/Folder")
                menu.addSeparator()
                paste_action = None
                if self.clipboard.get("path"):
                    paste_action = menu.addAction("Paste")
                    menu.addSeparator()
                rename_action = menu.addAction("Rename")
                delete_action = menu.addAction("Delete")
                menu.addSeparator()
                terminal_action = menu.addAction("Open Terminal")
                action = menu.exec(self.tree.viewport().mapToGlobal(position))
                if action == new_file:
                    self._create_item("file", item_path)
                elif action == new_folder:
                    self._create_item("folder", item_path)
                elif action == import_action:
                    self._import_from_drive(item_path)
                elif paste_action and action == paste_action:
                    self._paste_item(item_path)
                elif action == rename_action:
                    self._rename_item(item_path)
                elif action == delete_action:
                    self._delete_item(item_path)
                elif action == terminal_action:
                    result = self.service.open_terminal(str(item_path))
                    self._show_operation_error("Open Terminal", result)
                return

            copy_action = menu.addAction("Copy")
            rename_action = menu.addAction("Rename")
            delete_action = menu.addAction("Delete")
            action = menu.exec(self.tree.viewport().mapToGlobal(position))
            if action == copy_action:
                self._copy_item(item_path)
            elif action == rename_action:
                self._rename_item(item_path)
            elif action == delete_action:
                self._delete_item(item_path)
            return

        import_action = menu.addAction("Import File/Folder")
        paste_action = None
        if self.clipboard.get("path"):
            paste_action = menu.addAction("Paste")
        action = menu.exec(self.tree.viewport().mapToGlobal(position))
        if action == import_action:
            self._import_from_drive(self.root_path)
        elif paste_action and action == paste_action:
            self._paste_item(self.root_path)

    @staticmethod
    def _style_menu(menu):
        menu.setStyleSheet(
            "QMenu { background: #252526; color: #ffffff; border: 1px solid #333; }"
            "QMenu::item { padding: 6px 20px; }"
            "QMenu::item:selected { background: #007acc; }"
        )

    def _create_item(self, item_type: str, target_dir):
        name, accepted = QInputDialog.getText(
            self, f"New {item_type.title()}", f"{item_type.title()} name:"
        )
        if not accepted:
            return
        result = (
            self.service.create_file(str(target_dir), name)
            if item_type == "file"
            else self.service.create_folder(str(target_dir), name)
        )
        if result.get("success"):
            self.refresh()
        else:
            self._show_operation_error(f"Create {item_type.title()}", result)

    def _import_from_drive(self, target_dir):
        menu = QMenu(self)
        self._style_menu(menu)
        file_action = menu.addAction("Choose File...")
        folder_action = menu.addAction("Choose Folder...")
        action = menu.exec(self.mapToGlobal(self.rect().center()))
        if action == file_action:
            source, _ = QFileDialog.getOpenFileName(
                self, "Choose File", str(self.root_path)
            )
        elif action == folder_action:
            source = QFileDialog.getExistingDirectory(
                self, "Choose Folder", str(self.root_path)
            )
        else:
            return
        if not source:
            return
        result = self.service.copy_item(source, str(target_dir))
        if result.get("success"):
            self.refresh()
        else:
            self._show_operation_error("Import", result)

    def _copy_item(self, item_path: str):
        self.clipboard = {"path": item_path, "action": "copy"}

    def _paste_item(self, target_dir):
        source = self.clipboard.get("path")
        if not source:
            return
        result = self.service.copy_item(source, str(target_dir))
        if result.get("success"):
            self.refresh()
        else:
            self._show_operation_error("Copy", result)

    def _rename_item(self, item_path: str):
        old_name = Path(item_path).name
        new_name, accepted = QInputDialog.getText(
            self, "Rename", "New name:", text=old_name
        )
        if not accepted or new_name == old_name:
            return
        result = self.service.rename_item(item_path, new_name)
        if result.get("success"):
            self.refresh()
        else:
            self._show_operation_error("Rename", result)

    def _delete_item(self, item_path: str):
        answer = QMessageBox.question(
            self,
            "Delete Item",
            f"Permanently delete '{Path(item_path).name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        result = self.service.delete_item(item_path)
        if result.get("success"):
            self.refresh()
        else:
            self._show_operation_error("Delete", result)

    def _show_operation_error(self, title: str, result: dict):
        if not result.get("success"):
            QMessageBox.warning(
                self,
                title,
                result.get("error", "The filesystem operation failed."),
            )
