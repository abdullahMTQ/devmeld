# Domain: announcement, Purpose: fetch, Layer: service
from PySide6.QtCore import QObject, Signal
from ap_component.manager_layer.announcement_routing_manager import AnnouncementRoutingManager

# ==========================================
# THE OUTPUT CABLES (AP dictates the output)
# ==========================================
class AnnouncementServiceSignals(QObject):
    announcements_ready = Signal(list)   # Emits list of announcement dicts
    announcements_failed = Signal(str)   # Emits error message string

class AnnouncementFetchService:
    def __init__(self):
        self._manager = AnnouncementRoutingManager()
        self.signals = AnnouncementServiceSignals()
    
    # ==========================================
    # THE INPUT CABLE (AP dictates the input)
    # ==========================================
    def request_announcements(self):
        """The single entry point for the Host App to trigger a fetch."""
        result = self._manager.get_announcements()
        if result["status"] == "success":
            self.signals.announcements_ready.emit(result["data"])
        else:
            self.signals.announcements_failed.emit(result["message"])
