from django.db import models
from django.utils import timezone

from kernel.uuid7 import uuid7


class TenantStatus(models.TextChoices):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class Tenant(models.Model):
    """One customer organisation. The root of row-level security: this table has no RLS."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    slug = models.TextField(unique=True)
    name = models.TextField()
    status = models.TextField(choices=TenantStatus.choices, default=TenantStatus.ACTIVE)
    default_timezone = models.TextField(default="Asia/Ho_Chi_Minh")
    default_locale = models.TextField(default="vi")
    default_currency = models.CharField(max_length=3, default="VND")
    settings = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenants"

    def __str__(self) -> str:
        return self.slug
