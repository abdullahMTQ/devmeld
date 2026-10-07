import json

from impobj_utils import get_impobj_path


def get_hide_strangers_setting() -> bool:
    """Load the local preference for hiding chats without an outgoing message."""
    settings_file = get_impobj_path() / "settings.json"
    try:
        with settings_file.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return bool(data.get("hide_strangers", False)) if isinstance(data, dict) else False
    except (OSError, ValueError):
        return False


def save_hide_strangers_setting(value: bool):
    """Persist the local preference for hiding stranger conversations."""
    settings_dir = get_impobj_path()
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_file = settings_dir / "settings.json"
    try:
        with settings_file.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}

    data["hide_strangers"] = bool(value)
    with settings_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)