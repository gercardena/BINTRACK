from django.db import migrations, models


def crear_catalogo(apps, schema_editor):
    Plan = apps.get_model("accounts", "SubscriptionPlan")
    for secundarios, precio in [(0, 50000), (1, 60000), (2, 70000)]:
        Plan.objects.using(schema_editor.connection.alias).get_or_create(
            codigo=f"bintrack_mensual_{secundarios}",
            defaults={
                "nombre": f"Principal + {secundarios} secundarios",
                "usuarios_secundarios": secundarios,
                "precio": precio,
                "duracion_dias": 30,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_usuarioasociado")]
    operations = [
        migrations.AddField(
            model_name="subscriptionplan", name="codigo",
            field=models.CharField(max_length=40, unique=True, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="subscriptionplan", name="usuarios_secundarios",
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
        # Do not remove plans or reassign historical subscriptions on rollback.
        migrations.RunPython(crear_catalogo, migrations.RunPython.noop),
    ]
