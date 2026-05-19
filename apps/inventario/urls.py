from django.urls import path

from .views import (
    InventoryListView,
    ajustar_stock,
)

urlpatterns = [

    # 🔹 LISTAR INVENTARIO
    path(
        '',
        InventoryListView.as_view(),
        name='inventory-list'
    ),

    # 🔥 AJUSTAR STOCK
    path(
        'ajustar/',
        ajustar_stock,
        name='ajustar-stock'
    ),
]
