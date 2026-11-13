"""Nexora roles built on Django Groups (no custom User model required)."""

ADMIN_GROUP = "Administrators"
MODERATOR_GROUP = "Moderators"

ROLE_LABELS = {
    "superadmin": "Супер-администратор",
    "admin": "Администратор",
    "moderator": "Модератор",
    "user": "Пользователь",
    "guest": "Гость",
}


def get_user_role(user):
    """Return a display role. Permission checks must still use has_perm()."""
    if not user.is_authenticated:
        return "guest"
    if user.is_superuser:
        return "superadmin"
    if user.groups.filter(name=ADMIN_GROUP).exists():
        return "admin"
    if user.groups.filter(name=MODERATOR_GROUP).exists():
        return "moderator"
    return "user"
