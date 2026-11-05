from django.db import migrations

from kernel.db import enable_rls, same_tenant_fk


class Migration(migrations.Migration):
    dependencies = [
        ("availability", "0002_initial"),
        ("resources", "0002_db_rules"),
        ("users", "0002_db_rules"),
    ]

    operations = [
        enable_rls("availability_rules"),
        enable_rls("availability_exceptions"),
        same_tenant_fk("availability_rules", "location_id", "locations"),
        same_tenant_fk("availability_rules", "resource_id", "resources"),
        same_tenant_fk("availability_exceptions", "location_id", "locations"),
        same_tenant_fk("availability_exceptions", "resource_id", "resources"),
        same_tenant_fk("availability_exceptions", "created_by_membership_id", "memberships"),
        migrations.RunSQL(
            """
            ALTER TABLE availability_exceptions ADD CONSTRAINT availability_exceptions_one_target
                CHECK ((location_id IS NULL) <> (resource_id IS NULL));
            CREATE INDEX avail_exc_resource_gist ON availability_exceptions
                USING gist (resource_id, during);
            CREATE INDEX avail_exc_location_gist ON availability_exceptions
                USING gist (location_id, during);
            """,
            """
            DROP INDEX avail_exc_location_gist;
            DROP INDEX avail_exc_resource_gist;
            ALTER TABLE availability_exceptions DROP CONSTRAINT availability_exceptions_one_target;
            """,
        ),
    ]
