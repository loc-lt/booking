"""Public interface of the resources module: sites, resource types, resources."""

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import transaction
from django.db.models import QuerySet

from kernel.errors import InvalidTransition, NotFound, StaleVersion, ValidationFailed
from kernel.history import record_status
from modules.config import service as config
from modules.events import service as events
from modules.resources.models import (
    ActiveStatus,
    Location,
    Resource,
    ResourceStatus,
    ResourceType,
)

# ---------- sites ----------


def _slug(label: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:40]
    return slug or fallback


def check_timezone(name: str, field: str = "timezone") -> str:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValidationFailed.one(field, "Not an IANA timezone, e.g. Asia/Ho_Chi_Minh.") from None
    return name


@transaction.atomic
def create_location(
    *,
    tenant_id: UUID,
    code: str | None = None,
    name: str,
    timezone_name: str,
    address: dict[str, Any] | None = None,
) -> Location:
    """POST /sites and the create_tenant command (API_KICH_BAN.md 4.1)."""
    check_timezone(timezone_name)
    code = code or _slug(name, "site")
    if Location.objects.filter(code=code).exists():
        raise ValidationFailed.one("code", "A site with this code already exists.")
    return Location.objects.create(
        tenant_id=tenant_id,
        code=code,
        name=name,
        timezone=timezone_name,
        address=address or {},
    )


@transaction.atomic
def update_location(
    *, location_id: UUID, name: str | None, address: dict[str, Any] | None
) -> Location:
    """Timezone is fixed once a site exists: every stored local date depends on it."""
    location = get_location(location_id)
    if name is not None:
        location.name = name
    if address is not None:
        location.address = address
    location.save(update_fields=["name", "address", "updated_at"])
    return location


def get_location(location_id: UUID) -> Location:
    try:
        return Location.objects.get(id=location_id)
    except Location.DoesNotExist:
        raise NotFound("No site with this id.") from None


def list_locations_qs() -> QuerySet[Location]:
    return Location.objects.exclude(status=ActiveStatus.ARCHIVED)


# ---------- resource types ----------


def _actor(membership_id: UUID | None) -> dict[str, str]:
    return events.user_actor(membership_id) if membership_id else events.SYSTEM


def check_slot_minutes(value: int | None) -> int | None:
    if value is None:
        return None
    if not 5 <= value <= 240 or 1440 % value:
        raise ValidationFailed.one(
            "slotMinutes", "Use a length that divides a day: 5, 10, 15, 20, 30, 60, 120..."
        )
    return value


def _config_published(
    resource_type: ResourceType,
    membership_id: UUID | None,
    changes: dict[str, Any],
    versions: dict[str, int],
) -> None:
    events.emit_event(
        tenant_id=resource_type.tenant_id,
        name="config.published",
        subject_type="resource_type",
        subject_id=resource_type.id,
        actor=_actor(membership_id),
        changes=changes,
        config_versions=versions,
    )


@transaction.atomic
def create_resource_type(
    *,
    tenant_id: UUID,
    key: str,
    label: str,
    fields: list[dict[str, Any]],
    flow_config: dict[str, Any],
    membership_id: UUID | None,
    slot_minutes: int | None = 30,
) -> ResourceType:
    """One transaction: resource_types, policy_versions v1, field_definitions,
    object_schema_versions, outbox config.published (API_KICH_BAN.md 4.4)."""
    if ResourceType.objects.filter(tenant_id=tenant_id, code=key).exists():
        raise ValidationFailed.one("key", "A resource type with this key already exists.")
    resource_type = ResourceType.objects.create(
        tenant_id=tenant_id,
        code=key,
        name=label,
        slot_minutes=check_slot_minutes(slot_minutes) if slot_minutes is not None else 30,
    )
    policy = config.publish_policy(
        tenant_id=tenant_id,
        resource_type_id=resource_type.id,
        flow_config=flow_config,
        base=None,
        membership_id=membership_id,
    )
    config.publish_fields(
        tenant_id=tenant_id,
        resource_type_id=resource_type.id,
        fields=fields,
        membership_id=membership_id,
        target_type_exists=lambda rt_id: (
            rt_id == resource_type.id or ResourceType.objects.filter(id=rt_id).exists()
        ),
    )
    resource_type.current_policy_version_id = policy.id
    resource_type.save(update_fields=["current_policy_version", "updated_at"])
    _config_published(
        resource_type,
        membership_id,
        {"policyVersion": {"from": None, "to": policy.version}},
        {"flowConfig": policy.version},
    )
    return resource_type


@transaction.atomic
def update_flow_config(
    *,
    resource_type_id: UUID,
    base_version: int,
    flow_config: dict[str, Any],
    membership_id: UUID | None,
    label: str | None = None,
    slot_minutes: int | None = None,
) -> ResourceType:
    """Publish a new policy version. Stale baseVersion -> STALE_VERSION. Bookings already
    made keep pointing at their own policy version (API_KICH_BAN.md 4.5). An edit that
    changes nothing in the policy publishes nothing."""
    resource_type = _lock_type(resource_type_id)
    current = config.get_policy(resource_type.current_policy_version_id)
    if base_version != current.version:
        raise StaleVersion(
            f"This edit is based on version {base_version}; the current version is "
            f"{current.version}."
        )
    fields = ["updated_at"]
    if label is not None and label != resource_type.name:
        resource_type.name = label
        fields.append("name")
    if slot_minutes is not None and slot_minutes != resource_type.slot_minutes:
        resource_type.slot_minutes = check_slot_minutes(slot_minutes)
        fields.append("slot_minutes")
    body = config.body_from_flow_config(flow_config, current.body)
    if body != current.body:
        policy = config.publish_body(
            tenant_id=resource_type.tenant_id,
            resource_type_id=resource_type.id,
            body=body,
            base=current,
            membership_id=membership_id,
        )
        resource_type.current_policy_version_id = policy.id
        fields.append("current_policy_version")
        _config_published(
            resource_type,
            membership_id,
            {"policyVersion": {"from": current.version, "to": policy.version}},
            {"flowConfig": policy.version},
        )
    resource_type.save(update_fields=fields)
    return resource_type


@transaction.atomic
def restore_policy_version(
    *, resource_type_id: UUID, version: int, base_version: int, membership_id: UUID | None
) -> ResourceType:
    """Roll back: republish an earlier version's body as the newest version
    (docs/domain/configuration.md, step 5). History is never rewritten."""
    resource_type = _lock_type(resource_type_id)
    current = config.get_policy(resource_type.current_policy_version_id)
    if base_version != current.version:
        raise StaleVersion(
            f"This edit is based on version {base_version}; the current version is "
            f"{current.version}."
        )
    old = config.policy_by_version(resource_type.id, version)
    if old is None:
        raise NotFound("No policy version with this number.")
    if old.version == current.version:
        raise ValidationFailed.one("version", "This version is already the current one.")
    policy = config.publish_body(
        tenant_id=resource_type.tenant_id,
        resource_type_id=resource_type.id,
        body=dict(old.body),
        base=current,
        membership_id=membership_id,
    )
    resource_type.current_policy_version_id = policy.id
    resource_type.save(update_fields=["current_policy_version", "updated_at"])
    _config_published(
        resource_type,
        membership_id,
        {
            "policyVersion": {"from": current.version, "to": policy.version},
            "restoredFrom": old.version,
        },
        {"flowConfig": policy.version},
    )
    return resource_type


def _type_exists(rt_id: UUID) -> bool:
    return ResourceType.objects.filter(id=rt_id).exists()


@transaction.atomic
def add_fields(
    *, resource_type_id: UUID, fields: list[dict[str, Any]], membership_id: UUID | None
) -> ResourceType:
    resource_type = _lock_type(resource_type_id)
    forms = config.add_fields(
        tenant_id=resource_type.tenant_id,
        resource_type_id=resource_type.id,
        fields=fields,
        membership_id=membership_id,
        target_type_exists=_type_exists,
    )
    _config_published(
        resource_type,
        membership_id,
        {"fieldsAdded": [f["key"] for f in fields]},
        {f"form.{scope}": v for scope, v in forms.items()},
    )
    resource_type.save(update_fields=["updated_at"])
    return resource_type


@transaction.atomic
def archive_field(*, resource_type_id: UUID, key: str, membership_id: UUID | None) -> ResourceType:
    resource_type = _lock_type(resource_type_id)
    forms = config.archive_field(
        tenant_id=resource_type.tenant_id,
        resource_type_id=resource_type.id,
        key=key,
        membership_id=membership_id,
    )
    _config_published(
        resource_type,
        membership_id,
        {"fieldsArchived": [key]},
        {f"form.{scope}": v for scope, v in forms.items()},
    )
    resource_type.save(update_fields=["updated_at"])
    return resource_type


def _lock_type(resource_type_id: UUID) -> ResourceType:
    try:
        return ResourceType.objects.select_for_update().get(id=resource_type_id)
    except ResourceType.DoesNotExist:
        raise NotFound("No resource type with this id.") from None


def get_resource_type(resource_type_id: UUID) -> ResourceType:
    try:
        return ResourceType.objects.get(id=resource_type_id)
    except ResourceType.DoesNotExist:
        raise NotFound("No resource type with this id.") from None


def type_keys(resource_type_ids: list[UUID]) -> dict[UUID, str]:
    return dict(ResourceType.objects.filter(id__in=resource_type_ids).values_list("id", "code"))


@dataclass(frozen=True, slots=True)
class ResourceTypeView:
    """Everything the contract's ResourceType needs, gathered from three tables."""

    row: ResourceType
    version: int
    flow_config: dict[str, Any]
    fields: list[dict[str, Any]]


def describe_types(rows: list[ResourceType]) -> list[ResourceTypeView]:
    policies = config.get_policies([r.current_policy_version_id for r in rows])
    fields = config.fields_by_type([r.id for r in rows])
    return [
        ResourceTypeView(
            row=r,
            version=policies[r.current_policy_version_id].version,
            flow_config=config.flow_config_from_body(policies[r.current_policy_version_id].body),
            fields=fields[r.id],
        )
        for r in rows
    ]


def list_resource_types_qs() -> Any:
    return ResourceType.objects.exclude(status=ActiveStatus.ARCHIVED)


# ---------- resources ----------


def _free_code(tenant_id: UUID, location_id: UUID, label: str) -> str:
    """The contract has no `code`; derive a readable one from the label."""
    base = _slug(label, "resource")
    taken = set(
        Resource.objects.filter(
            tenant_id=tenant_id, location_id=location_id, code__startswith=base
        ).values_list("code", flat=True)
    )
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def _check_references(references: dict[str, str], values: dict[str, Any]) -> None:
    for key, target_type_id in references.items():
        ok = Resource.objects.filter(id=values[key], resource_type_id=target_type_id).exists()
        if not ok:
            raise ValidationFailed.one(
                f"customFieldValues.{key}", "No resource of the required type with this id."
            )


@transaction.atomic
def create_resource(
    *,
    tenant_id: UUID,
    resource_type_id: UUID,
    location_id: UUID,
    label: str,
    custom_field_values: dict[str, Any],
    membership_id: UUID | None,
    capacity: int = 1,
) -> Resource:
    """Values are checked against the type's latest resource form (API_KICH_BAN.md 4.7)."""
    resource_type = get_resource_type(resource_type_id)
    location = get_location(location_id)
    schema_id, references = config.validate_values(
        resource_type_id=resource_type.id, scope="resource", values=custom_field_values
    )
    _check_references(references, custom_field_values)
    resource = Resource.objects.create(
        tenant_id=tenant_id,
        location=location,
        resource_type=resource_type,
        code=_free_code(tenant_id, location.id, label),
        name=label,
        capacity=capacity,
        attributes=custom_field_values,
        schema_id=schema_id,
    )
    events.emit_event(
        tenant_id=tenant_id,
        name="resource.created",
        subject_type="resource",
        subject_id=resource.id,
        actor=_actor(membership_id),
    )
    return resource


@transaction.atomic
def update_resource(
    *,
    resource_id: UUID,
    label: str | None,
    custom_field_values: dict[str, Any] | None,
    membership_id: UUID | None,
) -> Resource:
    """New values are checked against the type's latest form, and the row then points at
    that form. Values the request leaves out are not touched."""
    resource = _lock_resource(resource_id)
    changes: dict[str, Any] = {}
    if label is not None and label != resource.name:
        changes["label"] = {"from": resource.name, "to": label}
        resource.name = label
    if custom_field_values is not None:
        schema_id, references = config.validate_values(
            resource_type_id=resource.resource_type_id,
            scope="resource",
            values=custom_field_values,
        )
        _check_references(references, custom_field_values)
        changes["customFieldValues"] = sorted(
            k
            for k in set(resource.attributes) | set(custom_field_values)
            if resource.attributes.get(k) != custom_field_values.get(k)
        )
        resource.attributes = custom_field_values
        resource.schema_id = schema_id
    resource.save()
    if changes:
        events.emit_event(
            tenant_id=resource.tenant_id,
            name="resource.updated",
            subject_type="resource",
            subject_id=resource.id,
            actor=_actor(membership_id),
            changes=changes,
        )
    return resource


# Resource status moves (API_KICH_BAN.md 4.8). Archived resources are gone from lists.
RESOURCE_MOVES: dict[str, tuple[frozenset[str], str]] = {
    "maintenance": (frozenset({ResourceStatus.ACTIVE}), ResourceStatus.MAINTENANCE),
    "deactivate": (
        frozenset({ResourceStatus.ACTIVE, ResourceStatus.MAINTENANCE}),
        ResourceStatus.INACTIVE,
    ),
    "activate": (
        frozenset({ResourceStatus.MAINTENANCE, ResourceStatus.INACTIVE}),
        ResourceStatus.ACTIVE,
    ),
}


@transaction.atomic
def move_resource(
    *, resource_id: UUID, move: str, membership_id: UUID | None, reason: str | None = None
) -> Resource:
    """Change a resource's status. Bookings already made are NOT cancelled: the caller
    returns them so an admin can decide (cancel one by one, or keep)."""
    resource = _lock_resource(resource_id)
    allowed_from, to = RESOURCE_MOVES[move]
    if resource.status not in allowed_from:
        raise InvalidTransition(f"Cannot {move} a resource that is {resource.status.lower()}.")
    before = resource.status
    resource.status = to
    resource.save(update_fields=["status", "updated_at"])
    record_status(
        tenant_id=resource.tenant_id,
        object_code="resource",
        record_id=resource.id,
        action=move,
        from_status=before,
        to_status=to,
        membership_id=membership_id,
        note=reason,
    )
    events.emit_event(
        tenant_id=resource.tenant_id,
        name="resource.updated",
        subject_type="resource",
        subject_id=resource.id,
        actor=_actor(membership_id),
        changes={"status": {"from": before.lower(), "to": to.lower()}},
        data={"reason": reason} if reason else None,
    )
    return resource


def _lock_resource(resource_id: UUID) -> Resource:
    try:
        return Resource.objects.select_for_update().get(id=resource_id)
    except Resource.DoesNotExist:
        raise NotFound("No resource with this id.") from None


def get_resource(resource_id: UUID) -> Resource:
    try:
        return Resource.objects.select_related("location", "resource_type").get(id=resource_id)
    except Resource.DoesNotExist:
        raise NotFound("No resource with this id.") from None


def bookable_resources(*, location_id: UUID, resource_type_id: UUID) -> list[Resource]:
    return list(
        Resource.objects.filter(
            location_id=location_id,
            resource_type_id=resource_type_id,
            status=ResourceStatus.ACTIVE,
        ).order_by("position", "name")
    )


def resource_ids_at(location_id: UUID) -> list[UUID]:
    return list(Resource.objects.filter(location_id=location_id).values_list("id", flat=True))


def list_resources_qs(
    *,
    resource_type_id: UUID | None = None,
    location_id: UUID | None = None,
    status: str | None = None,
) -> Any:
    qs = Resource.objects.exclude(status=ResourceStatus.ARCHIVED)
    if resource_type_id:
        qs = qs.filter(resource_type_id=resource_type_id)
    if location_id:
        qs = qs.filter(location_id=location_id)
    if status:
        qs = qs.filter(status=status.upper())
    return qs
