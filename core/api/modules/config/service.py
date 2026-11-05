"""Public interface of the config module: policy versions and custom field forms."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from kernel.errors import NotFound, ValidationFailed
from modules.config import fields as field_engine
from modules.config import policy
from modules.config.models import (
    CustomObject,
    FieldDefinition,
    FieldStatus,
    ObjectSchemaVersion,
    PolicyVersion,
    VersionStatus,
)

flow_config_from_body = policy.flow_config_from_body
refund_percent = policy.refund_percent
body_from_flow_config = policy.body_from_flow_config
FIELD_TYPES = field_engine.FIELD_TYPES


@dataclass(frozen=True, slots=True)
class PolicySnapshot:
    id: UUID
    version: int
    body: dict[str, Any]


def _snapshot(row: PolicyVersion) -> PolicySnapshot:
    return PolicySnapshot(id=row.id, version=row.version, body=row.body)


# ---------- policies ----------


@transaction.atomic
def publish_policy(
    *,
    tenant_id: UUID,
    resource_type_id: UUID,
    flow_config: dict[str, Any],
    base: PolicySnapshot | None,
    membership_id: UUID | None,
) -> PolicySnapshot:
    """Publish a new policy version from a contract flowConfig. Keys the contract doesn't
    expose are copied from `base`. The previous version becomes SUPERSEDED, never edited."""
    body = policy.body_from_flow_config(flow_config, base.body if base else None)
    return publish_body(
        tenant_id=tenant_id,
        resource_type_id=resource_type_id,
        body=body,
        base=base,
        membership_id=membership_id,
    )


@transaction.atomic
def publish_body(
    *,
    tenant_id: UUID,
    resource_type_id: UUID,
    body: dict[str, Any],
    base: PolicySnapshot | None,
    membership_id: UUID | None,
) -> PolicySnapshot:
    policy.validate_body(body)
    now = timezone.now()
    if base:
        PolicyVersion.objects.filter(id=base.id).update(status=VersionStatus.SUPERSEDED)
    row = PolicyVersion.objects.create(
        tenant_id=tenant_id,
        resource_type_id=resource_type_id,
        version=(base.version + 1) if base else 1,
        body=body,
        status=VersionStatus.PUBLISHED,
        based_on_version=base.version if base else None,
        created_by_membership_id=membership_id,
        published_by_membership_id=membership_id,
        published_at=now,
    )
    return _snapshot(row)


def get_policy(policy_version_id: UUID) -> PolicySnapshot:
    return _snapshot(PolicyVersion.objects.get(id=policy_version_id))


@dataclass(frozen=True, slots=True)
class PolicyVersionView:
    version: int
    status: str
    flow_config: dict[str, Any]
    based_on_version: int | None
    published_by_membership_id: UUID | None
    published_at: Any


def list_policy_versions(resource_type_id: UUID) -> list[PolicyVersionView]:
    rows = PolicyVersion.objects.filter(resource_type_id=resource_type_id).order_by("-version")
    return [
        PolicyVersionView(
            version=r.version,
            status=r.status,
            flow_config=policy.flow_config_from_body(r.body),
            based_on_version=r.based_on_version,
            published_by_membership_id=r.published_by_membership_id,
            published_at=r.published_at,
        )
        for r in rows
    ]


def policy_by_version(resource_type_id: UUID, version: int) -> PolicySnapshot | None:
    row = PolicyVersion.objects.filter(resource_type_id=resource_type_id, version=version).first()
    return _snapshot(row) if row else None


def get_policies(policy_version_ids: list[UUID]) -> dict[UUID, PolicySnapshot]:
    return {
        row.id: _snapshot(row) for row in PolicyVersion.objects.filter(id__in=policy_version_ids)
    }


# ---------- custom fields ----------


def _scope_to_object(scope: str) -> str:
    return CustomObject.BOOKING if scope == "booking" else CustomObject.RESOURCE


@transaction.atomic
def publish_fields(
    *,
    tenant_id: UUID,
    resource_type_id: UUID,
    fields: list[dict[str, Any]],
    membership_id: UUID | None,
    target_type_exists: Any,
) -> None:
    """Save a resource type's field definitions and publish one form per scope.

    `target_type_exists(id) -> bool` checks reference targets (owned by the resources module).
    """
    field_engine.check_definitions(fields)
    _check_targets(fields, target_type_exists)
    _insert_fields(tenant_id, resource_type_id, fields, membership_id, first_position=0)
    for object_code in (CustomObject.RESOURCE, CustomObject.BOOKING):
        _publish_form(
            tenant_id=tenant_id,
            resource_type_id=resource_type_id,
            object_code=object_code,
            membership_id=membership_id,
        )


def _check_targets(fields: list[dict[str, Any]], target_type_exists: Any) -> None:
    for i, field in enumerate(fields):
        target = (field.get("validation") or {}).get("targetResourceTypeId")
        if target and not target_type_exists(UUID(str(target))):
            raise ValidationFailed.one(
                f"fields[{i}].validation.targetResourceTypeId", "No resource type with this id."
            )


def _insert_fields(
    tenant_id: UUID,
    resource_type_id: UUID,
    fields: list[dict[str, Any]],
    membership_id: UUID | None,
    first_position: int,
) -> None:
    for offset, field in enumerate(fields):
        position = first_position + offset
        config: dict[str, Any] = {}
        if field.get("options"):
            config["options"] = field["options"]
        if field.get("validation"):
            config["validation"] = {
                k: (str(v) if k == "targetResourceTypeId" else v)
                for k, v in field["validation"].items()
            }
        FieldDefinition.objects.create(
            tenant_id=tenant_id,
            object_code=_scope_to_object(field.get("scope", "resource")),
            resource_type_id=resource_type_id,
            key=field["key"],
            label={"default": field["label"]},
            help_text={"default": field["help"]} if field.get("help") else None,
            data_type=field["type"],
            config=config,
            required=bool(field.get("required", False)),
            position=position,
            status=FieldStatus.PUBLISHED,
            created_by_membership_id=membership_id,
        )


@transaction.atomic
def add_fields(
    *,
    tenant_id: UUID,
    resource_type_id: UUID,
    fields: list[dict[str, Any]],
    membership_id: UUID | None,
    target_type_exists: Any,
) -> dict[str, int]:
    """Add fields to an existing resource type and publish new forms (API_KICH_BAN.md 4.6).

    No ALTER TABLE, no rewrite: existing records keep the form they were checked against.
    Keys are permanent, so a key used before (even archived) cannot be reused.
    Returns {scope: new form version} for the scopes that changed."""
    if not fields:
        raise ValidationFailed.one("fields", "Give at least one field.")
    field_engine.check_definitions(fields)
    _check_targets(fields, target_type_exists)
    used = set(
        FieldDefinition.objects.filter(resource_type_id=resource_type_id).values_list(
            "key", flat=True
        )
    )
    errors = [
        {"field": f"fields[{i}].key", "message": "This key is already used by this type."}
        for i, f in enumerate(fields)
        if f["key"] in used
    ]
    if errors:
        raise ValidationFailed(errors)
    last = FieldDefinition.objects.filter(resource_type_id=resource_type_id).aggregate(
        p=Max("position")
    )["p"]
    _insert_fields(tenant_id, resource_type_id, fields, membership_id, (last or 0) + 1)
    scopes = {_scope_to_object(f.get("scope", "resource")) for f in fields}
    return {
        code: _publish_form(
            tenant_id=tenant_id,
            resource_type_id=resource_type_id,
            object_code=code,
            membership_id=membership_id,
        ).version
        for code in sorted(scopes)
    }


@transaction.atomic
def archive_field(
    *, tenant_id: UUID, resource_type_id: UUID, key: str, membership_id: UUID | None
) -> dict[str, int]:
    """Stop asking for a field. Stored values stay; new records no longer accept it."""
    field = (
        FieldDefinition.objects.select_for_update()
        .filter(resource_type_id=resource_type_id, key=key, status=FieldStatus.PUBLISHED)
        .first()
    )
    if field is None:
        raise NotFound("No published field with this key.")
    field.status = FieldStatus.ARCHIVED
    field.archived_at = timezone.now()
    field.save(update_fields=["status", "archived_at", "updated_at"])
    form = _publish_form(
        tenant_id=tenant_id,
        resource_type_id=resource_type_id,
        object_code=field.object_code,
        membership_id=membership_id,
    )
    return {field.object_code: form.version}


def _publish_form(
    *, tenant_id: UUID, resource_type_id: UUID, object_code: str, membership_id: UUID | None
) -> ObjectSchemaVersion:
    contract_fields = [
        f
        for f in list_fields(resource_type_id=resource_type_id)
        if _scope_to_object(f["scope"]) == object_code
    ]
    json_schema, ui_schema = field_engine.compile_schema(contract_fields)
    last = ObjectSchemaVersion.objects.filter(
        tenant_id=tenant_id, object_code=object_code, resource_type_id=resource_type_id
    ).aggregate(v=Max("version"))["v"]
    return ObjectSchemaVersion.objects.create(
        tenant_id=tenant_id,
        object_code=object_code,
        resource_type_id=resource_type_id,
        version=(last or 0) + 1,
        json_schema=json_schema,
        ui_schema=ui_schema,
        published_by_membership_id=membership_id,
    )


def _to_contract(row: FieldDefinition) -> dict[str, Any]:
    field: dict[str, Any] = {
        "key": row.key,
        "label": row.label.get("default", ""),
        "type": row.data_type,
        "scope": "booking" if row.object_code == CustomObject.BOOKING else "resource",
        "required": row.required,
    }
    if row.help_text:
        field["help"] = row.help_text.get("default", "")
    if row.config.get("options"):
        field["options"] = row.config["options"]
    if row.config.get("validation"):
        field["validation"] = row.config["validation"]
    return field


def list_fields(*, resource_type_id: UUID) -> list[dict[str, Any]]:
    """The resource type's fields in the contract's FieldDefinition format."""
    rows = FieldDefinition.objects.filter(
        resource_type_id=resource_type_id,
        object_code__in=[CustomObject.RESOURCE, CustomObject.BOOKING],
        status=FieldStatus.PUBLISHED,
    ).order_by("position", "key")
    return [_to_contract(r) for r in rows]


def fields_by_type(resource_type_ids: list[UUID]) -> dict[UUID, list[dict[str, Any]]]:
    out: dict[UUID, list[dict[str, Any]]] = {rt: [] for rt in resource_type_ids}
    rows = FieldDefinition.objects.filter(
        resource_type_id__in=resource_type_ids,
        object_code__in=[CustomObject.RESOURCE, CustomObject.BOOKING],
        status=FieldStatus.PUBLISHED,
    ).order_by("position", "key")
    for r in rows:
        out[r.resource_type_id].append(_to_contract(r))
    return out


def _current_form(resource_type_id: UUID, object_code: str) -> ObjectSchemaVersion | None:
    return (
        ObjectSchemaVersion.objects.filter(
            resource_type_id=resource_type_id, object_code=object_code
        )
        .order_by("-version")
        .first()
    )


def validate_values(
    *,
    resource_type_id: UUID,
    scope: str,
    values: dict[str, Any],
    prefix: str = "customFieldValues",
) -> tuple[UUID | None, dict[str, str]]:
    """Check values against the current form of the scope. Raises ValidationFailed with
    per-field errors. Returns (schema_id to store, {reference key: target type id})."""
    form = _current_form(resource_type_id, _scope_to_object(scope))
    if form is None and not values:
        return None, {}
    errors = field_engine.check_values(form.json_schema if form else None, values, prefix)
    if errors:
        raise ValidationFailed(errors)
    if form is None:
        return None, {}
    references = field_engine.reference_fields(form.json_schema, form.ui_schema)
    return form.id, {k: v for k, v in references.items() if k in values}
