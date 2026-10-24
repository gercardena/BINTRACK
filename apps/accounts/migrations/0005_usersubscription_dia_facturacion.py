from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_planes_mensuales")]
    operations = [
        migrations.AddField(
            model_name="usersubscription", name="dia_facturacion",
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
    ]
