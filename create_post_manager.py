from content_filter_service import ContentFilterService
from threads_adapter import ThreadsAdapter


class CreatePostManager:
    def __init__(self):
        self.adapter = ThreadsAdapter()
        self.filter_service = ContentFilterService()

    def validate_and_submit(self, title: str, body: str, tag_ids: list, author_uid: str, id_token: str) -> dict:
        if not title.strip() or not body.strip():
            return {"success": False, "error": "Title and body cannot be empty."}
        if not tag_ids or len(tag_ids) < 1:
            return {"success": False, "error": "Please select at least one tag."}
        if len(tag_ids) > 3:
            return {"success": False, "error": "Maximum 3 tags allowed per post."}
        if not self.filter_service.validate_text(title)["valid"] or not self.filter_service.validate_text(body)["valid"]:
            return {"success": False, "error": "Please stay respectful."}
        return self.adapter.create_post(title, body, tag_ids, author_uid, id_token)
