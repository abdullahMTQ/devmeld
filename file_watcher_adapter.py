import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer


class WatcherSignals(QObject):
    directory_changed = Signal()


class ProjectEventHandler(FileSystemEventHandler):
    _IGNORED_EVENTS = {"opened", "modified", "closed", "closed_no_write"}
    _STRUCTURAL_EVENTS = {"created", "deleted", "moved"}

    def __init__(self, signals: WatcherSignals):
        super().__init__()
        self.signals = signals
        self._debounce_timer = None
        self._timer_lock = threading.Lock()

    def on_any_event(self, event):
        if (
            isinstance(event, FileModifiedEvent)
            or event.event_type in self._IGNORED_EVENTS
            or event.event_type not in self._STRUCTURAL_EVENTS
        ):
            return
        with self._timer_lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(
                0.5, self.signals.directory_changed.emit
            )
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def stop(self):
        with self._timer_lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
                self._debounce_timer = None


class FileWatcherAdapter:
    def __init__(self):
        self.observer = None
        self.event_handler = None

    def start_watching(self, root_path: str, signals: WatcherSignals):
        self.stop_watching()
        root = Path(root_path)
        if not root.is_dir():
            raise NotADirectoryError(f"Project directory does not exist: {root_path}")

        self.event_handler = ProjectEventHandler(signals)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, str(root), recursive=True)
        self.observer.start()

    def stop_watching(self):
        if self.event_handler:
            self.event_handler.stop()
            self.event_handler = None
        if self.observer:
            if self.observer.is_alive():
                self.observer.stop()
                self.observer.join(timeout=5)
            self.observer = None
