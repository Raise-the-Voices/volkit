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
    layout = {"items": {"apps": {"x": 0, "y": 0, "w": 12}}, "hidden": []}
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
def test_s2s_identity_answers_like_govkit(client, member):
    Identity.objects.create(user=member, issuer="https://live.linkedtrust.us", sub="42")
    url = "/api/v1/accounts/s2s/identity/linkedtrust/42/"
    assert client.get(url).status_code == 401
    got = client.get(url, HTTP_AUTHORIZATION="Bearer t0k").json()
    assert got["memberships"] == [{"org_slug": "acme", "org_name": "Acme", "role": "member"}]
    assert client.get("/api/v1/accounts/s2s/identity/linkedtrust/99/",
                      HTTP_AUTHORIZATION="Bearer t0k").status_code == 404


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


def test_dashboard_cards_own_script_and_requires(client, member, settings, tmp_path, monkeypatch):
    import json

    from frame import views

    (tmp_path / "home.json").write_text(json.dumps({"title": "Volunteer Dashboard", "cards": [
        {"id": "mine", "w": 6, "title": "Mine", "tag": "acme-mine", "script": "embed/acme.js"},
        {"id": "cases", "w": 6, "title": "Cases", "template": "frame/cards/apps.html", "requires": "CASES_URL"},
    ]}))
    monkeypatch.setattr(views, "DASHBOARDS", tmp_path)
    client.force_login(member)
    body = client.get("/o/acme/").content.decode()
    assert "<h1 class=\"dash-title\">Volunteer Dashboard</h1>" in body
    assert '<acme-mine data-org="acme" data-up="http://testserver"></acme-mine>' in body
    assert "/static/embed/acme.js" in body
    assert 'data-card="cases"' not in body
    settings.CASES_URL = "https://cases.example"
    assert 'data-card="cases"' in client.get("/o/acme/").content.decode()


def test_library_cards_with_attributes_only_from_a_peer_origin(client, member, tmp_path, monkeypatch, caplog):
    import json

    from frame import views

    lib = "https://demos.linkedtrust.us/baobab/components/"
    (tmp_path / "home.json").write_text(json.dumps({"title": "Home", "cards": [
        {"id": "claims", "tag": "lt-claims", "script": lib + "lt-claims.js",
         "attrs": {"data-up": "https://live.linkedtrust.us", "data-query": "elmwood"}},
        {"id": "bad", "tag": "evil-card", "script": "https://evil.example/x.js"},
    ]}))
    monkeypatch.setattr(views, "DASHBOARDS", tmp_path)
    client.force_login(member)
    body = client.get("/o/acme/").content.decode()
    assert 'data-card="claims"' not in body
    assert "not a peer's origin" in caplog.text
    Peer.objects.create(slug="lib", name="Components", app_url=lib, api_url=lib, embed_url=lib + "lt-claims.js")
    body = client.get("/o/acme/").content.decode()
    assert '<lt-claims data-org="acme" data-query="elmwood" data-up="https://live.linkedtrust.us"></lt-claims>' in body
    assert lib + "lt-claims.js" in body
    assert "evil" not in body
