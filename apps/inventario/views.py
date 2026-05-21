from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Inventory
from .serializers import InventorySerializer

from apps.productos.models import Product
from apps.bins.models import BinType


# =========================================================
# 🔹 LISTAR INVENTARIO
# =========================================================

class InventoryListView(generics.ListAPIView):

    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        # 🔥 SOLO INVENTARIO DEL USUARIO LOGEADO
        return Inventory.objects.filter(
            usuario=self.request.user
        ).order_by('-id')


# =========================================================
# 🔥 CREAR INVENTARIO
# =========================================================

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def crear_inventario(request):

    product_id = request.data.get('product')
    bin_id = request.data.get('bin')
    cantidad = request.data.get('cantidad', 0)

    print("CREAR INVENTARIO DATA:", request.data)

    # =====================================================
    # VALIDACIONES
    # =====================================================

    if not product_id or not bin_id:

        return Response(
            {
                "error": "product y bin son requeridos"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # =====================================================
    # PRODUCTO
    # =====================================================

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

    # =====================================================
    # BIN
    # =====================================================

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

    # =====================================================
    # VALIDAR DUPLICADOS
    # =====================================================

    existe = Inventory.objects.filter(
        usuario=request.user,
        product=producto,
        bin=bin_obj
    ).exists()

    if existe:

        return Response(
            {
                "error": "El inventario ya existe"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # =====================================================
    # CREAR INVENTARIO
    # =====================================================

    inventario = Inventory.objects.create(
        usuario=request.user,
        product=producto,
        bin=bin_obj,
        cantidad=int(cantidad)
    )

    serializer = InventorySerializer(inventario)

    return Response(
        serializer.data,
        status=status.HTTP_201_CREATED
    )


# =========================================================
# 🔥 AJUSTAR STOCK (PRO)
# =========================================================

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def ajustar_stock(request):

    product_id = request.data.get('product')
    bin_id = request.data.get('bin')
    cantidad = request.data.get('cantidad')

    print("AJUSTAR STOCK DATA:", request.data)

    # =====================================================
    # VALIDACIONES
    # =====================================================

    if product_id is None or bin_id is None or cantidad is None:

        return Response(
            {
                "error": "product, bin y cantidad son requeridos"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # =====================================================
    # VALIDAR CANTIDAD
    # =====================================================

    try:

        cantidad = int(cantidad)

    except ValueError:

        return Response(
            {
                "error": "cantidad debe ser numérica"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # =====================================================
    # PRODUCTO
    # =====================================================

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

    # =====================================================
    # BIN
    # =====================================================

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

    # =====================================================
    # CREAR O BUSCAR INVENTARIO
    # =====================================================

    inventario, created = Inventory.objects.get_or_create(

        usuario=request.user,
        product=producto,
        bin=bin_obj,

        defaults={
            "cantidad": 0
        }
    )

    # =====================================================
    # VALIDAR STOCK NEGATIVO
    # =====================================================

    nuevo_stock = inventario.cantidad + cantidad

    if nuevo_stock < 0:

        return Response(
            {
                "error": "Stock insuficiente",
                "stock_actual": inventario.cantidad
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # =====================================================
    # ACTUALIZAR STOCK
    # =====================================================

    inventario.cantidad = nuevo_stock

    inventario.save()

    serializer = InventorySerializer(inventario)

    # =====================================================
    # RESPONSE
    # =====================================================

    return Response(
        {
            "mensaje": "Stock actualizado correctamente",
            "inventario": serializer.data
        },
        status=status.HTTP_200_OK
    )