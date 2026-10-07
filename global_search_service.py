from global_search_manager import GlobalSearchManager


class GlobalSearchService:
    def __init__(self):
        self.manager = GlobalSearchManager()

    def search(self, root_path: str, query: str) -> list:
        return self.manager.search(root_path, query)
