"""Rule storage: one immutable snapshot per publish (like object_schema_versions).

Publishing replaces the whole rule set with a new version; bookings record the version they
were checked against (transition_log.rule_versions, Booking.appliedConfig.ruleSetVersion).
This table is outside the 24 MVP tables (docs/database): see the README's open decisions.
"""

from django.db import models
from django.utils import timezone

from kernel.uuid7 import uuid7


class RuleSetVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.PROTECT, related_name="+", db_index=False
    )
    version = models.IntegerField()
    rules = models.JSONField(default=list)  # contract Rule objects, as published
    note = models.TextField(null=True, blank=True)
    published_by_membership_id = models.UUIDField(null=True, blank=True)
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "rule_set_versions"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "version"], name="rule_set_versions_version"),
            models.UniqueConstraint(fields=["tenant", "id"], name="rule_set_versions_tenant_id"),
            models.CheckConstraint(
                condition=models.Q(version__gt=0), name="rule_set_versions_positive"
            ),
        ]
