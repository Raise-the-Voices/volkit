"""Live updates: server-sent events over Postgres LISTEN/NOTIFY (CONTRACT.md section 3).

publish() is called after a change commits. stream() is what /api/live/ returns.
A message carries ids only; cards refetch through the API, which applies permissions.
Each open stream holds one database connection.
"""

import asyncio
import json

from django.conf import settings
from django.db import connection, transaction

CHANNEL = "baobab_live"
HEARTBEAT_SECONDS = 20


def publish(topic, type_, id_):
    """Tell subscribers of `topic` (`<org>/<thing>`) that something changed."""
    if not settings.LIVE:
        return
    payload = json.dumps({"topic": topic, "type": type_, "id": id_})

    def send():
        with connection.cursor() as cur:
            cur.execute("SELECT pg_notify(%s, %s)", [CHANNEL, payload])

    transaction.on_commit(send)


def _conninfo():
    db = settings.DATABASES["default"]
    return {
        "dbname": db["NAME"], "user": db.get("USER") or None, "password": db.get("PASSWORD") or None,
        "host": db.get("HOST") or None, "port": db.get("PORT") or None,
    }


async def stream(topics):
    import psycopg

    async with await psycopg.AsyncConnection.connect(autocommit=True, **_conninfo()) as conn:
        await conn.execute(f"LISTEN {CHANNEL}")
        yield ": open\n\n"
        while True:
            got = False
            async for note in conn.notifies(timeout=HEARTBEAT_SECONDS):
                got = True
                try:
                    msg = json.loads(note.payload)
                except ValueError:
                    continue
                if msg.get("topic") in topics:
                    yield f"data: {json.dumps(msg)}\n\n"
            if not got:
                yield ": ping\n\n"
            await asyncio.sleep(0)
