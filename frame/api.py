"""The frame's JSON, under /api/. Org scope is checked here on every request; an
attribute on a page is never a permission (CONTRACT.md section 5)."""

import json
import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.urls import path
from django.views.decorators.http import require_GET
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import live
from .models import DashLayout, Identity, Membership, NavPlace
from .security import s2s_authorized

log = logging.getLogger(__name__)


def roles_of(user):
    """{org_slug: role} for a signed-in person."""
    return dict(Membership.objects.filter(user=user).values_list("org__slug", "role"))


class MeView(APIView):
    def get(self, request):
        u = request.user
        return Response({
            "name": u.get_full_name() or u.email,
            "email": u.email,
            "orgs": [
                {"slug": m.org.slug, "name": m.org.name, "role": m.role}
                for m in Membership.objects.filter(user=u).select_related("org").order_by("org__name")
            ],
        })


class LayoutView(APIView):
    """GET/PUT/DELETE the signed-in person's own arrangement of one dashboard."""

    MAX_BYTES = 32_000

    def get(self, request, dashboard):
        row = DashLayout.objects.filter(user=request.user, dashboard=dashboard).first()
        return Response({"layout": row.layout if row else {}})

    def put(self, request, dashboard):
        layout = request.data.get("layout") if isinstance(request.data, dict) else None
        if not isinstance(layout, dict) or len(json.dumps(layout)) > self.MAX_BYTES:
            return Response({"detail": "layout must be an object under 32 KB"}, status=400)
        DashLayout.objects.update_or_create(user=request.user, dashboard=dashboard, defaults={"layout": layout})
        return Response({"layout": layout})

    def delete(self, request, dashboard):
        DashLayout.objects.filter(user=request.user, dashboard=dashboard).delete()
        return Response({"layout": {}})


class NavView(APIView):
    """What <baobab-nav> shows this viewer."""

    permission_classes = [AllowAny]

    def get(self, request):
        u = request.user
        signed_in = u.is_authenticated
        held = set(roles_of(u).values()) if signed_in else set()
        places = []
        for p in NavPlace.objects.all():
            wanted = {r.strip() for r in p.roles.split(",") if r.strip()}
            if "public" in wanted or (signed_in and (not wanted or wanted & held)):
                places.append({"label": p.label, "url": request.build_absolute_uri(p.url)})
        return Response({
            "site": {"name": settings.SITE_NAME, "url": request.build_absolute_uri("/")},
            "places": places,
            "me": {"name": u.get_full_name() or u.email} if signed_in else None,
            "login_url": request.build_absolute_uri("/auth/login/"),
        })


class LogoutView(APIView):
    """Sign out of this frame. Called from <baobab-nav> on any page, with X-Baobab."""

    def post(self, request):
        logout(request)
        return Response(status=204)


@require_GET
def s2s_identity(request, provider, subject):
    """For roots: who this login is and which orgs they are in.

    Same path and answer as GovKit's (`govkit/apps/accounts/api.py`, s2s_identity), so a
    root works against either. `provider` is "linkedtrust" for OIDC_ISSUER. A stranger
    is 404; someone in no org is 200 with no memberships.
    """
    if not s2s_authorized(request):
        return JsonResponse({"error": "unauthorized"}, status=401)
    ident = None
    if provider == "linkedtrust":
        ident = Identity.objects.select_related("user").filter(issuer=settings.OIDC_ISSUER, sub=subject).first()
    if ident is None or not ident.user.is_active:
        return JsonResponse({"error": "not found"}, status=404)
    user = ident.user
    return JsonResponse({
        "display_name": user.get_full_name() or user.email,
        "email": user.email,
        "pool": False,
        "memberships": [
            {"org_slug": m.org.slug, "org_name": m.org.name, "role": m.role}
            for m in Membership.objects.filter(user=user).select_related("org").order_by("org__slug")
        ],
    })


async def live_view(request):
    """GET /api/live/?topics=<org>/<thing>,... as server-sent events."""
    if not settings.LIVE:
        return HttpResponse(status=404)
    user = await request.auser()
    topics = [t for t in request.GET.get("topics", "").split(",") if "/" in t]
    if not user.is_authenticated or not topics:
        return HttpResponse(status=403)
    held = await sync_to_async(roles_of)(user)
    if any(t.split("/", 1)[0] not in held for t in topics):
        log.warning("live: %s refused topics %s", user.pk, topics)
        return HttpResponse(status=403)
    response = StreamingHttpResponse(live.stream(set(topics)), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


urls = [
    path("me/", MeView.as_view()),
    path("me/layouts/<slug:dashboard>/", LayoutView.as_view()),
    path("nav/", NavView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("v1/accounts/s2s/identity/<slug:provider>/<path:subject>/", s2s_identity),
    path("live/", live_view),
]
