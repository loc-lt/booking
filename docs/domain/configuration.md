# Configuration and custom fields

Everything a tenant configures (resource types, custom fields, policies, rules, notification templates) is data with a version number. Tenants never edit the live version directly.

## How a change goes live

1. **Draft:** the admin edits a copy; the live version keeps running.
2. **Validate:** the system checks it makes sense (min ≤ max, no unknown fields, no rule that blocks everything).
3. **Preview:** "test this rule against last week's bookings".
4. **Publish:** the draft becomes the new version; `config.published` records who, when and what.
5. **Roll back:** any earlier version can be republished as the newest.

- Saving a setting never silently rewrites stored data.
- Keys are permanent; labels can change freely.
- Bookings keep the config version they were made under.
- Drafts carry the version they're based on; publishing over a newer version fails with `STALE_VERSION`.

## Custom fields

| Layer | Answers | Tool |
| --- | --- | --- |
| Field definition | "Capacity is an integer, required, 1–200" | Our own format, edited in the console |
| Per-field validation | "Is `capacity: 250` valid?" | JSON Schema, generated from the definition |

We keep our own definition format because the console needs labels, order, help text and widgets, which JSON Schema lacks. It compiles to JSON Schema, which the browser and the server both validate against. Errors come back per field. Rules across several fields ("with video conferencing, capacity must be at least 4") are after December. Example: [examples/field-definition.json](../examples/field-definition.json).

### Field scope

Every field has a `scope`, set once when it's defined:

| Scope | Who sets the value | Where it's shown |
| --- | --- | --- |
| `resource` (default) | An admin, once per resource instance (e.g. a meeting room's TV type) | Read-only on the resource; never asked again at booking |
| `booking` | The member, on every booking (e.g. number of attendees) | The booking form |

A field's scope is part of its definition, like its type: it never changes in place (see "Changing a field's type" below).

### Reference fields

A `reference` field's value is another resource's id. Its definition fixes which resource type that id must belong to (`FieldValidation.targetResourceTypeId`), chosen once when the field is defined — e.g. a `meeting_room`'s `primary_table` field is scoped to the `table` resource type. The console offers a picker of that type's resources wherever the value is set, instead of a raw id.

A reference is normally a `resource`-scoped field: an admin assigns the specific table once, when setting up the meeting room, the same as any other attribute. Nothing stops a `booking`-scoped reference (the member picks from a list at booking time), but that's the less common case.

A resource type can reference any other resource type, including itself. The core only stores the id and resolves it for display; it doesn't enforce lifecycle coupling (e.g. deleting a referenced resource doesn't cascade) — that stays a cross-product concern, same as [core-boundaries.md](../core-boundaries.md) describes for anything else a specific product needs.

### Field types

| Type | Stored as | Validations |
| --- | --- | --- |
| text, long_text | string | required, minLength, maxLength, pattern |
| integer, number | number | required, min, max, multipleOf |
| boolean | boolean | required |
| date, datetime | ISO string | required |
| select | string | required, options |
| multi_select | array | required, options, minItems, maxItems |
| email, url, phone | string | required |
| reference | id | required, target type |
| file, multi_file | — | Reserved: refused with `VALIDATION_FAILED` on `fields[i].type` until there is an upload endpoint |

When a definition is saved: min ≤ max, the pattern compiles and is length-capped, option values are unique, keys are snake_case and unique.

## Changing a field's type

A field's type and scope never change in place. To change them, the admin archives the field and adds a new one with a different key:

1. Archive the old field (`POST /resource-types/{id}/fields/{key}/archive`). Stored values stay on the records; new records no longer ask for it.
2. Add the new field (`POST /resource-types/{id}/fields`). Keys are permanent, so the new field needs a new key.
3. Existing records keep the form version they were checked against; new records are checked against the new form.

Converting stored values from one type to another (dry run, impact count, background migration, value history) is after December.
