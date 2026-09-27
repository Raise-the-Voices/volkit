import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from frame.auth import person_for, safe_next
from frame.models import DashLayout, Identity, Membership, NavPlace, Org, Peer

EMBED = {"HTTP_X_BAOBAB": "1"}


@pytest.fixture
def org(db):
    return Org.objects.create(slug="acme", name="Acme")


@pytest.fixture
def member(db, org):
    user = get_user_model().objects.create_user(username="a@example.com", email="a@example.com")
    Membership.objects.create(user=user, org=org, role="member")
    return user


@pytest.fixture
def stranger(db):
    return get_user_model().objects.create_user(username="s@example.com", email="s@example.com")


def test_layout_is_the_persons_own(client, member, stranger):
    url = "/api/me/layouts/home/"
    client.force_login(member)
    assert client.get(url).json() == {"layout": {}}
    layout = {"items": {"welcome": {"x": 0, "y": 0, "w": 12}}, "hidden": []}
    assert client.put(url, {"layout": layout}, content_type="application/json", **EMBED).status_code == 200
    assert client.get(url).json() == {"layout": layout}
    client.force_login(stranger)
    assert client.get(url).json() == {"layout": {}}
    client.force_login(member)
    client.delete(url, **EMBED)
    assert not DashLayout.objects.exists()


def test_cross_origin_write_without_the_header_is_refused(member):
    from django.test import Client

    c = Client(enforce_csrf_checks=True)
    c.force_login(member)
    r = c.put("/api/me/layouts/home/", {"layout": {}}, content_type="application/json")
    assert r.status_code == 403


def test_signed_out_is_told_to_sign_in(client, db):
    assert client.get("/api/me/layouts/home/").status_code == 401


def test_nav_shows_each_person_their_places(client, member, db):
    NavPlace.objects.create(label="About", url="/about/", roles="public")
    NavPlace.objects.create(label="Dash", url="/o/acme/")
    NavPlace.objects.create(label="Admin", url="/admin/", roles="admin")
    labels = lambda: [p["label"] for p in client.get("/api/nav/").json()["places"]]  # noqa: E731
    assert labels() == ["About"]
    client.force_login(member)
    assert labels() == ["About", "Dash"]


def test_dashboard_is_for_members_only(client, member, stranger):
    client.force_login(member)
    assert client.get("/o/acme/").status_code == 200
    client.force_login(stranger)
    assert client.get("/o/acme/").status_code == 404


def test_dashboard_loads_scripts_only_from_peers(client, member):
    Peer.objects.create(slug="planner", name="Planner", app_url="https://planner.example/",
                        api_url="https://api.planner.example", embed_url="https://planner.example/embed/planner.js")
    client.force_login(member)
    csp = client.get("/o/acme/")["Content-Security-Policy"]
    assert csp == "script-src 'self' https://planner.example"


@override_settings(S2S_TOKEN="t0k")
def test_s2s_membership(client, member):
    Identity.objects.create(user=member, issuer="https://live.linkedtrust.us", sub="42")
    url = "/api/s2s/membership/?sub=42&org=acme"
    assert client.get(url).status_code == 403
    assert client.get(url, HTTP_AUTHORIZATION="Bearer t0k").json() == {"member": True, "role": "member"}
    assert client.get("/api/s2s/membership/?sub=42&org=other",
                      HTTP_AUTHORIZATION="Bearer t0k").json() == {"member": False, "role": None}
    assert client.get("/api/s2s/orgs/?sub=42", HTTP_AUTHORIZATION="Bearer t0k").json() == {
        "orgs": [{"slug": "acme", "name": "Acme", "role": "member"}]}


@override_settings(LIVE=True)
def test_live_refuses_topics_outside_your_orgs(client, member):
    client.force_login(member)
    assert client.get("/api/live/?topics=other/items").status_code == 403


def test_sign_in_links_by_verified_email_then_by_id(member):
    assert person_for({"sub": "7", "email": "A@example.com", "email_verified": True}) == member
    assert person_for({"sub": "7", "email": "changed@example.com"}) == member
    new = person_for({"sub": "8", "email": "b@example.com"})
    assert new != member and not new.has_usable_password()


def test_an_unverified_email_never_takes_over_an_account(member):
    other = person_for({"sub": "9", "email": "a@example.com"})
    assert other != member


def test_an_account_already_linked_is_not_linked_again(member):
    person_for({"sub": "7", "email": "a@example.com", "email_verified": True})
    second = person_for({"sub": "10", "email": "a@example.com", "email_verified": True})
    assert second != member and second.username != member.username


@override_settings(EMBED_ORIGINS=["https://planner.example"])
def test_after_sign_in_only_known_places(rf):
    req = rf.get("/", HTTP_HOST="frame.example")
    assert safe_next(req, "/o/acme/") == "/o/acme/"
    assert safe_next(req, "https://planner.example/items") == "https://planner.example/items"
    assert safe_next(req, "https://evil.example/") == "/"


def test_sign_out_from_the_nav(client, member):
    client.force_login(member)
    assert client.get("/api/nav/").json()["me"]
    assert client.post("/api/logout/", **EMBED).status_code == 204
    assert client.get("/api/nav/").json()["me"] is None
