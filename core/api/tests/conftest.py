"""Shared fixtures. Tests run against real PostgreSQL (docs/backend.md, "Testing").

Row-level security does not apply to superusers. CI's postgres service connects as a
superuser, so the test session switches to a plain role when it finds itself superuser;
otherwise the tenancy tests would pass for the wrong reason.
"""

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from datetime import time as dtime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import jwt
import pytest
from django.conf import settings
from django.db import connection
from django.db.backends.signals import connection_created
from rest_framework.test import APIClient

from kernel.tenant_context import tenant_scope
from modules.availability import service as availability
from modules.resources import service as resources
from modules.tenancy import service as tenancy
from modules.users import service as users

TZ = "Asia/Ho_Chi_Minh"
APP_ROLE = "booking_rls_test"


def _use_app_role(sender: Any = None, connection: Any = None, **kwargs: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"SET ROLE {APP_ROLE}")


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup: None, django_db_blocker: Any) -> Iterator[None]:
    with django_db_blocker.unblock(), connection.cursor() as cursor:
        cursor.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        (is_superuser,) = cursor.fetchone()
        if is_superuser:
            cursor.execute(
                f"""
                DO $$ BEGIN
                  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
                    CREATE ROLE {APP_ROLE} NOSUPERUSER NOBYPASSRLS;
                  END IF;
                END $$;
                GRANT USAGE ON SCHEMA public TO {APP_ROLE};
                GRANT ALL ON ALL TABLES IN SCHEMA public TO {APP_ROLE};
                GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE};
                """
            )
            cursor.execute(f"SET ROLE {APP_ROLE}")
            connection_created.connect(_use_app_role, weak=False)
    yield


# ---------- tokens and clients ----------


def make_token(sub: str, **overrides: Any) -> str:
    cfg = settings.JWT
    now = int(time.time())
    claims = {
        "iss": cfg["ISSUER"],
        "aud": cfg["AUDIENCE"],
        "sub": sub,
        "iat": now,
        "exp": now + 3600,
        "email": f"{sub}@example.test",
    }
    claims.update(overrides)
    return jwt.encode(claims, cfg["SECRET"], algorithm="HS256")


def client_for(sub: str, tenant_id: UUID | str | None) -> APIClient:
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {make_token(sub)}",
        **({"HTTP_X_TENANT_ID": str(tenant_id)} if tenant_id else {}),
    )
    return client


# ---------- tenants ----------


@dataclass
class World:
    tenant_id: UUID
    site_id: UUID
    other_site_id: UUID
    slug: str

    def sub(self, role: str) -> str:
        return f"{self.slug}-{role}"

    def client(self, role: str = "owner") -> APIClient:
        return client_for(self.sub(role), self.tenant_id)

    def membership_id(self, role: str) -> UUID:
        from modules.users.models import Membership

        subject = f"{settings.JWT['ISSUER']}|{self.sub(role)}"
        with tenant_scope(self.tenant_id):
            return Membership.objects.get(user__auth_subject=subject).id


def build_world(slug: str) -> World:
    """A tenant with two sites open 08:00-20:00 every day, and one person per role:
    owner, admin (tenant-wide), staff (first site only), member, member2, guest."""
    tenant = tenancy.create_tenant(slug=slug, name=slug.title(), timezone_name=TZ)
    with tenant_scope(tenant.id):
        users.bootstrap_roles(tenant_id=tenant.id)
        sites = []
        for code in ("main", "second"):
            site = resources.create_location(
                tenant_id=tenant.id, code=code, name=code.title(), timezone_name=TZ
            )
            availability.set_weekly_hours(
                tenant_id=tenant.id,
                location_id=site.id,
                hours={d: [(dtime(8), dtime(20))] for d in range(7)},
            )
            sites.append(site)
        for role, code, site in (
            ("owner", "owner", None),
            ("admin", "admin", None),
            ("staff", "staff", sites[0].id),
            ("member", "member", None),
            ("member2", "member", None),
            ("guest", "guest", None),
        ):
            user = users.get_or_create_user(
                issuer=settings.JWT["ISSUER"], subject=f"{slug}-{role}", email=None
            )
            users.add_member(tenant_id=tenant.id, user_id=user.id, role_code=code, location_id=site)
    return World(tenant_id=tenant.id, site_id=sites[0].id, other_site_id=sites[1].id, slug=slug)


@pytest.fixture
def world(db: None) -> World:
    return build_world("alpha")


@pytest.fixture
def world_b(db: None) -> World:
    return build_world("beta")


# ---------- resource types, resources, times ----------

FLOW_INSTANT = {
    "confirmation": "instant",
    "checkIn": {"required": True, "opensMinutesBefore": 15, "noShowAfterMinutes": 15},
    "cancellation": {"allowedUntilMinutesBefore": 60},
}
FLOW_APPROVAL = {**FLOW_INSTANT, "confirmation": "approval"}


def create_type(world: World, key: str = "meeting_room", **extra: Any) -> dict[str, Any]:
    body = {
        "key": key,
        "label": key.replace("_", " ").title(),
        "fields": extra.pop("fields", []),
        "flowConfig": extra.pop("flowConfig", FLOW_INSTANT),
    }
    response = world.client("owner").post("/api/v1/resource-types", body, format="json")
    assert response.status_code == 201, response.json()
    return response.json()


def create_resource(
    world: World, type_id: str, label: str = "Room A", site_id: UUID | None = None, **values: Any
) -> dict[str, Any]:
    response = world.client("owner").post(
        "/api/v1/resources",
        {
            "resourceTypeId": type_id,
            "siteId": str(site_id or world.site_id),
            "label": label,
            "customFieldValues": values,
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    return response.json()


def local(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, dtime(hour, minute), tzinfo=ZoneInfo(TZ))


@pytest.fixture
def day() -> date:
    """A day a week ahead: inside the booking window, never in the past."""
    return datetime.now(ZoneInfo(TZ)).date() + timedelta(days=7)


def book(
    world: World,
    resource_id: str,
    start: datetime,
    end: datetime,
    role: str = "member",
    key: str | None = None,
    **body: Any,
) -> Any:
    payload = {"resourceId": resource_id, "start": start.isoformat(), "end": end.isoformat()}
    payload.update(body)
    return world.client(role).post(
        "/api/v1/bookings",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY=key or f"k-{start.isoformat()}-{resource_id}-{role}",
    )


@pytest.fixture
def freeze(monkeypatch: pytest.MonkeyPatch) -> Callable[[datetime], None]:
    """Pin "now" for the engine (django.utils.timezone.now)."""
    from django.utils import timezone as dj_timezone

    def at(moment: datetime) -> None:
        monkeypatch.setattr(dj_timezone, "now", lambda: moment)

    return at
