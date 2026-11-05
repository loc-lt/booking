"""Versioned configuration: booking policies and custom fields (docs/domain/configuration.md).

Published rows are never edited. A change publishes a new version; bookings keep pointing at
the version they were made under.
"""

from django.db import models
from django.utils import timezone

from kernel.models import TenantModel
from kernel.uuid7 import uuid7


class VersionStatus(models.TextChoices):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"


class PolicyVersion(models.Model):
    """One version of a resource type's policies. body: see modules/config/policy.py."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.PROTECT, related_name="+", db_index=False
    )
    resource_type = models.ForeignKey(
        "resources.ResourceType", on_delete=models.PROTECT, related_name="policy_versions"
    )
    version = models.IntegerField()
    body = models.JSONField()
    status = models.TextField(choices=VersionStatus.choices)
    based_on_version = models.IntegerField(null=True, blank=True)
    created_by_membership_id = models.UUIDField(null=True, blank=True)
    published_by_membership_id = models.UUIDField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "policy_versions"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "resource_type", "version"], name="policy_versions_version"
            ),
            models.UniqueConstraint(fields=["tenant", "id"], name="policy_versions_tenant_id"),
        ]


class CustomObject(models.TextChoices):
    LOCATION = "location"
    RESOURCE = "resource"
    BOOKING = "booking"
    CUSTOMER = "customer"
    PAYMENT = "payment"


class FieldStatus(models.TextChoices):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class FieldDefinition(TenantModel):
    """One custom field. Adding a field is an INSERT here, never an ALTER TABLE.

    Contract mapping: scope `resource`/`booking` -> object_code; `type` -> data_type;
    `label`/`help` -> label/help_text as {"default": ...}; `options` and `validation` are
    kept in config exactly as the contract sends them.
    """

    object_code = models.TextField(choices=CustomObject.choices)
    resource_type = models.ForeignKey(
        "resources.ResourceType",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="field_definitions",
    )
    key = models.TextField()
    label = models.JSONField()
    help_text = models.JSONField(null=True, blank=True)
    data_type = models.TextField()
    config = models.JSONField(default=dict)
    required = models.BooleanField(default=False)
    is_unique = models.BooleanField(default=False)
    visibility = models.TextField(default="all")
    editable_by = models.TextField(default="all")
    section = models.TextField(null=True, blank=True)
    position = models.IntegerField(default=0)
    analytics = models.BooleanField(default=False)
    status = models.TextField(choices=FieldStatus.choices, default=FieldStatus.PUBLISHED)
    created_by_membership_id = models.UUIDField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "field_definitions"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "object_code", "resource_type", "key"],
                name="field_definitions_key",
                nulls_distinct=False,
            ),
            models.UniqueConstraint(fields=["tenant", "id"], name="field_definitions_tenant_id"),
        ]


class ObjectSchemaVersion(models.Model):
    """Immutable snapshot of a form, compiled to JSON Schema at publish time. Every record
    with custom fields points at the snapshot it was validated against (schema_id)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.PROTECT, related_name="+", db_index=False
    )
    object_code = models.TextField(choices=CustomObject.choices)
    resource_type = models.ForeignKey(
        "resources.ResourceType", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    version = models.IntegerField()
    json_schema = models.JSONField()
    ui_schema = models.JSONField()
    published_by_membership_id = models.UUIDField(null=True, blank=True)
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "object_schema_versions"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "object_code", "resource_type", "version"],
                name="object_schema_versions_version",
                nulls_distinct=False,
            ),
            models.UniqueConstraint(
                fields=["tenant", "id"], name="object_schema_versions_tenant_id"
            ),
        ]
