from datetime import date, timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.services.users import get_usuario_titular

from .models import Sale, SaleItem
from .serializers import SaleSerializer, SaleItemSerializer


# ==========================
# SALE VIEWSET
# ==========================

class SaleViewSet(viewsets.ModelViewSet):

    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        titular = get_usuario_titular(
            self.request.user,
        )

        return Sale.objects.filter(
            usuario=titular,
        ).select_related(
            "cliente",
        ).prefetch_related(
            "items__product",
            "items__bin",
        )

    def perform_create(self, serializer):

        titular = get_usuario_titular(
            self.request.user,
        )

        serializer.save(
            usuario=titular,
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
                    "error": str(e),
                },
                status=400,
            )

        return Response(
            self.get_serializer(sale).data,
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
                    "error": str(e),
                },
                status=400,
            )

        return Response(
            self.get_serializer(sale).data,
        )

    # ==========================
    # DASHBOARD
    # ==========================

    @action(detail=False, methods=["get"])
    def dashboard(self, request):

        titular = get_usuario_titular(
            request.user,
        )

        hoy = timezone.localdate()

        inicio_mes = hoy.replace(day=1)

        ventas = Sale.objects.filter(
            usuario=titular,
        )

        ventas_hoy = ventas.filter(
            fecha_creacion__date=hoy,
            estado="paid",
        )

        ventas_mes = ventas.filter(
            fecha_creacion__date__gte=inicio_mes,
            estado="paid",
        )

        data = {

            "ventas_hoy": ventas_hoy.count(),

            "ingresos_hoy":
                ventas_hoy.aggregate(
                    total=Sum("total"),
                )["total"] or 0,

            "ventas_mes": ventas_mes.count(),

            "ingresos_mes":
                ventas_mes.aggregate(
                    total=Sum("total"),
                )["total"] or 0,

            "ventas_confirmadas":
                ventas.filter(
                    estado="confirmed",
                ).count(),

            "ventas_pagadas":
                ventas.filter(
                    estado="paid",
                ).count(),

            "ventas_draft":
                ventas.filter(
                    estado="draft",
                ).count(),

            "ventas_canceladas":
                ventas.filter(
                    estado="cancelled",
                ).count(),
        }

        return Response(data)

    # ==========================
    # REPORTE DE VENTAS
    # ==========================

    @action(detail=False, methods=["get"])
    def reporte(self, request):

        titular = get_usuario_titular(
            request.user,
        )

        periodo = request.query_params.get(
            "periodo",
            "semana",
        )

        hoy = timezone.localdate()

        desde_param = request.query_params.get("desde")
        hasta_param = request.query_params.get("hasta")

        if desde_param and hasta_param:
            try:
                desde = date.fromisoformat(desde_param)
                hasta = date.fromisoformat(hasta_param)
                periodo = "personalizado"
            except ValueError:
                raise ValidationError(
                    "Las fechas deben usar formato YYYY-MM-DD."
                )

        elif periodo == "hoy":
            desde = hoy
            hasta = hoy

        elif periodo == "mes":
            desde = hoy.replace(day=1)
            hasta = hoy

        else:
            periodo = "semana"
            desde = hoy - timedelta(
                days=hoy.weekday(),
            )
            hasta = hoy

        ventas = (
            Sale.objects
            .filter(
                usuario=titular,
                estado__in=[
                    "confirmed",
                    "paid",
                ],
                fecha_creacion__date__gte=desde,
                fecha_creacion__date__lte=hasta,
            )
            .select_related(
                "cliente",
            )
            .prefetch_related(
                "items__product",
                "items__bin",
            )
            .order_by(
                "-fecha_creacion",
            )
        )

        ventas_contado = ventas.filter(
            estado="paid",
        )

        ventas_credito = ventas.filter(
            estado="confirmed",
        )

        total_contado = (
            ventas_contado.aggregate(
                total=Sum("total"),
            )["total"] or 0
        )

        total_credito = (
            ventas_credito.aggregate(
                total=Sum("total"),
            )["total"] or 0
        )

        total_vendido = total_contado + total_credito

        clientes_pagados = (
            ventas_contado
            .values("cliente_id")
            .distinct()
            .count()
        )

        clientes_credito = (
            ventas_credito
            .values("cliente_id")
            .distinct()
            .count()
        )

        ventas_data = []

        for sale in ventas:

            items = []

            for item in sale.items.all():
                items.append({
                    "product_nombre": item.product.nombre,
                    "bin_nombre": item.bin.nombre,
                    "cantidad": item.cantidad,
                    "bins_cantidad": item.bins_cantidad,
                    "tipo_cobro": item.tipo_cobro_snapshot,
                    "kilos_pesados": item.kilos_pesados,
                    "precio_unitario": item.precio_unitario,
                    "subtotal": item.subtotal,
                })

            tipo_reporte = (
                "contado"
                if sale.estado == "paid"
                else "credito"
            )

            ventas_data.append({
                "id": sale.id,
                "numero": sale.numero,
                "fecha": sale.fecha_creacion,
                "cliente_id": sale.cliente_id,
                "cliente_nombre": sale.cliente.nombre,
                "estado": sale.estado,
                "tipo_reporte": tipo_reporte,
                "total": sale.total,
                "items": items,
            })

        data = {
            "periodo": periodo,
            "desde": desde,
            "hasta": hasta,

            "total_vendido": total_vendido,
            "total_contado": total_contado,
            "total_credito": total_credito,

            "cantidad_ventas": ventas.count(),
            "cantidad_ventas_contado": ventas_contado.count(),
            "cantidad_ventas_credito": ventas_credito.count(),

            "cantidad_clientes_pagados": clientes_pagados,
            "cantidad_clientes_credito": clientes_credito,

            "ventas": ventas_data,
        }

        return Response(data)


# ==========================
# SALE ITEM VIEWSET
# ==========================

class SaleItemViewSet(viewsets.ModelViewSet):

    serializer_class = SaleItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        titular = get_usuario_titular(
            self.request.user,
        )

        return SaleItem.objects.filter(
            sale__usuario=titular,
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