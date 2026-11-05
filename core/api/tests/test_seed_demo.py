"""The demo seed builds a working tenant through the same services as the API."""

import json
from io import StringIO

import pytest
from django.core.management import call_command

from tests.conftest import client_for

pytestmark = pytest.mark.django_db


def test_seed_demo_builds_a_bookable_tenant():
    out = StringIO()
    call_command("seed_demo", "--slug", "seedtest", "--json", stdout=out)
    data = json.loads(out.getvalue())
    assert set(data["resourceTypes"]) == {"meeting_room", "hot_desk", "event_hall"}
    assert data["ruleSetVersion"] == 1
    owner = client_for(data["people"]["owner"]["sub"], data["tenantId"])
    types = owner.get("/api/v1/resource-types").json()["data"]
    hall = next(t for t in types if t["key"] == "event_hall")
    assert (hall["flowConfig"]["confirmation"], hall["flowConfig"]["payment"]["mode"]) == (
        "approval",
        "upfront",
    )
    staff = client_for(data["people"]["staff"]["sub"], data["tenantId"]).get("/api/v1/me").json()
    assert staff["permissions"]["booking.approve"] == [data["sites"]["q1"]]
    assert owner.get("/api/v1/rules").json()["ruleCount"] == 3
