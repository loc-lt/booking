# Rules

A rule is **scope + condition + consequence + priority**, with an optional **limit** on deny rules. Tenants combine these predefined parts; they never write new ones. Example: [examples/rule.json](../examples/rule.json).

| Part | Values |
| --- | --- |
| Scope | Tenant (`{}`), or one of `siteId`, `resourceTypeId`, `resourceId` |
| Condition (`when`) | JSONLogic over a fixed context: `booking`, `resource`, `user`, `user.roles`, `time`, `usage`. Absent = always |
| Consequence | `deny`, `require_approval`, `require_payment` |
| Limit (deny only, optional) | `max_duration {minutes}`, `max_advance {days}`, `quota {per: day\|week, maxBookings?, maxMinutes?}` |
| Priority | Higher runs first |
| `label`, `message`, `enabled` | Name in the console; text shown to the member on a deny (defaults to `label`); `false` keeps the rule without applying it |

`user.roles` holds the member's role codes in the tenant (`owner`, `admin`, `staff`, `member`, `guest`, and the tenant's own roles). There is no separate "groups" concept.

An earlier version of this model had a `stage` (`eligibility`/`limits`/`approval`) and an `effect` object. Both are gone: `eligibility` and `limits` both denied, so one `deny` consequence loses nothing; "only these roles" (`allowed_groups`) is a deny with a negated `when`. Stored rule sets were converted by migration `rules/0003`.

### What each consequence does

| Consequence | Without `limit` | With `limit` |
| --- | --- | --- |
| `deny` | The booking is refused when `when` matches | `when` decides who the limit applies to; the booking is refused only when it exceeds the limit |
| `require_approval` | Adds approval on top of the resource type's `flowConfig.confirmation` | Not allowed |
| `require_payment` | Makes this booking paid even when the type is free (`payment.mode: none`); the price is still the type's `flowConfig.payment.amountMinor` | Not allowed |

Rules can only switch approval and payment **on**, never off: one source turns them on, so two rules can never disagree about it. A tenant that wants "always paid, except our team" sets the type free and writes one `require_payment` rule for everyone not in the team role. `flowConfig.confirmation` and `flowConfig.payment.mode` stay the no-exceptions default; rules handle the exceptions.

A `require_payment` rule scoped to a resource type or resource that has no price is rejected at publish (`VALIDATION_FAILED` on `rules[i].consequence`). With a tenant or site scope the type is only known at booking time; a type without a price then stays free.

The resource type's own limits (`flowConfig.limits`: min and max duration, lead time, booking window) stay where they are. They apply to everyone; rules add per-role or per-condition limits on top.

## How rules are evaluated

1. Load the enabled published rules for the booking's scope, most general first: tenant → site → resource type → resource.
2. Build the context from the fixed keys above.
3. Evaluate every rule's condition in one pass, highest priority first, and collect the consequences: each matching `deny` adds a reason, any `require_approval` or `require_payment` match sets that flag.
4. Resolve conflicts: deny beats allow. For `max_duration` and `max_advance`, the most specific matching scope wins, so a room can allow longer than the tenant-wide limit; quotas are each checked.
5. Return a decision and a **trace** naming every rule that ran and what it did. A condition that cannot be evaluated denies instead of silently allowing.

The same rules run in Python (the server's decision) and in the browser (admin impact checks). A shared file of example rules and expected results runs against both evaluators in the pipeline, so they can never disagree silently.

## Storing and publishing

A tenant's rules are **one rule set with a version**. `PUT /rules` publishes the whole set with `baseVersion` (stale → `STALE_VERSION`); `GET /rules/versions` and `GET /rules/versions/{v}` show history. Each booking records the rule set version it was checked against, so rolling back is publishing an older set again.

## Limits

- No loops, no external calls inside conditions, and at most 200 rules per set. Anything beyond that is an extension.
- AI-written rules return rule JSON, which is validated against the rule schema, checked for impact, and published by a person. The model never publishes.
