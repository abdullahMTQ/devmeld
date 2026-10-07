import re

from file_system_adapter import FileSystemAdapter


class FileSystemManager:
    INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00]')

    def __init__(self):
        self.adapter = FileSystemAdapter()

    def get_project_files(self, root_path: str) -> list:
        if not root_path:
            return []
        return self.adapter.scan_directory(root_path)

    def save_file(self, file_path: str, content: str) -> dict:
        return self.adapter.save_file_content(file_path, content)

    def validate_name(self, name: str) -> dict:
        if not isinstance(name, str) or not name.strip():
            return {"valid": False, "error": "Name cannot be empty."}
        if name in {".", ".."} or self.INVALID_CHARS.search(name):
            return {"valid": False, "error": "Name contains invalid characters."}
        return {"valid": True}

    def create_file(self, parent_dir: str, name: str) -> dict:
        validation = self.validate_name(name)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}
        return self.adapter.create_file(parent_dir, name)

    def create_folder(self, parent_dir: str, name: str) -> dict:
        validation = self.validate_name(name)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}
        return self.adapter.create_folder(parent_dir, name)

    def rename_item(self, old_path: str, new_name: str) -> dict:
        validation = self.validate_name(new_name)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}
        return self.adapter.rename_item(old_path, new_name)

    def delete_item(self, path: str) -> dict:
        return self.adapter.delete_item(path)

    def copy_item(self, source_path: str, dest_dir: str) -> dict:
        return self.adapter.copy_item(source_path, dest_dir)

    def move_item(self, source_path: str, dest_dir: str) -> dict:
        return self.adapter.move_item(source_path, dest_dir)

    def open_terminal(self, directory_path: str) -> dict:
        return self.adapter.open_terminal(directory_path)

    def create_checkpoint(self, source_dir: str) -> dict:
        if not source_dir:
            return {"success": False, "error": "No project folder selected."}
        return self.adapter.create_checkpoint(source_dir)
