"""Display Nexora roles and restrict account/group management to superadmins."""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as DefaultGroupAdmin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import Group

from .roles import ROLE_LABELS, get_user_role

User = get_user_model()


class SuperuserOnlyAdminMixin:
    """Don't allow content staff to alter users, roles, or privileges."""

    def _allowed(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_module_permission(self, request):
        return self._allowed(request)

    def has_view_permission(self, request, obj=None):
        return self._allowed(request)

    def has_add_permission(self, request):
        return self._allowed(request)

    def has_change_permission(self, request, obj=None):
        return self._allowed(request)

    def has_delete_permission(self, request, obj=None):
        return self._allowed(request)


if admin.site.is_registered(User):
    admin.site.unregister(User)


@admin.register(User)
class NexoraUserAdmin(SuperuserOnlyAdminMixin, DefaultUserAdmin):
    list_display = (*DefaultUserAdmin.list_display, "nexora_role")

    @admin.display(description="Роль")
    def nexora_role(self, obj):
        return ROLE_LABELS[get_user_role(obj)]


if admin.site.is_registered(Group):
    admin.site.unregister(Group)


@admin.register(Group)
class NexoraGroupAdmin(SuperuserOnlyAdminMixin, DefaultGroupAdmin):
    pass
