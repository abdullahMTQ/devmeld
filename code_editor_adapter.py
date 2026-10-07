import json
from pathlib import Path

from impobj_utils import get_impobj_path, logger

_QUICK_ENTRIES_FILE = "code_editor_quick_entries.json"


def _entries_path() -> Path:
    return get_impobj_path() / _QUICK_ENTRIES_FILE


def load_quick_entries() -> list:
    """Load quick entries from local storage."""
    path = _entries_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return [entry for entry in data if isinstance(entry, dict)] if isinstance(data, list) else []
    except (OSError, ValueError) as error:
        logger.error("Failed to load code editor quick entries: %s", error)
        return []


def save_quick_entries(entries: list) -> bool:
    """Persist quick entries to local storage."""
    path = _entries_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(entries, file, indent=2)
        return True
    except (OSError, TypeError, ValueError) as error:
        logger.error("Failed to save code editor quick entries: %s", error)
        return False


def folder_exists(folder_path: str) -> bool:
    """Check if a folder exists on disk."""
    try:
        return Path(folder_path).is_dir()
    except (OSError, TypeError, ValueError):
        return False


def get_folder_size(folder_path: str) -> float:
    """Calculate folder size in MB, skipping files that cannot be read."""
    total_bytes = 0
    try:
        for entry in Path(folder_path).rglob("*"):
            try:
                if entry.is_file():
                    total_bytes += entry.stat().st_size
            except OSError:
                continue
    except OSError:
        return 0.0
    return round(total_bytes / (1024 * 1024), 2)


def format_size(size_mb: float) -> str:
    """Format size for display in MB or GB."""
    if size_mb >= 1024:
        return f"{size_mb / 1024:.2f} GB"
    return f"{size_mb:.2f} MB"


def add_quick_entry(folder_path: str) -> dict:
    """Add a folder to quick entries and move it to the top."""
    path = Path(folder_path)
    if not path.is_dir():
        return {"success": False, "error": "Path is not a valid folder."}

    entries = load_quick_entries()
    entries = [entry for entry in entries if entry.get("path") != folder_path]
    entry = {
        "folder_name": path.name,
        "path": folder_path,
        "size_mb": get_folder_size(folder_path),
    }
    entries.insert(0, entry)
    if not save_quick_entries(entries):
        return {"success": False, "error": "Failed to save quick entries."}
    return {"success": True, "entry": entry}


def remove_quick_entry(folder_path: str) -> dict:
    """Remove a folder from quick entries."""
    entries = load_quick_entries()
    filtered = [entry for entry in entries if entry.get("path") != folder_path]
    if len(filtered) == len(entries):
        return {"success": False, "error": "Entry not found."}
    if not save_quick_entries(filtered):
        return {"success": False, "error": "Failed to save quick entries."}
    return {"success": True}


def cleanup_missing_entries() -> list:
    """Remove entries whose folders no longer exist."""
    entries = load_quick_entries()
    cleaned = [
        entry for entry in entries
        if folder_exists(entry.get("path", ""))
    ]
    if len(cleaned) != len(entries):
        save_quick_entries(cleaned)
        logger.info(
            "Code editor: cleaned %d missing folder entries.",
            len(entries) - len(cleaned),
        )
    return cleaned
