from django.contrib import admin
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rut", "telefono", "activo")
    search_fields = ("nombre", "rut")
