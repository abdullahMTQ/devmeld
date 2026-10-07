from content_filter_service import ContentFilterService
from threads_adapter import ThreadsAdapter


class ThreadsManager:
    def __init__(self):
        self.adapter = ThreadsAdapter()
        self.filter_service = ContentFilterService()

    def validate_and_create_post(self, title, body, tag_ids, author_uid, id_token):
        if self.filter_service.manager.contains_banned_word(title) or self.filter_service.manager.contains_banned_word(body):
            return {"success": False, "error": "Please stay respectful."}
        if not tag_ids:
            return {"success": False, "error": "Post must have at least one tag."}
        if len(tag_ids) > 3:
            return {"success": False, "error": "Maximum 3 tags allowed per post."}
        return self.adapter.create_post(title, body, tag_ids, author_uid, id_token)

    def validate_and_add_comment(
        self,
        thread_id,
        body,
        author_uid,
        author_username,
        author_pfp,
        id_token,
        post_author_uid=None,
    ):
        if not body.strip():
            return {"success": False, "error": "Comment cannot be empty."}
        if self.filter_service.manager.contains_banned_word(body):
            return {"success": False, "error": "Please stay respectful."}
        return self.adapter.add_comment(
            thread_id,
            body,
            author_uid,
            author_username,
            author_pfp,
            id_token,
            post_author_uid,
        )
