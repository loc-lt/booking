from django.db import migrations

from kernel.db import attributes_check, enable_rls, same_tenant_fk


class Migration(migrations.Migration):
    dependencies = [
        ("resources", "0001_initial"),
        ("config", "0002_initial"),
        ("kernel", "0002_db_rules"),
    ]

    operations = [
        enable_rls("locations"),
        enable_rls("resource_types"),
        enable_rls("resources"),
        same_tenant_fk("locations", "schema_id", "object_schema_versions"),
        same_tenant_fk("resource_types", "current_policy_version_id", "policy_versions"),
        same_tenant_fk("resources", "location_id", "locations"),
        same_tenant_fk("resources", "resource_type_id", "resource_types"),
        same_tenant_fk("resources", "schema_id", "object_schema_versions"),
        attributes_check("locations"),
        attributes_check("resources"),
    ]
