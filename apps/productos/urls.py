from django.urls import path

from .views import (
    ProductListCreateView,
    ProductDetailView,
    ProductPresentationListCreateView,
    ProductPresentationDetailView,
)

urlpatterns = [
    path(
        "",
        ProductListCreateView.as_view(),
        name="product_list_create",
    ),
    path(
        "<int:pk>/",
        ProductDetailView.as_view(),
        name="product_detail",
    ),
    path(
        "presentations/",
        ProductPresentationListCreateView.as_view(),
        name="presentation_list_create",
    ),
    path(
        "presentations/<int:pk>/",
        ProductPresentationDetailView.as_view(),
        name="presentation_detail",
    ),
]