import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings

from dashboard import views
from dashboard.auth import person_for, safe_next
from dashboard.models import App, DashLayout, NavPlace

EMBED = {"HTTP_X_EMBED": "1", "HTTP_ORIGIN": "https://cards.example"}
LIB = "https://demos.linkedtrust.us/baobab/components/"


@pytest.fixture
def person(db):
    return get_user_model().objects.create_user(username="a@example.com", email="a@example.com")


@pytest.fixture
def other(db):
    return get_user_model().objects.create_user(username="s@example.com", email="s@example.com")


def test_layout_is_the_persons_own(client, person, other):
    url = "/api/me/layouts/home/"
    client.force_login(person)
    assert client.get(url).json() == {"layout": {}}
    layout = {"items": {"apps": {"x": 0, "y": 0, "w": 12}}, "hidden": []}
    assert client.put(url, {"layout": layout}, content_type="application/json", **EMBED).status_code == 200
    assert client.get(url).json() == {"layout": layout}
    client.force_login(other)
    assert client.get(url).json() == {"layout": {}}
    client.force_login(person)
    client.delete(url, **EMBED)
    assert not DashLayout.objects.exists()


def test_cross_origin_write_without_the_header_is_refused(person):
    c = Client(enforce_csrf_checks=True)
    c.force_login(person)
    assert c.put("/api/me/layouts/home/", {"layout": {}}, content_type="application/json").status_code == 403


def test_write_with_the_header_from_an_unlisted_origin_is_refused(person):
    c = Client(enforce_csrf_checks=True)
    c.force_login(person)
    r = c.put("/api/me/layouts/home/", {"layout": {}}, content_type="application/json",
              HTTP_X_EMBED="1", HTTP_ORIGIN="https://elsewhere.example")
    assert r.status_code == 403


def test_signed_out_is_told_to_sign_in(client, db):
    assert client.get("/api/me/layouts/home/").status_code == 401
    assert "/auth/login/" in client.get("/").content.decode()
    assert client.get("/d/home/")["Location"].startswith("/auth/login/")


def test_signed_in_lands_on_the_home_dashboard(client, person):
    client.force_login(person)
    body = client.get("/").content.decode()
    assert '<h1 class="dash-title">Volunteer Dashboard</h1>' in body
    assert "<site-nav" in body


def test_dashboard_loads_scripts_only_from_apps(client, person):
    App.objects.create(slug="crm", name="CRM", app_url="https://crm.example/",
                       api_url="https://crm.example", embed_url="https://crm.example/embed/crm.js")
    client.force_login(person)
    assert client.get("/")["Content-Security-Policy"] == "script-src 'self' https://crm.example"


def test_sign_in_links_by_verified_email_then_by_id(person):
    assert person_for({"sub": "7", "email": "A@example.com", "email_verified": True}) == person
    assert person_for({"sub": "7", "email": "changed@example.com"}) == person
    new = person_for({"sub": "8", "email": "b@example.com"})
    assert new != person and not new.has_usable_password()


def test_an_unverified_email_never_takes_over_an_account(person):
    assert person_for({"sub": "9", "email": "a@example.com"}) != person


def test_an_account_already_linked_is_not_linked_again(person):
    person_for({"sub": "7", "email": "a@example.com", "email_verified": True})
    second = person_for({"sub": "10", "email": "a@example.com", "email_verified": True})
    assert second != person and second.username != person.username


@override_settings(EMBED_ORIGINS=["https://crm.example"])
def test_after_sign_in_only_known_places(rf):
    req = rf.get("/", HTTP_HOST="dashboard.example")
    assert safe_next(req, "/d/home/") == "/d/home/"
    assert safe_next(req, "https://crm.example/items") == "https://crm.example/items"
    assert safe_next(req, "https://evil.example/") == "/"


def test_nav_places_for_anyone_signed_in(client, person):
    NavPlace.objects.create(label="Tasks", url="https://tasks.example/")
    NavPlace.objects.create(label="Home", url="/", order=0)
    assert client.get("/api/nav/").json()["places"] == []
    client.force_login(person)
    got = client.get("/api/nav/").json()
    assert [p["label"] for p in got["places"]] == ["Tasks", "Home"]
    assert got["places"][0]["url"] == "https://tasks.example/"


def test_sign_out_from_the_nav(client, person):
    client.force_login(person)
    assert client.get("/api/nav/").json()["me"]
    assert client.post("/api/logout/", **EMBED).status_code == 204
    assert client.get("/api/nav/").json()["me"] is None


def test_cards_from_apps_own_scripts_and_requires(client, person, settings, tmp_path, monkeypatch):
    App.objects.create(slug="crm", name="CRM", app_url="https://crm.example/",
                       api_url="https://crm.example", embed_url="https://crm.example/embed/crm.js")
    (tmp_path / "home.json").write_text(json.dumps({"title": "Volunteer Dashboard", "cards": [
        {"id": "people", "w": 6, "title": "People", "app": "crm", "tag": "crm-people"},
        {"id": "mine", "w": 6, "title": "Mine", "tag": "acme-mine", "script": "embed/acme.js"},
        {"id": "cases", "w": 6, "title": "Cases", "template": "dashboard/cards/apps.html", "requires": "CASES_URL"},
    ]}))
    monkeypatch.setattr(views, "DASHBOARDS", tmp_path)
    client.force_login(person)
    body = client.get("/").content.decode()
    assert '<h1 class="dash-title">Volunteer Dashboard</h1>' in body
    assert '<crm-people data-app="https://crm.example/" data-up="https://crm.example"></crm-people>' in body
    assert '<acme-mine data-up="http://testserver"></acme-mine>' in body
    assert "/static/embed/acme.js" in body and "https://crm.example/embed/crm.js" in body
    assert 'data-card="cases"' not in body
    settings.CASES_URL = "https://cases.example"
    assert 'data-card="cases"' in client.get("/").content.decode()


def test_library_cards_only_from_an_app_origin(client, person, tmp_path, monkeypatch, caplog):
    (tmp_path / "home.json").write_text(json.dumps({"title": "Home", "cards": [
        {"id": "claims", "tag": "lt-claims", "script": LIB + "lt-claims.js",
         "attrs": {"data-up": "https://live.linkedtrust.us", "data-query": "elmwood"}},
        {"id": "bad", "tag": "evil-card", "script": "https://evil.example/x.js"},
    ]}))
    monkeypatch.setattr(views, "DASHBOARDS", tmp_path)
    client.force_login(person)
    assert 'data-card="claims"' not in client.get("/").content.decode()
    assert "not an app's origin" in caplog.text
    App.objects.create(slug="lib", name="Components", app_url=LIB, api_url=LIB, embed_url=LIB + "lt-claims.js")
    body = client.get("/").content.decode()
    assert '<lt-claims data-query="elmwood" data-up="https://live.linkedtrust.us"></lt-claims>' in body
    assert "evil" not in body
