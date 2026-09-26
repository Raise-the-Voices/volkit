from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from frame.models import Membership, Org, Peer

GHOST = {"VOLKIT_GHOST_URL": "https://ghost.example", "VOLKIT_GHOST_CONTENT_KEY": "k"}


@pytest.fixture
def member(db):
    org = Org.objects.create(slug="rtv", name="Raise the Voices")
    user = get_user_model().objects.create_user(username="v@example.com", email="v@example.com")
    Membership.objects.create(user=user, org=org, role="member")
    return user


@pytest.fixture
def stranger(db):
    return get_user_model().objects.create_user(username="s@example.com", email="s@example.com")


def test_team_articles_off_when_ghost_unset(client, member):
    client.force_login(member)
    assert client.get("/api/orgs/rtv/articles/team/").status_code == 404


@override_settings(**GHOST)
def test_team_articles_for_members_only(client, member, stranger):
    posts = [{"title": "A", "url": "https://ghost.example/a/", "published_at": "2026-09-01"}]
    with mock.patch("ghost.client._get", return_value={"posts": posts}) as get:
        client.force_login(member)
        r = client.get("/api/orgs/rtv/articles/team/?limit=99")
        assert r.status_code == 200 and r.json() == posts
        assert get.call_args[0][1]["limit"] == 4
        client.force_login(stranger)
        assert client.get("/api/orgs/rtv/articles/team/").status_code == 404


@override_settings(**GHOST)
def test_ghost_down_hides_the_card(client, member):
    from django.core.cache import cache
    cache.clear()
    with mock.patch("ghost.client._get", side_effect=OSError):
        client.force_login(member)
        assert client.get("/api/orgs/rtv/articles/team/").status_code == 404


@override_settings(VOLKIT_GHOST_URL="https://ghost.example", VOLKIT_GHOST_ADMIN_KEY="abc:" + "00" * 32)
def test_my_articles_are_the_persons_own(client, member):
    answers = [{"users": [{"slug": "vee"}]},
               {"posts": [{"id": "p1", "title": "Draft", "status": "draft", "updated_at": "2026-09-20"}]}]
    with mock.patch("ghost.client._get", side_effect=answers) as get:
        client.force_login(member)
        r = client.get("/api/orgs/rtv/articles/mine/")
    assert r.json() == [{"title": "Draft", "status": "draft", "updated_at": "2026-09-20",
                         "edit_url": "https://ghost.example/ghost/#/editor/post/p1"}]
    assert get.call_args_list[0][0][1]["filter"] == "email:'v@example.com'"
    assert get.call_args_list[1][0][1]["filter"] == "authors:vee"


def test_cases_card_only_when_cases_url_set(client, member):
    Peer.objects.create(slug="volkit", name="VolKit", app_url="https://v.example",
                        api_url="https://v.example", embed_url="https://v.example/static/embed/volkit.js")
    client.force_login(member)
    assert b"Open the cases app" not in client.get("/o/rtv/").content
    with override_settings(VOLKIT_CASES_URL="https://cases.example"):
        page = client.get("/o/rtv/").content
    assert b'href="https://cases.example/"' in page
    assert b"<volkit-team-articles" in page
