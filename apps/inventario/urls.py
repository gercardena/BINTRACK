from django.urls import path

from .views import InventoryView, StockListView, StockDetailView


urlpatterns = [

    path(
        "",
        InventoryView.as_view(),
        name="inventory",
    ),

    path(
        "stock/",
        StockListView.as_view(),
        name="stock_list",
    ),

    path(
        "stock/<int:pk>/",
        StockDetailView.as_view(),
        name="stock_detail",
    ),

]
