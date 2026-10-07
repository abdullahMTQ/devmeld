# Domain: image, Purpose: url_normalization, Layer: adapter
from urllib.parse import quote, unquote, urlsplit, urlunsplit

def normalize_image_url(url: str, storage_bucket: str) -> str:
    storage_base = f"https://firebasestorage.googleapis.com/v0/b/{storage_bucket}/o"
    if url.startswith("gs://"):
        parts = url[len("gs://"):].split("/", 1)
        path = parts[1] if len(parts) == 2 else ""
        return f"{storage_base}/{quote(path, safe='')}"
    if not url.startswith(("http://", "https://")):
        return f"{storage_base}/{quote(url, safe='')}"
    if "firebasestorage.googleapis.com" in url and "/o/" in url:
        scheme, netloc, path, query, fragment = urlsplit(url)
        prefix, _, object_part = path.partition("/o/")
        object_part = quote(unquote(object_part), safe="")
        new_path = f"{prefix}/o/{object_part}"
        if not query:
            query = "alt=media"
        elif "alt=media" not in query:
            query = f"{query}&alt=media"
        return urlunsplit((scheme, netloc, new_path, query, fragment))
    return url
