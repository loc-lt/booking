from django.db import migrations

from kernel.db import attributes_check, enable_rls, same_tenant_fk


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
        ("booking", "0003_db_rules"),
    ]

    operations = [
        enable_rls("payments"),
        same_tenant_fk("payments", "booking_id", "bookings"),
        same_tenant_fk("payments", "schema_id", "object_schema_versions"),
        attributes_check("payments"),
    ]
