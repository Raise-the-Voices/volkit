from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from dashboard.auth import EMAIL_VERIFIED

GHOST = {"VOLKIT_GHOST_URL": "https://ghost.example", "VOLKIT_GHOST_CONTENT_KEY": "k"}


@pytest.fixture
def person(db):
    return get_user_model().objects.create_user(username="v@example.com", email="v@example.com")


def verified(client):
    session = client.session
    session[EMAIL_VERIFIED] = True
    session.save()


def test_team_articles_off_when_ghost_unset(client, person):
    client.force_login(person)
    assert client.get("/api/articles/team/").status_code == 404


@override_settings(**GHOST)
def test_team_articles_for_anyone_signed_in(client, person):
    posts = [{"title": "A", "url": "https://ghost.example/a/", "published_at": "2026-09-01"}]
    with mock.patch("ghost.client._get", return_value={"posts": posts}) as get:
        assert client.get("/api/articles/team/").status_code in (401, 403)
        client.force_login(person)
        r = client.get("/api/articles/team/?limit=99")
    assert r.status_code == 200 and r.json() == posts
    assert get.call_args[0][1]["limit"] == 4


@override_settings(**GHOST)
def test_ghost_down_hides_the_card(client, person):
    from django.core.cache import cache
    cache.clear()
    with mock.patch("ghost.client._get", side_effect=OSError):
        client.force_login(person)
        assert client.get("/api/articles/team/").status_code == 404


@override_settings(VOLKIT_GHOST_URL="https://ghost.example", VOLKIT_GHOST_ADMIN_KEY="abc:" + "00" * 32)
def test_my_articles_are_the_persons_own(client, person):
    answers = [{"users": [{"slug": "vee"}]},
               {"posts": [{"id": "p1", "title": "Draft", "status": "draft", "updated_at": "2026-09-20"}]}]
    with mock.patch("ghost.client._get", side_effect=answers) as get:
        client.force_login(person)
        verified(client)
        r = client.get("/api/articles/mine/")
    assert r.json() == [{"title": "Draft", "status": "draft", "updated_at": "2026-09-20",
                         "edit_url": "https://ghost.example/ghost/#/editor/post/p1"}]
    assert get.call_args_list[0][0][1]["filter"] == "email:'v@example.com'"
    assert get.call_args_list[1][0][1]["filter"] == "authors:vee"


@override_settings(VOLKIT_GHOST_URL="https://ghost.example", VOLKIT_GHOST_ADMIN_KEY="abc:" + "00" * 32)
def test_my_articles_need_a_verified_email(client, person):
    with mock.patch("ghost.client._get") as get:
        client.force_login(person)
        assert client.get("/api/articles/mine/").status_code == 404
    get.assert_not_called()


def test_home_shows_volkit_cards_and_cases_only_when_set(client, person):
    client.force_login(person)
    page = client.get("/").content
    assert b"Open the cases app" not in page
    assert b"<volkit-team-articles" in page and b"embed/volkit" in page
    with override_settings(VOLKIT_CASES_URL="https://cases.example"):
        assert b'href="https://cases.example/"' in client.get("/").content


def test_seed_places_creates_once_and_never_overwrites(db, tmp_path):
    import json
    from django.core.management import call_command
    from dashboard.models import App, NavPlace
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps({"apps": [{"slug": "cases", "name": "Cases", "app_url": "https://cases.example/",
                                          "api_url": "https://cases.example/"}],
                                "nav": [{"label": "Tasks", "url": "https://tasks.example/"}]}))
    call_command("seed_places", str(seed))
    NavPlace.objects.filter(label="Tasks").update(url="https://changed.example/")
    call_command("seed_places", str(seed))
    assert list(NavPlace.objects.values_list("url", flat=True)) == ["https://changed.example/"]
    assert App.objects.count() == 1
