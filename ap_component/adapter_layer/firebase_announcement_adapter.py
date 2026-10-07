# Domain: firebase, Purpose: announcement_fetch, Layer: adapter
import requests
from ap_component.config_parser import parse_firebase_config_txt
from ap_component.adapter_layer.image_url_normalizer import normalize_image_url
import os

class FirebaseAnnouncementAdapter:
    def __init__(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "FIREBASE_CONFIG.txt")
        self.config = parse_firebase_config_txt(config_path)
        self.db_url = self.config.get("databaseURL", "")
        self.storage_bucket = self.config.get("storageBucket", "")

    def fetch_announcements(self) -> dict:
        try:
            target_url = f"{self.db_url}/dtap/announcements.json"
            response = requests.get(target_url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data is None:
                return {"status": "success", "data": []}
            
            announcements_list = []
            for key, value in data.items():
                value["id"] = key
                processed_images = []
                raw_images = value.get("images", [])
                if isinstance(raw_images, dict):
                    raw_images = list(raw_images.values())
                
                for img_url in raw_images:
                    try:
                        normalized_url = normalize_image_url(img_url, self.storage_bucket)
                        img_response = requests.get(normalized_url, timeout=5)
                        img_response.raise_for_status()
                        processed_images.append({"url": img_url, "bytes": img_response.content, "status": "success"})
                    except Exception:
                        processed_images.append({"url": img_url, "bytes": None, "status": "error"})
                
                value["processed_images"] = processed_images
                announcements_list.append(value)
            
            announcements_list.sort(key=lambda x: x.get("created_at", 0), reverse=True)
            return {"status": "success", "data": announcements_list}
        except Exception:
            return {"status": "error", "message": "Unable to load announcements."}
