from django.urls import path
from .views import (
    BinTypeListView,
    ClienteListView,
    BinMovementListView,
    BinBalanceView
)

urlpatterns = [
    path("types/", BinTypeListView.as_view(), name="bin_types"),
    path("clientes/", ClienteListView.as_view(), name="bin_clientes"),
    path("movements/", BinMovementListView.as_view(), name="bin_movements"),

    # 🔥 NUEVO
    path("balance/", BinBalanceView.as_view(), name="bin_balance"),
]