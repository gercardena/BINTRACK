from django.urls import path
from .views import InventarioListView

urlpatterns = [
    path("inventario/", InventarioListView.as_view(), name="inventario-list"),
]