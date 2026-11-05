from django.contrib.postgres.indexes import GinIndex
from django.db import models

from kernel.models import TenantModel


class ActiveStatus(models.TextChoices):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class Location(TenantModel):
    """A site: a physical place of the tenant with its own timezone. The contract calls it
    `site` (siteId)."""

    code = models.TextField()
    name = models.TextField()
    timezone = models.TextField()  # IANA; every local time is computed with it
    address = models.JSONField(default=dict)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.TextField(choices=ActiveStatus.choices, default=ActiveStatus.ACTIVE)
    attributes = models.JSONField(default=dict)
    schema = models.ForeignKey(
        "config.ObjectSchemaVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "locations"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="locations_tenant_code"),
            models.UniqueConstraint(fields=["tenant", "id"], name="locations_tenant_id"),
        ]


class BookingMode(models.TextChoices):
    EXCLUSIVE = "EXCLUSIVE"  # one booking per time range
    CAPACITY = "CAPACITY"  # several identical seats, counted per slot (after December)
    ACCESS_PASS = "ACCESS_PASS"  # noqa: S105  (a booking mode, not a password)


class ResourceType(TenantModel):
    """Template for bookable things. The contract's `key`/`label` are `code`/`name` here;
    its `flowConfig` and `version` come from the current policy version."""

    code = models.TextField()
    name = models.TextField()
    booking_mode = models.TextField(choices=BookingMode.choices, default=BookingMode.EXCLUSIVE)
    slot_minutes = models.IntegerField(null=True, blank=True, default=30)
    full_day = models.BooleanField(default=False)
    status_labels = models.JSONField(default=dict)
    current_policy_version = models.ForeignKey(
        "config.PolicyVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    icon = models.TextField(null=True, blank=True)
    position = models.IntegerField(default=0)
    status = models.TextField(choices=ActiveStatus.choices, default=ActiveStatus.ACTIVE)

    class Meta:
        db_table = "resource_types"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="resource_types_tenant_code"),
            models.UniqueConstraint(fields=["tenant", "id"], name="resource_types_tenant_id"),
        ]


class ResourceStatus(models.TextChoices):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"
    ARCHIVED = "ARCHIVED"


class Resource(TenantModel):
    """One bookable thing. Contract: `label` = name, `siteId` = location,
    `customFieldValues` = attributes."""

    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="resources")
    resource_type = models.ForeignKey(
        ResourceType, on_delete=models.PROTECT, related_name="resources"
    )
    code = models.TextField()
    name = models.TextField()
    description = models.TextField(null=True, blank=True)
    capacity = models.IntegerField(default=1)
    status = models.TextField(choices=ResourceStatus.choices, default=ResourceStatus.ACTIVE)
    position = models.IntegerField(default=0)
    attributes = models.JSONField(default=dict)
    schema = models.ForeignKey(
        "config.ObjectSchemaVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "resources"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "location", "code"], name="resources_tenant_location_code"
            ),
            models.UniqueConstraint(fields=["tenant", "id"], name="resources_tenant_id"),
            models.CheckConstraint(condition=models.Q(capacity__gt=0), name="resources_capacity"),
        ]
        indexes = [
            models.Index(fields=["tenant", "location", "status"], name="resources_location_status"),
            models.Index(fields=["tenant", "resource_type"], name="resources_type"),
            GinIndex(
                fields=["attributes"], name="resources_attr_gin", opclasses=["jsonb_path_ops"]
            ),
        ]
