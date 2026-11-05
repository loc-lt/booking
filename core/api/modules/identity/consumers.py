"""Sends the invitation email for member.invited, from the worker.

The link's secret is created here and goes only into the email, never into the outbox or a
log. Local runs print the email to the worker's log (console email backend):
`python scripts/dev.py logs worker`, or `python scripts/dev.py manage auth_link ...`.
"""

from typing import Any
from uuid import UUID

from modules.events.service import subscribe
from modules.identity import service
from modules.tenancy import service as tenancy


@subscribe("invitation_mailer", ["member.invited"])
def send_invitation(event: dict[str, Any]) -> None:
    email = (event.get("data") or {}).get("email")
    if not email:
        return
    tenant = tenancy.get_tenant(UUID(event["tenantId"]))
    service.send_invitation(
        tenant_id=tenant.id,
        membership_id=UUID(event["subject"]["id"]),
        email=email,
        tenant_name=tenant.name,
    )
