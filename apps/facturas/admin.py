from django.contrib import admin
from .models import Factura


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "numero",
        "sale",
        "cliente_nombre",
        "total",
        "fecha_emision",
    )

    search_fields = (
        "numero",
        "cliente_nombre",
        "cliente_rut",
    )

    list_filter = (
        "fecha_emision",
    )