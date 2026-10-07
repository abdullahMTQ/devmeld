import json

from impobj_utils import get_impobj_path, logger


class LocalStorageAdapter:
    def __init__(self):
        self.session_file = get_impobj_path() / "user_session.json"

    def save_session(self, user_data: dict) -> bool:
        try:
            with self.session_file.open("w", encoding="utf-8") as file:
                json.dump(user_data, file, indent=2)
            logger.info("Session saved successfully")
            return True
        except (OSError, TypeError, ValueError) as error:
            logger.error("Failed to save session: %s", error)
            return False

    def load_session(self) -> dict:
        try:
            if self.session_file.exists():
                with self.session_file.open("r", encoding="utf-8") as file:
                    data = json.load(file)
                logger.info("Session loaded successfully")
                return data if isinstance(data, dict) else {}
            return {}
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            logger.error("Failed to load session: %s", error)
            return {}

    def clear_session(self) -> bool:
        try:
            if self.session_file.exists():
                self.session_file.unlink()
            logger.info("Session cleared")
            return True
        except OSError as error:
            logger.error("Failed to clear session: %s", error)
            return False
