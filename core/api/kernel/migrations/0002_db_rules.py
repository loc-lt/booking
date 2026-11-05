"""Rules the ORM can't declare for the kernel's tables, plus the btree_gist extension that
exclusion constraints and range indexes on (uuid, tstzrange) need."""

from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations

from kernel.db import enable_rls


class Migration(migrations.Migration):
    dependencies = [("kernel", "0001_initial")]

    operations = [
        BtreeGistExtension(),
        # scheduled_jobs has no RLS on purpose: the worker scans every tenant for due jobs and
        # runs each inside tenant_scope(). Only code writes it.
        enable_rls("transition_log"),
        enable_rls("idempotency_keys"),
        migrations.RunSQL(
            "CREATE INDEX transition_log_at_brin ON transition_log USING brin (at);",
            "DROP INDEX transition_log_at_brin;",
        ),
    ]
