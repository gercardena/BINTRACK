from django.test import TestCase
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.accounts.models import UsuarioAsociado
from apps.clientes.models import Client
from apps.ventas.models import Sale
from .models import Factura, FacturaCambio
from .views import FacturaViewSet


class FacturaEdicionTests(TestCase):
    def setUp(self):
        user = get_user_model()
        self.titular = user.objects.create_user(username="titular")
        self.asociado = user.objects.create_user(username="asociado")
        self.otro = user.objects.create_user(username="otro")
        UsuarioAsociado.objects.create(titular=self.titular, usuario_asociado=self.asociado)
        self.cliente = Client.objects.create(usuario=self.titular, nombre="Cliente original", rut="11111111-1", direccion="Dirección original")
        self.sale = Sale.objects.create(usuario=self.titular, cliente=self.cliente, estado="paid", subtotal=100, iva=0, total=100)
        self.factura = Factura.objects.create(sale=self.sale, numero="F0001", cliente_nombre=self.cliente.nombre,
            cliente_rut=self.cliente.rut, cliente_direccion=self.cliente.direccion, subtotal=100, iva=0, total=100)

    def request(self, action="editar", user=None, data=None):
        factory = APIRequestFactory()
        method = "get" if action == "historial" else "post"
        request = getattr(factory, method)("/", data=data or {}, format="json")
        if user:
            force_authenticate(request, user=user)
        return FacturaViewSet.as_view({method: action})(request, pk=self.factura.pk)

    def test_asociado_edits_snapshot_and_actual_actor_is_audited(self):
        response = self.request(user=self.asociado, data={"version": 0, "cliente_nombre": "Nombre corregido",
            "cliente_direccion": "Otra dirección", "observaciones": "Entregado en bodega"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["version"], 1)
        self.factura.refresh_from_db()
        self.sale.refresh_from_db()
        self.cliente.refresh_from_db()
        self.assertEqual(self.factura.cliente_nombre, "Nombre corregido")
        self.assertEqual(self.cliente.nombre, "Cliente original")
        self.assertEqual(self.cliente.direccion, "Dirección original")
        self.assertEqual(self.sale.total, 100)
        self.assertEqual(self.sale.estado, "paid")
        self.assertEqual(self.factura.total, 100)
        self.assertEqual(self.factura.cliente_rut, "11111111-1")
        cambio = FacturaCambio.objects.get()
        self.assertEqual(cambio.usuario, self.asociado)
        self.assertEqual(cambio.usuario_nombre, "asociado")
        self.assertEqual(cambio.cambios["cliente_nombre"], {"antes": "Cliente original", "despues": "Nombre corregido"})
        history = self.request(action="historial", user=self.titular)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data[0]["usuario_nombre"], "asociado")

    def test_rejects_every_protected_or_unknown_field(self):
        for campo in ["total", "subtotal", "iva", "sale", "numero", "fecha_emision", "cliente_rut", "items", "usuario", "desconocido"]:
            with self.subTest(campo=campo):
                response = self.request(user=self.titular, data={"version": 0, campo: "alterado", "cliente_nombre": "No guardar"})
                self.assertEqual(response.status_code, 400)
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.version, 0)
        self.assertFalse(FacturaCambio.objects.exists())

    def test_unauthenticated_and_other_tenant_cannot_read_history_or_edit(self):
        for action in ["editar", "historial"]:
            self.assertEqual(self.request(action=action).status_code, 401)
            self.assertEqual(self.request(action=action, user=self.otro, data={"version": 0}).status_code, 404)
        UsuarioAsociado.objects.filter(usuario_asociado=self.asociado).update(activo=False)
        self.assertEqual(self.request(user=self.asociado, data={"version": 0}).status_code, 404)

    def test_validation_and_stale_version(self):
        for data in [{"version": 0, "cliente_nombre": "   "}, {"version": 0, "observaciones": "x" * 2001},
                     {"version": 0, "cliente_direccion": "x" * 256}, {"cliente_nombre": "Nombre"}]:
            self.assertEqual(self.request(user=self.titular, data=data).status_code, 400)
        self.assertEqual(self.request(user=self.titular, data={"version": 0, "observaciones": "Primera"}).status_code, 200)
        self.assertEqual(self.request(user=self.asociado, data={"version": 0, "observaciones": "Segunda"}).status_code, 409)
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.observaciones, "Primera")
        self.assertEqual(FacturaCambio.objects.count(), 1)

    def test_noop_and_clear_optional_fields(self):
        self.request(user=self.titular, data={"version": 0, "cliente_nombre": self.cliente.nombre})
        self.assertFalse(FacturaCambio.objects.exists())
        response = self.request(user=self.titular, data={"version": 0, "cliente_direccion": "", "observaciones": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["cliente_direccion"], "")

    def test_audit_failure_rolls_back_edit(self):
        with patch("apps.facturas.views.FacturaCambio.objects.create", side_effect=RuntimeError("audit failure")):
            with self.assertRaises(RuntimeError):
                self.request(user=self.titular, data={"version": 0, "observaciones": "No guardar"})
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.version, 0)
        self.assertEqual(self.factura.observaciones, "")
