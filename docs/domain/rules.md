# Rules

A rule is **scope + stage + condition + effect + priority**. Tenants combine predefined effects; they never write new ones. Example: [examples/rule.json](../examples/rule.json).

| Part | Values |
| --- | --- |
| Scope | Tenant, site, resource type or resource |
| Stage | `eligibility`, `limits`, `approval` (`pricing` later) |
| Condition (`when`) | JSONLogic over a fixed context: `booking`, `resource`, `user`, `user.groups`, `time`, `usage` |
| Effect | `deny`, `require_approval`, `max_duration`, `advance_window`, `quota`, `allowed_groups` |
| Priority | Higher runs first |

## How rules are evaluated

1. Load the published rules for the booking's scope, most general first: tenant → site → resource type → resource.
2. Build the context from the fixed keys above.
3. For the current stage, evaluate each rule's condition, highest priority first, and collect the effects.
4. Resolve conflicts: deny beats allow; ties go to the more specific scope.
5. Return a decision and a **trace** naming every rule that matched and what it did.

The same rules run in Python (the server's decision) and in the browser (admin previews). A shared file of example rules and expected results runs against both evaluators in the pipeline, so they can never disagree silently.

## Limits

- No loops, no external calls inside conditions, and a cap on rules per stage. Anything beyond that is an extension.
- AI-written rules return rule JSON, which is validated against the rule schema, previewed, and published by a person. The model never publishes.
