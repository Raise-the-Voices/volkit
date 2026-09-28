# VolKit

The Raise the Voices volunteer dashboard: one page, what is next for me.

| Card | Reads | Off when |
|---|---|---|
| From the team: a little help? | newest 4 published posts, Ghost Content API | `VOLKIT_GHOST_URL` or `VOLKIT_GHOST_CONTENT_KEY` unset |
| My articles | the person's own posts incl. drafts, Ghost Admin API, matched by email; only when the sign-in said the email is verified | `VOLKIT_GHOST_ADMIN_KEY` unset |
| My cases | link to the cases app (its own sign-in for now) | `VOLKIT_CASES_URL` unset |

Not built yet: To do next (Taiga), Upcoming events (Mobilize and Google Calendar, push and
pull), Learning, My impact (no source of record chosen).

Deploy: `deploy/ansible/` (see the playbook header and `example-vars.yml`).

A dashboard app: where people land. Sign-in, a nav bar, and dashboards of web components
from other apps, each person arranging their own. Made from [Cooperation-org/baobab](https://github.com/Cooperation-org/baobab); its rules are
[CONTRACT.md](https://github.com/Cooperation-org/baobab/blob/main/CONTRACT.md).

## Run it

```
uv venv && uv pip install -r requirements.txt
cp .env.example .env          # then fill in DATABASE_URL and the OIDC client
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver 8000
.venv/bin/pytest
```

Production: `gunicorn config.wsgi:application`, after `manage.py collectstatic`.
Locally without an OIDC client: sign in at `/admin/` as the superuser, then open `/`.

## Sign-in (LinkedTrust)

1. Register a client, one per app. The LinkedTrust admin runs, in `trust_claim_backend`:
   ```
   npx ts-node scripts/register-oidc-client.ts --name "VolKit" \
     --redirect https://<this app's host>/auth/linkedtrust/callback
   ```
   Add a second `--redirect` for `http://localhost:8000/auth/linkedtrust/callback` to sign in locally.
2. Put the printed `client_id` and `client_secret` (shown once) in `.env` as
   `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET`.

Endpoints, scopes and the flow: `trust_claim_backend/docs/sso-integration.md`.

## What it serves

| Path | What |
|---|---|
| `/` | Signed out: sign in. Signed in: the `home` dashboard |
| `/d/<dashboard>/` | Another dashboard |
| `/auth/login/?next=` | Sign in; `next` may be a path here or a URL on an origin in `EMBED_ORIGINS` |
| `/static/embed/nav.js` | `<site-nav data-up="<this app>">`: the nav bar, for any other app to mount so everything looks like one place |
| `/static/embed/theme.css` | The `--theme-*` variables |
| `/static/embed/grid.js` | `<dashboard-grid>`, the arrangeable dashboard |
| `/api/nav/` | The nav places, for anyone signed in |
| `/api/logout/` | POST with `X-Embed: 1`: sign out, from the nav on any page |
| `/api/me/layouts/<dashboard>/` | GET, PUT, DELETE the person's arrangement |
| `/api/articles/team/`, `/api/articles/mine/` | The Ghost cards' data, for anyone signed in |
| `/static/embed/volkit.js` | `<volkit-team-articles>`, `<volkit-my-articles>` |

## Nav

Places are rows under Nav places in the admin: a label and a URL, which may be this app,
another app, or an existing system (Taiga, the CRM).

## Dashboards

A dashboard is a file, `dashboards/<name>.json`, its cards in default order:

```json
{
  "title": "Home",
  "cards": [
    {"id": "apps", "w": 12, "title": "Apps", "template": "dashboard/cards/apps.html"},
    {"id": "people", "w": 6, "title": "People", "app": "crm", "tag": "crm-people"},
    {"id": "mine", "w": 6, "title": "Mine", "tag": "volkit-mine", "script": "embed/volkit.js"},
    {"id": "cases", "w": 6, "title": "Cases", "template": "dashboard/cards/cases.html", "requires": "CASES_URL"},
    {"id": "claims", "w": 6, "title": "Claims", "tag": "lt-claims",
     "script": "https://demos.linkedtrust.us/baobab/components/lt-claims.js",
     "attrs": {"data-up": "https://live.linkedtrust.us", "data-query": "our-group"}}
  ]
}
```

A card is one of:

- `template`: a template in this app.
- `tag` + `app`: an app's web component, from its web components file. It gets `data-up` =
  the app's API and `data-app` = the app's URL.
- `tag` + `script`: this app's own web component, from its static files (start from
  `static/embed/kit.js`), with `data-up` = this app.
- `tag` + `script` as a full URL: a component from a library. Its origin must be an app's
  (add the library under Apps), because a script on the page runs as the viewer.

`attrs` adds `data-*` attributes (see COMPONENTS.md). `requires`: shown only while that setting
is set. `w`: width out of 12. A card that cannot be shown is left out and the reason logged.
Each person's arrangement is theirs.

An app (its URL, API and web components file) is a row under Apps in the admin. Each app's
backend decides what the viewer may see; this app holds no permissions.

## Links

`/`, `/d/<dashboard>/`, `/api/articles/team/`, `/api/articles/mine/`,
`/static/embed/volkit.js`. Published link shapes never change (CONTRACT.md section 4).
