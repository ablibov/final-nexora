"""Assign a Nexora role to an already registered user.

Example: python manage.py set_role person@example.com moderator
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from accounts.roles import ADMIN_GROUP, MODERATOR_GROUP


class Command(BaseCommand):
    help = "Assign admin, moderator, or user role by email; superadmin uses createsuperuser"

    def add_arguments(self, parser):
        parser.add_argument("email", help="User email")
        parser.add_argument("role", choices=["admin", "moderator", "user"])

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=options["email"])
        except User.DoesNotExist as exc:
            raise CommandError("User with this email does not exist") from exc
        except User.MultipleObjectsReturned as exc:
            raise CommandError("Multiple users have this email; cannot choose safely") from exc

        if user.is_superuser:
            raise CommandError("User is already superadmin. Manage this account in Django Admin.")

        groups = list(Group.objects.filter(name__in=[ADMIN_GROUP, MODERATOR_GROUP]))
        if len(groups) != 2:
            raise CommandError("Run: python manage.py setup_roles")

        user.groups.remove(*groups)
        role = options["role"]
        if role == "admin":
            user.groups.add(next(g for g in groups if g.name == ADMIN_GROUP))
        elif role == "moderator":
            user.groups.add(next(g for g in groups if g.name == MODERATOR_GROUP))

        user.is_staff = role != "user"
        user.save(update_fields=["is_staff"])
        self.stdout.write(self.style.SUCCESS(f"{user.email}: {role}"))
