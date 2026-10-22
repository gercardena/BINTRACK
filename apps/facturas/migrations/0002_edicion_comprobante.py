from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("facturas", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="factura", name="observaciones",
            field=models.TextField(blank=True, default="", max_length=2000),
        ),
        migrations.AddField(
            model_name="factura", name="version",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="FacturaCambio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("usuario_nombre", models.CharField(max_length=150)),
                ("fecha", models.DateTimeField(default=django.utils.timezone.now)),
                ("cambios", models.JSONField()),
                ("factura", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cambios", to="facturas.factura")),
                ("usuario", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-fecha", "-id"]},
        ),
    ]
