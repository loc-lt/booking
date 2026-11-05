from django.db import migrations

from kernel.db import enable_rls


class Migration(migrations.Migration):
    dependencies = [
        ("rules", "0001_initial"),
        ("kernel", "0002_db_rules"),
    ]

    operations = [
        enable_rls("rule_set_versions"),
    ]
