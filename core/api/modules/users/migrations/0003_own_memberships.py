"""Let a signed-in person list their own memberships across tenants (GET /me/tenants).

The extra RLS policy applies only while NO tenant is active (app.tenant_id empty), so inside
a tenant request memberships stay limited to that tenant exactly as before. app.user_id is
set by kernel.auth after the token is verified.
"""

from django.db import migrations

_TENANT = "NULLIF(current_setting('app.tenant_id', true), '')"
_USER = "NULLIF(current_setting('app.user_id', true), '')::uuid"


class Migration(migrations.Migration):
    dependencies = [("users", "0002_db_rules")]

    operations = [
        migrations.RunSQL(
            f"""
            CREATE POLICY own_memberships ON memberships FOR SELECT
                USING ({_TENANT} IS NULL AND user_id = {_USER});
            """,
            "DROP POLICY own_memberships ON memberships;",
        ),
    ]
