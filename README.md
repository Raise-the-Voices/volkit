# VolKit

The Raise the Voices volunteer dashboard: one page, what is next for me. A baobab frame.

| Card | Reads | Off when |
|---|---|---|
| From the team: a little help? | newest 4 published posts, Ghost Content API | `VOLKIT_GHOST_URL` or `VOLKIT_GHOST_CONTENT_KEY` unset |
| My articles | the person's own posts incl. drafts, Ghost Admin API, matched by email | `VOLKIT_GHOST_ADMIN_KEY` unset |
| My cases | link to the cases app (its own sign-in for now) | `VOLKIT_CASES_URL` unset |

Not built yet: To do next (Taiga, waits on baobab Open decision A), Upcoming events,
Learning, My impact (no source of record chosen).

Deploy: `deploy/ansible/` (see the playbook header and `example-vars.yml`).

## Links

`/`, `/o/<org>/`, `/o/<org>/<dashboard>/`, `/api/orgs/<org>/articles/team/`,
`/api/orgs/<org>/articles/mine/`, `/static/embed/volkit.js`.

A baobab frame: where people land. Sign-in, orgs and members, the nav, dashboards,
and each person's arrangement of them. Made from
[Cooperation-org/baobab](https://github.com/Cooperation-org/baobab); the rules are its
[PRINCIPLES](https://github.com/Cooperation-org/baobab/blob/main/PRINCIPLES.md),
[AGENTS](https://github.com/Cooperation-org/baobab/blob/main/AGENTS.md) and
[CONTRACT](https://github.com/Cooperation-org/baobab/blob/main/CONTRACT.md).

## Run it

```
uv venv && uv pip install -r requirements.txt
cp .env.example .env          # then fill in DATABASE_URL and the OIDC client
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/uvicorn config.asgi:application --port 8000
.venv/bin/pytest
```

Production: `gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker`, after
`manage.py collectstatic`. Live updates (`/api/live/`) need Postgres and an ASGI server.

To see a dashboard locally without an OIDC client: sign in at `/admin/` as the superuser,
add yourself as a member on an org's admin page, then open `/o/<org>/`.

Behind nginx, `/api/live/` needs its own block, or the events stall with no error:

```
location /api/live/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto https;
    proxy_buffering off;
    proxy_read_timeout 1h;
}
```

## What it serves

| Path | What |
|---|---|
| `/` | Signed out: sign in. Signed in: your org's dashboard, or the list of your orgs |
| `/o/<org>/`, `/o/<org>/<dashboard>/` | A dashboard, for members of that org |
| `/auth/login/?next=` | Sign in; `next` may be a path here or a URL on an origin in `EMBED_ORIGINS` |
| `/static/embed/nav.js` | `<baobab-nav data-up="<this frame>">`, for fronds to mount (their `NAV_SRC`) |
| `/static/embed/theme.css` | The `--bb-*` variables, for fronds to load (their `THEME_CSS`) |
| `/static/embed/grid.js` | `<baobab-grid>`, the arrangeable dashboard |
| `/api/me/` | The signed-in person and their orgs |
| `/api/me/layouts/<dashboard>/` | GET, PUT, DELETE their arrangement |
| `/api/nav/` | The nav places this viewer sees |
| `/api/v1/accounts/s2s/identity/linkedtrust/<sub>/` | For roots, with `Authorization: Bearer <S2S_TOKEN>`: the person and their orgs. Same path and answer as GovKit |
| `/api/live/?topics=<org>/<thing>` | Server-sent events |

## Dashboards

A dashboard is a file, `dashboards/<name>.json`:

```json
{
  "title": "Home",
  "roles": [],
  "cards": [
    {"id": "apps", "w": 12, "title": "Apps", "template": "frame/cards/apps.html"},
    {"id": "items", "w": 6, "title": "Items", "peer": "planner", "tag": "planner-items"},
    {"id": "mine", "w": 6, "title": "Mine", "tag": "volkit-mine", "script": "embed/volkit.js"},
    {"id": "cases", "w": 6, "title": "Cases", "template": "frame/cards/cases.html", "requires": "CASES_URL"},
    {"id": "claims", "w": 6, "title": "Claims", "tag": "lt-claims",
     "script": "https://demos.linkedtrust.us/baobab/components/lt-claims.js",
     "attrs": {"data-up": "https://live.linkedtrust.us", "data-query": "our-group"}}
  ]
}
```

The default dashboard is one card, Apps: every peer, opening its app. `roles` empty: every
member of the org. `title` is the page heading.

A card is one of three things:

- `template`: a template in this frame.
- `tag` + `script`: this frame's own custom element, from its static files (start from
  `static/embed/kit.js`). It gets `data-up` = this frame and `data-org`.
- `tag` + `peer`: a peer's custom element, from the peer's cards file.
- `tag` + `script` as a full URL: a component from a library, e.g.
  `https://demos.linkedtrust.us/baobab/components/lt-claims.js`. Its origin must be a peer's
  (add the library under Peers), because a script on the page runs as the viewer.

Any element card may add `"attrs": {"data-...": "..."}` (see the component's attributes in
COMPONENTS.md). A card that cannot be shown is left out and the reason is logged.

`requires`: the card shows only while that setting is set (unset means off). `w` is a width
out of 12. A peer (its app, API and cards-file URLs) is a row under Peers in the admin, and
its cards-file origin is the only outside script the page may load. Card order in the file
is the default arrangement; each person's changes are theirs.

## Links

`/`, `/o/<org>/`, `/o/<org>/<dashboard>/`. Published link shapes never change
(CONTRACT.md section 4).
