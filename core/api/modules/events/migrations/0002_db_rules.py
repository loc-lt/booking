from django.db import migrations


class Migration(migrations.Migration):
    """outbox and processed_events have no RLS: the worker reads across tenants and runs each
    subscriber inside the event's tenant."""

    dependencies = [("events", "0001_initial")]

    operations = [
        migrations.RunSQL(
            "CREATE INDEX outbox_occurred_brin ON outbox USING brin (occurred_at);",
            "DROP INDEX outbox_occurred_brin;",
        ),
    ]
