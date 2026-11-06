from datetime import date, datetime, time
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import User
from apps.clientes.models import Client
from apps.pagos.models import Pago

from .models import Sale
from .views import SaleViewSet


class SalesReportTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="report_owner")
        self.client = Client.objects.create(
            usuario=self.owner,
            nombre="Cliente de reporte",
            rut="11111111-1",
        )
        self.factory = APIRequestFactory()

    def sale(self, *, total, estado, on):
        sale = Sale.objects.create(
            usuario=self.owner,
            cliente=self.client,
            estado=estado,
            subtotal=Decimal(total),
            total=Decimal(total),
        )
        created_at = timezone.make_aware(
            datetime.combine(on, time(hour=12)),
        )
        Sale.objects.filter(pk=sale.pk).update(fecha_creacion=created_at)
        sale.refresh_from_db()
        return sale

    def report(self, params):
        request = self.factory.get("/api/ventas/sales/reporte/", params)
        force_authenticate(request, user=self.owner)
        return SaleViewSet.as_view({"get": "reporte"})(request)

    def test_custom_range_reports_paid_partial_and_pending_balances(self):
        paid = self.sale(total="50000.00", estado="paid", on=date(2026, 11, 1))
        partial = self.sale(total="70000.00", estado="partial", on=date(2026, 11, 2))
        pending = self.sale(total="30000.00", estado="confirmed", on=date(2026, 11, 3))
        outside = self.sale(total="90000.00", estado="paid", on=date(2026, 10, 31))
        Pago.objects.create(sale=paid, monto=Decimal("50000.00"), metodo="efectivo")
        Pago.objects.create(sale=partial, monto=Decimal("20000.00"), metodo="transferencia")
        Pago.objects.create(sale=outside, monto=Decimal("90000.00"), metodo="efectivo")

        response = self.report({"desde": "2026-11-01", "hasta": "2026-11-03"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["periodo"], "personalizado")
        self.assertEqual(response.data["total_vendido"], Decimal("150000.00"))
        self.assertEqual(response.data["total_abonado"], Decimal("70000.00"))
        self.assertEqual(response.data["total_pendiente"], Decimal("80000.00"))
        self.assertEqual(response.data["cantidad_ventas_pagadas"], 1)
        self.assertEqual(response.data["cantidad_ventas_pendientes"], 2)
        self.assertEqual(response.data["ventas"][1]["tipo_reporte"], "abonada")

    def test_custom_range_rejects_incomplete_or_reversed_dates(self):
        incomplete = self.report({"desde": "2026-11-01"})
        reversed_dates = self.report({"desde": "2026-11-03", "hasta": "2026-11-01"})

        self.assertEqual(incomplete.status_code, 400)
        self.assertEqual(reversed_dates.status_code, 400)
