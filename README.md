# VolKit

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
| `/api/s2s/membership/?sub=&org=` | For roots, with `Authorization: Bearer <S2S_TOKEN>` |
| `/api/live/?topics=<org>/<thing>` | Server-sent events |

## Dashboards

A dashboard is a file, `dashboards/<name>.json`:

```json
{
  "title": "Home",
  "roles": [],
  "cards": [
    {"id": "welcome", "w": 12, "title": "Welcome", "template": "frame/cards/welcome.html"},
    {"id": "items", "w": 6, "title": "Items", "peer": "planner", "tag": "planner-items"}
  ]
}
```

`roles` empty: every member of the org. `w` is a width out of 12. A card is a template in
this frame, or a peer's custom element; the peer (its app, API and cards-file URLs) is a row
under Peers in the admin, and its cards-file origin is the only outside script the page
may load. Card order in the file is the default arrangement; each person's changes are
theirs.

## Links

`/`, `/o/<org>/`, `/o/<org>/<dashboard>/`. Published link shapes never change
(CONTRACT.md section 4).
