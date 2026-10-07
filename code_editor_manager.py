from code_editor_adapter import (
    add_quick_entry,
    cleanup_missing_entries,
    folder_exists,
    remove_quick_entry,
)
from impobj_utils import logger


class CodeEditorManager:
    def get_validated_entries(self) -> list:
        """Return quick entries, removing folders that no longer exist."""
        return cleanup_missing_entries()

    def open_folder(self, folder_path: str) -> dict:
        """Validate and save a folder before opening it."""
        if not folder_path or not folder_exists(folder_path):
            return {"success": False, "error": "Folder does not exist."}
        result = add_quick_entry(folder_path)
        if not result.get("success"):
            logger.error(
                "Code editor: failed to add quick entry: %s",
                result.get("error"),
            )
        return result

    def remove_entry(self, folder_path: str) -> dict:
        """Remove a quick entry."""
        return remove_quick_entry(folder_path)
