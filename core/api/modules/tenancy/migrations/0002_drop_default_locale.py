"""The core does not translate anything: languages are the frontend's job."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0001_initial")]

    operations = [migrations.RemoveField(model_name="tenant", name="default_locale")]
