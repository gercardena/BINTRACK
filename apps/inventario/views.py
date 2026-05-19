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

        # 🔥 DEBUG TEMPORAL
        return Inventory.objects.all()


# 🔥 AJUSTAR STOCK
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def ajustar_stock(request):

    product_id = request.data.get('product')
    bin_id = request.data.get('bin')
    cantidad = request.data.get('cantidad')

    print("DATA RECIBIDA:", request.data)

    # =========================================
    # VALIDACIONES
    # =========================================

    if product_id is None or bin_id is None or cantidad is None:

        return Response(
            {
                "error": "product, bin y cantidad son requeridos"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # =========================================
    # BUSCAR PRODUCTO
    # =========================================

    try:

        producto = Product.objects.get(
            id=product_id,
            usuario=request.user
        )

    except Product.DoesNotExist:

        return Response(
            {
                "error": "Producto no encontrado"
            },
            status=status.HTTP_404_NOT_FOUND
        )

    # =========================================
    # BUSCAR BIN
    # =========================================

    from apps.bins.models import BinType

    try:

        bin_obj = BinType.objects.get(
            id=bin_id
        )

    except BinType.DoesNotExist:

        return Response(
            {
                "error": "Bin no encontrado"
            },
            status=status.HTTP_404_NOT_FOUND
        )

    # =========================================
    # CREAR O ACTUALIZAR INVENTARIO
    # =========================================

    inventario, created = Inventory.objects.get_or_create(

        usuario=request.user,
        product=producto,
        bin=bin_obj,

        defaults={
            "cantidad": 0
        }
    )

    inventario.cantidad += int(cantidad)

    inventario.save()

    # =========================================
    # RESPONSE
    # =========================================

    return Response({

        "inventory_id": inventario.id,
        "product": producto.nombre,
        "bin": bin_obj.nombre,
        "cantidad": inventario.cantidad

    }, status=status.HTTP_200_OK)