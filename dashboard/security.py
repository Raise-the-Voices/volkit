"""The checks between pieces (CONTRACT.md section 5)."""

import logging

from django.conf import settings
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied

from .models import App


class EmbedSessionAuthentication(SessionAuthentication):
    """Session auth that also accepts writes from cards on other origins.

    A card on another site cannot read this host's CSRF token. It sends
    `X-Embed: 1` instead: browsers send a custom header cross-origin only after a
    CORS preflight, which only EMBED_ORIGINS pass. A forged form can do neither.
    """

    def authenticate_header(self, request):
        # Signed out answers 401 (not 403), so a web component knows the person is not signed in.
        return 'Session realm="api"'

    def enforce_csrf(self, request):
        if request.headers.get("X-Embed") == "1":
            sent = request.headers.get("Origin", "")
            if sent in settings.EMBED_ORIGINS or sent == f"{request.scheme}://{request.get_host()}":
                return
            logging.getLogger(__name__).warning("refused: write from origin %r, %s %s", sent, request.method, request.path)
            raise PermissionDenied("origin not allowed")
        return super().enforce_csrf(request)


class ScriptPolicyMiddleware:
    """Pages load scripts from this dashboard app and from its apps' web components files only.
    A script on a dashboard runs as the viewer, so the list of apps is the trust boundary."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.get("Content-Type", "").startswith("text/html") and not request.path.startswith("/admin/"):
            origins = sorted({origin(p.embed_url) for p in App.objects.exclude(embed_url="")})
            response["Content-Security-Policy"] = "script-src 'self' " + " ".join(origins)
        return response


def origin(url):
    scheme, _, rest = url.partition("://")
    return f"{scheme}://{rest.split('/', 1)[0]}"
