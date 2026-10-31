from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_usersubscription_dia_facturacion")]

    operations = [
        migrations.CreateModel(
            name="SubscriptionGrant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(max_length=250)),
                ("previous_end", models.DateTimeField(blank=True, null=True)),
                ("granted_from", models.DateTimeField()),
                ("granted_until", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("granted_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="subscription_grants_made", to=settings.AUTH_USER_MODEL)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="subscription_grants", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
