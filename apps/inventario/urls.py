from django.urls import path

from .views import (
    InventoryListView,
    crear_inventario,
    ajustar_stock,
)

urlpatterns = [

    # 🔹 LISTAR INVENTARIO
    path(
        '',
        InventoryListView.as_view(),
        name='inventory-list'
    ),

    # 🔥 CREAR INVENTARIO
    path(
        'crear/',
        crear_inventario,
        name='crear-inventario'
    ),

    # 🔥 AJUSTAR STOCK
    path(
        'ajustar/',
        ajustar_stock,
        name='ajustar-stock'
    ),
]
