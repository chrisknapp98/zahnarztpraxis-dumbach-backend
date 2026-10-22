from django.db import migrations


def create_editor_group(apps, schema_editor):
    alias = schema_editor.connection.alias
    Group = apps.get_model("auth", "Group")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    group, _ = Group.objects.using(alias).get_or_create(name="Practice editors")
    content_type, _ = ContentType.objects.using(alias).get_or_create(app_label="practice", model="announcement")
    for action in ("view", "add", "change", "delete"):
        permission, _ = Permission.objects.using(alias).get_or_create(
            content_type=content_type,
            codename=f"{action}_announcement",
            defaults={"name": f"Can {action} announcement"},
        )
        group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [
        ("practice", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]
    operations = [migrations.RunPython(create_editor_group, migrations.RunPython.noop)]
