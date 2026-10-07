from content_filter_manager import ContentFilterManager


class ContentFilterService:
    def __init__(self):
        self.manager = ContentFilterManager()

    def validate_username(self, raw_username: str) -> dict:
        clean_username = self.manager.sanitize_username(raw_username)
        if not clean_username or len(clean_username) < 2:
            return {"valid": False, "error": "Username is too short."}
        if self.manager.contains_banned_word(clean_username):
            return {"valid": False, "error": "Please stay respectful."}
        return {"valid": True, "clean_username": clean_username}

    def validate_text(self, text: str) -> dict:
        if self.manager.contains_banned_word(text):
            return {"valid": False, "error": "Please stay respectful."}
        return {"valid": True}

    def censor_text(self, text: str) -> str:
        return self.manager.censor_text(text)
