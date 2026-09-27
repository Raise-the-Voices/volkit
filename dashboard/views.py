"""The dashboard app's pages: the landing page and the dashboards.

A dashboard is a file, dashboards/<name>.json: its cards in default order. A card is a
template in this dashboard app, or a custom element: this dashboard app's own, an app's,
or one from a library on an app's origin. A card with
"requires" shows only while that setting is set. A card that cannot be shown is
left out and logged. How each person arranges it is theirs."""

import json
import logging
import re

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.shortcuts import render
from django.templatetags.static import static

from .models import App
from .security import origin

TAG = re.compile(r"^[a-z][a-z0-9]*-[a-z0-9-]+$")
ATTR = re.compile(r"^data-[a-z0-9-]+$")
log = logging.getLogger(__name__)
DASHBOARDS = settings.BASE_DIR / "dashboards"


def site(request):
    return {"site_name": settings.SITE_NAME}


def home(request):
    if not request.user.is_authenticated:
        return render(request, "dashboard/landing.html")
    return dashboard(request)


def load_dashboard(name):
    path = DASHBOARDS / f"{name}.json"
    if not re.fullmatch(r"[a-z0-9-]+", name) or not path.is_file():
        raise Http404
    return json.loads(path.read_text())


def build_card(c, apps, allowed):
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
    if "app" in c:
        app = apps.get(c["app"])
        if app is None:
            return None, f"no app {c['app']!r} (add it under Apps in the admin)"
        card.update(app=app, script=app.embed_url or None)
    elif "script" in c:
        if "://" in c["script"]:
            if origin(c["script"]) not in allowed:
                return None, f"{origin(c['script'])} is not an app's origin (add it under Apps)"
            card["script"] = c["script"]
        else:
            card.update(own=True, script=static(c["script"]))
    else:
        return None, "needs template, app, or script"
    return card, None


def dashboard(request, dashboard="home"):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), "/auth/login/")
    spec = load_dashboard(dashboard)
    apps = {a.slug: a for a in App.objects.order_by("name")}
    allowed = {origin(a.embed_url) for a in apps.values() if a.embed_url}
    cards, scripts = [], []
    for c in spec.get("cards", []):
        if c.get("requires") and not getattr(settings, c["requires"], None):
            continue
        card, problem = build_card(c, apps, allowed)
        if problem:
            log.warning("dashboard %s: card %r left out: %s", dashboard, c.get("id"), problem)
            continue
        if card.get("script") and card["script"] not in scripts:
            scripts.append(card["script"])
        cards.append(card)
    return render(request, "dashboard/dashboard.html", {
        "dashboard": dashboard, "title": spec.get("title", dashboard),
        "cards": cards, "scripts": scripts, "apps": list(apps.values()),
    })
