"""Authentication orchestration with rollback for partial sign-ups."""

import logging

from content_filter_service import ContentFilterService
from firebase_rest_adapter import FirebaseRestAdapter
from hardware_id_adapter import HardwareIdAdapter
from hardware_id_service import HardwareIdService

logger = logging.getLogger("devmeld")


class AuthManager:
    def __init__(self):
        self.adapter = FirebaseRestAdapter()
        self.filter_service = ContentFilterService()

    def execute_sign_up(self, email: str, password: str, raw_username: str) -> dict:
        username_check = self.filter_service.validate_username(raw_username)
        if not username_check["valid"]:
            return {"success": False, "error": username_check["error"], "step": "validation"}

        clean_username = username_check["clean_username"]
        ban_check = HardwareIdService().check_ban_status()
        if ban_check.get("banned"):
            return {
                "success": False,
                "error": "This device is permanently banned from devmeld.",
                "step": "hardware_check",
            }
        availability = self.adapter.check_username_rtdb(clean_username)
        if "error" in availability:
            return {"success": False, "error": "Network error checking username.", "step": "username_check"}
        if availability["exists"]:
            return {"success": False, "error": "Username is already taken.", "step": "username_check"}

        auth_result = self.adapter.sign_up_with_email(email, password)
        if not auth_result["success"]:
            error = auth_result.get("error", "Unknown error")
            if error == "EMAIL_EXISTS":
                error = "Email is already registered."
            return {"success": False, "error": error, "step": "auth_creation"}

        uid = auth_result["data"]["localId"]
        id_token = auth_result["data"]["idToken"]
        refresh_token = auth_result["data"]["refreshToken"]
        hw_id = HardwareIdAdapter().get_machine_id()
        claim_result = self.adapter.claim_username_rtdb(
            clean_username, uid, hw_id, id_token
        )
        if not claim_result["success"]:
            logger.warning("Username claim failed for %s, rolling back auth account", uid)
            self.adapter.delete_auth_user(uid, id_token)
            return {"success": False, "error": "Failed to claim username. Please try again.", "step": "username_claim"}

        pfp_number = 0
        firestore_result = self.adapter.create_user_firestore(
            uid, clean_username, pfp_number, id_token
        )
        if not firestore_result["success"]:
            logger.warning("Firestore creation failed for %s, rolling back everything", uid)
            self.adapter.delete_username_rtdb(clean_username, id_token)
            self.adapter.delete_auth_user(uid, id_token)
            return {"success": False, "error": "Failed to create profile. Please try again.", "step": "firestore_creation"}

        return {
            "success": True,
            "uid": uid,
            "username": clean_username,
            "token": id_token,
            "refresh_token": refresh_token,
            "pfp_number": pfp_number,
        }

    def execute_sign_in(self, email: str, password: str) -> dict:
        auth_result = self.adapter.sign_in_with_email(email, password)
        if not auth_result["success"]:
            error = auth_result.get("error", "Unknown error")
            if error in {"INVALID_PASSWORD", "USER_NOT_FOUND"}:
                error = "Invalid email or password."
            return {"success": False, "error": error}

        uid = auth_result["data"]["localId"]
        id_token = auth_result["data"]["idToken"]
        refresh_token = auth_result["data"]["refreshToken"]
        user_data = self.adapter.get_user_firestore(uid, id_token)
        if not user_data["success"]:
            logger.error("Failed to fetch user data for %s", uid)
            return {"success": False, "error": "Failed to load profile data."}

        return {
            "success": True,
            "uid": uid,
            "username": user_data["username"],
            "pfp_number": user_data.get("pfp_number", 0),
            "token": id_token,
            "refresh_token": refresh_token,
        }

    def delete_account(self, uid: str, id_token: str, username: str) -> dict:
        if not self.adapter.delete_user_firestore(uid, id_token):
            logger.error("Failed to delete Firestore doc for %s", uid)
        if not self.adapter.delete_username_rtdb(username, id_token):
            logger.error("Failed to delete RTDB username for %s", username)
        if not self.adapter.delete_auth_user(uid, id_token):
            logger.error("Failed to delete auth account for %s", uid)
            return {"success": False, "error": "Failed to delete account completely."}
        return {"success": True}
