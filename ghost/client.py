"""Reads the Ghost site (a vine: Ghost stays the record, nothing is copied).

Content API for published posts, Admin API for a person's own drafts. Both are
off when their key is unset. Keys and URL are VOLKIT_GHOST_* settings."""

import json
import time
import urllib.parse
import urllib.request

import jwt
from django.conf import settings
from django.core.cache import cache

TIMEOUT = 5
TEAM_CACHE_SECONDS = 300  # published posts change rarely; drafts are never cached


def _get(path, params, headers=None):
    url = f"{settings.VOLKIT_GHOST_URL}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept-Version": "v6.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def team_posts(limit):
    """The newest published posts: [{title, url, published_at}]."""
    if not (settings.VOLKIT_GHOST_URL and settings.VOLKIT_GHOST_CONTENT_KEY):
        return None
    key = f"volkit:ghost:team:{limit}"
    posts = cache.get(key)
    if posts is None:
        data = _get("/ghost/api/content/posts/", {
            "key": settings.VOLKIT_GHOST_CONTENT_KEY, "limit": limit,
            "fields": "title,url,published_at", "order": "published_at desc",
        })
        posts = [{"title": p["title"], "url": p["url"], "published_at": p["published_at"]}
                 for p in data.get("posts", [])]
        cache.set(key, posts, TEAM_CACHE_SECONDS)
    return posts


def _admin_token():
    kid, secret = settings.VOLKIT_GHOST_ADMIN_KEY.split(":", 1)
    now = int(time.time())
    return jwt.encode({"iat": now, "exp": now + 300, "aud": "/admin/"},
                      bytes.fromhex(secret), algorithm="HS256", headers={"kid": kid})


def my_posts(email, limit):
    """Posts (any status) whose author is the Ghost staff user with this email:
    [{title, status, edit_url, updated_at}]. None when the Admin API is off."""
    if not (settings.VOLKIT_GHOST_URL and settings.VOLKIT_GHOST_ADMIN_KEY) or not email:
        return None
    auth = {"Authorization": f"Ghost {_admin_token()}"}
    users = _get("/ghost/api/admin/users/", {"filter": f"email:'{email}'", "fields": "slug"}, auth)
    if not users.get("users"):
        return []
    slug = users["users"][0]["slug"]
    data = _get("/ghost/api/admin/posts/", {
        "filter": f"authors:{slug}", "limit": limit,
        "fields": "id,title,status,updated_at", "order": "updated_at desc",
    }, auth)
    return [{
        "title": p["title"], "status": p["status"], "updated_at": p["updated_at"],
        "edit_url": f"{settings.VOLKIT_GHOST_URL}/ghost/#/editor/post/{p['id']}",
    } for p in data.get("posts", [])]
