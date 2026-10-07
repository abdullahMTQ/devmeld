from hardware_id_manager import HardwareIdManager


class HardwareIdService:
    def __init__(self):
        self.manager = HardwareIdManager()

    def check_ban_status(self) -> dict:
        return self.manager.is_banned()
