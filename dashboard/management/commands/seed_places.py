"""Create the apps and nav places listed in a JSON file, if missing.
Rows that exist are left alone: after the first deploy they are admin data."""

import json

from django.core.management.base import BaseCommand

from dashboard.models import App, NavPlace


class Command(BaseCommand):
    help = "Create missing apps and nav places from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, path, **options):
        data = json.loads(open(path).read())
        for a in data.get("apps", []):
            App.objects.get_or_create(slug=a["slug"], defaults={k: a.get(k, "") for k in ("name", "app_url", "api_url", "embed_url")})
        for i, n in enumerate(data.get("nav", [])):
            NavPlace.objects.get_or_create(label=n["label"], defaults={"url": n["url"], "order": i})
