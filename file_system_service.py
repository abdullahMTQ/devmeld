from file_system_manager import FileSystemManager


class FileSystemService:
    def __init__(self):
        self.manager = FileSystemManager()

    def get_project_files(self, root_path: str) -> list:
        return self.manager.get_project_files(root_path)

    def save_file(self, file_path: str, content: str) -> dict:
        return self.manager.save_file(file_path, content)

    def create_file(self, parent_dir: str, name: str) -> dict:
        return self.manager.create_file(parent_dir, name)

    def create_folder(self, parent_dir: str, name: str) -> dict:
        return self.manager.create_folder(parent_dir, name)

    def rename_item(self, old_path: str, new_name: str) -> dict:
        return self.manager.rename_item(old_path, new_name)

    def delete_item(self, path: str) -> dict:
        return self.manager.delete_item(path)

    def copy_item(self, source_path: str, dest_dir: str) -> dict:
        return self.manager.copy_item(source_path, dest_dir)

    def move_item(self, source_path: str, dest_dir: str) -> dict:
        return self.manager.move_item(source_path, dest_dir)

    def open_terminal(self, directory_path: str) -> dict:
        return self.manager.open_terminal(directory_path)

    def create_checkpoint(self, source_dir: str) -> dict:
        return self.manager.create_checkpoint(source_dir)
