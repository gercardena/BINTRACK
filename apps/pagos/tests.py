from decimal import Decimal

from django.test import RequestFactory, TestCase

from apps.accounts.models import User
from apps.clientes.models import Client
from apps.ventas.models import Sale

from .models import Pago
from .serializers import PagoSerializer


class PartialPaymentTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner_abonos")
        self.client = Client.objects.create(
            usuario=self.owner,
            nombre="Cliente de prueba",
            rut="11111111-1",
        )
        self.sale = Sale.objects.create(
            usuario=self.owner,
            cliente=self.client,
            estado="confirmed",
            subtotal=Decimal("50000.00"),
            total=Decimal("50000.00"),
        )
        self.request = RequestFactory().post("/api/pagos/")
        self.request.user = self.owner

    def registrar_abono(self, monto):
        serializer = PagoSerializer(
            data={
                "sale": self.sale.pk,
                "monto": monto,
                "metodo": "efectivo",
            },
            context={"request": self.request},
        )
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    def test_two_partial_payments_close_the_sale(self):
        self.registrar_abono("20000.00")
        self.sale.refresh_from_db()

        self.assertEqual(self.sale.estado, "partial")
        self.assertEqual(self.sale.total_pagado, Decimal("20000.00"))
        self.assertEqual(self.sale.saldo_pendiente, Decimal("30000.00"))

        self.registrar_abono("30000.00")
        self.sale.refresh_from_db()

        self.assertEqual(self.sale.estado, "paid")
        self.assertEqual(self.sale.total_pagado, Decimal("50000.00"))
        self.assertEqual(self.sale.saldo_pendiente, Decimal("0.00"))
        self.assertEqual(Pago.objects.filter(sale=self.sale).count(), 2)

    def test_payment_cannot_exceed_pending_balance(self):
        self.registrar_abono("20000.00")

        serializer = PagoSerializer(
            data={
                "sale": self.sale.pk,
                "monto": "30000.01",
                "metodo": "transferencia",
            },
            context={"request": self.request},
        )

        self.assertTrue(serializer.is_valid())
        with self.assertRaisesMessage(
            Exception,
            "El abono no puede superar el saldo pendiente.",
        ):
            serializer.save()

        self.assertEqual(Pago.objects.filter(sale=self.sale).count(), 1)

    def test_legacy_client_without_amount_pays_remaining_balance(self):
        serializer = PagoSerializer(
            data={
                "sale": self.sale.pk,
                "metodo": "tarjeta",
            },
            context={"request": self.request},
        )

        serializer.is_valid(raise_exception=True)
        pago = serializer.save()
        self.sale.refresh_from_db()

        self.assertEqual(pago.monto, Decimal("50000.00"))
        self.assertEqual(self.sale.estado, "paid")
