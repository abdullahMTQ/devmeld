from notification_adapter import NotificationAdapter


class NotificationManager:
    def __init__(self):
        self.adapter = NotificationAdapter()

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
        if not target_uid or target_uid == commenter_uid:
            return None
        return self.adapter.add_notification(
            target_uid,
            thread_id,
            comment_id,
            commenter_uid,
            commenter_username,
            comment_body,
            id_token,
        )

    def get_unread(self, uid, id_token):
        return self.adapter.get_unread_notifications(uid, id_token)

    def get_unread_count(self, uid, id_token):
        return self.adapter.get_unread_count(uid, id_token)

    def mark_read(self, uid, notification_id, id_token):
        return self.adapter.mark_notification_read(uid, notification_id, id_token)

    def cleanup_read_notifications(self, user_uid: str, id_token: str) -> dict:
        return self.adapter.cleanup_read_notifications(user_uid, id_token)
