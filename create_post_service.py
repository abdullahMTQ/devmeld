from create_post_manager import CreatePostManager


class CreatePostService:
    def __init__(self):
        self.manager = CreatePostManager()

    def submit_post(self, title: str, body: str, tag_ids: list, author_uid: str, id_token: str) -> dict:
        return self.manager.validate_and_submit(title, body, tag_ids, author_uid, id_token)
