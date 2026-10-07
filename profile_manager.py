from firebase_rest_adapter import FirebaseRestAdapter
from hardware_id_adapter import HardwareIdAdapter


class ProfileManager:
    def __init__(self):
        self.adapter = FirebaseRestAdapter()

    def load_profile(self, target_uid: str, id_token: str) -> dict:
        return self.adapter.get_profile_firestore(target_uid, id_token)

    def get_online_status(self, username: str) -> int:
        return self.adapter.get_online_status_rtdb(username)

    def change_pfp(self, uid: str, pfp_number: int, id_token: str) -> dict:
        return self.adapter.update_pfp_firestore(uid, pfp_number, id_token)

    def report_user(self, reporter_uid: str, target_uid: str, id_token: str) -> dict:
        reporter_hw_id = HardwareIdAdapter().get_machine_id()
        return self.validate_and_report(
            target_uid, reporter_hw_id, id_token, reporter_uid=reporter_uid
        )

    def validate_and_report(
        self, target_uid: str, reporter_hw_id: str, id_token: str, reporter_uid=None
    ) -> dict:
        if not reporter_hw_id:
            return {"success": False, "error": "Device ID missing."}
        if reporter_uid and target_uid == reporter_uid:
            return {"success": False, "error": "You cannot report yourself."}
        return self.adapter.report_user(target_uid, reporter_hw_id, id_token)
