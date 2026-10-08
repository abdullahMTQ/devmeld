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
        import re
        import unicodedata

        # 1. Normalize Unicode and remove invisible chars
        text = unicodedata.normalize("NFKD", text)
        text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00a0]", "", text)
        text_lower = text.lower()

        # 2. Apply leet-speak replacements
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
            text_lower = text_lower.replace(char, replacement)

        # 3. Check for banned words using smart regex with lookarounds
        # This prevents "class" from triggering "ass" while still catching "f u c k"
        for word in self.banwords:
            # Create pattern allowing optional non-alphanumeric chars between letters
            pattern = r"[^a-zA-Z0-9]*".join(
                re.escape(char) for char in word
            )
            # Lookarounds ensure it's a standalone word, not part of a larger word
            full_pattern = r"(?<![a-zA-Z0-9])" + pattern + r"(?![a-zA-Z0-9])"
            if re.search(full_pattern, text_lower):
                return True

        return False

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
