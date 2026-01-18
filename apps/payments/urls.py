from django.urls import path
from .views import (
    CrearPagoView,
    ConfirmarPagoView,
    MercadoPagoWebhookView,
    SimularPagoAprobadoView,
)

urlpatterns = [
    path("crear/", CrearPagoView.as_view(), name="crear_pago"),
    path("confirmar/", ConfirmarPagoView.as_view(), name="confirmar_pago"),
    path("webhook/", MercadoPagoWebhookView, name="mp_webhook"),

    # 🧪 Simulación de pago aprobado
    path(
        "simular-aprobado/<int:payment_id>/",
        SimularPagoAprobadoView.as_view(),
        name="simular_pago_aprobado",
    ),
]

