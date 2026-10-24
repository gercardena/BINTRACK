from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import SubscriptionPlan, UserSubscription, UsuarioAsociado
from .services.account_management import create_secondary

User = get_user_model()


class AccountManagementTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="principal", email="principal@example.test")
        self.other = User.objects.create_user(username="otra_cuenta")
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.plan = SubscriptionPlan.objects.create(nombre="Plan anterior", precio=20000)
        self.subscription = UserSubscription.objects.create(
            usuario=self.owner, plan=self.plan, fecha_fin=timezone.now() + timedelta(days=10),
        )
        self.end = self.subscription.fecha_fin

    def payload(self, suffix="1"):
        return {"username": f"operador{suffix}", "email": f"operador{suffix}@example.test",
                "first_name": "Operador", "password": "Local-Only-Test!9458"}

    def create(self, suffix="1"):
        return self.client.post("/api/accounts/cuenta/", self.payload(suffix), format="json")

    def summary(self):
        return self.client.get("/api/accounts/cuenta/")

    def change(self, pk, data):
        return self.client.put(f"/api/accounts/cuenta/usuarios/{pk}/", data, format="json")

    def test_seeded_catalog_prices_and_existing_subscription_unchanged(self):
        data = self.summary().data
        self.assertEqual([p["precio_final_clp"] for p in data["planes"]], [50000, 60000, 70000])
        self.assertEqual(data["plan_segun_usuarios"]["precio_final_clp"], 50000)
        self.assertFalse(data["cobro_habilitado"])
        self.assertFalse(data["prorrateo"])
        self.assertEqual(data["adicional_alta_clp"], 10000)
        self.assertEqual(data["periodicidad"], "mensual")
        self.subscription.refresh_from_db()
        self.plan.refresh_from_db()
        self.assertEqual(self.subscription.plan_id, self.plan.pk)
        self.assertEqual(self.subscription.fecha_fin, self.end)
        self.assertEqual(self.plan.precio, 20000)

    def test_create_two_only_hash_password_and_do_not_activate_subscription(self):
        for suffix, price in [("1", 60000), ("2", 70000)]:
            result = self.create(suffix)
            self.assertEqual(result.status_code, 201, result.data)
            self.assertNotIn("password", result.data)
            user = User.objects.get(pk=result.data["user_id"])
            self.assertTrue(user.check_password(self.payload()["password"]))
            self.assertFalse(user.is_staff)
            self.assertFalse(user.is_superuser)
            self.assertFalse(user.suscripcion_activa)
            self.assertEqual(self.summary().data["plan_segun_usuarios"]["precio_final_clp"], price)
        self.assertEqual(self.create("3").status_code, 400)
        self.assertFalse(User.objects.filter(username="operador3").exists())
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.fecha_fin, self.end)
        self.assertEqual(UserSubscription.objects.count(), 1)

    def test_no_anonymous_access(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.summary().status_code, 401)
        self.assertEqual(self.create().status_code, 401)

    def test_secondary_cannot_manage_even_with_legacy_admin_role(self):
        result = self.create()
        relation = UsuarioAsociado.objects.get(pk=result.data["id"])
        relation.rol = "admin"
        relation.save()
        self.client.force_authenticate(relation.usuario_asociado)
        self.assertEqual(self.summary().status_code, 403)
        self.assertEqual(self.create("2").status_code, 403)
        self.assertEqual(self.change(relation.pk, {"activo": False}).status_code, 403)
        with patch("apps.payments.views.MercadoPagoService") as provider:
            self.assertEqual(self.client.post("/api/payments/crear/").status_code, 403)
            provider.assert_not_called()

    def test_profile_owner_flag_and_shared_operational_data(self):
        from apps.clientes.models import Client
        Client.objects.create(usuario=self.owner, nombre="Cliente del negocio", rut="11111111-1")
        self.assertTrue(self.client.get("/api/accounts/user/profile/").data["puede_gestionar_cuenta"])
        result = self.create()
        secondary = User.objects.get(pk=result.data["user_id"])
        self.client.force_authenticate(secondary)
        profile = self.client.get("/api/accounts/user/profile/").data
        self.assertFalse(profile["puede_gestionar_cuenta"])
        self.assertTrue(profile["es_usuario_asociado"])
        self.assertEqual(profile["titular_id"], self.owner.pk)
        response = self.client.get("/api/clientes/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["nombre"], "Cliente del negocio")

    def test_owner_cannot_edit_another_account_or_self(self):
        result = self.create()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.summary().data["usuarios"], [])
        self.assertEqual(self.change(result.data["id"], {"activo": False}).status_code, 404)
        self.assertEqual(self.change(999999, {"activo": False}).status_code, 404)

    def test_no_privilege_or_identity_injection(self):
        for field in ["rol", "titular", "user_id", "is_staff", "is_superuser", "suscripcion_activa", "precio"]:
            with self.subTest(field=field):
                response = self.client.post("/api/accounts/cuenta/", {**self.payload(), field: True}, format="json")
                self.assertEqual(response.status_code, 400)
        created = self.create()
        for field in ["username", "password", "rol", "titular", "is_staff", "is_superuser", "is_active"]:
            self.assertEqual(self.change(created.data["id"], {field: True}).status_code, 400)

    def test_validation_duplicates_and_no_existing_user_link(self):
        overrides = [
            {"password": "123"}, {"password": " Local-Only-Test!9458 "},
            {"username": "principal"}, {"email": "PRINCIPAL@example.test"}, {"email": "invalid"},
        ]
        for override in overrides:
            with self.subTest(override=override):
                response = self.client.post("/api/accounts/cuenta/", {**self.payload(), **override}, format="json")
                self.assertEqual(response.status_code, 400)
        self.assertFalse(UsuarioAsociado.objects.exists())

    def test_deactivate_preserves_identity_and_immediately_blocks_existing_token(self):
        created = self.create()
        secondary = User.objects.get(pk=created.data["user_id"])
        token = str(RefreshToken.for_user(secondary).access_token)
        self.assertEqual(self.change(created.data["id"], {"activo": False}).status_code, 200)
        self.assertTrue(User.objects.filter(pk=secondary.pk).exists())
        self.assertTrue(UsuarioAsociado.objects.filter(pk=created.data["id"]).exists())
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(client.get("/api/clientes/").status_code, 401)
        self.assertEqual(self.summary().data["secundarios_activos"], 0)

    def test_inactive_legacy_relation_does_not_turn_into_owner(self):
        created = self.create()
        relation = UsuarioAsociado.objects.get(pk=created.data["id"])
        relation.activo = False
        relation.save()
        self.client.force_authenticate(relation.usuario_asociado)
        self.assertEqual(self.summary().status_code, 403)
        self.assertEqual(self.client.get("/api/clientes/").status_code, 403)

    def test_reactivation_capacity_noop_and_contact_edits(self):
        first = self.create().data
        self.assertEqual(self.change(first["id"], {"activo": False}).status_code, 200)
        self.create("2")
        self.create("3")
        self.assertEqual(self.change(first["id"], {"activo": True}).status_code, 400)
        self.assertEqual(self.change(first["id"], {"first_name": "Nuevo nombre"}).status_code, 200)
        self.assertEqual(self.change(first["id"], {"email": self.owner.email}).status_code, 400)
        active = UsuarioAsociado.objects.filter(titular=self.owner, activo=True).first()
        self.assertEqual(self.change(active.pk, {"activo": True}).status_code, 200)
        self.change(active.pk, {"activo": False})
        self.assertEqual(self.change(first["id"], {"activo": True}).status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.fecha_fin, self.end)

    def test_creation_rolls_back_if_relation_fails(self):
        with patch("apps.accounts.services.account_management.UsuarioAsociado.objects.create", side_effect=RuntimeError("failed")):
            with self.assertRaises(RuntimeError):
                self.create()
        self.assertFalse(User.objects.filter(username="operador1").exists())
        self.assertFalse(UsuarioAsociado.objects.exists())

    def test_legacy_over_capacity_is_reported_without_deleting_users(self):
        for index in range(3):
            user = User.objects.create_user(username=f"legacy{index}")
            UsuarioAsociado.objects.create(titular=self.owner, usuario_asociado=user)
        summary = self.summary().data
        self.assertEqual(summary["secundarios_activos"], 3)
        self.assertTrue(summary["requiere_revision"])
        self.assertFalse(summary["puede_agregar"])
        self.assertIsNone(summary["plan_segun_usuarios"])
        self.assertEqual(self.create().status_code, 400)
        self.assertEqual(UsuarioAsociado.objects.filter(titular=self.owner).count(), 3)

    def test_account_without_subscription_and_delete_not_exposed(self):
        self.client.force_authenticate(self.other)
        summary = self.summary().data
        self.assertIsNone(summary["fecha_fin"])
        self.assertFalse(summary["suscripcion_vigente"])
        result = self.create()
        self.assertEqual(result.status_code, 201)
        response = self.client.delete(f'/api/accounts/cuenta/usuarios/{result.data["id"]}/')
        self.assertEqual(response.status_code, 405)
        self.assertTrue(UsuarioAsociado.objects.filter(pk=result.data["id"]).exists())
        self.assertFalse(UserSubscription.objects.filter(usuario=self.other).exists())


class AccountCapacityConcurrencyTests(TransactionTestCase):
    def test_simultaneous_creations_cannot_exceed_two_active_secondaries(self):
        if connection.vendor != "postgresql":
            self.skipTest("Real row-lock concurrency requires PostgreSQL")
        owner = User.objects.create_user(username="concurrent_owner")
        first = User.objects.create_user(username="existing_secondary")
        UsuarioAsociado.objects.create(titular=owner, usuario_asociado=first)
        barrier = Barrier(2, timeout=20)

        def attempt(index):
            close_old_connections()
            try:
                local_owner = User.objects.get(pk=owner.pk)
                # Bound waits so a locking regression fails instead of hanging tests.
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '15s'")
                barrier.wait()
                try:
                    create_secondary(local_owner, {
                        "username": f"concurrent{index}",
                        "email": f"concurrent{index}@example.test",
                        "password": "Local-Only-Test!9458",
                    })
                    return "created"
                except ValidationError:
                    return "full"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, [1, 2]))
        self.assertCountEqual(results, ["created", "full"])
        self.assertEqual(UsuarioAsociado.objects.filter(
            titular=owner, activo=True, usuario_asociado__is_active=True,
        ).count(), 2)
        self.assertEqual(User.objects.filter(username__in=["concurrent1", "concurrent2"]).count(), 1)
