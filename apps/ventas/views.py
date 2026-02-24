from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from .models import Sale
from .serializers import SaleSerializer
from .models import SaleItem
from .serializers import SaleItemSerializer



class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Sale.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        sale = self.get_object()

        try:
            sale.confirm()
            return Response(self.get_serializer(sale).data)

        except ValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        sale = self.get_object()

        try:
            sale.cancel()
            return Response(self.get_serializer(sale).data)

        except ValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
class SaleItemViewSet(viewsets.ModelViewSet):
    queryset = SaleItem.objects.all()
    serializer_class = SaleItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        sale = serializer.validated_data["sale"]

        # 🔒 Solo permitir agregar items si la venta está en draft
        if sale.estado != "draft":
            raise ValidationError(
                "No se pueden agregar items a una venta confirmada"
            )

        serializer.save()