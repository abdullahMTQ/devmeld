from file_watcher_adapter import FileWatcherAdapter, WatcherSignals


class FileWatcherManager:
    def __init__(self):
        self.adapter = FileWatcherAdapter()
        self.signals = WatcherSignals()

    def start(self, root_path: str):
        self.adapter.start_watching(root_path, self.signals)
        return self.signals

    def stop(self):
        self.adapter.stop_watching()
