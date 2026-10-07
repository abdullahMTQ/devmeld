from notification_manager import NotificationManager


class NotificationService:
    def __init__(self):
        self.manager = NotificationManager()

    def notify_new_comment(
        self,
        target_uid,
        thread_id,
        comment_id,
        commenter_uid,
        commenter_username,
        comment_body,
        id_token,
    ):
        return self.manager.notify_new_comment(
            target_uid,
            thread_id,
            comment_id,
            commenter_uid,
            commenter_username,
            comment_body,
            id_token,
        )

    def get_unread(self, uid, id_token):
        return self.manager.get_unread(uid, id_token)

    def get_unread_count(self, uid, id_token):
        return self.manager.get_unread_count(uid, id_token)

    def mark_read(self, uid, notification_id, id_token):
        return self.manager.mark_read(uid, notification_id, id_token)

    def cleanup_read_notifications(self, user_uid: str, id_token: str) -> dict:
        return self.manager.cleanup_read_notifications(user_uid, id_token)
