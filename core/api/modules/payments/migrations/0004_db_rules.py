from django.db import migrations

from kernel.db import enable_rls, same_tenant_fk


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0003_payment_events_refunds"),
    ]

    operations = [
        enable_rls("payment_events"),
        enable_rls("refunds"),
        same_tenant_fk("payment_events", "payment_id", "payments"),
        same_tenant_fk("refunds", "payment_id", "payments"),
        migrations.RunSQL(
            """
            ALTER TABLE refunds ADD CONSTRAINT refunds_status
                CHECK (status IN ('PENDING', 'SUCCEEDED', 'FAILED'));
            """,
            "ALTER TABLE refunds DROP CONSTRAINT refunds_status;",
        ),
    ]
