from rest_framework import generics, permissions
from .models import Product
from .serializers import ProductSerializer


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