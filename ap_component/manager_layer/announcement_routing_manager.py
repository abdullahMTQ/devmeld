# Domain: announcement, Purpose: routing, Layer: manager
from ap_component.adapter_layer.firebase_announcement_adapter import FirebaseAnnouncementAdapter

class AnnouncementRoutingManager:
    def __init__(self):
        self._adapter = FirebaseAnnouncementAdapter()
    
    def get_announcements(self) -> dict:
        result = self._adapter.fetch_announcements()
        if result["status"] == "error":
            return {"status": "error", "message": result["message"]}
        return result
