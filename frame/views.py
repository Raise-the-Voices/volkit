"""The frame's pages: the landing page, and each org's dashboards.

A dashboard is a file, dashboards/<name>.json: who sees it, and its cards in
default order. A card is either a template in this frame or a peer's custom
element. How each person arranges it is theirs (DashLayout)."""

import json
import re

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.shortcuts import redirect, render

from .models import Membership, Peer

TAG = re.compile(r"^[a-z][a-z0-9]*-[a-z0-9-]+$")
DASHBOARDS = settings.BASE_DIR / "dashboards"


def site(request):
    return {"site_name": settings.SITE_NAME}


def home(request):
    if not request.user.is_authenticated:
        return render(request, "frame/landing.html")
    orgs = list(Membership.objects.filter(user=request.user).select_related("org").order_by("org__name"))
    if len(orgs) == 1:
        return redirect("dashboard", org=orgs[0].org.slug)
    return render(request, "frame/landing.html", {"memberships": orgs})


def load_dashboard(name):
    path = DASHBOARDS / f"{name}.json"
    if not re.fullmatch(r"[a-z0-9-]+", name) or not path.is_file():
        raise Http404
    return json.loads(path.read_text())


def dashboard(request, org, dashboard="home"):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), "/auth/login/")
    membership = Membership.objects.filter(user=request.user, org__slug=org).select_related("org").first()
    spec = load_dashboard(dashboard)
    if membership is None or (spec.get("roles") and membership.role not in spec["roles"]):
        raise Http404
    peers = {p.slug: p for p in Peer.objects.all()}
    cards, scripts = [], []
    for c in spec.get("cards", []):
        card = {"id": c["id"], "w": int(c.get("w", 4)), "title": c.get("title", "")}
        if "template" in c:
            card["template"] = c["template"]
        else:
            peer = peers.get(c.get("peer"))
            if peer is None or not TAG.match(c.get("tag", "")):
                continue
            card.update(tag=c["tag"], peer=peer)
            if peer.embed_url and peer.embed_url not in scripts:
                scripts.append(peer.embed_url)
        cards.append(card)
    return render(request, "frame/dashboard.html", {
        "org": membership.org, "role": membership.role, "dashboard": dashboard,
        "title": spec.get("title", dashboard), "cards": cards, "scripts": scripts,
    })
