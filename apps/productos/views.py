from rest_framework import generics, permissions
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
        return Product.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)


# 🔥 ELIMINAR + EDITAR
class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):

    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(usuario=self.request.user)
    
class ProductPresentationListCreateView(
    generics.ListCreateAPIView
):

    serializer_class = ProductPresentationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProductPresentation.objects.filter(
            product__usuario=self.request.user
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
        return ProductPresentation.objects.filter(
            product__usuario=self.request.user
        ).select_related(
            "product",
            "bin_type",
        )