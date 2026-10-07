from local_file_adapter import LocalFileAdapter


class ContentFilterManager:
    def __init__(self):
        self.adapter = LocalFileAdapter()
        self.banwords = self.adapter.read_banwords()

    def sanitize_username(self, username: str) -> str:
        clean_name = username.replace("@", "").strip()
        return f"@{clean_name}" if clean_name else ""

    def normalize_text(self, text: str) -> str:
        import unicodedata
        import re

        text = text.lower()
        text = unicodedata.normalize("NFKD", text)
        text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00a0]", "", text)

        leet_map = {
            "@": "a",
            "4": "a",
            "3": "e",
            "1": "i",
            "!": "i",
            "0": "o",
            "5": "s",
            "$": "s",
            "7": "t",
            "+": "t",
            "9": "g",
            "x": "k",
        }
        for char, replacement in leet_map.items():
            text = text.replace(char, replacement)

        text = re.sub(r"[\s\.\-\_]+", "", text)
        return text

    def contains_banned_word(self, text: str) -> bool:
        normalized = self.normalize_text(text)
        alternate_normalized = self.normalize_text(text.replace("@", "u"))
        return any(
            word in normalized or word in alternate_normalized
            for word in self.banwords
        )

    def censor_text(self, text: str) -> str:
        import re
        import unicodedata

        text = unicodedata.normalize("NFKD", text)
        text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00a0]", "", text)

        censored = text
        for word in self.banwords:
            pattern = r"[^a-zA-Z0-9]*".join(
                re.escape(char) for char in word
            )
            full_pattern = r"(?<![a-zA-Z0-9])" + pattern + r"(?![a-zA-Z0-9])"
            censored = re.sub(
                full_pattern, "******", censored, flags=re.IGNORECASE
            )

        return censored
