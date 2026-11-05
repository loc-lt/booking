"""Custom fields: definition checks, compiling to JSON Schema, checking values.

Three layers (docs/domain/configuration.md, "Custom fields"):
1. The definition, in the contract's FieldDefinition format (labels, order, help).
2. JSON Schema compiled from it. The browser (Ajv) and the server check values against the
   same schema. Formats use `pattern`, not `format`, so both sides behave the same.
3. Cross-field rules (when/assert): not in the contract yet.
"""

import re
from typing import Any

from jsonschema import Draft202012Validator

from kernel.errors import ValidationFailed

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
MAX_PATTERN_LENGTH = 200
MAX_FIELDS = 100

# Hard columns a custom field key may not shadow.
RESERVED_KEYS = frozenset({"id", "tenant_id", "status", "created_at", "updated_at", "schema_id"})

_DATE = r"^\d{4}-\d{2}-\d{2}$"
_DATETIME = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$"
_EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
_URL = r"^https?://\S+$"
_PHONE = r"^\+?[0-9 ()\-.]{6,20}$"
_UUID = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"

# Which `validation` keys each type accepts.
_ALLOWED_VALIDATION: dict[str, set[str]] = {
    "text": {"minLength", "maxLength", "pattern"},
    "long_text": {"minLength", "maxLength", "pattern"},
    "integer": {"min", "max", "multipleOf"},
    "number": {"min", "max", "multipleOf"},
    "boolean": set(),
    "date": set(),
    "datetime": set(),
    "select": set(),
    "multi_select": {"minItems", "maxItems"},
    "email": set(),
    "url": set(),
    "phone": set(),
    "reference": {"targetResourceTypeId"},
    "file": set(),
    "multi_file": {"minItems", "maxItems"},
}
FIELD_TYPES = frozenset(_ALLOWED_VALIDATION)


def check_definitions(fields: list[dict[str, Any]]) -> None:
    """Checks run when definitions are saved: min <= max, the pattern compiles and is
    length-capped, option values are unique, keys are snake_case and unique."""
    errors: list[dict[str, str]] = []

    def err(index: int, name: str, message: str) -> None:
        errors.append({"field": f"fields[{index}].{name}", "message": message})

    if len(fields) > MAX_FIELDS:
        raise ValidationFailed.one("fields", f"At most {MAX_FIELDS} fields.")
    seen: set[str] = set()
    for i, field in enumerate(fields):
        key, ftype = field["key"], field["type"]
        validation = field.get("validation") or {}
        if not KEY_PATTERN.match(key):
            err(i, "key", "Use snake_case: a-z, 0-9 and _, starting with a letter.")
        if key in RESERVED_KEYS:
            err(i, "key", "This key is reserved.")
        if key in seen:
            err(i, "key", "Duplicate key.")
        seen.add(key)
        for name in set(validation) - _ALLOWED_VALIDATION[ftype]:
            err(i, f"validation.{name}", f"Not allowed for type {ftype}.")
        for low, high in (("min", "max"), ("minLength", "maxLength"), ("minItems", "maxItems")):
            if low in validation and high in validation and validation[low] > validation[high]:
                err(i, f"validation.{low}", f"{low} is greater than {high}.")
        if "pattern" in validation:
            pattern = validation["pattern"]
            if len(pattern) > MAX_PATTERN_LENGTH:
                err(i, "validation.pattern", f"At most {MAX_PATTERN_LENGTH} characters.")
            else:
                try:
                    re.compile(pattern)
                except re.error:
                    err(i, "validation.pattern", "Not a valid regular expression.")
        options = field.get("options")
        if ftype in ("select", "multi_select"):
            if not options:
                err(i, "options", "Required for select fields.")
            else:
                values = [o["value"] for o in options]
                if len(values) != len(set(values)):
                    err(i, "options", "Option values must be unique.")
        elif options:
            err(i, "options", f"Not allowed for type {ftype}.")
        if ftype == "reference" and "targetResourceTypeId" not in validation:
            err(i, "validation.targetResourceTypeId", "Required for reference fields.")
    if errors:
        raise ValidationFailed(errors)


def _property(field: dict[str, Any]) -> dict[str, Any]:
    ftype = field["type"]
    v = field.get("validation") or {}
    options = [o["value"] for o in field.get("options") or []]
    prop: dict[str, Any]
    if ftype in ("text", "long_text"):
        prop = {"type": "string"}
        for src, dst in (
            ("minLength", "minLength"),
            ("maxLength", "maxLength"),
            ("pattern", "pattern"),
        ):
            if src in v:
                prop[dst] = v[src]
        prop.setdefault("maxLength", 255 if ftype == "text" else 5000)
    elif ftype in ("integer", "number"):
        prop = {"type": ftype}
        for src, dst in (("min", "minimum"), ("max", "maximum"), ("multipleOf", "multipleOf")):
            if src in v:
                prop[dst] = v[src]
    elif ftype == "boolean":
        prop = {"type": "boolean"}
    elif ftype == "date":
        prop = {"type": "string", "pattern": _DATE}
    elif ftype == "datetime":
        prop = {"type": "string", "pattern": _DATETIME}
    elif ftype == "select":
        prop = {"type": "string", "enum": options}
    elif ftype == "multi_select":
        prop = {"type": "array", "items": {"type": "string", "enum": options}, "uniqueItems": True}
    elif ftype == "email":
        prop = {"type": "string", "maxLength": 254, "pattern": _EMAIL}
    elif ftype == "url":
        prop = {"type": "string", "maxLength": 2048, "pattern": _URL}
    elif ftype == "phone":
        prop = {"type": "string", "pattern": _PHONE}
    elif ftype == "reference":
        prop = {"type": "string", "pattern": _UUID}
    elif ftype == "file":
        prop = {"type": "string", "minLength": 1}
    else:  # multi_file
        prop = {"type": "array", "items": {"type": "string", "minLength": 1}}
    if ftype in ("multi_select", "multi_file"):
        if "minItems" in v:
            prop["minItems"] = v["minItems"]
        if "maxItems" in v:
            prop["maxItems"] = v["maxItems"]
    prop["x-field-type"] = ftype
    return prop


def compile_schema(fields: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Contract field definitions -> (JSON Schema, ordered form layout)."""
    json_schema = {
        "$schema": JSON_SCHEMA_DIALECT,
        "type": "object",
        "properties": {f["key"]: _property(f) for f in fields},
        "required": [f["key"] for f in fields if f.get("required")],
        "additionalProperties": False,
    }
    return json_schema, list(fields)


def check_values(
    json_schema: dict[str, Any] | None, values: dict[str, Any], prefix: str
) -> list[dict[str, str]]:
    """Errors per field, named like the contract: `customFieldValues.capacity`."""
    if json_schema is None:
        return [{"field": f"{prefix}.{k}", "message": "Unknown field."} for k in sorted(values)]
    errors: list[dict[str, str]] = []
    for error in Draft202012Validator(json_schema).iter_errors(values):
        if error.validator == "required":
            for key in error.validator_value:
                if key not in error.instance:
                    errors.append(
                        {"field": f"{prefix}.{key}", "message": "This field is required."}
                    )
        elif error.validator == "additionalProperties":
            for key in sorted(set(error.instance) - set(json_schema["properties"])):
                errors.append({"field": f"{prefix}.{key}", "message": "Unknown field."})
        else:
            path = ".".join(str(p) for p in error.absolute_path)
            errors.append(
                {"field": f"{prefix}.{path}" if path else prefix, "message": error.message}
            )
    return errors


def reference_fields(
    json_schema: dict[str, Any] | None, ui_schema: list[dict[str, Any]]
) -> dict[str, str]:
    """key -> target resource type id, for reference fields of a form."""
    if not json_schema:
        return {}
    return {
        f["key"]: f["validation"]["targetResourceTypeId"]
        for f in ui_schema
        if f["type"] == "reference"
    }
