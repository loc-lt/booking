"""Field labels and help become plain text.

They were stored as {"default": text} to leave room for translations; the core does not
translate (languages are the frontend's job) and the API always read and wrote plain strings.
"""

from django.db import migrations, models

_TO_TEXT = """
ALTER TABLE field_definitions
    ALTER COLUMN label TYPE text USING label->>'default',
    ALTER COLUMN help_text TYPE text USING help_text->>'default';
"""
_TO_JSON = """
ALTER TABLE field_definitions
    ALTER COLUMN label TYPE jsonb USING jsonb_build_object('default', label),
    ALTER COLUMN help_text TYPE jsonb USING
        CASE WHEN help_text IS NULL THEN NULL ELSE jsonb_build_object('default', help_text) END;
"""


class Migration(migrations.Migration):
    dependencies = [("config", "0003_db_rules")]

    operations = [
        migrations.RunSQL(
            _TO_TEXT,
            _TO_JSON,
            state_operations=[
                migrations.AlterField(
                    model_name="fielddefinition", name="label", field=models.TextField()
                ),
                migrations.AlterField(
                    model_name="fielddefinition",
                    name="help_text",
                    field=models.TextField(blank=True, null=True),
                ),
            ],
        )
    ]
