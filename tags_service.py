from tags_manager import TagsManager


class TagsService:
    def __init__(self):
        self.manager = TagsManager()

    def get_tags(self) -> list:
        return self.manager.get_all_tags()

    def toggle_tag_filter(self, tag_id: int):
        self.manager.toggle_filter(tag_id)

    def get_active_tag_filters(self) -> list:
        return self.manager.get_active_filters()

    def search_tags(self, query: str) -> list:
        query_lower = query.lower().replace("#", "")
        return [
            tag for tag in self.manager.get_all_tags()
            if query_lower in tag["tag"].lower().replace("#", "")
        ]
