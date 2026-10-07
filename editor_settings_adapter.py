import json

from impobj_utils import get_impobj_path, logger

SETTINGS_FILE = "editor_settings.json"


def load_editor_settings() -> dict:
    path = get_impobj_path() / SETTINGS_FILE
    if not path.exists():
        return {"auto_save": True}
    try:
        with path.open("r", encoding="utf-8") as file:
            settings = json.load(file)
        if isinstance(settings, dict):
            settings.setdefault("auto_save", True)
            return settings
        logger.error("Editor settings must contain a JSON object: %s", path)
    except (OSError, ValueError) as error:
        logger.error("Failed to load editor settings: %s", error)
    return {"auto_save": True}


def save_editor_settings(settings: dict) -> bool:
    path = get_impobj_path() / SETTINGS_FILE
    try:
        with path.open("w", encoding="utf-8") as file:
            json.dump(settings, file, indent=2)
        return True
    except (OSError, TypeError, ValueError) as error:
        logger.error("Failed to save editor settings: %s", error)
        return False
