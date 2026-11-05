"""Print a fresh invitation or password-reset link, for local runs without a mail server.

python manage.py auth_link invitation --tenant <tenantId> --member <memberId>
python manage.py auth_link reset --email someone@demo.test
"""

from datetime import timedelta
from typing import Any
from uuid import UUID

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from kernel.tenant_context import activate_tenant
from modules.identity import service
from modules.identity.models import LinkPurpose
from modules.users import service as users


class Command(BaseCommand):
    help = "Print an invitation or password-reset link (DEBUG only)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("kind", choices=["invitation", "reset"])
        parser.add_argument("--tenant", type=UUID)
        parser.add_argument("--member", type=UUID)
        parser.add_argument("--email")

    @transaction.atomic
    def handle(self, *args: Any, **o: Any) -> None:
        if not settings.DEBUG:
            raise CommandError("auth_link only runs with DJANGO_DEBUG=true.")
        if o["kind"] == "reset":
            user = users.find_user_by_email(o["email"] or "")
            if user is None:
                raise CommandError("No user with this email.")
            link = service.issue_link(
                purpose=LinkPurpose.PASSWORD_RESET, user=user, ttl=timedelta(hours=1)
            )
        else:
            if not (o["tenant"] and o["member"]):
                raise CommandError("invitation needs --tenant and --member.")
            activate_tenant(o["tenant"])
            member = users.get_member(o["member"])
            link = service.issue_link(
                purpose=LinkPurpose.INVITATION,
                user=member.user,
                ttl=timedelta(days=7),
                tenant_id=o["tenant"],
                membership_id=member.id,
            )
        self.stdout.write(link)
