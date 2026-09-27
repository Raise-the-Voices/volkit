"""/api/articles/...: the Ghost site's posts, for anyone signed in.
Unset keys or a Ghost error answer 404, and the card hides."""

import logging

from django.http import Http404
from django.urls import path
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.auth import EMAIL_VERIFIED

from . import client

log = logging.getLogger(__name__)


def limit_of(request, default, most):
    try:
        return max(1, min(int(request.GET.get("limit", default)), most))
    except ValueError:
        return default


def answer(fetch):
    try:
        posts = fetch()
    except Exception:
        log.exception("ghost read failed")
        raise Http404
    if posts is None:
        raise Http404
    return Response(posts)


class TeamArticles(APIView):
    def get(self, request):
        return answer(lambda: client.team_posts(limit_of(request, 4, 4)))


class MyArticles(APIView):
    """Drafts are matched to a Ghost author by email, so only a verified email counts."""

    def get(self, request):
        if not request.session.get(EMAIL_VERIFIED):
            log.warning("articles/mine: %s refused, email not verified at sign-in", request.user.pk)
            raise Http404
        return answer(lambda: client.my_posts(request.user.email, limit_of(request, 5, 10)))


urls = [
    path("articles/team/", TeamArticles.as_view()),
    path("articles/mine/", MyArticles.as_view()),
]
