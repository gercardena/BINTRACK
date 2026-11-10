from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = (
        "Crea un titular de negocio con contraseña temporal y obliga "
        "su cambio al primer ingreso."
    )

    def add_arguments(self, parser):
        parser.add_argument("username", help="Usuario titular del negocio.")
        parser.add_argument("--email", required=True, help="Correo del titular.")
        parser.add_argument(
            "--temporary-password",
            required=True,
            help="Contraseña temporal que el titular deberá cambiar.",
        )
        parser.add_argument("--first-name", default="")
        parser.add_argument("--last-name", default="")
        parser.add_argument("--telefono", default="")
        parser.add_argument("--rut", default="")

    def handle(self, *args, **options):
        username = options["username"].strip()
        email = options["email"].strip().lower()
        password = options["temporary_password"]

        if not username:
            raise CommandError("El usuario no puede estar vacío.")
        if password != password.strip():
            raise CommandError("La contraseña temporal no puede tener espacios externos.")
        if User.objects.filter(username__iexact=username).exists():
            raise CommandError("Ese usuario ya existe.")
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError("Ese correo ya está registrado.")

        candidate = User(username=username, email=email)
        try:
            validate_password(password, candidate)
        except DjangoValidationError as error:
            raise CommandError(" ".join(error.messages)) from error

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=options["first_name"].strip(),
            last_name=options["last_name"].strip(),
            telefono=options["telefono"].strip() or None,
            rut=options["rut"].strip() or None,
            suscripcion_activa=False,
            debe_cambiar_contrasena=True,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Titular {user.username} creado. Debe cambiar la contraseña al primer ingreso."
            )
        )
