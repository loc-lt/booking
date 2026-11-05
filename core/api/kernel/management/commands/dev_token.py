"""Mint a JWT signed with JWT_SECRET, for local runs and frontend testing against the real
API. Refuses to run when DEBUG is off: real tokens come from the auth service.

    python manage.py dev_token --sub owner-1 --email owner@demo.test
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from kernel.devtokens import NotInDebug, mint


class Command(BaseCommand):
    help = "Print a development JWT (DEBUG only)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--sub", required=True)
        parser.add_argument("--email", default=None)
        parser.add_argument("--name", default="")
        parser.add_argument("--hours", type=int, default=12)

    def handle(self, *args: Any, **o: Any) -> None:
        try:
            token = mint(o["sub"], email=o["email"], name=o["name"], hours=o["hours"])
        except NotInDebug as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(token)
