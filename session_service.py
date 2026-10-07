import logging

from session_manager import SessionManager

logger = logging.getLogger("devmeld")


class SessionService:
    def __init__(self):
        self.manager = SessionManager()

    def restore_session(self) -> dict:
        saved_data = self.manager.get_saved_session()
        if not saved_data.get("uid") or not saved_data.get("token"):
            return {"success": False}

        # Refresh the ID token if we have a refresh token
        refresh_token = saved_data.get("refresh_token")
        if refresh_token:
            refresh_result = self.manager.firebase_adapter.refresh_id_token(refresh_token)
            if refresh_result.get("success"):
                saved_data["token"] = refresh_result["id_token"]
                if "refresh_token" in refresh_result:
                    saved_data["refresh_token"] = refresh_result["refresh_token"]
                # Save the updated tokens locally so we don't have to refresh again immediately
                self.manager.storage_adapter.save_session(saved_data)
            else:
                # If refresh fails, the session is truly dead
                return {"success": False}

        profile = self.manager.firebase_adapter.get_profile_firestore(
            saved_data["uid"], saved_data["token"]
        )
        if profile.get("success"):
            # FIX: Always update username and pfp_number from the fresh profile
            saved_data["username"] = profile.get(
                "username", saved_data.get("username", "@unknown")
            )
            saved_data["pfp_number"] = profile.get(
                "pfp_number", saved_data.get("pfp_number", 0)
            )
            # Save the updated session to prevent stale data on next launch
            self.manager.storage_adapter.save_session(saved_data)
            return {"success": True, "user_data": saved_data}
        return {"success": False}

    def login_user(self, user_data: dict) -> bool:
        return self.manager.login(user_data)

    def logout_user(self) -> bool:
        return self.manager.logout()

    def check_and_enforce_ban(self, uid: str, token: str) -> dict:
        try:
            result = self.manager.check_auto_ban(uid, token)
            result["report_count"] = int(result.get("report_count", 0) or 0)
            return result
        except (TypeError, ValueError, KeyError) as error:
            logger.error("Ban check error: %s", error)
            return {"banned": False, "error": str(error)}

    def ban_user_permanently(self, uid: str, token: str) -> dict:
        return self.manager.execute_permanent_ban(uid, token)
