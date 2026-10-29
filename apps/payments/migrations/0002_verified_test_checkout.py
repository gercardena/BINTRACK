import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
        ("accounts", "0005_usersubscription_dia_facturacion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment", name="status",
            field=models.CharField(max_length=20, default="pending", choices=[
                ("pending", "Pendiente"), ("approved", "Aprobado"), ("rejected", "Rechazado"),
                ("cancelled", "Cancelado"), ("refunded", "Reembolsado"), ("charged_back", "Contracargo"),
            ]),
        ),
        # No historical payment is backfilled with an activation-capable reference.
        migrations.AddField(model_name="payment", name="reference", field=models.UUIDField(null=True, blank=True, unique=True, editable=False)),
        migrations.AddField(model_name="payment", name="environment", field=models.CharField(max_length=20, blank=True)),
        migrations.AddField(model_name="payment", name="plan_code", field=models.CharField(max_length=40, blank=True)),
        migrations.AddField(model_name="payment", name="secondary_ids", field=models.JSONField(default=list, blank=True)),
        migrations.AddField(model_name="payment", name="expected_due_at", field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name="payment", name="expires_at", field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name="payment", name="checkout_url", field=models.URLField(max_length=1000, blank=True)),
        migrations.AddField(model_name="payment", name="applied_at", field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name="payment", name="applied_until", field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name="payment", name="applied_provider_id", field=models.CharField(max_length=100, blank=True)),
        migrations.AddField(model_name="payment", name="needs_review", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="payment", name="review_reason", field=models.CharField(max_length=60, blank=True)),
        migrations.CreateModel(
            name="PaymentAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider_payment_id", models.CharField(max_length=100, unique=True)),
                ("status", models.CharField(max_length=30)),
                ("provider_updated_at", models.DateTimeField()),
                ("observed_at", models.DateTimeField(auto_now=True)),
                ("payment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attempts", to="payments.payment")),
            ],
        ),
    ]
