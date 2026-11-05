"""Signing in to the core (D-003): register, login and lockout, refresh rotation and theft
detection, password reset and change, invitation links, guest tokens, /me/tenants."""

import re

import pytest
from django.core import mail
from rest_framework.test import APIClient

from kernel.tenant_context import tenant_scope
from modules.events import service as events
from modules.tenancy.models import Tenant
from modules.users import service as users

pytestmark = pytest.mark.django_db

PASSWORD = "Correct-Horse-42"


def _post(path, body, token=None, tenant=None):
    client = APIClient()
    if token:
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    extra = {"HTTP_X_TENANT_ID": str(tenant)} if tenant else {}
    return client.post(f"/api/v1/auth/{path}", body, format="json", **extra)


def _get(path, token, tenant=None):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {token}",
        **({"HTTP_X_TENANT_ID": str(tenant)} if tenant else {}),
    )
    return client.get(f"/api/v1/{path}")


def _register(email="an@example.test"):
    response = _post("register", {"email": email, "password": PASSWORD, "fullName": "An"})
    assert response.status_code == 201, response.json()
    return response.json()


def _link(message) -> str:
    return re.search(r"token=([\w-]+)", message.body).group(1)


def test_register_then_use_the_token():
    tokens = _register()
    assert set(tokens) == {"accessToken", "refreshToken", "tokenType", "expiresIn", "user"}
    assert tokens["user"]["email"] == "an@example.test"
    assert _get("me/tenants", tokens["accessToken"]).json() == {"data": []}
    again = _post("register", {"email": "AN@example.test", "password": PASSWORD, "fullName": "X"})
    assert again.json()["errors"][0]["field"] == "email"
    weak = _post("register", {"email": "b@example.test", "password": "12345678", "fullName": "B"})
    assert weak.status_code == 422
    assert {e["field"] for e in weak.json()["errors"]} == {"password"}


# Login and refresh commit on their own (a wrong password must stay counted even when the
# answer is 401), so these tests need real commits, not the per-test transaction.
@pytest.mark.django_db(transaction=True)
def test_login_wrong_password_and_lockout(settings):
    _register()
    unknown = _post("login", {"email": "nobody@example.test", "password": PASSWORD})
    wrong = _post("login", {"email": "an@example.test", "password": "nope-nope-1"})
    # Same answer for an unknown email and a wrong password.
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]
    ok = _post("login", {"email": "an@example.test", "password": PASSWORD})
    assert ok.status_code == 200
    for _ in range(settings.AUTH["MAX_FAILED_LOGINS"]):
        _post("login", {"email": "an@example.test", "password": "nope-nope-1"})
    locked = _post("login", {"email": "an@example.test", "password": PASSWORD})
    assert locked.status_code == 401
    assert "Too many" in locked.json()["detail"]


# Login and refresh commit on their own (a wrong password must stay counted even when the
# answer is 401), so these tests need real commits, not the per-test transaction.
@pytest.mark.django_db(transaction=True)
def test_refresh_rotates_and_a_reused_token_ends_the_session():
    first = _register()["refreshToken"]
    second = _post("refresh", {"refreshToken": first})
    assert second.status_code == 200
    rotated = second.json()["refreshToken"]
    assert rotated != first
    # The old one again: someone copied it. Both it and its successor stop working.
    assert _post("refresh", {"refreshToken": first}).status_code == 401
    assert _post("refresh", {"refreshToken": rotated}).status_code == 401


def test_logout_revokes():
    refresh = _register()["refreshToken"]
    assert _post("logout", {"refreshToken": refresh}).status_code == 204
    assert _post("refresh", {"refreshToken": refresh}).status_code == 401


@pytest.mark.django_db(transaction=True)
def test_forgot_and_reset_password(django_capture_on_commit_callbacks):
    old = _register()["refreshToken"]
    with django_capture_on_commit_callbacks(execute=True):
        sent = _post("password/forgot", {"email": "an@example.test"})
        assert _post("password/forgot", {"email": "ghost@example.test"}).status_code == 202
    assert sent.status_code == 202
    assert len(mail.outbox) == 1  # only the real account gets mail
    token = _link(mail.outbox[0])
    reset = _post("password/reset", {"token": token, "password": "Brand-New-Pass-7"})
    assert reset.status_code == 200, reset.json()
    assert (
        _post("password/reset", {"token": token, "password": "Brand-New-Pass-8"}).status_code == 422
    )
    assert _post("refresh", {"refreshToken": old}).status_code == 401  # every device signs in again
    assert _post("login", {"email": "an@example.test", "password": PASSWORD}).status_code == 401
    assert (
        _post("login", {"email": "an@example.test", "password": "Brand-New-Pass-7"}).status_code
        == 200
    )


def test_change_password():
    tokens = _register()
    bad = _post(
        "password/change",
        {"currentPassword": "wrong-one-9", "newPassword": "Another-Pass-9"},
        token=tokens["accessToken"],
    )
    assert bad.json()["errors"][0]["field"] == "currentPassword"
    ok = _post(
        "password/change",
        {"currentPassword": PASSWORD, "newPassword": "Another-Pass-9"},
        token=tokens["accessToken"],
    )
    assert ok.status_code == 200
    assert _post("refresh", {"refreshToken": tokens["refreshToken"]}).status_code == 401
    assert _post("password/change", {"currentPassword": "x", "newPassword": "y"}).status_code == 401


def test_invitation_link_sets_the_password_and_joins(world, django_capture_on_commit_callbacks):
    invited = world.client("owner").post(
        "/api/v1/members/invite",
        {"email": "lan@example.test", "displayName": "Lan", "roles": [{"role": "member"}]},
        format="json",
    )
    assert invited.status_code == 201
    with django_capture_on_commit_callbacks(execute=True):
        events.relay_batch()  # the worker: invitation_mailer sends the link
    letter = next(m for m in mail.outbox if "lan@example.test" in m.to)
    token = _link(letter)
    accepted = _post(
        "invitations/accept", {"token": token, "password": PASSWORD, "fullName": "Lan"}
    )
    assert accepted.status_code == 200, accepted.json()
    body = accepted.json()
    assert body["tenantId"] == str(world.tenant_id)
    me = _get("me", body["accessToken"], tenant=world.tenant_id).json()
    assert (me["member"]["status"], me["member"]["roles"][0]["role"]) == ("active", "member")
    assert _post("invitations/accept", {"token": token, "password": PASSWORD}).status_code == 422
    assert _post("login", {"email": "lan@example.test", "password": PASSWORD}).status_code == 200
    # Registering the address of a pending invitation is refused (the link is the way in).
    world.client("owner").post(
        "/api/v1/members/invite",
        {"email": "ha@example.test", "roles": [{"role": "member"}]},
        format="json",
    )
    blocked = _post(
        "register", {"email": "ha@example.test", "password": PASSWORD, "fullName": "Ha"}
    )
    assert "invitation" in blocked.json()["errors"][0]["message"]


def test_guest_token_books_as_guest_in_one_tenant(world, world_b):
    response = _post(
        "guest", {"tenantId": str(world.tenant_id), "name": "Khách", "phone": "+84901234567"}
    )
    assert response.status_code == 201, response.json()
    guest = response.json()
    assert "refreshToken" not in guest
    me = _get("me", guest["accessToken"], tenant=world.tenant_id).json()
    assert me["member"]["roles"][0]["role"] == "guest"
    assert _get("me", guest["accessToken"], tenant=world_b.tenant_id).status_code == 403
    unknown = _post("guest", {"tenantId": "0193f4c2-7a3b-7c3e-8e2a-1f9b6c5d4e3a", "name": "X"})
    assert unknown.status_code == 404
    Tenant.objects.filter(id=world_b.tenant_id).update(settings={"guestBooking": False})
    closed = _post("guest", {"tenantId": str(world_b.tenant_id), "name": "X"})
    assert closed.status_code == 403


def test_my_tenants_lists_every_membership_and_nothing_leaks(world, world_b):
    tokens = _register("multi@example.test")
    user_id = tokens["user"]["id"]
    for w in (world, world_b):
        with tenant_scope(w.tenant_id):
            users.add_member(tenant_id=w.tenant_id, user_id=user_id, role_code="member")
    mine = _get("me/tenants", tokens["accessToken"]).json()["data"]
    assert {t["tenantId"] for t in mine} == {str(world.tenant_id), str(world_b.tenant_id)}
    # Inside a tenant request the extra RLS policy is off: lists stay per tenant.
    listed = world.client("owner").get("/api/v1/members", {"limit": 100}).json()["data"]
    assert len(listed) == 7
    assert all(
        m["id"] != next(t["memberId"] for t in mine if t["tenantId"] == str(world_b.tenant_id))
        for m in listed
    )


def test_public_endpoints_need_no_token_but_the_rest_still_do():
    assert APIClient().get("/api/v1/me/tenants").status_code == 401
    assert APIClient().get("/api/v1/resource-types").status_code == 401
    assert _post("login", {"email": "x@example.test", "password": "whatever-1"}).status_code == 401
