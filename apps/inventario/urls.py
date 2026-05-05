from django.urls import path
from .views import InventoryListView, ajustar_stock

urlpatterns = [
    path("", InventoryListView.as_view(), name="inventory_list"),
    path("ajustar/", ajustar_stock, name="ajustar_stock"),
]
