"""The frame's data: who people are, which orgs they are in, which pieces it shows,
its nav, and how each person arranged each dashboard. Nothing else lives here
(CONTRACT.md section 8)."""

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


class Org(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Role(models.TextChoices):
    ADMIN = "admin"
    MEMBER = "member"


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "org"], name="uniq_membership")]

    def __str__(self):
        return f"{self.user} in {self.org} ({self.role})"


class Peer(models.Model):
    """A frond or root this frame shows. Its embed_url is the only script source a
    dashboard loads besides the frame's own (CONTRACT.md section 5)."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    app_url = models.URLField(help_text="Where a card's expand link goes.")
    api_url = models.URLField(help_text="Handed to its cards as data-up.")
    embed_url = models.URLField(blank=True, help_text="Its cards file, e.g. https://planner.example/embed/planner.js")

    def __str__(self):
        return self.name


class NavPlace(models.Model):
    label = models.CharField(max_length=60)
    url = models.CharField(max_length=500, help_text="Absolute, or a path on this frame.")
    order = models.PositiveSmallIntegerField(default=0)
    roles = models.CharField(
        max_length=200, blank=True,
        help_text="Who sees it: empty = anyone signed in; 'public' = everyone; "
                  "else roles, comma-separated (admin, member).",
    )

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
