import requests

from impobj_utils import logger


class FirebaseRestAdapter:
    def __init__(self):
        self.api_key = "AIzaSyAxYhSW1prz8f4B2gcGKxO1Cywgyoku0fM"
        self.rtdb_url = "https://devmeld-default-rtdb.firebaseio.com"
        self.firestore_url = "https://firestore.googleapis.com/v1/projects/devmeld/databases/(default)/documents"
        self.auth_url = "https://identitytoolkit.googleapis.com/v1/accounts"

    def sign_up_with_email(self, email: str, password: str) -> dict:
        url = f"{self.auth_url}:signUp?key={self.api_key}"
        try:
            response = requests.post(
                url,
                json={"email": email, "password": password, "returnSecureToken": True},
                timeout=10,
            )
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            return {
                "success": False,
                "error": response.json().get("error", {}).get("message", "Unknown error"),
            }
        except requests.exceptions.RequestException as error:
            logger.error("Network error during sign up: %s", error)
            return {"success": False, "error": "Network connection lost. Please try again."}

    def check_username_rtdb(self, username: str) -> dict:
        url = f"{self.rtdb_url}/usernames/{username}.json"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return {"exists": response.json() is not None}
            return {"exists": False}
        except requests.exceptions.RequestException as error:
            logger.error("Network error checking username: %s", error)
            return {"exists": False, "error": "Network error"}

    def claim_username_rtdb(self, username: str, uid: str, hw_id: str, id_token: str) -> dict:
        if not hw_id:
            return {"success": False, "error": "Device ID missing."}
        return self.save_username_to_rtdb(username, uid, hw_id, id_token)

    def save_username_to_rtdb(self, username: str, uid: str, hw_id: str, id_token: str) -> dict:
        url = f"{self.rtdb_url}/usernames/{username}.json?auth={id_token}"
        try:
            headers = {"Authorization": f"Bearer {id_token}"}
            payload = {"uid": uid, "hw_id": hw_id}
            response = requests.put(url, json=payload, headers=headers, timeout=10)
            return {"success": response.status_code == 200}
        except requests.exceptions.RequestException as error:
            logger.error("Network error claiming username: %s", error)
            return {"success": False}

    def get_username_rtdb(self, username: str, id_token: str):
        from urllib.parse import quote

        safe_username = quote(username, safe="")
        url = f"{self.rtdb_url}/usernames/{safe_username}.json?auth={id_token}"
        try:
            response = requests.get(url, timeout=10)
            return response.json() if response.status_code == 200 else None
        except requests.exceptions.RequestException as error:
            logger.error("Failed to read username record: %s", error)
            return None

    def get_online_status_rtdb(self, username: str) -> int:
        """Fetch the online status (1 or 0) of a username from RTDB."""
        from urllib.parse import quote

        safe_username = quote(username, safe="")
        url = f"{self.rtdb_url}/usernames/{safe_username}/online.json"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return 1 if response.json() == 1 else 0
            return 0
        except requests.exceptions.RequestException as error:
            logger.error(
                "Network error fetching online status for %s: %s",
                username,
                error,
            )
            return 0

    def set_online_status(
        self, username: str, is_online: bool, id_token: str
    ) -> dict:
        """Set the online status (1 or 0) for a username in RTDB."""
        from urllib.parse import quote

        safe_username = quote(username, safe="")
        url = (
            f"{self.rtdb_url}/usernames/{safe_username}/online.json"
            f"?auth={id_token}"
        )
        try:
            payload = 1 if is_online else 0
            response = requests.put(url, json=payload, timeout=10)
            return {"success": response.status_code == 200}
        except requests.exceptions.RequestException as error:
            logger.error("Network error setting online status: %s", error)
            return {"success": False, "error": str(error)}

    def set_online_status_on_disconnect(
        self, username: str, id_token: str
    ) -> dict:
        """Report that RTDB onDisconnect presence is not available through REST."""
        return {
            "success": False,
            "error": "RTDB onDisconnect is not supported by the REST API.",
        }

    def sign_in_with_email(self, email: str, password: str) -> dict:
        url = f"{self.auth_url}:signInWithPassword?key={self.api_key}"
        try:
            response = requests.post(
                url,
                json={"email": email, "password": password, "returnSecureToken": True},
                timeout=10,
            )
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            return {
                "success": False,
                "error": response.json().get("error", {}).get("message", "Unknown error"),
            }
        except requests.exceptions.RequestException as error:
            logger.error("Network error during sign in: %s", error)
            return {"success": False, "error": "Network connection lost."}

    def refresh_id_token(self, refresh_token: str) -> dict:
        """Use a refresh token to get a new ID token."""
        url = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
        try:
            response = requests.post(
                url,
                json={"grant_type": "refresh_token", "refresh_token": refresh_token},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "id_token": data.get("id_token"),
                    "refresh_token": data.get("refresh_token"),
                }
            return {"success": False, "error": "Token refresh failed"}
        except requests.exceptions.RequestException as error:
            logger.error("Token refresh error: %s", error)
            return {"success": False, "error": "Network error during token refresh"}

    def create_user_firestore(
        self, uid: str, username: str, pfp_number: int, id_token: str
    ) -> dict:
        url = f"{self.firestore_url}/users/{uid}?key={self.api_key}"
        headers = {
            "Authorization": f"Bearer {id_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "fields": {
                "username": {"stringValue": username},
                "pfp_number": {"integerValue": pfp_number},
                "report_count": {"integerValue": 0},
            }
        }
        try:
            response = requests.patch(url, json=payload, headers=headers, timeout=10)
            return {"success": response.status_code in [200, 204]}
        except requests.exceptions.RequestException as error:
            logger.error("Network error creating Firestore doc: %s", error)
            return {"success": False}

    def get_user_firestore(self, uid: str, id_token: str) -> dict:
        url = f"{self.firestore_url}/users/{uid}?key={self.api_key}"
        try:
            response = requests.get(
                url, headers={"Authorization": f"Bearer {id_token}"}, timeout=10
            )
            if response.status_code == 200:
                fields = response.json().get("fields", {})
                return {
                    "success": True,
                    "username": fields.get("username", {}).get("stringValue", ""),
                    "pfp_number": fields.get("pfp_number", {}).get("integerValue", 0),
                    "report_count": fields.get("report_count", {}).get("integerValue", 0),
                }
            return {"success": False, "error": "Failed to fetch user data"}
        except requests.exceptions.RequestException as error:
            logger.error("Network error fetching user: %s", error)
            return {"success": False}

    def delete_auth_user(self, uid: str, id_token: str) -> bool:
        url = f"{self.auth_url}:delete?key={self.api_key}"
        try:
            response = requests.post(url, json={"idToken": id_token}, timeout=10)
            return response.status_code == 200
        except requests.exceptions.RequestException as error:
            logger.error("Failed to delete auth user: %s", error)
            return False

    def delete_username_rtdb(self, username: str, id_token: str) -> bool:
        from urllib.parse import quote

        safe_username = quote(username, safe="")
        url = f"{self.rtdb_url}/usernames/{safe_username}.json?auth={id_token}"
        try:
            response = requests.delete(url, timeout=10)
            return response.status_code == 200
        except Exception as error:
            logger.error("Delete username error: %s", error)
            return False

    def delete_user_firestore(self, uid: str, id_token: str) -> bool:
        url = f"{self.firestore_url}/users/{uid}?key={self.api_key}"
        try:
            response = requests.delete(
                url, headers={"Authorization": f"Bearer {id_token}"}, timeout=10
            )
            return response.status_code in [200, 204]
        except requests.exceptions.RequestException as error:
            logger.error("Failed to delete Firestore user: %s", error)
            return False

    def flag_auth_for_deletion(self, uid: str, id_token: str) -> bool:
        url = f"{self.rtdb_url}/banned_auth/{uid}.json?auth={id_token}"
        try:
            response = requests.put(url, json=True, timeout=10)
            return response.status_code == 200
        except requests.exceptions.RequestException as error:
            logger.error("Auth flag error: %s", error)
            return False

    def check_blacklist(self, hw_id: str) -> dict:
        url = f"{self.rtdb_url}/blacklist/{hw_id}.json"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return {"banned": response.json() is not None}
            return {"banned": False}
        except requests.exceptions.RequestException as error:
            logger.error("Blacklist check error: %s", error)
            return {"banned": False}

    def get_hw_id(self, uid: str, id_token: str) -> str:
        url = f"{self.rtdb_url}/users/{uid}/hw_id.json?auth={id_token}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as error:
            logger.error("Get HW ID error: %s", error)
        return None

    def add_to_blacklist(self, hw_id: str, id_token: str) -> bool:
        url = f"{self.rtdb_url}/blacklist/{hw_id}.json?auth={id_token}"
        try:
            response = requests.put(url, json=True, timeout=10)
            return response.status_code == 200
        except Exception as error:
            logger.error("Add to blacklist error: %s", error)
            return False

    def register_hw_id(self, hw_id: str, uid: str, id_token: str) -> dict:
        url = f"{self.rtdb_url}/users/{uid}/hw_id.json?auth={id_token}"
        try:
            response = requests.put(url, json=hw_id, timeout=10)
            return {"success": response.status_code == 200}
        except requests.exceptions.RequestException as error:
            logger.error("HW ID register error: %s", error)
            return {"success": False}

    def get_profile_firestore(self, target_uid: str, id_token: str) -> dict:
        url = f"{self.firestore_url}/users/{target_uid}?key={self.api_key}"
        headers = {"Authorization": f"Bearer {id_token}"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return {"success": False, "error": "Failed to fetch user data"}

            fields = response.json().get("fields", {})
            report_count_raw = fields.get("report_count", {}).get("integerValue", 0)
            pfp_number_raw = fields.get("pfp_number", {}).get("integerValue", 0)
            try:
                report_count = int(report_count_raw) if report_count_raw is not None else 0
            except (TypeError, ValueError):
                report_count = 0
            try:
                pfp_number = int(pfp_number_raw) if pfp_number_raw is not None else 0
            except (TypeError, ValueError):
                pfp_number = 0

            return {
                "success": True,
                "username": fields.get("username", {}).get("stringValue", ""),
                "pfp_number": pfp_number,
                "report_count": report_count,
            }
        except requests.exceptions.RequestException as error:
            logger.error("Network error fetching user profile: %s", error)
            return {"success": False, "error": str(error)}

    def update_pfp_firestore(self, uid: str, pfp_number: int, id_token: str) -> dict:
        url = (
            f"{self.firestore_url}/users/{uid}?key={self.api_key}"
            "&updateMask.fieldPaths=pfp_number"
        )
        headers = {
            "Authorization": f"Bearer {id_token}",
            "Content-Type": "application/json",
        }
        payload = {"fields": {"pfp_number": {"integerValue": pfp_number}}}
        try:
            response = requests.patch(url, json=payload, headers=headers, timeout=10)
            return {"success": response.status_code in [200, 204]}
        except requests.exceptions.RequestException as error:
            logger.error("Network error updating PFP: %s", error)
            return {"success": False}

    def submit_report(self, reporter_uid: str, target_uid: str, id_token: str) -> dict:
        report_url = f"{self.rtdb_url}/reports/{target_uid}/{reporter_uid}.json?auth={id_token}"
        try:
            response = requests.get(report_url, timeout=10)
            if response.status_code == 200 and response.json() is not None:
                return {"success": False, "error": "You have already reported this user."}
        except requests.exceptions.RequestException as error:
            logger.error("Report check error: %s", error)
            return {"success": False, "error": "Unable to check existing report."}

        try:
            response = requests.put(report_url, json=True, timeout=10)
            if response.status_code != 200:
                return {"success": False, "error": "Failed to submit report."}
        except requests.exceptions.RequestException as error:
            logger.error("Report submit error: %s", error)
            return {"success": False, "error": "Failed to submit report."}

        profile = self.get_profile_firestore(target_uid, id_token)
        if not profile.get("success"):
            return {"success": False, "error": "Failed to fetch profile for report count."}
        new_count = int(profile.get("report_count", 0)) + 1
        profile_url = f"{self.firestore_url}/users/{target_uid}?key={self.api_key}"
        headers = {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}
        payload = {"fields": {"report_count": {"integerValue": new_count}}}
        try:
            requests.patch(profile_url, json=payload, headers=headers, timeout=10)
        except requests.exceptions.RequestException as error:
            logger.error("Report count update error: %s", error)

        if new_count >= 50:
            self._execute_auto_ban(target_uid, id_token)
            return {"success": True, "message": "Report submitted. User has been banned."}
        return {"success": True, "message": "Report submitted successfully."}

    def report_user(self, target_uid: str, reporter_hw_id: str, id_token: str) -> dict:
        """Create a per-device report and synchronize the profile report counter."""
        from urllib.parse import quote

        try:
            safe_hw_id = quote(reporter_hw_id, safe="")
            url = (
                f"{self.firestore_url}/users/{target_uid}/reports/{safe_hw_id}"
                f"?key={self.api_key}"
            )
            headers = {
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json",
            }
            existing = requests.get(url, headers=headers, timeout=10)
            if existing.status_code == 200:
                return {
                    "success": False,
                    "error": "You have already reported this user from this device.",
                }
            if existing.status_code not in (404,):
                logger.error("Report existence check failed (%s): %s", existing.status_code, existing.text)
                return {"success": False, "error": "Report failed. Please try again."}

            payload = {"fields": {"timestamp": {"stringValue": "true"}}}
            response = requests.patch(url, json=payload, headers=headers, timeout=10)
            if response.status_code in (200, 201):
                user_url = f"{self.firestore_url}/users/{target_uid}?key={self.api_key}"
                user_response = requests.get(user_url, headers=headers, timeout=10)
                if user_response.status_code != 200:
                    return {"success": False, "error": "Report saved, but report count could not be read."}
                fields = user_response.json().get("fields", {})
                raw_count = fields.get("report_count", {}).get("integerValue", 0)
                try:
                    report_count = int(raw_count or 0)
                except (TypeError, ValueError):
                    report_count = 0
                update_url = f"{user_url}&updateMask.fieldPaths=report_count"
                update_payload = {"fields": {"report_count": {"integerValue": report_count + 1}}}
                update_response = requests.patch(
                    update_url, json=update_payload, headers=headers, timeout=10
                )
                if update_response.status_code not in (200, 204):
                    logger.error("Report count update failed: %s", update_response.text)
                    return {"success": False, "error": "Report saved, but report count could not be updated."}
                return {"success": True, "report_count": report_count + 1}
            if response.status_code == 409 or "already exists" in response.text.casefold():
                return {
                    "success": False,
                    "error": "You have already reported this user from this device.",
                }
            logger.error("Report user failed (%s): %s", response.status_code, response.text)
            return {"success": False, "error": f"Report failed. Status: {response.status_code}"}
        except Exception as error:
            logger.error("Report user error: %s", error)
            return {"success": False, "error": "Network error."}

    def _execute_auto_ban(self, target_uid: str, admin_token: str):
        logger.warning("AUTO-BAN TRIGGERED for UID: %s", target_uid)
        hw_url = f"{self.rtdb_url}/users/{target_uid}/hw_id.json?auth={admin_token}"
        try:
            response = requests.get(hw_url, timeout=10)
            hw_id = response.json()
            if hw_id:
                ban_url = f"{self.rtdb_url}/blacklist/{hw_id}.json?auth={admin_token}"
                requests.put(ban_url, json=True, timeout=10)
        except requests.RequestException as error:
            logger.error("Auto-ban HW ID error: %s", error)

        profile = self.get_profile_firestore(target_uid, admin_token)
        if profile.get("success") and profile.get("username"):
            username_url = f"{self.rtdb_url}/usernames/{profile['username']}.json?auth={admin_token}"
            requests.delete(username_url, timeout=10)

        firestore_url = f"{self.firestore_url}/users/{target_uid}?key={self.api_key}"
        requests.delete(firestore_url, headers={"Authorization": f"Bearer {admin_token}"}, timeout=10)
        flag_url = f"{self.rtdb_url}/banned_auth/{target_uid}.json?auth={admin_token}"
        requests.put(flag_url, json=True, timeout=10)
