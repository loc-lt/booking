"""People: /me, roles built from permission codes, invitations, member status
(API_KICH_BAN.md section 5)."""

import pytest
from rest_framework.test import APIClient

from kernel.models import TransitionLog
from kernel.tenant_context import tenant_scope
from modules.events.models import Outbox
from tests.conftest import make_token

pytestmark = pytest.mark.django_db


def test_me_lists_permissions_per_site(world):
    me = world.client("staff").get("/api/v1/me").json()
    assert me["tenantId"] == str(world.tenant_id)
    assert me["member"]["roles"] == [
        {
            "roleId": me["member"]["roles"][0]["roleId"],
            "role": "staff",
            "siteId": str(world.site_id),
        }
    ]
    assert me["permissions"]["booking.approve"] == [str(world.site_id)]
    owner = world.client("owner").get("/api/v1/me").json()
    assert owner["permissions"]["role.manage"] == ["*"]


def test_permission_catalogue_and_system_roles(world):
    catalogue = world.client("member").get("/api/v1/permissions").json()["data"]
    assert {
        "code": "booking.approve",
        "description": "Approve or reject bookings at the role's sites",
    } in catalogue
    roles = world.client("admin").get("/api/v1/roles").json()["data"]
    assert [r["code"] for r in roles if r["isSystem"]] == [
        "admin",
        "guest",
        "member",
        "owner",
        "staff",
    ]
    staff = next(r for r in roles if r["code"] == "staff")
    assert "payment.mark_paid" in staff["permissions"]
    # Members may not see the role list.
    assert world.client("member").get("/api/v1/roles").status_code == 403


def test_custom_role_controls_access(world):
    owner = world.client("owner")
    bad = owner.post(
        "/api/v1/roles",
        {"code": "front_desk", "name": "Front desk", "permissions": ["booking.fly"]},
        format="json",
    )
    assert bad.status_code == 422
    assert bad.json()["errors"][0]["field"] == "permissions"

    role = owner.post(
        "/api/v1/roles",
        {
            "code": "front_desk",
            "name": "Front desk",
            "permissions": ["booking.read_all", "booking.check_in_any", "resource.read"],
        },
        format="json",
    ).json()
    member2 = world.membership_id("member2")
    granted = owner.put(
        f"/api/v1/members/{member2}/roles",
        {"roles": [{"role": "front_desk", "siteId": str(world.site_id)}]},
        format="json",
    )
    assert granted.status_code == 200, granted.json()
    perms = world.client("member2").get("/api/v1/me").json()["permissions"]
    assert perms == {
        "booking.check_in_any": [str(world.site_id)],
        "booking.read_all": [str(world.site_id)],
        "resource.read": [str(world.site_id)],
    }
    # Turning a permission off takes effect on the next request.
    owner.put(
        f"/api/v1/roles/{role['id']}/permissions",
        {"permissions": ["resource.read"]},
        format="json",
    )
    perms = world.client("member2").get("/api/v1/me").json()["permissions"]
    assert set(perms) == {"resource.read"}

    system = next(r for r in owner.get("/api/v1/roles").json()["data"] if r["code"] == "member")
    locked = owner.put(
        f"/api/v1/roles/{system['id']}/permissions", {"permissions": []}, format="json"
    )
    assert locked.status_code == 409


def test_invite_then_accept_with_a_verified_email(world):
    owner = world.client("owner")
    invited = owner.post(
        "/api/v1/members/invite",
        {"email": "Lan@Example.test", "displayName": "Lan", "roles": [{"role": "member"}]},
        format="json",
    )
    assert invited.status_code == 201, invited.json()
    m = invited.json()
    assert (m["status"], m["email"], m["roles"][0]["role"]) == (
        "invited",
        "lan@example.test",
        "member",
    )
    again = owner.post(
        "/api/v1/members/invite",
        {"email": "lan@example.test", "roles": [{"role": "member"}]},
        format="json",
    )
    assert again.status_code == 422

    def lan(verified: bool) -> APIClient:
        client = APIClient()
        token = make_token("lan-sub", email="lan@example.test", email_verified=verified)
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token}", HTTP_X_TENANT_ID=str(world.tenant_id)
        )
        return client

    # Not active yet: every normal endpoint says FORBIDDEN.
    assert lan(True).get("/api/v1/resource-types").status_code == 403
    accepted = lan(True).post("/api/v1/me/accept-invitation")
    assert accepted.status_code == 200, accepted.json()
    assert accepted.json()["status"] == "active"
    assert lan(True).get("/api/v1/resource-types").status_code == 200
    assert lan(True).post("/api/v1/me/accept-invitation").status_code == 409
    with tenant_scope(world.tenant_id):
        names = list(
            Outbox.objects.filter(aggregate_id=m["id"]).values_list("event_type", flat=True)
        )
        assert names == ["member.invited", "member.joined"]
        moves = TransitionLog.objects.filter(record_id=m["id"]).values_list("to_status", flat=True)
        assert list(moves) == ["INVITED", "ACTIVE"]


def test_an_unverified_email_cannot_claim_an_invitation(world):
    world.client("owner").post(
        "/api/v1/members/invite",
        {"email": "ha@example.test", "roles": [{"role": "staff", "siteId": str(world.site_id)}]},
        format="json",
    )
    client = APIClient()
    token = make_token("intruder", email="ha@example.test", email_verified=False)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}", HTTP_X_TENANT_ID=str(world.tenant_id))
    assert client.post("/api/v1/me/accept-invitation").status_code == 403


def test_disabled_members_lose_access_and_can_be_enabled(world):
    owner = world.client("owner")
    member = world.membership_id("member")
    assert owner.post(f"/api/v1/members/{member}/disable").json()["status"] == "disabled"
    assert world.client("member").get("/api/v1/me").status_code == 403
    assert owner.post(f"/api/v1/members/{member}/disable").status_code == 409
    assert owner.post(f"/api/v1/members/{member}/enable").json()["status"] == "active"
    assert world.client("member").get("/api/v1/me").status_code == 200
    # Nobody locks themselves out.
    me = world.membership_id("owner")
    assert owner.post(f"/api/v1/members/{me}/disable").status_code == 409


def test_member_list_and_search(world):
    owner = world.client("owner")
    page = owner.get("/api/v1/members", {"limit": 2}).json()
    assert len(page["data"]) == 2 and page["nextCursor"]
    everyone = owner.get("/api/v1/members", {"limit": 100}).json()["data"]
    assert len(everyone) == 6
    assert owner.get("/api/v1/members", {"status": "weird"}).status_code == 422
    assert world.client("member").get("/api/v1/members").status_code == 403
    # Staff may read members (to book on someone's behalf).
    assert world.client("staff").get("/api/v1/members").status_code == 200


def test_grants_with_unknown_site_or_role_fail_per_field(world):
    member2 = world.membership_id("member2")
    response = world.client("owner").put(
        f"/api/v1/members/{member2}/roles",
        {"roles": [{"role": "nope"}]},
        format="json",
    )
    assert response.json()["errors"] == [
        {"field": "roles[0].role", "message": "No role with this code or id."}
    ]
    response = world.client("owner").put(
        f"/api/v1/members/{member2}/roles",
        {"roles": [{"role": "staff", "siteId": "0193f4c2-7a3b-7c3e-8e2a-1f9b6c5d4e3a"}]},
        format="json",
    )
    assert response.json()["errors"][0]["field"] == "roles[0].siteId"


def test_roles_are_tenant_private(world, world_b):
    role = (
        world.client("owner")
        .post(
            "/api/v1/roles",
            {"code": "auditor", "name": "Auditor", "permissions": ["audit.read"]},
            format="json",
        )
        .json()
    )
    codes = [r["code"] for r in world_b.client("owner").get("/api/v1/roles").json()["data"]]
    assert "auditor" not in codes
    other = world_b.client("owner").put(
        f"/api/v1/roles/{role['id']}/permissions", {"permissions": []}, format="json"
    )
    assert other.status_code == 404
