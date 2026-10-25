import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from core.models import User
from core.services import record


class Command(BaseCommand):
    help = "Provision an account interactively. Passwords never appear in command arguments."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--role", choices=User.Role.values, default="student")

    def handle(self, *args, **options):
        if User.objects.filter(username__iexact=options["username"]).exists():
            raise CommandError("Username already exists; no account was changed.")
        user = User(username=options["username"], email=options["email"].lower(), role=options["role"])
        try:
            user.full_clean(exclude=["password"])
            password = getpass.getpass("New password (15+ characters): ")
            if password != getpass.getpass("Confirm password: "):
                raise CommandError("Passwords did not match.")
            validate_password(password, user)
        except ValidationError as error:
            raise CommandError("; ".join(error.messages)) from error
        user.set_password(password)
        user.save()
        record(user, "account.provisioned_cli")
        self.stdout.write(self.style.SUCCESS(f"Created {user.username} with role {user.role}."))
