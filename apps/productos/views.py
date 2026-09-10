from rest_framework import generics, permissions

from apps.accounts.services.users import get_usuario_titular

from .models import Product, ProductPresentation
from .serializers import (
    ProductSerializer,
    ProductPresentationSerializer,
)


# 🔥 LISTAR + CREAR
class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        titular = get_usuario_titular(
            self.request.user,
        )

        return Product.objects.filter(
            usuario=titular,
        )

    def perform_create(self, serializer):
        titular = get_usuario_titular(
            self.request.user,
        )

        serializer.save(
            usuario=titular,
        )


# 🔥 ELIMINAR + EDITAR
class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        titular = get_usuario_titular(
            self.request.user,
        )

        return Product.objects.filter(
            usuario=titular,
        )


class ProductPresentationListCreateView(
    generics.ListCreateAPIView
):
    serializer_class = ProductPresentationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        titular = get_usuario_titular(
            self.request.user,
        )

        return ProductPresentation.objects.filter(
            product__usuario=titular,
        ).select_related(
            "product",
            "bin_type",
        )


class ProductPresentationDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    serializer_class = ProductPresentationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        titular = get_usuario_titular(
            self.request.user,
        )

        return ProductPresentation.objects.filter(
            product__usuario=titular,
        ).select_related(
            "product",
            "bin_type",
        )