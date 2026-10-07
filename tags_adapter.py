from impobj_utils import get_impobj_path, logger


class TagsAdapter:
    def __init__(self):
        self.tags_file = get_impobj_path() / "tags.txt"

    def load_tags(self) -> list:
        try:
            if not self.tags_file.exists():
                logger.warning("tags.txt not found, creating empty file")
                self.tags_file.write_text("", encoding="utf-8")
                return []
            tags = []
            with self.tags_file.open("r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line or "/" not in line:
                        continue
                    tag, raw_id = line.split("/", 1)
                    try:
                        tags.append({"tag": tag.strip(), "id": int(raw_id.strip())})
                    except ValueError:
                        logger.warning("Ignoring malformed tag: %s", line)
            return tags
        except (OSError, ValueError) as error:
            logger.error("Failed to load tags: %s", error)
            return []
