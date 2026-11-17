"""The core does not translate anything: languages are the frontend's job."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("users", "0003_own_memberships")]

    operations = [migrations.RemoveField(model_name="user", name="locale")]
