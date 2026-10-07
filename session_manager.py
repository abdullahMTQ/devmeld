import logging

import requests

from firebase_rest_adapter import FirebaseRestAdapter
from hardware_id_adapter import HardwareIdAdapter
from local_storage_adapter import LocalStorageAdapter

logger = logging.getLogger("devmeld")


class SessionManager:
    def __init__(self):
        self.storage_adapter = LocalStorageAdapter()
        self.firebase_adapter = FirebaseRestAdapter()
        self.hw_adapter = HardwareIdAdapter()

    def login(self, user_data: dict) -> bool:
        result = self.storage_adapter.save_session(user_data)
        if result:
            username = user_data.get("username", "")
            token = user_data.get("token", "")
            if username and token:
                status_result = self.firebase_adapter.set_online_status(
                    username, True, token
                )
                if not status_result.get("success"):
                    logger.warning(
                        "Failed to set online status for %s: %s",
                        username,
                        status_result.get("error", "RTDB request failed"),
                    )
        return result

    def logout(self) -> bool:
        session = self.storage_adapter.load_session()
        username = session.get("username")
        token = session.get("token")
        if username and token:
            status_result = self.firebase_adapter.set_online_status(
                username, False, token
            )
            if not status_result.get("success"):
                logger.warning(
                    "Failed to clear online status for %s: %s",
                    username,
                    status_result.get("error", "RTDB request failed"),
                )
        return self.storage_adapter.clear_session()

    def get_saved_session(self) -> dict:
        return self.storage_adapter.load_session()

    def check_auto_ban(self, uid: str, id_token: str) -> dict:
        profile = self.firebase_adapter.get_profile_firestore(uid, id_token)
        if not profile.get("success"):
            return {"banned": False, "error": "Failed to fetch profile"}
        report_count = int(profile.get("report_count", 0))
        return {"banned": report_count >= 50, "report_count": report_count}

    def execute_permanent_ban(self, uid: str, id_token: str) -> dict:
        logger.warning("EXECUTING PERMANENT BAN for UID: %s", uid)
        adapter = self.firebase_adapter

        username_to_delete = ""
        try:
            profile = adapter.get_profile_firestore(uid, id_token)
            if profile.get("success"):
                username_to_delete = profile.get("username", "")
        except Exception as error:
            logger.error("Profile fetch for ban error: %s", error)

        hw_id = None
        try:
            username_record = (
                adapter.get_username_rtdb(username_to_delete, id_token)
                if username_to_delete
                else None
            )
            hw_id = username_record.get("hw_id") if isinstance(username_record, dict) else None
            if not hw_id:
                # Legacy accounts may still have the old per-user HW ID node.
                legacy_url = f"{adapter.rtdb_url}/users/{uid}/hw_id.json?auth={id_token}"
                legacy_response = requests.get(legacy_url, timeout=10)
                hw_id = legacy_response.json() if legacy_response.status_code == 200 else None
            if hw_id:
                logger.info("Adding HW ID to blacklist: %s", hw_id)
                blacklist_url = f"{adapter.rtdb_url}/blacklist/{hw_id}.json?auth={id_token}"
                requests.put(blacklist_url, json=True, timeout=10)
        except Exception as error:
            logger.error("Blacklist HW ID error: %s", error)

        if username_to_delete:
            try:
                adapter.delete_username_rtdb(username_to_delete, id_token)
                logger.info("Deleted username %s from RTDB", username_to_delete)
            except Exception as error:
                logger.error("Username deletion error: %s", error)

        try:
            delete_rtdb_url = f"{adapter.rtdb_url}/users/{uid}.json?auth={id_token}"
            response = requests.delete(delete_rtdb_url, timeout=10)
            if response.status_code == 200:
                logger.info("Deleted user data from RTDB")
        except Exception as error:
            logger.error("RTDB user node deletion error: %s", error)

        try:
            adapter.delete_user_firestore(uid, id_token)
            logger.info("Deleted Firestore document")
        except Exception as error:
            logger.error("Firestore deletion error: %s", error)

        try:
            delete_auth_url = f"{adapter.auth_url}:delete?key={adapter.api_key}"
            response = requests.post(
                delete_auth_url, json={"idToken": id_token}, timeout=10
            )
            if response.status_code == 200:
                logger.info("Deleted Firebase Auth account")
            else:
                logger.error("Auth delete failed: %s", response.text)
        except Exception as error:
            logger.error("Auth deletion error: %s", error)

        self.logout()
        return {"success": True}
