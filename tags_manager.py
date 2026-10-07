from tags_adapter import TagsAdapter


class TagsManager:
    def __init__(self):
        self.adapter = TagsAdapter()
        self.available_tags = self.adapter.load_tags()
        self.active_filters = []

    def get_all_tags(self) -> list:
        return self.available_tags.copy()

    def toggle_filter(self, tag_id: int):
        if tag_id in self.active_filters:
            self.active_filters.remove(tag_id)
        else:
            self.active_filters.append(tag_id)

    def get_active_filters(self) -> list:
        return self.active_filters.copy()

    def clear_filters(self):
        self.active_filters.clear()
