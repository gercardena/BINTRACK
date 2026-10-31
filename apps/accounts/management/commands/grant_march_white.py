from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.services.trial_periods import grant_march_white_period


class Command(BaseCommand):
    help = "Otorga un mes de marcha blanca a un titular y registra la decisión."

    def add_arguments(self, parser):
        parser.add_argument("owner", help="Usuario titular que recibirá el período.")
        parser.add_argument("--actor", required=True, help="Usuario administrador que autoriza la acción.")
        parser.add_argument("--reason", required=True, help="Motivo administrativo de la activación.")

    def handle(self, *args, **options):
        user_model = get_user_model()
        try:
            owner = user_model.objects.get(username=options["owner"])
        except user_model.DoesNotExist as error:
            raise CommandError("No existe el usuario titular indicado.") from error
        try:
            actor = user_model.objects.get(username=options["actor"])
        except user_model.DoesNotExist as error:
            raise CommandError("No existe el administrador indicado.") from error

        try:
            grant = grant_march_white_period(
                owner,
                granted_by=actor,
                reason=options["reason"],
            )
        except Exception as error:
            raise CommandError(str(error)) from error

        self.stdout.write(
            self.style.SUCCESS(
                f"Marcha blanca otorgada a {grant.owner.username} hasta "
                f"{grant.granted_until:%d/%m/%Y}. Registro #{grant.pk}."
            )
        )
