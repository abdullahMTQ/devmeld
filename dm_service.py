from dm_manager import DMManager


class DMService:
    def __init__(self):
        self.manager = DMManager()

    def initialize_chat(
        self,
        user_a_uid: str,
        user_b_uid: str,
        user_a_username: str,
        user_b_username: str,
        id_token: str,
    ) -> dict:
        return self.manager.initialize_chat(
            user_a_uid,
            user_b_uid,
            user_a_username,
            user_b_username,
            id_token,
        )

    def send_message(
        self,
        user_uid: str,
        chat_id: str,
        content: str,
        username: str,
        id_token: str,
        storage_path: str = None,
        file_name: str = None,
    ) -> dict:
        return self.manager.send_message(
            user_uid, chat_id, content, username, id_token, storage_path, file_name
        )

    def delete_message(
        self, user_uid: str, chat_id: str, message_id: str, id_token: str
    ) -> dict:
        return self.manager.delete_message(
            user_uid, chat_id, message_id, id_token
        )

    def block_user_and_delete_chat(
        self, user_uid: str, other_uid: str, chat_id: str, id_token: str
    ) -> dict:
        return self.manager.block_user_and_delete_chat(
            user_uid, other_uid, chat_id, id_token
        )

    def get_messages(
        self,
        user_uid: str,
        chat_id: str,
        id_token: str,
        page_size: int = 20,
        start_after: str = None,
    ) -> dict:
        return self.manager.get_messages(
            user_uid, chat_id, id_token, page_size, start_after
        )

    def preload_allowed_chats(
        self, user_uid: str, chat_ids: list, id_token: str
    ) -> dict:
        return self.manager.preload_allowed_chats(user_uid, chat_ids, id_token)

    def delete_text_messages(
        self, target_uids: list, chat_id: str, message_ids: list, id_token: str
    ) -> dict:
        return self.manager.delete_text_messages(
            target_uids, chat_id, message_ids, id_token
        )

    def cleanup_notifications(self, user_uid: str, id_token: str) -> dict:
        return self.manager.cleanup_notifications(user_uid, id_token)

    def get_user_chats(self, uid: str, id_token: str) -> dict:
        return self.manager.get_user_chats(uid, id_token)

    def upload_file(
        self, chat_id: str, message_id: str, file_path: str, id_token: str
    ) -> dict:
        return self.manager.upload_file(chat_id, message_id, file_path, id_token)

    def download_file(
        self, storage_path: str, destination_path: str, id_token: str
    ) -> dict:
        return self.manager.download_file(storage_path, destination_path, id_token)
