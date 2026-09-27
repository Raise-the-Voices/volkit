"""The dashboard app's JSON, under /api/: the nav, sign-out, and each person's own
arrangement of a dashboard."""

import json

from django.conf import settings
from django.contrib.auth import logout
from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DashLayout, NavPlace


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
    """What <site-nav> shows: the places, and who is signed in."""

    permission_classes = [AllowAny]

    def get(self, request):
        u = request.user
        signed_in = u.is_authenticated
        return Response({
            "site": {"name": settings.SITE_NAME, "url": request.build_absolute_uri("/")},
            "places": [{"label": p.label, "url": request.build_absolute_uri(p.url)}
                       for p in NavPlace.objects.all()] if signed_in else [],
            "me": {"name": u.get_full_name() or u.email} if signed_in else None,
            "login_url": request.build_absolute_uri("/auth/login/"),
        })


class LogoutView(APIView):
    """Sign out of this dashboard app, from <site-nav> on any page, with X-Embed."""

    def post(self, request):
        logout(request)
        return Response(status=204)


urls = [
    path("nav/", NavView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/layouts/<slug:dashboard>/", LayoutView.as_view()),
]
