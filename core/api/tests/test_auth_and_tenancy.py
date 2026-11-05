"""Auth and tenancy: docs/backend.md "Testing" rows Auth and Tenancy."""

import time

import pytest
from django.db import ProgrammingError, transaction

from kernel.tenant_context import tenant_scope
from modules.resources.models import ResourceType
from tests.conftest import client_for, create_resource, create_type, make_token


@pytest.mark.django_db
def test_healthz_needs_no_token(client):
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "token",
    [
        None,
        make_token("x", exp=int(time.time()) - 3600),  # expired
        make_token("x", aud="someone-else"),  # wrong audience
        make_token("x", iss="https://evil.example"),  # wrong issuer
        make_token("x")[:-4] + "AAAA",  # wrong signature
    ],
    ids=["missing", "expired", "audience", "issuer", "signature"],
)
def test_bad_tokens_are_rejected(world, token):
    from rest_framework.test import APIClient

    client = APIClient()
    if token:
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get("/api/v1/resource-types", HTTP_X_TENANT_ID=str(world.tenant_id))
    assert response.status_code == 401
    assert response["Content-Type"] == "application/problem+json"
    assert response.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.django_db
def test_first_sight_creates_the_user_but_non_members_get_forbidden(world):
    response = client_for("stranger", world.tenant_id).get("/api/v1/resource-types")
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


@pytest.mark.django_db
def test_missing_tenant_header(world):
    response = client_for(world.sub("owner"), None).get("/api/v1/resource-types")
    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"field": "X-Tenant-Id", "message": "This header is required."}
    ]


@pytest.mark.django_db
def test_member_of_a_cannot_act_in_b(world, world_b):
    response = client_for(world.sub("owner"), world_b.tenant_id).get("/api/v1/resource-types")
    assert response.status_code == 403


@pytest.mark.django_db
def test_tenant_a_cannot_read_tenant_b_through_the_api(world, world_b):
    rt_b = create_type(world_b)
    res_b = create_resource(world_b, rt_b["id"])
    a = world.client("owner")
    assert a.get("/api/v1/resource-types").json()["data"] == []
    assert a.get(f"/api/v1/resource-types/{rt_b['id']}").status_code == 404
    assert a.get(f"/api/v1/resources/{res_b['id']}").status_code == 404
    # Using B's resource type to create a resource in A fails: invisible under RLS.
    response = a.post(
        "/api/v1/resources",
        {"resourceTypeId": rt_b["id"], "siteId": str(world.site_id), "label": "X"},
        format="json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_rls_hides_and_refuses_rows_of_other_tenants(world, world_b):
    create_type(world_b)
    with tenant_scope(world.tenant_id):
        assert ResourceType.objects.count() == 0
        # WITH CHECK: a row for tenant B can't be written while acting as tenant A.
        with pytest.raises(ProgrammingError, match="row-level security"), transaction.atomic():
            ResourceType.objects.create(tenant_id=world_b.tenant_id, code="x", name="X")
    with tenant_scope(world_b.tenant_id):
        assert ResourceType.objects.count() == 1


@pytest.mark.django_db
def test_without_tenant_every_tenant_table_looks_empty(world):
    create_type(world)
    with transaction.atomic():
        from kernel.tenant_context import activate_tenant

        activate_tenant(None)
        assert ResourceType.objects.count() == 0


def test_cors_only_for_configured_origins(settings, rf):
    from django.http import HttpResponse

    from kernel.cors import LocalCorsMiddleware

    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]
    mw = LocalCorsMiddleware(lambda request: HttpResponse("ok"))

    preflight = mw(rf.options("/api/v1/bookings", HTTP_ORIGIN="http://localhost:5173"))
    assert preflight.status_code == 204
    assert preflight["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "Idempotency-Key" in preflight["Access-Control-Allow-Headers"]

    other = mw(rf.get("/api/v1/bookings", HTTP_ORIGIN="http://evil.example"))
    assert "Access-Control-Allow-Origin" not in other


@pytest.mark.django_db
def test_a_request_leaves_no_tenant_behind(world):
    """The tenant context variable is per request: a later request without X-Tenant-Id (or the
    worker's tenant_scope) must not inherit the previous request's tenant."""
    from kernel.tenant_context import current_tenant_id

    assert world.client("owner").get("/api/v1/me").status_code == 200
    assert current_tenant_id() is None
