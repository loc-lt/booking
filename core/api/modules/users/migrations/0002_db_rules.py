from django.db import migrations

from kernel.db import attributes_check, enable_rls, same_tenant_fk


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
        ("resources", "0001_initial"),
        ("config", "0002_initial"),
        ("kernel", "0002_db_rules"),
    ]

    operations = [
        # users has no tenant_id and no RLS: one person, many tenants.
        enable_rls("memberships"),
        enable_rls("roles"),
        enable_rls("membership_roles"),
        same_tenant_fk("memberships", "default_location_id", "locations"),
        same_tenant_fk("memberships", "schema_id", "object_schema_versions"),
        same_tenant_fk("memberships", "invited_by_membership_id", "memberships"),
        same_tenant_fk("membership_roles", "membership_id", "memberships"),
        same_tenant_fk("membership_roles", "role_id", "roles"),
        same_tenant_fk("membership_roles", "location_id", "locations"),
        attributes_check("memberships"),
    ]
