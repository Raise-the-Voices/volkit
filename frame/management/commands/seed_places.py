"""Create the orgs, peers and nav places listed in a JSON file, if missing.
Rows that exist are left alone: after the first deploy they are admin data."""

import json

from django.core.management.base import BaseCommand

from frame.models import NavPlace, Org, Peer


class Command(BaseCommand):
    help = "Create missing orgs, peers and nav places from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, path, **options):
        data = json.loads(open(path).read())
        for o in data.get("orgs", []):
            Org.objects.get_or_create(slug=o["slug"], defaults={"name": o["name"]})
        for p in data.get("peers", []):
            Peer.objects.get_or_create(slug=p["slug"], defaults={k: p[k] for k in ("name", "app_url", "api_url", "embed_url")})
        for i, n in enumerate(data.get("nav", [])):
            NavPlace.objects.get_or_create(label=n["label"], defaults={"url": n["url"], "order": i, "roles": n.get("roles", "")})
