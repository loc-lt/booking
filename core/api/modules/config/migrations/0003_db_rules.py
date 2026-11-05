from django.db import migrations

from kernel.db import enable_rls, same_tenant_fk


class Migration(migrations.Migration):
    dependencies = [
        ("config", "0002_initial"),
        ("users", "0002_db_rules"),
        ("resources", "0002_db_rules"),
    ]

    operations = [
        enable_rls("policy_versions"),
        enable_rls("field_definitions"),
        enable_rls("object_schema_versions"),
        same_tenant_fk("policy_versions", "resource_type_id", "resource_types"),
        same_tenant_fk("policy_versions", "created_by_membership_id", "memberships"),
        same_tenant_fk("policy_versions", "published_by_membership_id", "memberships"),
        same_tenant_fk("field_definitions", "resource_type_id", "resource_types"),
        same_tenant_fk("field_definitions", "created_by_membership_id", "memberships"),
        same_tenant_fk("object_schema_versions", "resource_type_id", "resource_types"),
        same_tenant_fk("object_schema_versions", "published_by_membership_id", "memberships"),
    ]
