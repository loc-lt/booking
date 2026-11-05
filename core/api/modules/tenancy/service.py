"""Public interface of the tenancy module."""

from uuid import UUID

from django.db import transaction

from modules.tenancy.models import Tenant, TenantStatus


@transaction.atomic
def create_tenant(
    *,
    slug: str,
    name: str,
    timezone_name: str,
    currency: str = "VND",
    tenant_id: UUID | None = None,
) -> Tenant:
    return Tenant.objects.create(
        **({"id": tenant_id} if tenant_id else {}),
        slug=slug,
        name=name,
        status=TenantStatus.ACTIVE,
        default_timezone=timezone_name,
        default_currency=currency,
    )


def get_tenant(tenant_id: UUID) -> Tenant:
    return Tenant.objects.get(id=tenant_id)


def tenant_currency(tenant_id: UUID) -> str:
    return Tenant.objects.values_list("default_currency", flat=True).get(id=tenant_id)
