"""The dashboard app's data: sign-in ids, which apps' web components it shows, the nav, and how
each person arranged each dashboard. Nothing else lives here (CONTRACT.md section 8).
Who may see what is decided by each app's own backend, never here."""

from django.conf import settings
from django.db import models


class Identity(models.Model):
    """The sign-in provider's stable id for a person (the OIDC `sub`)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="identities")
    issuer = models.URLField()
    sub = models.CharField(max_length=255)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["issuer", "sub"], name="uniq_identity")]

    def __str__(self):
        return f"{self.user} @ {self.issuer}"


class App(models.Model):
    """An app whose web components this dashboard shows. Its embed_url is the only script
    source a dashboard loads besides this app's own (CONTRACT.md section 5)."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    app_url = models.URLField(help_text="Where the Apps card and a web component's link go.")
    api_url = models.URLField(help_text="Handed to its web components as data-up.")
    embed_url = models.URLField(blank=True, help_text="Its web components file, e.g. https://crm.example/embed/crm.js")

    def __str__(self):
        return self.name


class NavPlace(models.Model):
    """One place in the nav bar: this dashboard, another app, an existing system."""

    label = models.CharField(max_length=60)
    url = models.CharField(max_length=500, help_text="Absolute, or a path on this dashboard app.")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.label


class DashLayout(models.Model):
    """How one person arranged one dashboard. Only they change it."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dash_layouts")
    dashboard = models.SlugField(max_length=64)
    layout = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "dashboard"], name="uniq_dash_layout")]
