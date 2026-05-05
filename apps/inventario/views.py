from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Inventory
from .serializers import InventorySerializer
from apps.productos.models import Product


# 🔹 LISTAR INVENTARIO
class InventoryListView(generics.ListAPIView):
    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Inventory.objects.filter(usuario=self.request.user)


# 🔥 AJUSTAR STOCK
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def ajustar_stock(request):

    product_id = request.data.get('product')
    cantidad = request.data.get('cantidad')

    print("DATA RECIBIDA:", request.data)

    if product_id is None or cantidad is None:
        return Response(
            {"error": "product y cantidad son requeridos"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        producto = Product.objects.get(
            id=product_id,
            usuario=request.user
        )
    except Product.DoesNotExist:
        return Response(
            {"error": "Producto no encontrado"},
            status=status.HTTP_404_NOT_FOUND
        )

    inventario, _ = Inventory.objects.get_or_create(
        product=producto,
        usuario=request.user,
        defaults={"cantidad": 0}
    )

    inventario.cantidad += int(cantidad)
    inventario.save()

    return Response({
        "product": producto.nombre,
        "cantidad": inventario.cantidad
    }, status=status.HTTP_200_OK)