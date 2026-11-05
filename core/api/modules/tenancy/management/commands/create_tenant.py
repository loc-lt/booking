"""Create a tenant with its system roles, one site with weekly hours, and an owner.

The contract has no API for tenants, sites or members yet, so this is how a tenant starts:

    python manage.py create_tenant --slug demo --name "Demo Co" \\
        --owner-sub owner-1 --owner-email owner@demo.test \\
        --site-code hq --site-name "Head site" --timezone Asia/Ho_Chi_Minh

Prints the ids the frontend needs (X-Tenant-Id, siteId).
"""

from datetime import time
from typing import Any
from uuid import UUID

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from kernel.tenant_context import activate_tenant
from modules.availability import service as availability
from modules.resources import service as resources
from modules.tenancy import service as tenancy
from modules.users import service as users


class Command(BaseCommand):
    help = "Create a tenant, its roles, a site with opening hours, and its owner."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--tenant-id",
            type=UUID,
            default=None,
            help="Fixed id, e.g. the DEMO_TENANT_ID the apps use before auth is wired up",
        )
        parser.add_argument("--slug", required=True)
        parser.add_argument("--name", required=True)
        parser.add_argument("--owner-sub", required=True, help="`sub` claim of the owner's JWT")
        parser.add_argument("--owner-email", default=None)
        parser.add_argument("--site-code", default="main")
        parser.add_argument("--site-name", default="Main site")
        parser.add_argument("--timezone", default="Asia/Ho_Chi_Minh")
        parser.add_argument("--opens", default="08:00")
        parser.add_argument("--closes", default="20:00")

    @transaction.atomic
    def handle(self, *args: Any, **o: Any) -> None:
        tenant = tenancy.create_tenant(
            slug=o["slug"],
            name=o["name"],
            timezone_name=o["timezone"],
            tenant_id=o["tenant_id"],
        )
        activate_tenant(tenant.id)
        users.bootstrap_roles(tenant_id=tenant.id)
        site = resources.create_location(
            tenant_id=tenant.id,
            code=o["site_code"],
            name=o["site_name"],
            timezone_name=o["timezone"],
        )
        opens, closes = time.fromisoformat(o["opens"]), time.fromisoformat(o["closes"])
        availability.set_weekly_hours(
            tenant_id=tenant.id,
            location_id=site.id,
            hours={weekday: [(opens, closes)] for weekday in range(7)},
        )
        owner = users.get_or_create_user(
            issuer=settings.JWT["ISSUER"], subject=o["owner_sub"], email=o["owner_email"]
        )
        membership = users.add_member(tenant_id=tenant.id, user_id=owner.id, role_code="owner")
        self.stdout.write(f"tenantId     {tenant.id}")
        self.stdout.write(f"siteId       {site.id}")
        self.stdout.write(f"membershipId {membership.id}")
