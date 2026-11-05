"""Two parallel requests for one slot: exactly one succeeds (real PostgreSQL, real commits)."""

import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.db import connection

from tests.conftest import TZ, book, build_world, create_resource, create_type, local


@pytest.mark.django_db(transaction=True)
def test_two_racing_requests_one_wins():
    world = build_world("race")
    rt = create_type(world)
    room = create_resource(world, rt["id"])
    day = datetime.now(ZoneInfo(TZ)).date() + timedelta(days=7)
    barrier = threading.Barrier(2)
    results: dict[str, int] = {}

    def attempt(role: str) -> None:
        try:
            barrier.wait()
            response = book(world, room["id"], local(day, 9), local(day, 10), role=role)
            results[role] = response.status_code
        finally:
            connection.close()

    threads = [threading.Thread(target=attempt, args=(r,)) for r in ("member", "member2")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results.values()) == [201, 409]
