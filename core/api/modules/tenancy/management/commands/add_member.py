"""Add a person to a tenant with a role (owner, admin, staff, member, guest), optionally
limited to one site. No API for members yet.

    python manage.py add_member --tenant <id> --sub member-1 --role member
    python manage.py add_member --tenant <id> --sub staff-1 --role staff --site <siteId>
"""

from typing import Any
from uuid import UUID

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from kernel.tenant_context import activate_tenant
from modules.users import service as users


class Command(BaseCommand):
    help = "Add a member to a tenant."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--tenant", required=True, type=UUID)
        parser.add_argument("--sub", required=True)
        parser.add_argument("--email", default=None)
        parser.add_argument("--role", default="member")
        parser.add_argument("--site", type=UUID, default=None)

    @transaction.atomic
    def handle(self, *args: Any, **o: Any) -> None:
        activate_tenant(o["tenant"])
        user = users.get_or_create_user(
            issuer=settings.JWT["ISSUER"], subject=o["sub"], email=o["email"]
        )
        membership = users.add_member(
            tenant_id=o["tenant"], user_id=user.id, role_code=o["role"], location_id=o["site"]
        )
        self.stdout.write(f"membershipId {membership.id}")
