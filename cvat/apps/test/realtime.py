# Copyright (C) 2026
# SPDX-License-Identifier: MIT
"""
Real-time class distribution over a WebSocket.

CVAT serves HTTP through Django's ASGI handler, which does not speak WebSocket.
Instead of adding a new dependency (Django Channels), ``with_websockets`` wraps
the existing ASGI application: connections to
``/ws/analytics/tasks/<id>/class-distribution/`` are handled here and every
other request is passed to Django untouched.

Protocol (JSON text frames)
  server -> client   {"type": "snapshot", "data": {...}}   same payload as the REST endpoint
                     {"type": "error", "detail": "..."}
                     {"type": "pong"}
  client -> server   {"type": "refresh"}                    send a fresh snapshot now
                     {"type": "ping"}
  close codes        4401 not signed in / session expired
                     4403 no access to the task (or foreign origin)

How changes are noticed
  Every connection runs a cheap "fingerprint" query about every two seconds
  (row count + newest id of each annotation table, and the newest Job
  ``updated_date``). Only when the fingerprint moves is the full distribution
  recomputed, and it is pushed only if the result really differs. This works
  across all uvicorn processes and needs no hooks into CVAT's save code
  (annotations are written with ``bulk_create``, which never fires Django
  signals).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from http.cookies import CookieError, SimpleCookie
from importlib import import_module
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user
from django.db import connections
from django.db.models import Count, Max
from django.http.request import validate_host

from cvat.apps.engine.models import Job, LabeledImage, LabeledShape, Task, TrackedShape

from .permissions import user_can_view_task
from .services import compute_class_distribution

log = logging.getLogger(__name__)

ROUTE = re.compile(r"^/ws/analytics/tasks/(?P<task_id>\d+)/class-distribution/?$")

POLL_INTERVAL = 2.0  # seconds between "did anything change?" checks
REAUTH_INTERVAL = 60.0  # seconds between session / permission re-checks

CLOSE_UNAUTHENTICATED = 4401
CLOSE_FORBIDDEN = 4403


# --------------------------------------------------------------------------- helpers


async def _run(func, *args):
    """Run blocking ORM code in a worker thread and release its DB connection."""

    def call():
        try:
            return func(*args)
        finally:
            connections.close_all()

    return await sync_to_async(call, thread_sensitive=False)()


def _header(scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin-1")
    return None


async def _send_json(send, message: dict[str, Any]) -> None:
    await send({"type": "websocket.send", "text": json.dumps(message)})


async def _close(send, code: int) -> None:
    await send({"type": "websocket.close", "code": code})


# ------------------------------------------------------------------- authentication


def _origin_allowed(scope) -> bool:
    """Reject cross-site WebSocket hijacking: browsers attach cookies to any origin."""
    origin = _header(scope, b"origin")
    if not origin:
        return True  # not a browser (curl, scripts): no ambient cookies
    origin_host = urlsplit(origin).hostname
    request_host = urlsplit("//" + (_header(scope, b"host") or "")).hostname
    if not origin_host:
        return False
    return origin_host == request_host or validate_host(origin_host, settings.ALLOWED_HOSTS)


def _session_key(scope) -> str | None:
    raw = _header(scope, b"cookie")
    if not raw:
        return None
    jar = SimpleCookie()
    try:
        jar.load(raw)
    except CookieError:
        return None
    morsel = jar.get(settings.SESSION_COOKIE_NAME)
    return morsel.value if morsel else None


def _authorize(scope, task_id: int) -> int | None:
    """Blocking. Returns None if the socket may stay open, otherwise a close code."""
    key = _session_key(scope)
    if not key:
        return CLOSE_UNAUTHENTICATED

    session = import_module(settings.SESSION_ENGINE).SessionStore(key)
    user = get_user(SimpleNamespace(session=session))
    if not user.is_authenticated:
        return CLOSE_UNAUTHENTICATED

    if not user_can_view_task(user, task_id):
        return CLOSE_FORBIDDEN
    return None


# ------------------------------------------------------------------ change detection


def _fingerprint(task_id: int) -> tuple:
    """A few tiny aggregate queries that change whenever the annotations do."""

    def stat(queryset):
        row = queryset.aggregate(count=Count("id"), last=Max("id"))
        return row["count"], row["last"]

    touched = Job.objects.filter(segment__task_id=task_id).aggregate(last=Max("updated_date"))[
        "last"
    ]
    return (
        stat(LabeledShape.objects.filter(job__segment__task_id=task_id)),
        stat(LabeledImage.objects.filter(job__segment__task_id=task_id)),
        stat(TrackedShape.objects.filter(track__job__segment__task_id=task_id)),
        touched.isoformat() if touched else None,
    )


# ---------------------------------------------------------------------------- tasks


async def _reader(receive, send, refresh: asyncio.Event) -> None:
    """Handle frames coming from the browser until it disconnects."""
    while True:
        message = await receive()
        if message["type"] == "websocket.disconnect":
            return

        text = message.get("text")
        if not text:
            continue
        try:
            request = json.loads(text)
        except ValueError:
            continue
        if not isinstance(request, dict):
            continue

        kind = request.get("type")
        if kind == "refresh":
            refresh.set()
        elif kind == "ping":
            await _send_json(send, {"type": "pong"})


async def _pump(scope, send, task_id: int, refresh: asyncio.Event) -> None:
    """Push a snapshot on connect, then whenever the data changes."""
    last_fingerprint: tuple | None = None
    last_payload: dict | None = None
    last_auth = time.monotonic()

    while True:
        try:
            fingerprint = await _run(_fingerprint, task_id)
            forced = refresh.is_set()
            if forced or fingerprint != last_fingerprint:
                refresh.clear()
                payload = await _run(compute_class_distribution, task_id)
                last_fingerprint = fingerprint
                if forced or payload != last_payload:
                    last_payload = payload
                    await _send_json(send, {"type": "snapshot", "data": payload})
        except Task.DoesNotExist:
            await _close(send, CLOSE_FORBIDDEN)
            return
        except Exception:
            log.exception("class-distribution websocket: update failed for task %s", task_id)
            await _send_json(send, {"type": "error", "detail": "Could not read analytics, retrying"})

        if time.monotonic() - last_auth >= REAUTH_INTERVAL:
            last_auth = time.monotonic()
            code = await _run(_authorize, scope, task_id)
            if code is not None:
                await _close(send, code)
                return

        try:
            await asyncio.wait_for(refresh.wait(), timeout=POLL_INTERVAL)
        except asyncio.TimeoutError:
            pass


async def _serve(scope, receive, send, task_id: int) -> None:
    first = await receive()
    if first["type"] != "websocket.connect":
        return

    # Accept first so that we can close with our own codes (a rejected handshake
    # would only show up as a generic 1006 in the browser).
    await send({"type": "websocket.accept"})

    code = CLOSE_FORBIDDEN if not _origin_allowed(scope) else await _run(_authorize, scope, task_id)
    if code is not None:
        await _close(send, code)
        return

    refresh = asyncio.Event()
    workers = [
        asyncio.create_task(_reader(receive, send, refresh)),
        asyncio.create_task(_pump(scope, send, task_id, refresh)),
    ]
    done, pending = await asyncio.wait(workers, return_when=asyncio.FIRST_COMPLETED)
    for worker in pending:
        worker.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    for worker in done:
        if not worker.cancelled() and worker.exception():
            log.warning("class-distribution websocket closed: %r", worker.exception())


# ---------------------------------------------------------------------------- router


def with_websockets(inner):
    """Wrap the Django ASGI application with our WebSocket endpoint."""

    async def application(scope, receive, send):
        if scope["type"] != "websocket":
            await inner(scope, receive, send)
            return

        match = ROUTE.match(scope.get("path", ""))
        if match:
            await _serve(scope, receive, send, int(match["task_id"]))
        else:
            await receive()  # websocket.connect
            await send({"type": "websocket.close", "code": 4404})

    return application