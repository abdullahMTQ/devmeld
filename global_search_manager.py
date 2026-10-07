from global_search_adapter import GlobalSearchAdapter


class GlobalSearchManager:
    def __init__(self):
        self.adapter = GlobalSearchAdapter()

    def search(self, root_path: str, query: str) -> list:
        return self.adapter.search_project(root_path, query)
