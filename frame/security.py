"""The checks between pieces (CONTRACT.md section 5)."""

import secrets

from django.conf import settings
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied

from .models import Peer


class EmbedSessionAuthentication(SessionAuthentication):
    """Session auth that also accepts writes from cards on other origins.

    A card on another site cannot read this host's CSRF token. It sends
    `X-Baobab: 1` instead: browsers send a custom header cross-origin only after a
    CORS preflight, which only EMBED_ORIGINS pass. A forged form can do neither.
    """

    def authenticate_header(self, request):
        # Signed out answers 401 (not 403), so a frond knows to send the person to sign in.
        return 'Session realm="api"'

    def enforce_csrf(self, request):
        if request.headers.get("X-Baobab") == "1":
            return
        return super().enforce_csrf(request)


def s2s_authorized(request):
    """A server holding S2S_TOKEN (a root). Unset token: always refused."""
    expected = settings.S2S_TOKEN
    supplied = request.headers.get("Authorization", "")
    return bool(expected) and secrets.compare_digest(supplied, f"Bearer {expected}")


class ScriptPolicyMiddleware:
    """Pages load scripts from this frame and from its peers' cards files only.
    A card script runs as the viewer, so the peer list is the trust boundary."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.get("Content-Type", "").startswith("text/html") and not request.path.startswith("/admin/"):
            origins = sorted({origin(p.embed_url) for p in Peer.objects.exclude(embed_url="")})
            response["Content-Security-Policy"] = "script-src 'self' " + " ".join(origins)
        return response


def origin(url):
    scheme, _, rest = url.partition("://")
    return f"{scheme}://{rest.split('/', 1)[0]}"
