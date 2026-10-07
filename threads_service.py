from threads_adapter import ThreadsAdapter
from threads_manager import ThreadsManager


class ThreadsService:
    def __init__(self):
        self.manager = ThreadsManager()
        self.adapter = ThreadsAdapter()

    def get_posts(self, page_size=10, start_after=None, tag_filters=None, id_token=None):
        return self.adapter.get_posts_paginated(page_size, start_after, tag_filters, id_token)

    def create_post(self, title, body, tag_ids, author_uid, id_token):
        return self.manager.validate_and_create_post(title, body, tag_ids, author_uid, id_token)

    def search(self, query, start_after=None, id_token=None):
        if query.startswith("@"):
            return self.adapter.search_users_by_username(query, start_after)
        if query.startswith("#"):
            return {"results": [], "next_page_token": None, "has_more": False}
        return self.adapter.search_posts(
            query, limit=10, start_after=start_after, id_token=id_token
        )

    def get_post(self, thread_id, id_token):
        return self.adapter.get_post_details(thread_id, id_token)

    def get_comments(self, thread_id, page_size=20, start_after=None, id_token=None):
        return self.adapter.get_comments_paginated(thread_id, page_size, start_after, id_token)

    def add_comment(
        self,
        thread_id,
        body,
        author_uid,
        author_username,
        author_pfp,
        id_token,
        post_author_uid=None,
    ):
        return self.manager.validate_and_add_comment(
            thread_id,
            body,
            author_uid,
            author_username,
            author_pfp,
            id_token,
            post_author_uid,
        )

    def delete_post(self, thread_id, id_token):
        return self.adapter.delete_post_and_orphans(thread_id, id_token)
