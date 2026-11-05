"""DRF fields every module's request serializers share."""

from typing import Any

from rest_framework import serializers


class AwareDateTimeField(serializers.DateTimeField):
    """The contract requires an offset: a time without one is ambiguous across sites."""

    def to_internal_value(self, value: Any) -> Any:
        parsed = super().to_internal_value(value)
        if isinstance(value, str) and not (
            value.endswith("Z") or "+" in value[10:] or "-" in value[10:]
        ):
            raise serializers.ValidationError("Include a UTC offset, e.g. +07:00 or Z.")
        return parsed
