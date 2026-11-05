"""Request validation and response shapes, named exactly like contracts/openapi.yaml.

Requests: DRF serializers check shape only (types, required, patterns). Business rules live
in service.py. Responses: plain functions, so nested JSON (customFieldValues) keeps its keys.
"""

from typing import Any

from rest_framework import serializers

from modules.config.service import FIELD_TYPES
from modules.resources.models import Location, Resource
from modules.resources.service import ResourceTypeView

KEY_REGEX = r"^[a-z][a-z0-9_]*$"


class FieldOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class FieldValidationSerializer(serializers.Serializer):
    minLength = serializers.IntegerField(required=False, min_value=0)
    maxLength = serializers.IntegerField(required=False, min_value=1)
    pattern = serializers.CharField(required=False)
    min = serializers.FloatField(required=False)
    max = serializers.FloatField(required=False)
    multipleOf = serializers.FloatField(required=False, min_value=0)
    minItems = serializers.IntegerField(required=False, min_value=0)
    maxItems = serializers.IntegerField(required=False, min_value=1)
    targetResourceTypeId = serializers.UUIDField(required=False)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        value = super().to_internal_value(data)
        # Keep integers as integers so the compiled JSON Schema matches what was sent.
        for key in ("min", "max", "multipleOf"):
            if key in value and float(value[key]).is_integer():
                value[key] = int(value[key])
        return value


class FieldDefinitionSerializer(serializers.Serializer):
    key = serializers.RegexField(KEY_REGEX, max_length=63)
    label = serializers.CharField(max_length=200)
    type = serializers.ChoiceField(choices=sorted(FIELD_TYPES))
    scope = serializers.ChoiceField(choices=["resource", "booking"], default="resource")
    required = serializers.BooleanField(default=False)
    help = serializers.CharField(required=False, allow_blank=True, max_length=500)
    options = FieldOptionSerializer(many=True, required=False)
    validation = FieldValidationSerializer(required=False)


class CheckInPolicySerializer(serializers.Serializer):
    required = serializers.BooleanField()
    opensMinutesBefore = serializers.IntegerField(min_value=0, max_value=24 * 60)
    noShowAfterMinutes = serializers.IntegerField(min_value=0, max_value=24 * 60)


class CancellationPolicySerializer(serializers.Serializer):
    allowedUntilMinutesBefore = serializers.IntegerField(min_value=0, max_value=60 * 24 * 365)


class LimitsPolicySerializer(serializers.Serializer):
    minDurationMinutes = serializers.IntegerField(required=False, min_value=0, max_value=10080)
    maxDurationMinutes = serializers.IntegerField(required=False, min_value=1, max_value=10080)
    leadTimeMinutes = serializers.IntegerField(required=False, min_value=0, max_value=525600)
    bookingWindowDays = serializers.IntegerField(required=False, min_value=1, max_value=730)


class BuffersPolicySerializer(serializers.Serializer):
    beforeMinutes = serializers.IntegerField(required=False, min_value=0, max_value=1440)
    afterMinutes = serializers.IntegerField(required=False, min_value=0, max_value=1440)


class RefundRuleSerializer(serializers.Serializer):
    minutesBefore = serializers.IntegerField(min_value=0, max_value=525600)
    percent = serializers.IntegerField(min_value=0, max_value=100)


class PaymentPolicySerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["none", "upfront"])
    amountMinor = serializers.IntegerField(required=False, min_value=0)
    per = serializers.ChoiceField(choices=["booking", "hour"], required=False)
    holdMinutes = serializers.IntegerField(required=False, min_value=1, max_value=1440)
    refundRules = RefundRuleSerializer(many=True, required=False, max_length=10)


class FlowConfigSerializer(serializers.Serializer):
    confirmation = serializers.ChoiceField(choices=["instant", "approval"])
    checkIn = CheckInPolicySerializer()
    cancellation = CancellationPolicySerializer()
    limits = LimitsPolicySerializer(required=False)
    buffers = BuffersPolicySerializer(required=False)
    payment = PaymentPolicySerializer(required=False)


class CreateResourceTypeRequest(serializers.Serializer):
    key = serializers.RegexField(KEY_REGEX, max_length=63)
    label = serializers.CharField(max_length=200)
    slotMinutes = serializers.IntegerField(required=False, default=30)
    fields = FieldDefinitionSerializer(many=True, default=list)
    flowConfig = FlowConfigSerializer()


class UpdateResourceTypeRequest(serializers.Serializer):
    baseVersion = serializers.IntegerField(min_value=1)
    label = serializers.CharField(max_length=200, required=False)
    slotMinutes = serializers.IntegerField(required=False)
    flowConfig = FlowConfigSerializer()


class AddFieldsRequest(serializers.Serializer):
    fields = FieldDefinitionSerializer(many=True)


class RestoreVersionRequest(serializers.Serializer):
    baseVersion = serializers.IntegerField(min_value=1)


class CreateResourceRequest(serializers.Serializer):
    resourceTypeId = serializers.UUIDField()
    siteId = serializers.UUIDField()
    label = serializers.CharField(max_length=200)
    capacity = serializers.IntegerField(required=False, default=1, min_value=1, max_value=10000)
    customFieldValues = serializers.DictField(default=dict)


class UpdateResourceRequest(serializers.Serializer):
    label = serializers.CharField(max_length=200, required=False)
    customFieldValues = serializers.DictField(required=False)


class ResourceMoveRequest(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class CreateSiteRequest(serializers.Serializer):
    code = serializers.RegexField(r"^[a-z0-9][a-z0-9-]{0,39}$", required=False)
    name = serializers.CharField(max_length=200)
    timezone = serializers.CharField(max_length=64)
    address = serializers.DictField(required=False, default=dict)


class UpdateSiteRequest(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    address = serializers.DictField(required=False)


def resource_type_json(view: ResourceTypeView) -> dict[str, Any]:
    row = view.row
    return {
        "id": str(row.id),
        "key": row.code,
        "label": row.name,
        "version": view.version,
        "slotMinutes": row.slot_minutes,
        "bookingMode": row.booking_mode.lower(),
        "fields": view.fields,
        "flowConfig": view.flow_config,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }


def resource_json(row: Resource) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "resourceTypeId": str(row.resource_type_id),
        "siteId": str(row.location_id),
        "label": row.name,
        "code": row.code,
        "status": row.status.lower(),
        "capacity": row.capacity,
        "customFieldValues": row.attributes,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }


def site_json(row: Location) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "code": row.code,
        "name": row.name,
        "timezone": row.timezone,
        "address": row.address,
        "status": row.status.lower(),
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }
