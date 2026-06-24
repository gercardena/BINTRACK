from rest_framework import viewsets, permissions
from django.utils import timezone
from django.db.models import Sum
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

        return Sale.objects.filter(
            usuario=self.request.user
        ).select_related(
            "cliente"
        ).prefetch_related(
            "items__product"
        )

    def perform_create(self, serializer):

        serializer.save(
            usuario=self.request.user
        )

    # ==========================
    # BLOQUEAR UPDATE
    # ==========================

    def update(self, request, *args, **kwargs):

        sale = self.get_object()

        if sale.estado != "draft":
            raise ValidationError(
                "No se puede modificar una venta no draft"
            )

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):

        sale = self.get_object()

        if sale.estado != "draft":
            raise ValidationError(
                "No se puede modificar una venta no draft"
            )

        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):

        sale = self.get_object()

        if sale.estado != "draft":
            raise ValidationError(
                "No se puede eliminar una venta no draft"
            )

        return super().destroy(request, *args, **kwargs)

    # ==========================
    # CONFIRM
    # ==========================

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def confirm(self, request, pk=None):

        sale = self.get_object()

        try:

            sale.confirm()

        except Exception as e:

            print("===================================")
            print("CONFIRM ERROR:")
            print(str(e))
            print("===================================")

            return Response(
                {
                    "error": str(e)
                },
                status=400
            )

        return Response(
            self.get_serializer(sale).data
        )

    # ==========================
    # PAY
    # ==========================

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):

        return Response(
            {
                "error": (
                    "El pago debe registrarse mediante "
                    "el endpoint /api/pagos/."
                )
            },
            status=400,
        )

    # ==========================
    # CANCEL
    # ==========================

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def cancel(self, request, pk=None):

        sale = self.get_object()

        try:

            sale.cancel()

        except Exception as e:

            return Response(
                {
                    "error": str(e)
                },
                status=400
            )

        return Response(
            self.get_serializer(sale).data
        )

    # ==========================
    # DASHBOARD
    # ==========================

    @action(detail=False, methods=["get"])
    def dashboard(self, request):

        user = request.user

        hoy = timezone.now().date()

        inicio_mes = hoy.replace(day=1)

        ventas = Sale.objects.filter(
            usuario=user
        )

        ventas_hoy = ventas.filter(
            fecha_creacion__date=hoy,
            estado="paid"
        )

        ventas_mes = ventas.filter(
            fecha_creacion__date__gte=inicio_mes,
            estado="paid"
        )

        data = {

            "ventas_hoy": ventas_hoy.count(),

            "ingresos_hoy":
                ventas_hoy.aggregate(
                    total=Sum("total")
                )["total"] or 0,

            "ventas_mes": ventas_mes.count(),

            "ingresos_mes":
                ventas_mes.aggregate(
                    total=Sum("total")
                )["total"] or 0,

            "ventas_confirmadas":
                ventas.filter(
                    estado="confirmed"
                ).count(),

            "ventas_pagadas":
                ventas.filter(
                    estado="paid"
                ).count(),

            "ventas_draft":
                ventas.filter(
                    estado="draft"
                ).count(),

            "ventas_canceladas":
                ventas.filter(
                    estado="cancelled"
                ).count(),
        }

        return Response(data)


# ==========================
# SALE ITEM VIEWSET
# ==========================

class SaleItemViewSet(viewsets.ModelViewSet):

    serializer_class = SaleItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        return SaleItem.objects.filter(
            sale__usuario=self.request.user
        ).select_related(
            "sale",
            "product",
            "bin",
        )

    # ==========================
    # CREAR ITEM
    # ==========================

    def perform_create(self, serializer):

        sale = serializer.validated_data["sale"]

        if sale.estado != "draft":

            raise ValidationError(
                "No se pueden agregar items a venta no draft"
            )

        serializer.save()

    # ==========================
    # UPDATE ITEM
    # ==========================

    def update(self, request, *args, **kwargs):

        item = self.get_object()

        if item.sale.estado != "draft":

            raise ValidationError(
                "No se puede modificar items"
            )

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):

        item = self.get_object()

        if item.sale.estado != "draft":

            raise ValidationError(
                "No se puede modificar items"
            )

        return super().partial_update(request, *args, **kwargs)

    # ==========================
    # DELETE ITEM
    # ==========================

    def destroy(self, request, *args, **kwargs):

        item = self.get_object()

        if item.sale.estado != "draft":

            raise ValidationError(
                "No se puede eliminar items"
            )

        return super().destroy(request, *args, **kwargs)