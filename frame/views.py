"""The frame's pages: the landing page, and each org's dashboards.

A dashboard is a file, dashboards/<name>.json: who sees it, and its cards in
default order. A card is a template in this frame, or a custom element: this
frame's own, a peer's, or one from a library on a peer's origin. A card with
"requires" shows only while that setting is set. A card that cannot be shown is
left out and logged. How each person arranges it is theirs."""

import json
import logging
import re

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.shortcuts import redirect, render
from django.templatetags.static import static

from .models import Membership, Peer
from .security import origin

TAG = re.compile(r"^[a-z][a-z0-9]*-[a-z0-9-]+$")
ATTR = re.compile(r"^data-[a-z0-9-]+$")
log = logging.getLogger(__name__)
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


def build_card(c, peers, allowed):
    """One card from a dashboard file, or the reason it cannot be shown."""
    card = {"id": c.get("id"), "w": int(c.get("w", 4)), "title": c.get("title", "")}
    if not card["id"]:
        return None, "no id"
    if "template" in c:
        card["template"] = c["template"]
        return card, None
    if not TAG.match(c.get("tag", "")):
        return None, f"tag {c.get('tag')!r} is not a custom element name"
    attrs = c.get("attrs", {})
    if not all(ATTR.match(k) and isinstance(v, str) for k, v in attrs.items()):
        return None, "attrs must be data-* names with string values"
    card.update(tag=c["tag"], attrs=attrs)
    if "peer" in c:
        peer = peers.get(c["peer"])
        if peer is None:
            return None, f"no peer {c['peer']!r} (add it under Peers in the admin)"
        card.update(peer=peer, script=peer.embed_url or None)
    elif "script" in c:
        if "://" in c["script"]:
            if origin(c["script"]) not in allowed:
                return None, f"{origin(c['script'])} is not a peer's origin (add it under Peers)"
            card["script"] = c["script"]
        else:
            card.update(own=True, script=static(c["script"]))
    else:
        return None, "needs template, peer, or script"
    return card, None


def dashboard(request, org, dashboard="home"):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), "/auth/login/")
    membership = Membership.objects.filter(user=request.user, org__slug=org).select_related("org").first()
    spec = load_dashboard(dashboard)
    if membership is None or (spec.get("roles") and membership.role not in spec["roles"]):
        raise Http404
    peers = {p.slug: p for p in Peer.objects.order_by("name")}
    allowed = {origin(p.embed_url) for p in peers.values() if p.embed_url}
    cards, scripts = [], []
    for c in spec.get("cards", []):
        if c.get("requires") and not getattr(settings, c["requires"], None):
            continue
        card, problem = build_card(c, peers, allowed)
        if problem:
            log.warning("dashboard %s: card %r left out: %s", dashboard, c.get("id"), problem)
            continue
        if card.get("script") and card["script"] not in scripts:
            scripts.append(card["script"])
        cards.append(card)
    return render(request, "frame/dashboard.html", {
        "org": membership.org, "role": membership.role, "dashboard": dashboard,
        "title": spec.get("title", dashboard), "cards": cards, "scripts": scripts,
        "apps": list(peers.values()),
    })
