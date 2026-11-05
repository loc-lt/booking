"""Migration operations for rules the Django ORM cannot declare.

Table and column names come from migration code, never from user input.
"""

from django.db import DatabaseError, IntegrityError, migrations

# NULLIF: once set_config has run on a connection, the setting reads '' (not NULL) in
# later transactions, and ''::uuid raises an error instead of returning no rows.
_TENANT = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def enable_rls(table: str) -> migrations.RunSQL:
    """Rows are visible and writable only when tenant_id matches app.tenant_id.

    FORCE applies the policy to the table owner too. Only superusers and roles with
    BYPASSRLS skip it, so the application must never connect as one of those.
    """
    return migrations.RunSQL(
        sql=f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY tenant_isolation ON {table}
                USING (tenant_id = {_TENANT})
                WITH CHECK (tenant_id = {_TENANT});
        """,
        reverse_sql=f"""
            DROP POLICY IF EXISTS tenant_isolation ON {table};
            ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
            ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
        """,
    )


def same_tenant_fk(table: str, column: str, ref_table: str) -> migrations.RunSQL:
    """FK (tenant_id, column) -> ref_table (tenant_id, id): a row cannot point at another
    tenant's row, even if the code has a bug. ref_table needs UNIQUE (tenant_id, id)."""
    name = f"{table}_{column}_same_tenant"
    return migrations.RunSQL(
        sql=f"""
            ALTER TABLE {table} ADD CONSTRAINT {name}
            FOREIGN KEY (tenant_id, {column}) REFERENCES {ref_table} (tenant_id, id)
            DEFERRABLE INITIALLY DEFERRED;
        """,
        reverse_sql=f"ALTER TABLE {table} DROP CONSTRAINT {name};",
    )


def attributes_check(table: str, max_bytes: int = 65536) -> migrations.RunSQL:
    """Custom field values must be a JSON object and stay small."""
    name = f"{table}_attributes_shape"
    return migrations.RunSQL(
        sql=f"""
            ALTER TABLE {table} ADD CONSTRAINT {name}
            CHECK (jsonb_typeof(attributes) = 'object'
                   AND pg_column_size(attributes) <= {max_bytes});
        """,
        reverse_sql=f"ALTER TABLE {table} DROP CONSTRAINT {name};",
    )


def violated_constraint(exc: IntegrityError) -> str | None:
    """Name of the constraint behind an IntegrityError, so services can map it to an error."""
    diag = getattr(exc.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None)


DEADLOCK_DETECTED = "40P01"


def sqlstate(exc: DatabaseError) -> str | None:
    """SQLSTATE of the PostgreSQL error behind a Django database error."""
    return getattr(exc.__cause__, "sqlstate", None)
