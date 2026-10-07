from datetime import datetime, timezone

import requests

from firebase_rest_adapter import FirebaseRestAdapter
from impobj_utils import logger


class ThreadsAdapter:
    def __init__(self):
        self.firebase = FirebaseRestAdapter()

    def _parse_document(self, document: dict) -> dict:
        fields = document.get("fields", {})
        raw_tags = fields.get("tag_ids", fields.get("tag_numbers", {})).get("arrayValue", {}).get("values", [])
        tag_ids = []
        for value in raw_tags:
            try:
                tag_ids.append(int(value.get("integerValue", 0)))
            except (TypeError, ValueError):
                continue
        return {
            "id": document.get("name", "").rsplit("/", 1)[-1],
            "title": fields.get("title", {}).get("stringValue", ""),
            "body": fields.get("body", {}).get("stringValue", ""),
            "tag_numbers": tag_ids,
            "author_uid": fields.get("author_uid", {}).get("stringValue", ""),
            "timestamp": fields.get("timestamp", {}).get("timestampValue", "") or fields.get("timestamp", {}).get("stringValue", ""),
        }

    def get_posts_paginated(self, page_size: int = 10, start_after: str = None, tag_filters: list = None, id_token: str = None) -> dict:
        print(f"[ThreadsAdapter] >>> FETCHING POSTS. Filters: {tag_filters} <<<")
        try:
            page_size = max(1, min(page_size, 10))
            url = f"{self.firebase.firestore_url}/threads"
            params = {"pageSize": str(page_size), "orderBy": "timestamp desc"}
            if start_after:
                params["pageToken"] = start_after
            headers = {"Authorization": f"Bearer {id_token}"} if id_token else {}
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code == 200:
                response_data = response.json()
                documents = response_data.get("documents", [])
                posts = []
                for document in documents:
                    fields = document.get("fields", {})
                    posts.append({
                        "id": document.get("name", "").split("/")[-1],
                        "title": fields.get("title", {}).get("stringValue", ""),
                        "body": fields.get("body", {}).get("stringValue", ""),
                        "tag_ids": fields.get("tag_ids", {}).get("arrayValue", {}).get("values", []),
                        "author_uid": fields.get("author_uid", {}).get("stringValue", ""),
                        "timestamp": fields.get("timestamp", {}).get("stringValue", ""),
                    })
                if tag_filters and len(tag_filters) > 0:
                    print(f"[ThreadsAdapter] >>> APPLYING FILTERS: {tag_filters} <<<")
                    filtered_posts = []
                    for post in posts:
                        post_tag_ids = []
                        for tag_value in post.get("tag_ids", []):
                            if isinstance(tag_value, dict) and "integerValue" in tag_value:
                                post_tag_ids.append(int(tag_value["integerValue"]))
                            elif isinstance(tag_value, int):
                                post_tag_ids.append(tag_value)
                        print(f"[ThreadsAdapter] Post '{post['title']}' has tags: {post_tag_ids}")
                        if any(tag_id in post_tag_ids for tag_id in tag_filters):
                            print("[ThreadsAdapter] -> MATCH! Keeping post.")
                            filtered_posts.append(post)
                        else:
                            print("[ThreadsAdapter] -> No match. Skipping.")
                    posts = filtered_posts
                    print(f"[ThreadsAdapter] Final filtered count: {len(posts)}")
                else:
                    print(f"[ThreadsAdapter] No filters active. Showing all {len(posts)} posts.")
                next_page_token = response_data.get("nextPageToken")
                return {
                    "posts": posts,
                    "has_more": bool(next_page_token),
                    "next_page_token": next_page_token,
                }
            print(f"[ThreadsAdapter] Failed to fetch posts. Status: {response.status_code}")
            return {"posts": [], "has_more": False, "next_page_token": None}
        except Exception as error:
            print(f"[ThreadsAdapter] Exception during fetch: {error}")
            return {"posts": [], "has_more": False, "next_page_token": None}

    def create_post(self, title, body, tag_ids, author_uid, id_token):
        """Create a post and fail safely when the network is unavailable."""
        logger.info("[ThreadsAdapter] Creating post for user: %s", author_uid)
        try:
            url = f"{self.firebase.firestore_url}/threads?key={self.firebase.api_key}"
            headers = {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}
            values = [{"integerValue": int(tag_id)} for tag_id in tag_ids]
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            payload = {"fields": {"title": {"stringValue": title}, "body": {"stringValue": body}, "tag_ids": {"arrayValue": {"values": values}}, "author_uid": {"stringValue": author_uid}, "timestamp": {"stringValue": timestamp}}}
            logger.info("[ThreadsAdapter] POSTing to %s", url)
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            logger.info("[ThreadsAdapter] Create post status: %s | Response: %s", response.status_code, response.text)
            if response.status_code not in (200, 201):
                return {"success": False, "error": f"Failed to post. Status: {response.status_code}"}
            return {"success": True}
        except requests.exceptions.RequestException:
            return {"success": False, "error": "Network connection lost. Post not saved."}
        except (ValueError, TypeError) as error:
            logger.error("Failed to create post: %s", error)
            return {"success": False, "error": "An unexpected error occurred."}

    def _add_to_user_threads(self, uid, thread_id, id_token):
        url = f"{self.firebase.firestore_url}/users/{uid}/threads/{thread_id}?key={self.firebase.api_key}"
        headers = {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}
        try:
            requests.patch(url, json={"fields": {"thread_id": {"stringValue": thread_id}}}, headers=headers, timeout=10)
        except requests.RequestException as error:
            logger.error("Failed to add user thread reference: %s", error)

    def get_post_details(self, thread_id: str, id_token: str) -> dict:
        try:
            url = f"{self.firebase.firestore_url}/threads/{thread_id}?key={self.firebase.api_key}"
            response = requests.get(
                url, headers={"Authorization": f"Bearer {id_token}"}, timeout=10
            )
            if response.status_code != 200:
                return {"success": False}
            fields = response.json().get("fields", {})
            raw_tags = fields.get("tag_ids", fields.get("tag_numbers", {})).get("arrayValue", {}).get("values", [])
            return {
                "success": True,
                "id": thread_id,
                "title": fields.get("title", {}).get("stringValue", ""),
                "body": fields.get("body", {}).get("stringValue", ""),
                "tag_ids": raw_tags,
                "author_uid": fields.get("author_uid", {}).get("stringValue", ""),
                "timestamp": fields.get("timestamp", {}).get("stringValue", "") or fields.get("timestamp", {}).get("timestampValue", ""),
            }
        except Exception as error:
            logger.error("Get post details error: %s", error)
            return {"success": False}

    def get_comments_paginated(self, thread_id: str, page_size=20, start_after=None, id_token=None):
        try:
            url = f"{self.firebase.firestore_url}/threads/{thread_id}/comments"
            headers = {"Authorization": f"Bearer {id_token}"} if id_token else {}
            params = {"key": self.firebase.api_key, "pageSize": str(page_size), "orderBy": "timestamp desc"}
            if start_after:
                params["pageToken"] = start_after
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code != 200:
                return {"comments": [], "has_more": False, "next_page_token": None}
            response_data = response.json()
            comments = []
            for document in response_data.get("documents", []):
                fields = document.get("fields", {})
                comments.append({
                    "id": document.get("name", "").rsplit("/", 1)[-1],
                    "body": fields.get("body", {}).get("stringValue", ""),
                    "author_uid": fields.get("author_uid", {}).get("stringValue", ""),
                    "author_username": fields.get("author_username", {}).get("stringValue", "@unknown"),
                    "author_pfp_number": int(fields.get("author_pfp_number", {}).get("integerValue", 0) or 0),
                    "timestamp": fields.get("timestamp", {}).get("stringValue", ""),
                })
            next_page_token = response_data.get("nextPageToken")
            return {
                "comments": comments,
                "has_more": bool(next_page_token),
                "next_page_token": next_page_token,
            }
        except Exception as error:
            logger.error("Get comments error: %s", error)
            return {"comments": [], "has_more": False, "next_page_token": None}

    def add_comment(
        self,
        thread_id,
        body,
        author_uid,
        author_username,
        author_pfp_number,
        id_token,
        post_author_uid=None,
    ):
        try:
            url = f"{self.firebase.firestore_url}/threads/{thread_id}/comments?key={self.firebase.api_key}"
            headers = {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            payload = {"fields": {
                "body": {"stringValue": body},
                "author_uid": {"stringValue": author_uid},
                "author_username": {"stringValue": author_username},
                "author_pfp_number": {"integerValue": int(author_pfp_number)},
                "timestamp": {"stringValue": timestamp},
            }}
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            success = response.status_code in (200, 201)
            if success and post_author_uid:
                try:
                    comment_id = response.json().get("name", "").rsplit("/", 1)[-1]
                    from notification_service import NotificationService

                    NotificationService().notify_new_comment(
                        post_author_uid,
                        thread_id,
                        comment_id,
                        author_uid,
                        author_username,
                        body,
                        id_token,
                    )
                except Exception as notification_error:
                    logger.error("Comment notification error: %s", notification_error)
            return {"success": success}
        except Exception as error:
            logger.error("Add comment error: %s", error)
            return {"success": False}

    def delete_post_and_orphans(self, thread_id: str, id_token: str) -> dict:
        try:
            headers = {"Authorization": f"Bearer {id_token}"}
            comments_url = f"{self.firebase.firestore_url}/threads/{thread_id}/comments?key={self.firebase.api_key}"
            response = requests.get(comments_url, headers=headers, timeout=10)
            if response.status_code == 200:
                for document in response.json().get("documents", []):
                    document_url = document.get("name")
                    if document_url:
                        full_url = f"https://firestore.googleapis.com/v1/{document_url}?key={self.firebase.api_key}"
                        requests.delete(full_url, headers=headers, timeout=5)
            post_url = f"{self.firebase.firestore_url}/threads/{thread_id}?key={self.firebase.api_key}"
            response = requests.delete(post_url, headers=headers, timeout=10)
            return {"success": response.status_code in (200, 204)}
        except Exception as error:
            logger.error("Delete post error: %s", error)
            return {"success": False}

    def search_posts(
        self,
        query: str,
        limit: int = 10,
        start_after: str = None,
        id_token: str = None,
    ) -> dict:
        """Search at most 10 documents from one Firestore page."""
        limit = max(1, min(limit, 10))
        logger.info("[ThreadsAdapter] Searching posts for: %s (limit: %d)", query, limit)
        try:
            headers = {"Authorization": f"Bearer {id_token}"} if id_token else {}
            params = {
                "key": self.firebase.api_key,
                "pageSize": str(limit),
                "orderBy": "timestamp desc",
            }
            if start_after:
                params["pageToken"] = start_after
            response = requests.get(
                f"{self.firebase.firestore_url}/threads",
                params=params,
                headers=headers,
                timeout=15,
            )
            if response.status_code != 200:
                return {"results": [], "next_page_token": None, "has_more": False}
            response_data = response.json()
            query_lower = query.casefold()
            results = []
            for document in response_data.get("documents", []):
                post = self._parse_document(document)
                if query_lower in post["title"].casefold() or query_lower in post["body"].casefold():
                    post["type"] = "post"
                    post["tag_ids"] = post.get("tag_numbers", [])
                    post["tag_numbers"] = post["tag_ids"]
                    results.append(post)
            next_page_token = response_data.get("nextPageToken")
            return {
                "results": results,
                "next_page_token": next_page_token,
                "has_more": bool(next_page_token),
            }
        except Exception as error:
            logger.error("[ThreadsAdapter] Post search exception: %s", error)
            return {"results": [], "next_page_token": None, "has_more": False}

    def search_users_by_username(self, username: str, start_after: str = None) -> dict:
        """Search usernames using an RTDB key range and bounded result count."""
        logger.info("[ThreadsAdapter] Searching user: %s", username)
        try:
            import json

            search_query = username.replace("@", "").lower()
            start_key = start_after or f"@{search_query}"
            params = {
                "orderBy": '"$key"',
                "startAt": json.dumps(start_key),
                "endAt": json.dumps(f"@{search_query}\uf8ff"),
                "limitToFirst": 10,
            }
            response = requests.get(
                f"{self.firebase.rtdb_url}/usernames.json",
                params=params,
                timeout=10,
            )
            logger.info("[ThreadsAdapter] RTDB Search URL: %s with params: %s", self.firebase.rtdb_url, params)
            logger.info("[ThreadsAdapter] RTDB search status: %s", response.status_code)
            if response.status_code != 200:
                return {"results": [], "next_page_token": None, "has_more": False}
            raw_users = response.json() or {}
            results = []
            for name, value in raw_users.items():
                if start_after and name == start_after:
                    continue
                uid = value.get("uid", "") if isinstance(value, dict) else value
                results.append({"username": name, "uid": uid, "type": "user"})
            next_page_token = next(reversed(raw_users), None) if len(raw_users) >= 10 else None
            return {
                "results": results,
                "next_page_token": next_page_token,
                "has_more": bool(next_page_token),
            }
        except Exception as error:
            logger.error("[ThreadsAdapter] User search exception: %s", error)
            return {"results": [], "next_page_token": None, "has_more": False}
