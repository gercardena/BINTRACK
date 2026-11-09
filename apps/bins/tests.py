from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import User
from apps.clientes.models import Client

from .models import BinMovement, BinType
from .serializers import BinMovementSerializer
from .views import BinBalanceView


class BinBalanceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="bins_owner")
        self.other_owner = User.objects.create_user(username="other_owner")
        self.client = Client.objects.create(
            usuario=self.owner,
            nombre="Cliente con préstamo",
            rut="11111111-1",
        )
        self.other_client = Client.objects.create(
            usuario=self.owner,
            nombre="Cliente al día",
            rut="22222222-2",
        )
        self.bin_type = BinType.objects.create(
            usuario=self.owner,
            nombre="Bin gris",
            material="Plástico",
            valor_deposito=Decimal("2500.00"),
        )
        self.factory = APIRequestFactory()

    def balance(self, params=None):
        request = self.factory.get("/api/bins/balance/", params or {})
        force_authenticate(request, user=self.owner)
        return BinBalanceView.as_view()(request)

    def test_reports_current_bins_and_associated_deposit(self):
        BinMovement.objects.create(
            usuario=self.owner,
            cliente=self.client,
            bin_type=self.bin_type,
            tipo_movimiento="prestamo",
            cantidad=8,
        )
        BinMovement.objects.create(
            usuario=self.owner,
            cliente=self.client,
            bin_type=self.bin_type,
            tipo_movimiento="devolucion",
            cantidad=3,
        )
        BinMovement.objects.create(
            usuario=self.owner,
            cliente=self.other_client,
            bin_type=self.bin_type,
            tipo_movimiento="prestamo",
            cantidad=2,
        )
        BinMovement.objects.create(
            usuario=self.owner,
            cliente=self.other_client,
            bin_type=self.bin_type,
            tipo_movimiento="devolucion",
            cantidad=2,
        )

        response = self.balance({"solo_pendientes": "true"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["cliente_nombre"], "Cliente con préstamo")
        self.assertEqual(response.data[0]["saldo"], 5)
        self.assertEqual(response.data[0]["deposito_pendiente"], "12500.00")
        self.assertEqual(response.data[0]["deposito_retenido"], "0.00")

    def test_rejects_invalid_filter_identifier(self):
        response = self.balance({"cliente": "no-es-un-id"})

        self.assertEqual(response.status_code, 400)

    def test_tracks_received_and_returned_deposit_separately(self):
        BinMovement.objects.create(
            usuario=self.owner,
            cliente=self.client,
            bin_type=self.bin_type,
            tipo_movimiento="prestamo",
            cantidad=4,
            deposito_pagado=Decimal("10000.00"),
            garantia_confirmada=True,
        )
        BinMovement.objects.create(
            usuario=self.owner,
            cliente=self.client,
            bin_type=self.bin_type,
            tipo_movimiento="devolucion",
            cantidad=2,
            deposito_devuelto=Decimal("5000.00"),
        )

        response = self.balance()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["saldo"], 2)
        self.assertEqual(response.data[0]["deposito_recibido"], "10000.00")
        self.assertEqual(response.data[0]["deposito_devuelto"], "5000.00")
        self.assertEqual(response.data[0]["deposito_retenido"], "5000.00")

    def test_rejects_return_larger_than_pending_loan(self):
        BinMovement.objects.create(
            usuario=self.owner,
            cliente=self.client,
            bin_type=self.bin_type,
            tipo_movimiento="prestamo",
            cantidad=2,
        )
        request = self.factory.post("/api/bins/movements/")
        request.user = self.owner
        serializer = BinMovementSerializer(
            data={
                "cliente": self.client.id,
                "bin_type": self.bin_type.id,
                "tipo_movimiento": "devolucion",
                "cantidad": 3,
                "deposito_pagado": "0",
                "deposito_devuelto": "0",
            },
            context={"request": request},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("cantidad", serializer.errors)
