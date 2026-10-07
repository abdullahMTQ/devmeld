from file_watcher_manager import FileWatcherManager


class FileWatcherService:
    def __init__(self):
        self.manager = FileWatcherManager()

    def start_watching(self, root_path: str):
        return self.manager.start(root_path)

    def stop_watching(self):
        self.manager.stop()
