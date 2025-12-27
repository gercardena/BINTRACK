from django.urls import path
from .views import CrearPagoView, ConfirmarPagoView

urlpatterns = [
    path("crear/", CrearPagoView.as_view(), name="crear_pago"),
    path("confirmar/", ConfirmarPagoView.as_view(), name="confirmar_pago"),
]
