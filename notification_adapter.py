from datetime import datetime, timezone

import requests

from firebase_rest_adapter import FirebaseRestAdapter
from impobj_utils import logger


class NotificationAdapter:
    def __init__(self):
        self.firebase = FirebaseRestAdapter()

    def add_notification(
        self,
        target_uid,
        thread_id,
        comment_id,
        commenter_uid,
        commenter_username,
        comment_snippet,
        id_token,
    ):
        url = (
            f"{self.firebase.firestore_url}/users/{target_uid}/notifications"
            f"?key={self.firebase.api_key}"
        )
        headers = {
            "Authorization": f"Bearer {id_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "fields": {
                "thread_id": {"stringValue": thread_id},
                "comment_id": {"stringValue": comment_id},
                "commenter_uid": {"stringValue": commenter_uid},
                "commenter_username": {"stringValue": commenter_username},
                "comment_snippet": {"stringValue": comment_snippet[:30]},
                "timestamp": {
                    "stringValue": datetime.now(timezone.utc).isoformat()
                },
                "is_read": {"booleanValue": False},
            }
        }
        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=10
            )
            if response.status_code not in (200, 201):
                logger.error("Add notification failed: %s", response.text)
                return {"success": False}
            return {"success": True}
        except requests.RequestException as error:
            logger.error("Add notification error: %s", error)
            return {"success": False}

    def get_unread_notifications(self, uid, id_token):
        url = f"{self.firebase.firestore_url}/users/{uid}/notifications"
        headers = {"Authorization": f"Bearer {id_token}"}
        params = {
            "key": self.firebase.api_key,
            "orderBy": "timestamp desc",
            "pageSize": "20",
        }
        try:
            response = requests.get(
                url, params=params, headers=headers, timeout=10
            )
            if response.status_code != 200:
                return []
            results = []
            for document in response.json().get("documents", []):
                fields = document.get("fields", {})
                is_read = fields.get("is_read", {}).get("booleanValue", False)
                if is_read:
                    continue
                results.append(
                    {
                        "id": document.get("name", "").rsplit("/", 1)[-1],
                        "thread_id": fields.get("thread_id", {}).get("stringValue", ""),
                        "comment_id": fields.get("comment_id", {}).get("stringValue", ""),
                        "commenter_username": fields.get("commenter_username", {}).get("stringValue", "@unknown"),
                        "comment_snippet": fields.get("comment_snippet", {}).get("stringValue", ""),
                        "is_read": is_read,
                    }
                )
            return results
        except requests.RequestException as error:
            logger.error("Get notifications error: %s", error)
            return []

    def get_unread_count(self, uid, id_token):
        url = f"{self.firebase.firestore_url}/users/{uid}/notifications"
        headers = {"Authorization": f"Bearer {id_token}"}
        params = {
            "key": self.firebase.api_key,
            "orderBy": "timestamp desc",
            "pageSize": "10",
        }
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                documents = response.json().get("documents", [])
                return sum(
                    not document.get("fields", {})
                    .get("is_read", {})
                    .get("booleanValue", True)
                    for document in documents
                )
            return 0
        except requests.RequestException as error:
            logger.error("Get unread count error: %s", error)
            return 0

    def mark_notification_read(self, uid, notification_id, id_token):
        url = (
            f"{self.firebase.firestore_url}/users/{uid}/notifications/"
            f"{notification_id}?key={self.firebase.api_key}"
            "&updateMask.fieldPaths=is_read"
        )
        headers = {
            "Authorization": f"Bearer {id_token}",
            "Content-Type": "application/json",
        }
        payload = {"fields": {"is_read": {"booleanValue": True}}}
        try:
            response = requests.patch(
                url, json=payload, headers=headers, timeout=5
            )
            if response.status_code not in (200, 204):
                logger.error("Mark read failed: %s", response.text)
                return False
            return True
        except requests.RequestException as error:
            logger.error("Mark read error: %s", error)
            return False

    def cleanup_read_notifications(self, user_uid: str, id_token: str) -> dict:
        """Fetch notifications and delete documents that have been read."""
        url = f"{self.firebase.firestore_url}/users/{user_uid}/notifications"
        headers = {"Authorization": f"Bearer {id_token}"}
        params = {"key": self.firebase.api_key, "pageSize": "50"}
        try:
            response = requests.get(
                url, params=params, headers=headers, timeout=10
            )
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": "Failed to fetch notifications",
                }

            deleted_count = 0
            for document in response.json().get("documents", []):
                fields = document.get("fields", {})
                is_read = fields.get("is_read", {}).get("booleanValue", False)
                if not is_read:
                    continue
                document_id = document.get("name", "").rsplit("/", 1)[-1]
                if not document_id:
                    continue
                delete_url = f"{url}/{document_id}"
                delete_response = requests.delete(
                    delete_url,
                    params={"key": self.firebase.api_key},
                    headers=headers,
                    timeout=5,
                )
                if delete_response.status_code in (200, 204):
                    deleted_count += 1
            return {"success": True, "deleted": deleted_count}
        except Exception as error:
            logger.error("Cleanup notifications error: %s", error)
            return {"success": False, "error": str(error)}

    def mark_all_read(self, uid, id_token):
        return None
