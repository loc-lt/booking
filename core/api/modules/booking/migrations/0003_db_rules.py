"""The double-booking guard and the other rules of bookings and booking_allocations."""

from django.db import migrations

from kernel.db import attributes_check, enable_rls, same_tenant_fk

OPEN = "'awaiting_payment', 'pending_approval', 'confirmed', 'checked_in'"


class Migration(migrations.Migration):
    dependencies = [
        ("booking", "0002_initial"),
        ("config", "0003_db_rules"),
        ("resources", "0002_db_rules"),
        ("users", "0002_db_rules"),
    ]

    operations = [
        enable_rls("bookings"),
        enable_rls("booking_allocations"),
        same_tenant_fk("bookings", "location_id", "locations"),
        same_tenant_fk("bookings", "resource_id", "resources"),
        same_tenant_fk("bookings", "resource_type_id", "resource_types"),
        same_tenant_fk("bookings", "booker_membership_id", "memberships"),
        same_tenant_fk("bookings", "created_by_membership_id", "memberships"),
        same_tenant_fk("bookings", "cancelled_by_membership_id", "memberships"),
        same_tenant_fk("bookings", "policy_version_id", "policy_versions"),
        same_tenant_fk("bookings", "schema_id", "object_schema_versions"),
        same_tenant_fk("bookings", "rescheduled_from_id", "bookings"),
        same_tenant_fk("booking_allocations", "booking_id", "bookings"),
        same_tenant_fk("booking_allocations", "resource_id", "resources"),
        attributes_check("bookings"),
        migrations.RunSQL(
            f"""
            -- Two open EXCLUSIVE allocations of one resource can never overlap. The second of
            -- two racing requests fails here; the API turns it into SLOT_TAKEN.
            ALTER TABLE booking_allocations ADD CONSTRAINT allocations_no_overlap
                EXCLUDE USING gist (tenant_id WITH =, resource_id WITH =, during WITH &&)
                WHERE (booking_mode = 'EXCLUSIVE' AND closed_at IS NULL);
            ALTER TABLE booking_allocations ADD CONSTRAINT allocations_hold_expiry
                CHECK (effect = 'HOLD' OR hold_expires_at IS NULL);
            CREATE INDEX allocations_hold_due ON booking_allocations (hold_expires_at)
                WHERE effect = 'HOLD' AND closed_at IS NULL;
            -- ACCESS_PASS: one open day pass per member, site and local day.
            CREATE UNIQUE INDEX bookings_one_pass_per_day ON bookings
                (tenant_id, booker_membership_id, location_id, local_date)
                WHERE booking_mode = 'ACCESS_PASS' AND status IN ({OPEN});
            """,
            """
            DROP INDEX bookings_one_pass_per_day;
            DROP INDEX allocations_hold_due;
            ALTER TABLE booking_allocations DROP CONSTRAINT allocations_hold_expiry;
            ALTER TABLE booking_allocations DROP CONSTRAINT allocations_no_overlap;
            """,
        ),
    ]
