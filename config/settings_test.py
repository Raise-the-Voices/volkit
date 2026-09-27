"""Tests run on SQLite with fixed values, so they need no .env and no Postgres."""

import os

os.environ["RUNNING_TESTS"] = "1"

for key, value in {
    "SECRET_KEY": "test",
    "DATABASE_URL": "sqlite://:memory:",
    "OIDC_CLIENT_ID": "test",
    "OIDC_CLIENT_SECRET": "test",
    "EMBED_ORIGINS": "https://cards.example",
    "ALLOWED_HOSTS": "testserver,dashboard.example",
}.items():
    os.environ.setdefault(key, value)

from .settings import *  # noqa: E402,F403

STORAGES = {**STORAGES, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}  # noqa: F405
