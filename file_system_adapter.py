import platform
import shutil
import subprocess
from pathlib import Path

from impobj_utils import logger


class FileSystemAdapter:
    def scan_directory(self, root_path: str) -> list:
        """Return paths beneath a valid project root, relative to that root."""
        try:
            root = Path(root_path)
            if not root.is_dir():
                logger.error(
                    "FileSystemAdapter: %s is not a valid directory.", root_path
                )
                return []
            return [path.relative_to(root) for path in root.rglob("*")]
        except PermissionError as error:
            logger.warning(
                "FileSystemAdapter: Permission denied scanning %s: %s",
                root_path,
                error,
            )
        except (OSError, ValueError) as error:
            logger.error(
                "FileSystemAdapter: Could not scan %s: %s", root_path, error
            )
        return []

    def save_file_content(self, file_path: str, content: str) -> dict:
        """Write editor content to a UTF-8 file on disk."""
        try:
            path = Path(file_path)
            if not path.is_file():
                return {"success": False, "error": "File does not exist."}
            path.write_text(content, encoding="utf-8")
            return {"success": True}
        except (OSError, TypeError, ValueError) as error:
            logger.error("FileSystemAdapter: Save error: %s", error)
            return {"success": False, "error": str(error)}

    def create_file(self, parent_dir: str, name: str) -> dict:
        try:
            path = Path(parent_dir) / name
            path.touch(exist_ok=False)
            return {"success": True}
        except FileExistsError:
            return {"success": False, "error": "An item with this name already exists."}
        except (OSError, TypeError, ValueError) as error:
            logger.error("FileSystemAdapter: Create file error: %s", error)
            return {"success": False, "error": str(error)}

    def create_folder(self, parent_dir: str, name: str) -> dict:
        try:
            (Path(parent_dir) / name).mkdir()
            return {"success": True}
        except FileExistsError:
            return {"success": False, "error": "An item with this name already exists."}
        except (OSError, TypeError, ValueError) as error:
            logger.error("FileSystemAdapter: Create folder error: %s", error)
            return {"success": False, "error": str(error)}

    def rename_item(self, old_path: str, new_name: str) -> dict:
        try:
            old = Path(old_path)
            if not old.exists():
                return {"success": False, "error": "Item does not exist."}
            new = old.parent / new_name
            if new.exists():
                return {"success": False, "error": "An item with this name already exists."}
            old.rename(new)
            return {"success": True}
        except (OSError, TypeError, ValueError) as error:
            logger.error("FileSystemAdapter: Rename error: %s", error)
            return {"success": False, "error": str(error)}

    def delete_item(self, path: str) -> dict:
        try:
            item = Path(path)
            if item.is_symlink() or not item.is_dir():
                item.unlink()
            else:
                shutil.rmtree(item)
            return {"success": True}
        except (OSError, TypeError, ValueError) as error:
            logger.error("FileSystemAdapter: Delete error: %s", error)
            return {"success": False, "error": str(error)}

    def copy_item(self, source_path: str, dest_dir: str) -> dict:
        try:
            source = Path(source_path)
            destination_dir = Path(dest_dir)
            if not source.exists() or not destination_dir.is_dir():
                return {"success": False, "error": "Source or destination does not exist."}
            destination = destination_dir / source.name
            if source.is_dir() and destination.resolve().is_relative_to(source.resolve()):
                return {"success": False, "error": "Cannot copy a folder into itself."}
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
            return {"success": True}
        except (OSError, TypeError, ValueError) as error:
            logger.error("FileSystemAdapter: Copy error: %s", error)
            return {"success": False, "error": str(error)}

    def move_item(self, source_path: str, dest_dir: str) -> dict:
        try:
            source = Path(source_path)
            destination_dir = Path(dest_dir)
            if not source.exists() or not destination_dir.is_dir():
                return {"success": False, "error": "Source or destination does not exist."}
            destination = destination_dir / source.name
            if source.is_dir() and destination.resolve().is_relative_to(source.resolve()):
                return {"success": False, "error": "Cannot move a folder into itself."}
            if destination.exists():
                return {"success": False, "error": "An item with this name already exists."}
            shutil.move(str(source), str(destination))
            return {"success": True}
        except (OSError, TypeError, ValueError) as error:
            logger.error("FileSystemAdapter: Move error: %s", error)
            return {"success": False, "error": str(error)}

    def open_terminal(self, directory_path: str) -> dict:
        try:
            directory = Path(directory_path)
            if not directory.is_dir():
                return {"success": False, "error": "Directory does not exist."}
            system = platform.system()
            if system == "Windows":
                subprocess.Popen(["cmd.exe"], cwd=str(directory))
            elif system == "Darwin":
                subprocess.Popen(["open", "-a", "Terminal"], cwd=str(directory))
            else:
                subprocess.Popen(["x-terminal-emulator"], cwd=str(directory))
            return {"success": True}
        except (OSError, TypeError, ValueError) as error:
            logger.error("FileSystemAdapter: Open terminal error: %s", error)
            return {"success": False, "error": str(error)}

    def create_checkpoint(self, source_dir: str) -> dict:
        """Copy a project into a uniquely numbered folder in Downloads."""
        try:
            source = Path(source_dir).resolve(strict=True)
            if not source.is_dir():
                return {
                    "success": False,
                    "error": "Source is not a valid directory.",
                }

            downloads_dir = Path.home() / "Downloads"
            downloads_dir.mkdir(parents=True, exist_ok=True)
            resolved_downloads = downloads_dir.resolve()
            if resolved_downloads.is_relative_to(source):
                return {
                    "success": False,
                    "error": "Downloads is inside the source folder; cannot checkpoint recursively.",
                }

            base_name = f"{source.name}_checkpoint"
            counter = 1
            while True:
                destination = resolved_downloads / f"{base_name}_{counter}"
                if not destination.exists():
                    break
                counter += 1

            shutil.copytree(source, destination)
            logger.info("Checkpoint created at: %s", destination)
            return {"success": True, "path": str(destination)}
        except (OSError, TypeError, ValueError, shutil.Error) as error:
            logger.error("Checkpoint creation error: %s", error)
            return {"success": False, "error": str(error)}
