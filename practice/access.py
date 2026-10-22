EDITOR_GROUP = "Practice editors"


def can_access_practice(user):
    return bool(
        user is not None
        and user.is_authenticated
        and user.is_active
        and (user.is_superuser or user.groups.filter(name=EDITOR_GROUP).exists())
    )
