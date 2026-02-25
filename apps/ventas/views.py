from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db import transaction

from .models import Sale, SaleItem
from .serializers import SaleSerializer, SaleItemSerializer


# ==========================
# SALE VIEWSET
# ==========================

class SaleViewSet(viewsets.ModelViewSet):

    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Sale.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    # 🔒 BLOQUEAR UPDATE
    def update(self, request, *args, **kwargs):
        sale = self.get_object()

        if sale.estado != "draft":
            raise ValidationError("No se puede modificar una venta confirmada")

        return super().update(request, *args, **kwargs)

    # 🔒 BLOQUEAR PATCH
    def partial_update(self, request, *args, **kwargs):
        sale = self.get_object()

        if sale.estado != "draft":
            raise ValidationError("No se puede modificar una venta confirmada")

        return super().partial_update(request, *args, **kwargs)

    # 🔒 BLOQUEAR DELETE
    def destroy(self, request, *args, **kwargs):
        sale = self.get_object()

        if sale.estado != "draft":
            raise ValidationError("No se puede eliminar una venta confirmada")

        return super().destroy(request, *args, **kwargs)

    # ==========================
    # CONFIRM SALE
    # ==========================

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def confirm(self, request, pk=None):
        sale = self.get_object()

        if sale.estado != "draft":
            return Response(
                {"error": "Solo se pueden confirmar ventas en draft"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            sale.confirm()
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(sale)
        return Response(serializer.data)

    # ==========================
    # CANCEL SALE
    # ==========================

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def cancel(self, request, pk=None):
        sale = self.get_object()

        if sale.estado != "confirmed":
            return Response(
                {"error": "Solo se pueden cancelar ventas confirmadas"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            sale.cancel()
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(sale)
        return Response(serializer.data)


# ==========================
# SALE ITEM VIEWSET
# ==========================

class SaleItemViewSet(viewsets.ModelViewSet):

    queryset = SaleItem.objects.all()
    serializer_class = SaleItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    # 🔒 SOLO CREAR SI SALE ES DRAFT
    def perform_create(self, serializer):
        sale = serializer.validated_data["sale"]

        if sale.estado != "draft":
            raise ValidationError(
                "No se pueden agregar items a una venta confirmada"
            )

        serializer.save()

    # 🔒 BLOQUEAR UPDATE
    def update(self, request, *args, **kwargs):
        item = self.get_object()

        if item.sale.estado != "draft":
            raise ValidationError(
                "No se puede modificar items de una venta confirmada"
            )

        return super().update(request, *args, **kwargs)

    # 🔒 BLOQUEAR PATCH
    def partial_update(self, request, *args, **kwargs):
        item = self.get_object()

        if item.sale.estado != "draft":
            raise ValidationError(
                "No se puede modificar items de una venta confirmada"
            )

        return super().partial_update(request, *args, **kwargs)

    # 🔒 BLOQUEAR DELETE
    def destroy(self, request, *args, **kwargs):
        item = self.get_object()

        if item.sale.estado != "draft":
            raise ValidationError(
                "No se puede eliminar items de una venta confirmada"
            )

        return super().destroy(request, *args, **kwargs)