from django.urls import path

from .views import (
    BinTypeListView,
    BinTypeDetailView,
    ClienteListView,
    ClienteDetailView,
    BinMovementListView,
    BinBalanceView,
)

urlpatterns = [
    path(
        "types/",
        BinTypeListView.as_view(),
        name="bin_types",
    ),

    path(
        "types/<int:pk>/",
        BinTypeDetailView.as_view(),
        name="bin_type_detail",
    ),

    path(
        "clientes/",
        ClienteListView.as_view(),
        name="bin_clientes",
    ),

    path(
        "clientes/<int:pk>/",
        ClienteDetailView.as_view(),
        name="bin_cliente_detail",
    ),

    path(
        "movements/",
        BinMovementListView.as_view(),
        name="bin_movements",
    ),

    path(
        "balance/",
        BinBalanceView.as_view(),
        name="bin_balance",
    ),
]