from datetime import datetime, timezone
import json
import os
import time
import uuid
from urllib.parse import quote

import requests

from firebase_rest_adapter import FirebaseRestAdapter
from impobj_utils import logger


def get_blocked_chats() -> list:
    """Load locally blocked chat IDs."""
    from impobj_utils import get_impobj_path

    blocked_file = get_impobj_path() / "blockedchatUIDs" / "blocked.json"
    try:
        with blocked_file.open("r", encoding="utf-8") as file:
            blocked = json.load(file)
        return blocked if isinstance(blocked, list) else []
    except (OSError, ValueError):
        return []


def add_blocked_chat(chat_id: str):
    """Persist a chat ID in the local block list."""
    from impobj_utils import get_impobj_path

    blocked_dir = get_impobj_path() / "blockedchatUIDs"
    blocked_dir.mkdir(parents=True, exist_ok=True)
    blocked_file = blocked_dir / "blocked.json"
    blocked = get_blocked_chats()
    if chat_id not in blocked:
        blocked.append(chat_id)
        with blocked_file.open("w", encoding="utf-8") as file:
            json.dump(blocked, file, indent=2)
    logger.info("[DMAdapter] Added %s to local blocked list.", chat_id)


def remove_blocked_chat(chat_id: str):
    """Remove a chat ID from the local block list."""
    from impobj_utils import get_impobj_path

    blocked_dir = get_impobj_path() / "blockedchatUIDs"
    blocked_file = blocked_dir / "blocked.json"
    blocked = get_blocked_chats()
    if chat_id in blocked:
        blocked.remove(chat_id)
        blocked_dir.mkdir(parents=True, exist_ok=True)
        with blocked_file.open("w", encoding="utf-8") as file:
            json.dump(blocked, file, indent=2)
        logger.info(
            "[DMAdapter] Removed %s from local blocked list (unblocked via profile DM).",
            chat_id,
        )


class DMAdapter:
    def __init__(self):
        self.firebase = FirebaseRestAdapter()

    def create_or_get_chat(
        self,
        user_a_uid: str,
        user_b_uid: str,
        user_a_username: str,
        user_b_username: str,
        id_token: str,
    ) -> dict:
        """Upsert the chat in both user collections with deterministic fields."""
        sorted_uids = sorted([user_a_uid, user_b_uid])
        chat_id = f"{sorted_uids[0]}_{sorted_uids[1]}"
        if sorted_uids[0] == user_a_uid:
            participant_a_uid, participant_b_uid = user_a_uid, user_b_uid
            username_a, username_b = user_a_username, user_b_username
        else:
            participant_a_uid, participant_b_uid = user_b_uid, user_a_uid
            username_a, username_b = user_b_username, user_a_username
        headers = {
            "Authorization": f"Bearer {id_token}",
            "Content-Type": "application/json",
        }
        try:
            payload = {
                "fields": {
                    "username_a": {"stringValue": username_a},
                    "username_b": {"stringValue": username_b},
                    "participant_a_uid": {"stringValue": participant_a_uid},
                    "participant_b_uid": {"stringValue": participant_b_uid},
                    "created_at": {
                        "stringValue": datetime.now(timezone.utc).isoformat()
                    },
                }
            }
            params = {"key": self.firebase.api_key}
            url_a = (
                f"{self.firebase.firestore_url}/users/{user_a_uid}/DM/{chat_id}"
            )
            url_b = (
                f"{self.firebase.firestore_url}/users/{user_b_uid}/DM/{chat_id}"
            )

            response_a = requests.patch(
                url_a, params=params, json=payload, headers=headers, timeout=10
            )
            response_b = requests.patch(
                url_b, params=params, json=payload, headers=headers, timeout=10
            )

            successful_statuses = (200, 201, 204)
            if (
                response_a.status_code in successful_statuses
                and response_b.status_code in successful_statuses
            ):
                logger.info(
                    "[DMAdapter] Successfully upserted chat %s for both users.",
                    chat_id,
                )
                return {
                    "success": True,
                    "chat_id": chat_id,
                    "username_a": username_a,
                    "username_b": username_b,
                    "user_a_uid": participant_a_uid,
                    "user_b_uid": participant_b_uid,
                }

            logger.error(
                "[DMAdapter] Failed to upsert chat. A: %s (%s), B: %s (%s)",
                response_a.status_code,
                response_a.text,
                response_b.status_code,
                response_b.text,
            )
            return {
                "success": False,
                "error": (
                    f"Failed to create chat. A: {response_a.status_code}, "
                    f"B: {response_b.status_code}"
                ),
            }
        except Exception as error:
            logger.error("Create/get chat error: %s", error)
            return {"success": False, "error": str(error)}

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
        """Write one UUID-keyed message to both participants' collections."""
        message_id = str(uuid.uuid4())
        own_prefix = f"{user_uid}_"
        own_suffix = f"_{user_uid}"
        if chat_id.startswith(own_prefix):
            other_uid = chat_id[len(own_prefix):]
        elif chat_id.endswith(own_suffix):
            other_uid = chat_id[:-len(own_suffix)]
        else:
            return {
                "success": False,
                "error": "Current user is not a participant in this chat.",
            }
        if not other_uid:
            return {"success": False, "error": "Chat participant UID is missing."}

        headers = {
            "Authorization": f"Bearer {id_token}",
            "Content-Type": "application/json",
        }
        fields = {
            "author": {"stringValue": username},
            "content": {"stringValue": content},
            "author_uid": {"stringValue": user_uid},
            "timestamp": {
                "stringValue": datetime.now(timezone.utc).isoformat()
            },
        }
        if storage_path:
            fields["storage_path"] = {"stringValue": storage_path}
        if file_name:
            fields["file_name"] = {"stringValue": file_name}
        payload = {"fields": fields}
        params = {"key": self.firebase.api_key}
        own_url = (
            f"{self.firebase.firestore_url}/users/{user_uid}/DM/{chat_id}/"
            f"messages/{message_id}"
        )
        other_url = (
            f"{self.firebase.firestore_url}/users/{other_uid}/DM/{chat_id}/"
            f"messages/{message_id}"
        )
        try:
            successful_statuses = (200, 201, 204)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    own_response = requests.patch(
                        own_url,
                        params=params,
                        json=payload,
                        headers=headers,
                        timeout=20,
                    )
                    other_response = requests.patch(
                        other_url,
                        params=params,
                        json=payload,
                        headers=headers,
                        timeout=20,
                    )
                except requests.RequestException as error:
                    logger.warning(
                        "[DMAdapter] Dual-write network error on attempt %d/%d: %s",
                        attempt + 1,
                        max_retries,
                        error,
                    )
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(1)
                    continue

                logger.info(
                    "[DMAdapter] Dual-write message %s. Self: %s, Other: %s",
                    message_id,
                    own_response.status_code,
                    other_response.status_code,
                )
                if (
                    own_response.status_code in successful_statuses
                    and other_response.status_code in successful_statuses
                ):
                    return {"success": True, "message_id": message_id}

                retryable = any(
                    response.status_code == 429 or response.status_code >= 500
                    for response in (own_response, other_response)
                )
                if retryable and attempt < max_retries - 1:
                    logger.warning(
                        "[DMAdapter] Transient dual-write failure, retrying %d/%d",
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(1)
                    continue
                return {
                    "success": False,
                    "error": (
                        "Failed to dual-write message. "
                        f"Self: {own_response.status_code}, "
                        f"Other: {other_response.status_code}"
                    ),
                }
            return {"success": False, "error": "Failed to send message after retries."}
        except Exception as error:
            logger.error("Send message error: %s", error)
            return {"success": False, "error": str(error)}

    def delete_message(
        self,
        user_uid: str,
        chat_id: str,
        message_id: str,
        id_token: str,
    ) -> dict:
        """Delete a message from both participant folders and Storage."""
        headers = {"Authorization": f"Bearer {id_token}"}
        try:
            prefix = f"{user_uid}_"
            suffix = f"_{user_uid}"
            if chat_id.startswith(prefix):
                other_uid = chat_id[len(prefix):]
            elif chat_id.endswith(suffix):
                other_uid = chat_id[:-len(suffix)]
            else:
                logger.error(
                    "[DMAdapter] Cannot determine peer UID from chat %s for user %s",
                    chat_id,
                    user_uid,
                )
                return {"success": False, "error": "Chat participants could not be resolved"}
            if not other_uid:
                return {"success": False, "error": "Chat peer UID is missing"}

            params = {"key": self.firebase.api_key}
            message_url_self = (
                f"{self.firebase.firestore_url}/users/{user_uid}/DM/"
                f"{chat_id}/messages/{message_id}"
            )
            response = requests.get(
                message_url_self,
                params=params,
                headers=headers,
                timeout=10,
            )
            storage_path = None
            if response.status_code == 200:
                fields = response.json().get("fields", {})
                storage_path = fields.get("storage_path", {}).get("stringValue")
                if storage_path:
                    logger.info(
                        "[DMAdapter] Found storage_path for deletion: %s",
                        storage_path,
                    )
            else:
                logger.warning(
                    "[DMAdapter] Could not fetch message to get storage_path. "
                    "Status: %s",
                    response.status_code,
                )

            for target_uid in (user_uid, other_uid):
                delete_url = (
                    f"{self.firebase.firestore_url}/users/{target_uid}/DM/"
                    f"{chat_id}/messages/{message_id}"
                )
                delete_response = requests.delete(
                    delete_url,
                    params=params,
                    headers=headers,
                    timeout=10,
                )
                if delete_response.status_code in (200, 204):
                    logger.info(
                        "[DMAdapter] Deleted message %s from %s's folder",
                        message_id,
                        target_uid,
                    )
                else:
                    logger.warning(
                        "[DMAdapter] Failed to delete message from %s's folder. "
                        "Status: %s, Body: %s",
                        target_uid,
                        delete_response.status_code,
                        delete_response.text,
                    )
            if storage_path:
                self._delete_storage_file(storage_path, id_token)
            else:
                logger.info(
                    "[DMAdapter] No storage_path found, skipping storage deletion."
                )
            return {"success": True}
        except Exception as error:
            logger.error("Delete message error: %s", error)
            return {"success": False, "error": str(error)}

    def _delete_storage_file(self, storage_path: str, id_token: str) -> bool:
        """Delete an associated Firebase Storage object using its encoded path."""
        try:
            encoded_path = quote(storage_path, safe="")
            url = (
                "https://firebasestorage.googleapis.com/v0/b/"
                f"devmeld.firebasestorage.app/o/{encoded_path}"
            )
            headers = {"Authorization": f"Bearer {id_token}"}
            logger.info(
                "[DMAdapter] Attempting to delete storage file: %s", url
            )
            response = requests.delete(url, headers=headers, timeout=10)
            if response.status_code in (200, 204, 404):
                logger.info(
                    "[DMAdapter] Successfully deleted storage file: %s",
                    storage_path,
                )
                return True
            logger.error(
                "[DMAdapter] Failed to delete storage file. Status: %s, Body: %s",
                response.status_code,
                response.text,
            )
            return False
        except Exception as error:
            logger.error("Storage deletion error: %s", error)
            return False

    def block_user_and_delete_chat(
        self, user_uid: str, other_uid: str, chat_id: str, id_token: str
    ) -> dict:
        """Delete both copies of a chat and its attachments, then block it locally."""
        from impobj_utils import get_impobj_path

        if user_uid == other_uid or chat_id != "_".join(sorted((user_uid, other_uid))):
            return {"success": False, "error": "Chat participants do not match chat ID."}

        headers = {"Authorization": f"Bearer {id_token}"}
        params = {"key": self.firebase.api_key}
        target_uids = list(dict.fromkeys((user_uid, other_uid)))
        documents_by_uid = {}
        storage_paths = set()

        try:
            for target_uid in target_uids:
                messages_url = (
                    f"{self.firebase.firestore_url}/users/{target_uid}/DM/"
                    f"{chat_id}/messages"
                )
                page_token = None
                documents = []
                while True:
                    page_params = {**params, "pageSize": "1000"}
                    if page_token:
                        page_params["pageToken"] = page_token
                    response = requests.get(
                        messages_url,
                        params=page_params,
                        headers=headers,
                        timeout=20,
                    )
                    if response.status_code == 404:
                        break
                    if response.status_code != 200:
                        return {
                            "success": False,
                            "error": (
                                f"Could not list messages for {target_uid}: "
                                f"{response.status_code} {response.text}"
                            ),
                        }
                    response_data = response.json()
                    documents.extend(response_data.get("documents", []))
                    page_token = response_data.get("nextPageToken")
                    if not page_token:
                        break
                documents_by_uid[target_uid] = documents
                for document in documents:
                    storage_path = (
                        document.get("fields", {})
                        .get("storage_path", {})
                        .get("stringValue")
                    )
                    if storage_path:
                        storage_paths.add(storage_path)

            for storage_path in storage_paths:
                if not self._delete_storage_file(storage_path, id_token):
                    return {
                        "success": False,
                        "error": f"Could not delete attachment: {storage_path}",
                    }

            message_ids = {
                document.get("name", "").rsplit("/", 1)[-1]
                for documents in documents_by_uid.values()
                for document in documents
                if document.get("name")
            }
            for target_uid in target_uids:
                for message_id in message_ids:
                    message_url = (
                        f"{self.firebase.firestore_url}/users/{target_uid}/DM/"
                        f"{chat_id}/messages/{message_id}"
                    )
                    response = requests.delete(
                        message_url,
                        params=params,
                        headers=headers,
                        timeout=10,
                    )
                    if response.status_code not in (200, 204, 404):
                        return {
                            "success": False,
                            "error": (
                                f"Could not delete message {message_id} from "
                                f"{target_uid}: {response.status_code} {response.text}"
                            ),
                        }

            for target_uid in target_uids:
                chat_url = (
                    f"{self.firebase.firestore_url}/users/{target_uid}/DM/{chat_id}"
                )
                response = requests.delete(
                    chat_url,
                    params=params,
                    headers=headers,
                    timeout=10,
                )
                if response.status_code not in (200, 204, 404):
                    return {
                        "success": False,
                        "error": (
                            f"Could not delete chat metadata for {target_uid}: "
                            f"{response.status_code} {response.text}"
                        ),
                    }

            local_chat_file = get_impobj_path() / "chatMSG" / f"{chat_id}.json"
            if local_chat_file.exists():
                local_chat_file.unlink()
            add_blocked_chat(chat_id)
            logger.info("[DMAdapter] Nuclear deletion complete for chat %s.", chat_id)
            return {"success": True}
        except Exception as error:
            logger.exception("Block user error: %s", error)
            return {"success": False, "error": str(error)}

    def get_chat_messages(
        self,
        user_uid: str,
        chat_id: str,
        id_token: str,
        page_size: int = 20,
        start_after: str = None,
    ) -> dict:
        """Fetch one page of messages from a chat."""
        url = (
            f"{self.firebase.firestore_url}/users/{user_uid}/DM/{chat_id}/messages"
        )
        headers = {"Authorization": f"Bearer {id_token}"}
        params = {
            "key": self.firebase.api_key,
            "pageSize": str(page_size),
            "orderBy": "timestamp desc",
        }
        if start_after:
            params["pageToken"] = start_after
        try:
            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = requests.get(
                        url, params=params, headers=headers, timeout=20
                    )
                except requests.RequestException as error:
                    logger.warning(
                        "[DMAdapter] Message fetch network error on attempt %d/%d: %s",
                        attempt + 1,
                        max_retries,
                        error,
                    )
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(1)
                    continue

                if response.status_code == 200:
                    break
                if response.status_code == 429 or response.status_code >= 500:
                    logger.warning(
                        "[DMAdapter] Fetch messages failed (status %s), "
                        "retrying %d/%d",
                        response.status_code,
                        attempt + 1,
                        max_retries,
                    )
                    if attempt < max_retries - 1:
                        time.sleep(1)
                    continue
                return {
                    "messages": [],
                    "has_more": False,
                    "next_page_token": None,
                }

            if response is None or response.status_code != 200:
                return {
                    "messages": [],
                    "has_more": False,
                    "next_page_token": None,
                }
            response_data = response.json()
            messages = []
            for document in response_data.get("documents", []):
                fields = document.get("fields", {})
                messages.append(
                    {
                        "id": document.get("name", "").rsplit("/", 1)[-1],
                        "author": fields.get("author", {}).get("stringValue", ""),
                        "author_uid": fields.get("author_uid", {}).get("stringValue", ""),
                        "content": fields.get("content", {}).get("stringValue", ""),
                        "timestamp": fields.get("timestamp", {}).get("stringValue", ""),
                        "storage_path": fields.get("storage_path", {}).get("stringValue"),
                        "file_name": fields.get("file_name", {}).get("stringValue", ""),
                    }
                )
            next_page_token = response_data.get("nextPageToken")
            return {
                "messages": messages,
                "has_more": bool(next_page_token),
                "next_page_token": next_page_token,
            }
        except requests.RequestException as error:
            logger.error("Get messages error: %s", error)
            return {"messages": [], "has_more": False, "next_page_token": None}

    def preload_allowed_chats(
        self, user_uid: str, chat_ids: list, id_token: str
    ) -> dict:
        """Cache recent messages for allowed chats and report latest-message status."""
        from impobj_utils import get_impobj_path

        headers = {"Authorization": f"Bearer {id_token}"}
        params = {
            "key": self.firebase.api_key,
            "pageSize": "5",
            "orderBy": "timestamp desc",
        }
        chat_dir = get_impobj_path() / "chatMSG"
        unread_status = {}
        errors = {}

        for chat_id in dict.fromkeys(chat_ids):
            url = (
                f"{self.firebase.firestore_url}/users/{user_uid}/DM/"
                f"{chat_id}/messages"
            )
            try:
                response = requests.get(
                    url, params=params, headers=headers, timeout=20
                )
                if response.status_code == 404:
                    unread_status[chat_id] = False
                    continue
                if response.status_code != 200:
                    errors[chat_id] = (
                        f"Message preload failed: {response.status_code} "
                        f"{response.text}"
                    )
                    continue

                documents = response.json().get("documents", [])
                unread_status[chat_id] = bool(
                    documents
                    and documents[0]
                    .get("fields", {})
                    .get("author_uid", {})
                    .get("stringValue", "")
                    != user_uid
                )

                chat_dir.mkdir(parents=True, exist_ok=True)
                chat_file = chat_dir / f"{chat_id}.json"
                try:
                    with chat_file.open("r", encoding="utf-8") as file:
                        local_messages = json.load(file)
                    if not isinstance(local_messages, list):
                        local_messages = []
                except (OSError, ValueError):
                    local_messages = []

                local_messages = [
                    message for message in local_messages
                    if isinstance(message, dict)
                ]
                local_ids = {
                    message.get("id")
                    for message in local_messages
                    if message.get("id")
                }
                for document in documents:
                    message_id = document.get("name", "").rsplit("/", 1)[-1]
                    if not message_id or message_id in local_ids:
                        continue
                    fields = document.get("fields", {})
                    local_messages.append(
                        {
                            "id": message_id,
                            "author": fields.get("author", {}).get("stringValue", ""),
                            "author_uid": fields.get("author_uid", {}).get("stringValue", ""),
                            "content": fields.get("content", {}).get("stringValue", ""),
                            "timestamp": fields.get("timestamp", {}).get("stringValue", ""),
                            "storage_path": fields.get("storage_path", {}).get("stringValue"),
                            "file_name": fields.get("file_name", {}).get("stringValue", ""),
                        }
                    )
                    local_ids.add(message_id)

                def timestamp_key(message):
                    timestamp = message.get("timestamp", "")
                    try:
                        parsed = datetime.fromisoformat(
                            timestamp.replace("Z", "+00:00")
                        )
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=timezone.utc)
                        return parsed.astimezone(timezone.utc)
                    except (AttributeError, TypeError, ValueError):
                        return datetime.min.replace(tzinfo=timezone.utc)

                local_messages.sort(key=timestamp_key)
                with chat_file.open("w", encoding="utf-8") as file:
                    json.dump(local_messages, file, indent=2)
            except requests.RequestException as error:
                errors[chat_id] = str(error)
                logger.warning(
                    "[DMAdapter] Preload failed for chat %s: %s", chat_id, error
                )
            except (OSError, ValueError) as error:
                errors[chat_id] = str(error)
                logger.warning(
                    "[DMAdapter] Could not update cache for chat %s: %s",
                    chat_id,
                    error,
                )

        logger.info(
            "[DMAdapter] Preloaded %d chats. Unread: %d",
            len(unread_status),
            sum(unread_status.values()),
        )
        return {"success": True, "unread_status": unread_status, "errors": errors}

    def delete_text_messages_from_firestore(
        self,
        target_uids: list,
        chat_id: str,
        message_ids: list,
        id_token: str,
    ) -> dict:
        """Delete text-message documents from all target chat collections."""
        headers = {"Authorization": f"Bearer {id_token}"}
        deleted_count = 0
        try:
            target_uids = list(dict.fromkeys(target_uids))
            logger.info(
                "[DMAdapter] Starting dual cleanup. Target UIDs: %s, chat ID: %s, "
                "messages: %s",
                target_uids,
                chat_id,
                message_ids,
            )
            for target_uid in target_uids:
                for message_id in message_ids:
                    url = (
                        f"{self.firebase.firestore_url}/users/{target_uid}/DM/"
                        f"{chat_id}/messages/{message_id}"
                    )
                    logger.info("[DMAdapter] Attempting DELETE: %s", url)
                    response = requests.delete(
                        url,
                        params={"key": self.firebase.api_key},
                        headers=headers,
                        timeout=10,
                    )
                    if response.status_code in (200, 204):
                        logger.info(
                            "[DMAdapter] Deleted message %s from %s",
                            message_id,
                            target_uid,
                        )
                        deleted_count += 1
                    else:
                        logger.warning(
                            "[DMAdapter] Failed to delete %s from %s: %s; %s",
                            message_id,
                            target_uid,
                            response.status_code,
                            response.text,
                        )
            logger.info(
                "[DMAdapter] Dual cleanup complete. Deleted %s operations.",
                deleted_count,
            )
            return {"success": True, "deleted": deleted_count}
        except Exception as error:
            logger.exception(
                "[DMAdapter] Critical error deleting text messages: %s", error
            )
            return {"success": False, "error": str(error)}

    def get_user_chats(self, uid: str, id_token: str) -> dict:
        """Fetch the chat records stored under the user's DM collection."""
        url = f"{self.firebase.firestore_url}/users/{uid}/DM"
        headers = {"Authorization": f"Bearer {id_token}"}
        params = {"key": self.firebase.api_key, "pageSize": "100"}
        try:
            response = requests.get(
                url, params=params, headers=headers, timeout=10
            )
            if response.status_code != 200:
                return {"success": False, "error": "Failed to fetch chats"}

            chats = []
            for document in response.json().get("documents", []):
                fields = document.get("fields", {})
                chat_id = document.get("name", "").rsplit("/", 1)[-1]
                user_a_uid = fields.get(
                    "participant_a_uid",
                    fields.get("user_a_uid", {}),
                ).get("stringValue", "")
                user_b_uid = fields.get(
                    "participant_b_uid",
                    fields.get("user_b_uid", {}),
                ).get("stringValue", "")
                if not user_a_uid or not user_b_uid:
                    prefix = f"{uid}_"
                    suffix = f"_{uid}"
                    if chat_id.startswith(prefix):
                        other_uid = chat_id[len(prefix):]
                        user_a_uid, user_b_uid = uid, other_uid
                    elif chat_id.endswith(suffix):
                        other_uid = chat_id[:-len(suffix)]
                        user_a_uid, user_b_uid = other_uid, uid

                username_a = fields.get("username_a", {}).get("stringValue", "")
                username_b = fields.get("username_b", {}).get("stringValue", "")
                is_user_a = user_a_uid == uid
                chats.append(
                    {
                        "chat_id": chat_id,
                        "user_a_uid": user_a_uid,
                        "user_b_uid": user_b_uid,
                        "target_uid": user_b_uid if is_user_a else user_a_uid,
                        "username_a": username_a,
                        "username_b": username_b,
                        "target_username": username_b if is_user_a else username_a,
                    }
                )
            return {"success": True, "chats": chats}
        except requests.RequestException as error:
            logger.error("Get user chats error: %s", error)
            return {"success": False, "error": str(error)}

    def upload_file_to_storage(
        self, chat_id: str, message_id: str, file_path: str, id_token: str
    ) -> dict:
        """Upload a file to Firebase Storage and return its storage path."""
        try:
            file_name = os.path.basename(file_path)
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > 35:
                return {
                    "success": False,
                    "error": (
                        f"File size ({file_size_mb:.2f} MB) exceeds "
                        "35 MB limit"
                    ),
                }
            storage_path = f"dm_media/{chat_id}/{message_id}/{file_name}"
            upload_url = "https://firebasestorage.googleapis.com/v0/b/devmeld.firebasestorage.app/o"
            params = {"uploadType": "media", "name": storage_path}
            headers = {
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/octet-stream",
            }
            with open(file_path, "rb") as file:
                file_data = file.read()

            logger.info("[DMAdapter] Attempting storage upload to: %s", upload_url)
            logger.info("[DMAdapter] Upload params: %s", params)
            response = requests.post(
                upload_url,
                params=params,
                data=file_data,
                headers=headers,
                timeout=60,
            )
            logger.info(
                "[DMAdapter] Storage upload response status: %s",
                response.status_code,
            )
            logger.info(
                "[DMAdapter] Storage upload response body: %s",
                response.text,
            )
            if response.status_code in (200, 201):
                return {"success": True, "storage_path": storage_path}
            return {
                "success": False,
                "error": (
                    f"Upload failed. Status: {response.status_code}, "
                    f"Details: {response.text}"
                ),
            }
        except Exception as error:
            logger.error("File upload error: %s", error)
            return {"success": False, "error": str(error)}

    def download_file_from_storage(
        self, storage_path: str, destination_path: str, id_token: str
    ) -> dict:
        """Download a Firebase Storage object to a local destination."""
        try:
            download_url = (
                "https://firebasestorage.googleapis.com/v0/b/"
                f"devmeld.firebasestorage.app/o/{quote(storage_path, safe='')}"
            )
            headers = {"Authorization": f"Bearer {id_token}"}
            response = requests.get(
                download_url,
                params={"alt": "media"},
                headers=headers,
                timeout=60,
                stream=True,
            )
            if response.status_code != 200:
                return {"success": False, "error": "Download failed"}

            os.makedirs(os.path.dirname(destination_path) or ".", exist_ok=True)
            with open(destination_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
            return {"success": True, "path": destination_path}
        except (OSError, requests.RequestException) as error:
            logger.error("File download error: %s", error)
            return {"success": False, "error": str(error)}

    def cleanup_read_notifications(self, user_uid: str, id_token: str) -> dict:
        """Delete read notification documents from the user's collection."""
        url = f"{self.firebase.firestore_url}/users/{user_uid}/notifications"
        headers = {"Authorization": f"Bearer {id_token}"}
        params = {"key": self.firebase.api_key, "pageSize": "100"}
        try:
            response = requests.get(
                url, params=params, headers=headers, timeout=10
            )
            if response.status_code != 200:
                return {"success": False, "error": "Failed to fetch notifications"}

            deleted_count = 0
            for document in response.json().get("documents", []):
                fields = document.get("fields", {})
                is_read = fields.get("is_read", {}).get("booleanValue", False)
                if not is_read:
                    continue
                notification_id = document.get("name", "").rsplit("/", 1)[-1]
                if not notification_id:
                    continue
                delete_url = (
                    f"{url}/{notification_id}?key={self.firebase.api_key}"
                )
                delete_response = requests.delete(
                    delete_url, headers=headers, timeout=5
                )
                if delete_response.status_code in (200, 204):
                    deleted_count += 1
            return {"success": True, "deleted_count": deleted_count}
        except requests.RequestException as error:
            logger.error("Cleanup notifications error: %s", error)
            return {"success": False, "error": str(error)}
