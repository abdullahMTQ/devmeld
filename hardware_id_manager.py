from firebase_rest_adapter import FirebaseRestAdapter
from hardware_id_adapter import HardwareIdAdapter


class HardwareIdManager:
    def __init__(self):
        self.adapter = HardwareIdAdapter()
        self.firebase_adapter = FirebaseRestAdapter()

    def is_banned(self) -> dict:
        return self.firebase_adapter.check_blacklist(self.adapter.get_machine_id())
