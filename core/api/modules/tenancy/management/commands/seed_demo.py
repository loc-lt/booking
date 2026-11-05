"""A ready-to-use tenant for demos, manual testing and the Postman scenario.

    python manage.py seed_demo                  # full demo: sites, types, resources, rules
    python manage.py seed_demo --bare --json    # tenant, roles, one site, people; JSON out
    python manage.py seed_demo --tenant-id 0193f4c1-0000-7000-8000-000000000002

People: owner (Minh Anh, owner), staff (Hà, front desk at the first site only), lan and tuan
(members), guest (Khách). Each signs in with email <slug>-<who>@demo.test and the one random
password printed per run (POST /auth/login). With DEBUG on, a 12-hour dev token per person
is printed too (sub = <slug>-<who>; never in production).

Everything goes through the same service functions as the API, so the demo data obeys the
same checks, versions and events as data made by hand.
"""

import json
import secrets
from datetime import time
from typing import Any
from uuid import UUID

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from kernel.devtokens import NotInDebug, mint
from kernel.tenant_context import activate_tenant
from modules.availability import service as availability
from modules.identity import service as identity
from modules.resources import service as resources
from modules.rules import service as rules
from modules.tenancy import service as tenancy
from modules.users import service as users

TZ = "Asia/Ho_Chi_Minh"

PEOPLE = [
    # who, display name, role, site index (None = whole tenant)
    ("owner", "Minh Anh", "owner", None),
    ("staff", "Hà (lễ tân)", "staff", 0),
    ("lan", "Lan", "member", None),
    ("tuan", "Tuấn", "member", None),
    ("guest", "Khách", "guest", None),
]

# Check-in opens 30 minutes ahead: a demo can always book "the next slot" and check in.
CHECK_IN = {"required": True, "opensMinutesBefore": 30, "noShowAfterMinutes": 15}

TYPES: list[dict[str, Any]] = [
    {
        "key": "meeting_room",
        "label": "Phòng họp",
        "slot": 30,
        "fields": [
            {
                "key": "seats",
                "label": "Số ghế",
                "type": "integer",
                "validation": {"min": 1, "max": 50},
            },
            {"key": "has_tv", "label": "Có TV", "type": "boolean"},
            {
                "key": "attendee_count",
                "label": "Số người tham dự",
                "type": "integer",
                "scope": "booking",
                "required": True,
                "validation": {"min": 1, "max": 50},
            },
            {
                "key": "purpose",
                "label": "Mục đích",
                "type": "select",
                "scope": "booking",
                "options": [
                    {"value": "meeting", "label": "Họp nội bộ"},
                    {"value": "client", "label": "Gặp khách hàng"},
                    {"value": "interview", "label": "Phỏng vấn"},
                ],
            },
        ],
        "flow": {
            "confirmation": "instant",
            "checkIn": CHECK_IN,
            "cancellation": {"allowedUntilMinutesBefore": 60},
            "limits": {"maxDurationMinutes": 240},
        },
        "resources": [
            ("Phòng Sài Gòn", 0, {"seats": 8, "has_tv": True}),
            ("Phòng Hà Nội", 0, {"seats": 4, "has_tv": False}),
            ("Phòng Hoàn Kiếm", 1, {"seats": 6, "has_tv": True}),
        ],
    },
    {
        "key": "hot_desk",
        "label": "Bàn linh hoạt",
        "slot": 60,
        "fields": [],
        "flow": {
            "confirmation": "instant",
            # Opens 60 min ahead: the demo books the next whole hour and checks in.
            "checkIn": {"required": False, "opensMinutesBefore": 60, "noShowAfterMinutes": 15},
            "cancellation": {"allowedUntilMinutesBefore": 0},
        },
        "resources": [("Bàn 01", 0, {}), ("Bàn 02", 0, {}), ("Bàn 01 HN", 1, {})],
    },
    {
        "key": "event_hall",
        "label": "Hội trường",
        "slot": 60,
        "fields": [],
        "flow": {
            "confirmation": "approval",
            "checkIn": CHECK_IN,
            "cancellation": {"allowedUntilMinutesBefore": 0},
            "payment": {
                "mode": "upfront",
                "amountMinor": 500000,
                "per": "hour",
                "holdMinutes": 15,
                "refundRules": [
                    {"minutesBefore": 2880, "percent": 100},
                    {"minutesBefore": 0, "percent": 50},
                ],
            },
        },
        "resources": [("Hội trường lớn", 0, {})],
    },
]


def _rules(site_id: UUID) -> list[dict[str, Any]]:
    return [
        {
            "id": "guests-max-2h",
            "name": "Khách vãng lai đặt tối đa 2 giờ",
            "scope": {"resourceType": "meeting_room"},
            "stage": "limits",
            "priority": 10,
            "when": {"in": ["guest", {"var": "user.groups"}]},
            "effect": {"type": "max_duration", "minutes": 120},
        },
        {
            "id": "members-3-per-day",
            "name": "Mỗi thành viên tối đa 3 lượt mỗi ngày",
            "stage": "limits",
            "when": {"in": ["member", {"var": "user.groups"}]},
            "effect": {"type": "quota", "per": "day", "maxBookings": 3},
        },
        {
            "id": "q1-long-needs-approval",
            "name": "Ở Quận 1, đặt trên 3 giờ cần duyệt",
            "scope": {"siteId": str(site_id)},
            "stage": "approval",
            "when": {">": [{"var": "booking.durationMinutes"}, 180]},
            "effect": {"type": "require_approval"},
        },
    ]


class Command(BaseCommand):
    help = "Create a demo tenant with sites, resource types, resources, rules and people."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--tenant-id", type=UUID, default=None)
        parser.add_argument("--slug", default=None)
        parser.add_argument("--bare", action="store_true", help="No types, resources or rules")
        parser.add_argument("--json", action="store_true", help="Print one JSON object")

    @transaction.atomic
    def handle(self, *args: Any, **o: Any) -> None:
        slug = o["slug"] or f"demo-{secrets.token_hex(3)}"
        tenant = tenancy.create_tenant(
            slug=slug, name=f"The Rise demo ({slug})", timezone_name=TZ, tenant_id=o["tenant_id"]
        )
        activate_tenant(tenant.id)
        users.bootstrap_roles(tenant_id=tenant.id)
        sites = [
            resources.create_location(
                tenant_id=tenant.id,
                code="q1",
                name="The Rise Quận 1",
                timezone_name=TZ,
                address={"city": "Hồ Chí Minh"},
            ),
        ]
        if not o["bare"]:
            sites.append(
                resources.create_location(
                    tenant_id=tenant.id,
                    code="hn",
                    name="The Rise Hà Nội",
                    timezone_name=TZ,
                    address={"city": "Hà Nội"},
                )
            )
        for site in sites:
            availability.set_weekly_hours(
                tenant_id=tenant.id,
                location_id=site.id,
                hours={d: [(time(6), time(23))] for d in range(7)},
            )
        # One random password for every person of this demo tenant, printed below: they can
        # sign in with POST /auth/login (email <slug>-<who>@demo.test).
        password = f"Demo-{secrets.token_urlsafe(9)}"
        people: dict[str, dict[str, str]] = {}
        for who, name, role, site_index in PEOPLE:
            sub = f"{slug}-{who}"
            user = users.get_or_create_user(
                issuer=settings.JWT["ISSUER"], subject=sub, email=f"{sub}@demo.test", name=name
            )
            membership = users.add_member(
                tenant_id=tenant.id,
                user_id=user.id,
                role_code=role,
                location_id=sites[site_index].id if site_index is not None else None,
                display_name=name,
            )
            identity.set_password(user, password)
            people[who] = {
                "sub": sub,
                "email": f"{sub}@demo.test",
                "memberId": str(membership.id),
                "role": role,
            }

        out: dict[str, Any] = {
            "tenantId": str(tenant.id),
            "slug": slug,
            "sites": {s.code: str(s.id) for s in sites},
            "people": people,
            "password": password,
            "resourceTypes": {},
            "resources": {},
        }
        if not o["bare"]:
            owner = UUID(people["owner"]["memberId"])
            for spec in TYPES:
                rt = resources.create_resource_type(
                    tenant_id=tenant.id,
                    key=spec["key"],
                    label=spec["label"],
                    fields=spec["fields"],
                    flow_config=spec["flow"],
                    membership_id=owner,
                    slot_minutes=spec["slot"],
                )
                out["resourceTypes"][spec["key"]] = str(rt.id)
                for label, site_index, values in spec["resources"]:
                    r = resources.create_resource(
                        tenant_id=tenant.id,
                        resource_type_id=rt.id,
                        location_id=sites[site_index].id,
                        label=label,
                        custom_field_values=values,
                        membership_id=owner,
                    )
                    out["resources"][label] = str(r.id)
            published = rules.publish(
                tenant_id=tenant.id,
                base_version=0,
                rules=_rules(sites[0].id),
                note="Demo rules",
                membership_id=owner,
                site_exists=lambda v: True,
                type_key_exists=lambda v: True,
                resource_exists=lambda v: True,
            )
            out["ruleSetVersion"] = published.version

        try:
            for person in people.values():
                person["token"] = mint(person["sub"], email=f"{person['sub']}@demo.test")
            out["tokensValidHours"] = 12
        except NotInDebug:
            out["tokens"] = "Run with DJANGO_DEBUG=true (app.settings.local) to print tokens."

        if o["json"]:
            self.stdout.write(json.dumps(out, indent=2))
            return
        self.stdout.write(f"tenantId   {out['tenantId']}  ({slug})")
        for code, sid in out["sites"].items():
            self.stdout.write(f"site {code:<5} {sid}")
        for key, tid in out["resourceTypes"].items():
            self.stdout.write(f"type {key:<13} {tid}")
        for label, rid in out["resources"].items():
            self.stdout.write(f"resource {label:<16} {rid}")
        self.stdout.write(f"password   {password}   (same for everyone below; POST /auth/login)")
        for who, person in people.items():
            self.stdout.write(
                f"{who:<6} {person['role']:<7} {person['email']:<32} memberId {person['memberId']}"
            )
            if "token" in person:
                self.stdout.write(f"       token {person['token']}")
