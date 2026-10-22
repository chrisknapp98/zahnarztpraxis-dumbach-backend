import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_author(apps, schema_editor):
    alias = schema_editor.connection.alias
    Announcement = apps.get_model("practice", "Announcement")
    missing = Announcement.objects.using(alias).filter(author__isnull=True)
    if not missing.exists():
        return
    User = apps.get_model(settings.AUTH_USER_MODEL)
    # Explicitly chosen by the maintainer for pre-existing announcements.
    author = User.objects.using(alias).get(username="admin")
    missing.update(author_id=author.pk)


class Migration(migrations.Migration):
    dependencies = [
        ("practice", "0002_practice_editors"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(
            model_name="announcement",
            name="author",
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT,
                related_name="announcements", editable=False, null=True,
            ),
        ),
        migrations.RunPython(backfill_author, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="announcement",
            name="author",
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT,
                related_name="announcements", editable=False,
            ),
        ),
    ]
