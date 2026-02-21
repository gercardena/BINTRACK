from django.contrib import admin
from .models import Inventory


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "product", "bin", "cantidad")
    list_filter = ("usuario", "product", "bin")
