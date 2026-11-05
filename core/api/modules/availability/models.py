from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models
from django.utils import timezone

from kernel.uuid7 import uuid7


class AvailabilityRule(models.Model):
    """Weekly opening hours in the site's local time. Exactly one of location/resource is set;
    a resource's own rules replace its site's rules."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.PROTECT, related_name="+", db_index=False
    )
    location = models.ForeignKey(
        "resources.Location", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    resource = models.ForeignKey(
        "resources.Resource", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    weekday = models.SmallIntegerField()  # 0 = Monday ... 6 = Sunday
    start_local = models.TimeField()
    end_local = models.TimeField()
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "availability_rules"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_local__lt=models.F("end_local")),
                name="availability_rules_order",
            ),
            models.CheckConstraint(
                condition=models.Q(weekday__gte=0, weekday__lte=6),
                name="availability_rules_weekday",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(location__isnull=False, resource__isnull=True)
                    | models.Q(location__isnull=True, resource__isnull=False)
                ),
                name="availability_rules_one_target",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "resource"], name="avail_rules_resource"),
            models.Index(fields=["tenant", "location"], name="avail_rules_location"),
        ]


class ExceptionKind(models.TextChoices):
    OPEN = "OPEN"  # extra opening outside the weekly hours
    BLOCK = "BLOCK"  # holiday, maintenance, private event


class AvailabilityException(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.PROTECT, related_name="+", db_index=False
    )
    location = models.ForeignKey(
        "resources.Location", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    resource = models.ForeignKey(
        "resources.Resource", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    kind = models.TextField(choices=ExceptionKind.choices)
    during = DateTimeRangeField()
    reason_code = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    created_by_membership_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "availability_exceptions"
