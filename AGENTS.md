# For agents

This is a dashboard app. Read https://github.com/Cooperation-org/baobab/blob/main/AGENTS.md first.

It holds no permissions and no list of members: each app's backend decides what the viewer
sees. Its tables are in `dashboard/models.py`; adding another needs the project owner's OK.
Pages load no inline script: the Content-Security-Policy allows this app and its apps' web
components files only.
