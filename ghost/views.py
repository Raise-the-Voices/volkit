"""/api/orgs/<org>/articles/...: the Ghost site's posts, for members of the org.
Unset keys or a Ghost error answer 404, and the card hides."""

import logging

from django.http import Http404
from django.urls import path
from rest_framework.response import Response
from rest_framework.views import APIView

from frame.models import Membership

from . import client

log = logging.getLogger(__name__)


def limit_of(request, default, most):
    try:
        return max(1, min(int(request.GET.get("limit", default)), most))
    except ValueError:
        return default


class MemberView(APIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not Membership.objects.filter(user=request.user, org__slug=kwargs["org"]).exists():
            log.warning("articles: %s refused org %s", request.user.pk, kwargs["org"])
            raise Http404

    def answer(self, fetch):
        try:
            posts = fetch()
        except Exception:
            log.exception("ghost read failed")
            raise Http404
        if posts is None:
            raise Http404
        return Response(posts)


class TeamArticles(MemberView):
    def get(self, request, org):
        return self.answer(lambda: client.team_posts(limit_of(request, 4, 4)))


class MyArticles(MemberView):
    def get(self, request, org):
        return self.answer(lambda: client.my_posts(request.user.email, limit_of(request, 5, 10)))


urls = [
    path("orgs/<slug:org>/articles/team/", TeamArticles.as_view()),
    path("orgs/<slug:org>/articles/mine/", MyArticles.as_view()),
]
