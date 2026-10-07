from profile_manager import ProfileManager


class ProfileService:
    def __init__(self):
        self.manager = ProfileManager()

    def get_profile(self, target_uid: str, id_token: str) -> dict:
        return self.manager.load_profile(target_uid, id_token)

    def get_online_status(self, username: str) -> int:
        return self.manager.get_online_status(username)

    def update_pfp(self, uid: str, pfp_number: int, id_token: str) -> dict:
        return self.manager.change_pfp(uid, pfp_number, id_token)

    def report(self, reporter_uid: str, target_uid: str, id_token: str) -> dict:
        return self.manager.report_user(reporter_uid, target_uid, id_token)

    def report_user(self, target_uid: str, reporter_hw_id: str, id_token: str, reporter_uid=None) -> dict:
        return self.manager.validate_and_report(
            target_uid, reporter_hw_id, id_token, reporter_uid=reporter_uid
        )
