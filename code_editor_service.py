from code_editor_manager import CodeEditorManager


class CodeEditorService:
    def __init__(self):
        self.manager = CodeEditorManager()

    def get_quick_entries(self) -> list:
        return self.manager.get_validated_entries()

    def open_folder(self, folder_path: str) -> dict:
        return self.manager.open_folder(folder_path)

    def remove_quick_entry(self, folder_path: str) -> dict:
        return self.manager.remove_entry(folder_path)
