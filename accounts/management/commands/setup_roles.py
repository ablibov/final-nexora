"""Create Nexora role groups and optionally grant content model permissions.

Example: python manage.py setup_roles --model core.Post
Repeat --model for additional content models.
"""

from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError

from accounts.roles import ADMIN_GROUP, MODERATOR_GROUP


class Command(BaseCommand):
    help = "Create Administrators/Moderators groups; optionally configure content permissions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model", action="append", default=[], metavar="APP.MODEL",
            help="Model whose permissions should be granted (e.g. core.Post); repeatable",
        )

    def handle(self, *args, **options):
        # Validate first so a bad model name won't partially configure groups.
        models = []
        for model_label in options["model"]:
            try:
                app_label, model_name = model_label.split(".", 1)
                if not app_label or not model_name:
                    raise ValueError
                model = apps.get_model(app_label, model_name)
                if model is None:
                    raise LookupError(model_label)
            except (ValueError, LookupError) as exc:
                raise CommandError(
                    f"Unknown model {model_label!r}. Check the model name in your models.py"
                ) from exc
            # Group/permission/account models must never be assigned wholesale to
            # content staff; doing so can enable privilege escalation.
            if model._meta.app_label in {"auth", "admin", "contenttypes", "sessions", "accounts"}:
                raise CommandError(
                    f"{model._meta.label} is a sensitive model. Only configure content models."
                )
            models.append(model)

        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        mod_group, _ = Group.objects.get_or_create(name=MODERATOR_GROUP)

        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            model_name = model._meta.model_name
            admin_permissions = Permission.objects.filter(
                content_type=content_type,
                codename__in=[
                    f"view_{model_name}", f"add_{model_name}",
                    f"change_{model_name}", f"delete_{model_name}",
                ],
            )
            mod_permissions = Permission.objects.filter(
                content_type=content_type,
                codename__in=[f"view_{model_name}", f"change_{model_name}"],
            )
            admin_group.permissions.add(*admin_permissions)
            mod_group.permissions.add(*mod_permissions)
            self.stdout.write(f"Permissions configured for {model._meta.label}.")

        self.stdout.write(self.style.SUCCESS("Roles: Administrators, Moderators created."))
        if not models:
            self.stdout.write(
                "No model given: groups are empty. Use --model core.YourModel to grant content permissions."
            )
