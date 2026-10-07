from impobj_utils import get_impobj_path, logger


class LocalFileAdapter:
    def read_banwords(self) -> list:
        try:
            banwords_file = get_impobj_path() / "banwords.txt"
            if not banwords_file.exists():
                banwords_file.write_text("", encoding="utf-8")
                return []
            with banwords_file.open("r", encoding="utf-8") as file:
                return [line.strip().lower() for line in file if line.strip()]
        except Exception as error:
            logger.error("Failed to read banwords.txt: %s", error)
            return []
