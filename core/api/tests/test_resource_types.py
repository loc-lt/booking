"""Resource types, policies and custom fields (API_KICH_BAN.md 4.4-4.7)."""

import pytest

from kernel.tenant_context import tenant_scope
from modules.config.models import ObjectSchemaVersion, PolicyVersion
from modules.events.models import Outbox
from tests.conftest import FLOW_APPROVAL, FLOW_INSTANT, create_resource, create_type

FIELDS = [
    {
        "key": "capacity",
        "label": "Capacity",
        "type": "integer",
        "required": True,
        "validation": {"min": 1, "max": 200},
    },
    {
        "key": "equipment",
        "label": "Equipment",
        "type": "multi_select",
        "options": [{"value": "tv", "label": "TV"}, {"value": "whiteboard", "label": "Board"}],
    },
    {
        "key": "attendee_count",
        "label": "Attendees",
        "type": "integer",
        "scope": "booking",
        "required": True,
        "validation": {"min": 1},
    },
]


@pytest.mark.django_db
def test_create_returns_the_contract_shape(world):
    body = create_type(world, fields=FIELDS)
    assert set(body) == {
        "id",
        "key",
        "label",
        "version",
        "slotMinutes",
        "bookingMode",
        "fields",
        "flowConfig",
        "createdAt",
        "updatedAt",
    }
    assert body["version"] == 1
    assert (body["slotMinutes"], body["bookingMode"]) == (30, "exclusive")
    assert {k: body["flowConfig"][k] for k in FLOW_INSTANT} == FLOW_INSTANT
    assert body["flowConfig"]["limits"]["maxDurationMinutes"] == 480  # platform default
    assert [f["key"] for f in body["fields"]] == ["capacity", "equipment", "attendee_count"]
    assert body["fields"][0] == {
        "key": "capacity",
        "label": "Capacity",
        "type": "integer",
        "scope": "resource",
        "required": True,
        "validation": {"min": 1, "max": 200},
    }
    with tenant_scope(world.tenant_id):
        # One form per scope, and one config.published event, in the same transaction.
        assert ObjectSchemaVersion.objects.filter(resource_type_id=body["id"]).count() == 2
    assert (
        Outbox.objects.filter(event_type="config.published", aggregate_id=body["id"]).count() == 1
    )


@pytest.mark.django_db
def test_list_is_paginated_newest_first(world):
    for key in ("a_type", "b_type", "c_type"):
        create_type(world, key=key)
    client = world.client("member")
    first = client.get("/api/v1/resource-types?limit=2").json()
    assert [t["key"] for t in first["data"]] == ["c_type", "b_type"]
    second = client.get(f"/api/v1/resource-types?limit=2&cursor={first['nextCursor']}").json()
    assert [t["key"] for t in second["data"]] == ["a_type"]
    assert second["nextCursor"] is None


@pytest.mark.django_db
def test_members_cannot_create_types(world):
    response = world.client("member").post(
        "/api/v1/resource-types",
        {"key": "x", "label": "X", "flowConfig": FLOW_INSTANT},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("fields", "field"),
    [
        ([{"key": "Bad-Key", "label": "x", "type": "text"}], "fields[0].key"),
        ([{"key": "x", "label": "x", "type": "select"}], "fields[0].options"),
        (
            [{"key": "x", "label": "x", "type": "integer", "validation": {"min": 5, "max": 1}}],
            "fields[0].validation.min",
        ),
        (
            [{"key": "x", "label": "x", "type": "text", "validation": {"pattern": "("}}],
            "fields[0].validation.pattern",
        ),
        (
            [
                {"key": "x", "label": "x", "type": "text"},
                {"key": "x", "label": "y", "type": "text"},
            ],
            "fields[1].key",
        ),
        (
            [{"key": "x", "label": "x", "type": "reference"}],
            "fields[0].validation.targetResourceTypeId",
        ),
    ],
    ids=["key", "options", "min-max", "pattern", "duplicate", "reference"],
)
def test_bad_field_definitions_fail_per_field(world, fields, field):
    response = world.client("owner").post(
        "/api/v1/resource-types",
        {"key": "room", "label": "Room", "fields": fields, "flowConfig": FLOW_INSTANT},
        format="json",
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert field in [e["field"] for e in body["errors"]]


@pytest.mark.django_db
def test_duplicate_key_is_a_validation_error(world):
    create_type(world, key="room")
    response = world.client("owner").post(
        "/api/v1/resource-types",
        {"key": "room", "label": "Again", "flowConfig": FLOW_INSTANT},
        format="json",
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "key"


@pytest.mark.django_db
def test_patch_publishes_a_new_version_and_rejects_stale_edits(world):
    rt = create_type(world)
    client = world.client("owner")
    url = f"/api/v1/resource-types/{rt['id']}"

    ok = client.patch(url, {"baseVersion": 1, "flowConfig": FLOW_APPROVAL}, format="json")
    assert ok.status_code == 200
    assert ok.json()["version"] == 2
    assert ok.json()["flowConfig"]["confirmation"] == "approval"

    stale = client.patch(url, {"baseVersion": 1, "flowConfig": FLOW_INSTANT}, format="json")
    assert stale.status_code == 409
    assert stale.json()["code"] == "STALE_VERSION"

    with tenant_scope(world.tenant_id):
        versions = dict(
            PolicyVersion.objects.filter(resource_type_id=rt["id"]).values_list("version", "status")
        )
    assert versions == {1: "SUPERSEDED", 2: "PUBLISHED"}


@pytest.mark.django_db
def test_patch_keeps_policy_keys_the_contract_does_not_expose(world):
    rt = create_type(world)
    with tenant_scope(world.tenant_id):
        v1 = PolicyVersion.objects.get(resource_type_id=rt["id"], version=1)
        body = {**v1.body, "buffer_after_seconds": 900}
        PolicyVersion.objects.filter(id=v1.id).update(body=body)
    world.client("owner").patch(
        f"/api/v1/resource-types/{rt['id']}",
        {"baseVersion": 1, "flowConfig": FLOW_APPROVAL},
        format="json",
    )
    with tenant_scope(world.tenant_id):
        v2 = PolicyVersion.objects.get(resource_type_id=rt["id"], version=2)
    assert v2.body["buffer_after_seconds"] == 900
    assert v2.body["requires_approval"] is True


@pytest.mark.django_db
def test_resource_values_are_checked_against_the_form(world):
    rt = create_type(world, fields=FIELDS)
    ok = create_resource(world, rt["id"], capacity=8, equipment=["tv"])
    assert ok["customFieldValues"] == {"capacity": 8, "equipment": ["tv"]}
    assert ok["siteId"] == str(world.site_id)

    bad = world.client("owner").post(
        "/api/v1/resources",
        {
            "resourceTypeId": rt["id"],
            "siteId": str(world.site_id),
            "label": "Room B",
            "customFieldValues": {"capacity": 500, "equipment": ["sofa"], "colour": "red"},
        },
        format="json",
    )
    assert bad.status_code == 422
    fields = {e["field"] for e in bad.json()["errors"]}
    assert fields == {
        "customFieldValues.capacity",
        "customFieldValues.equipment.0",
        "customFieldValues.colour",
    }


@pytest.mark.django_db
def test_booking_scoped_fields_are_not_asked_on_the_resource(world):
    rt = create_type(world, fields=FIELDS)
    response = world.client("owner").post(
        "/api/v1/resources",
        {
            "resourceTypeId": rt["id"],
            "siteId": str(world.site_id),
            "label": "Room C",
            "customFieldValues": {"capacity": 4, "attendee_count": 3},
        },
        format="json",
    )
    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"field": "customFieldValues.attendee_count", "message": "Unknown field."}
    ]


@pytest.mark.django_db
def test_reference_fields_must_point_at_the_target_type(world):
    table_type = create_type(world, key="table")
    table = create_resource(world, table_type["id"], label="Table 1")
    other = create_resource(world, create_type(world, key="locker")["id"], label="Locker 1")
    room_type = create_type(
        world,
        key="meeting_room",
        fields=[
            {
                "key": "primary_table",
                "label": "Primary table",
                "type": "reference",
                "validation": {"targetResourceTypeId": table_type["id"]},
            }
        ],
    )
    create_resource(world, room_type["id"], label="Room 1", primary_table=table["id"])
    response = world.client("owner").post(
        "/api/v1/resources",
        {
            "resourceTypeId": room_type["id"],
            "siteId": str(world.site_id),
            "label": "Room 2",
            "customFieldValues": {"primary_table": other["id"]},
        },
        format="json",
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "customFieldValues.primary_table"


@pytest.mark.django_db
def test_staff_can_only_create_resources_at_their_site(world):
    rt = create_type(world)
    client = world.client("staff")  # staff has no resource.manage at all
    response = client.post(
        "/api/v1/resources",
        {"resourceTypeId": rt["id"], "siteId": str(world.site_id), "label": "X"},
        format="json",
    )
    assert response.status_code == 403
