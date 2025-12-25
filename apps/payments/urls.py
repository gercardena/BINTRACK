from django.urls import path
from .views import CrearPagoView

urlpatterns = [
    path("crear/", CrearPagoView.as_view(), name="crear_pago"),
]
