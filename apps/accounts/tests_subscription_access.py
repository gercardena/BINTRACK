from datetime import datetime, timedelta, timezone as dt_timezone
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import URLResolver, get_resolver
from django.utils import timezone
from rest_framework.test import APIClient

from .models import SubscriptionPlan, UserSubscription, UsuarioAsociado
from .permissions.subscription import HasActiveSubscription
from .services.monthly_periods import next_month, renew_monthly_period
from .services.subscription_access import subscription_access

User = get_user_model()
UTC = dt_timezone.utc
CL = ZoneInfo("America/Santiago")


class AccessClockTests(SimpleTestCase):
    def setUp(self):
        self.end = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)
        self.subscription = SimpleNamespace(
            activa=True, fecha_inicio=self.end - timedelta(days=30), fecha_fin=self.end,
        )

    def test_exact_expiry_and_grace_boundaries(self):
        for offset, state, writable in [
            (-1, "activa", True), (0, "en_gracia", True),
            (72 * 3600 - 1, "en_gracia", True), (72 * 3600, "vencida", False),
        ]:
            with self.subTest(offset=offset):
                access = subscription_access(self.subscription, at=self.end + timedelta(seconds=offset))
                self.assertEqual(access["estado"], state)
                self.assertEqual(access["puede_operar"], writable)
                self.assertEqual(access["solo_lectura"], not writable)

    def test_missing_inactive_and_future_subscription_are_read_only(self):
        self.assertEqual(subscription_access(None)["estado"], "sin_suscripcion")
        self.assertFalse(subscription_access(None)["puede_operar"])
        self.subscription.activa = False
        self.assertEqual(subscription_access(self.subscription, at=self.end)["estado"], "inactiva")
        self.subscription.activa = True
        access = subscription_access(self.subscription, at=self.subscription.fecha_inicio - timedelta(seconds=1))
        self.assertEqual(access["estado"], "pendiente")
        self.assertFalse(access["puede_operar"])

    def test_grace_is_72_hours_across_chilean_dst(self):
        self.subscription.fecha_fin = datetime(2026, 9, 5, 12, tzinfo=CL)
        self.subscription.fecha_inicio = self.subscription.fecha_fin - timedelta(days=30)
        end = self.subscription.fecha_fin.astimezone(UTC)
        self.assertEqual(subscription_access(self.subscription, at=end + timedelta(hours=71))["estado"], "en_gracia")
        access = subscription_access(self.subscription, at=end + timedelta(hours=72))
        self.assertEqual(access["estado"], "vencida")
        self.assertEqual(datetime.fromisoformat(access["gracia_hasta"]) - end, timedelta(hours=72))

    def test_calendar_months_keep_anchor_through_february(self):
        jan = datetime(2027, 1, 31, 15, 21, tzinfo=CL)
        feb = next_month(jan, 31)
        mar = next_month(feb, 31)
        self.assertEqual((feb.month, feb.day, feb.hour, feb.minute), (2, 28, 15, 21))
        self.assertEqual((mar.month, mar.day), (3, 31))
        self.assertEqual(next_month(datetime(2028, 1, 31, 12, tzinfo=CL), 31).day, 29)
        self.assertEqual(next_month(datetime(2026, 12, 31, 12, tzinfo=CL), 31).year, 2027)

    def test_calendar_month_keeps_local_hour_and_normalizes_nonexistent_hour(self):
        end = next_month(datetime(2026, 8, 15, 12, tzinfo=CL), 15)
        self.assertEqual((end.month, end.day, end.hour), (9, 15, 12))
        midnight = next_month(datetime(2026, 8, 6, 0, 30, tzinfo=CL), 6)
        self.assertEqual(midnight, midnight.astimezone(UTC).astimezone(CL))
        self.assertEqual((midnight.month, midnight.day, midnight.hour), (9, 6, 1))
        with self.assertRaises(ValueError):
            next_month(end, 0)


class SubscriptionRenewalTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="monthly_owner")
        self.now = datetime(2026, 10, 24, 12, tzinfo=CL)
        self.plan = SubscriptionPlan.objects.get(codigo="bintrack_mensual_0")

    def test_first_period_uses_calendar_month_and_active_secondary_tier(self):
        secondary = User.objects.create_user(username="monthly_secondary")
        UsuarioAsociado.objects.create(titular=self.owner, usuario_asociado=secondary)
        subscription = renew_monthly_period(self.owner, at=self.now)
        self.assertEqual(subscription.plan.precio, 60000)
        self.assertEqual(subscription.fecha_inicio, self.now)
        self.assertEqual(subscription.fecha_fin, next_month(self.now, 24))
        self.assertEqual(subscription.dia_facturacion, 24)
        self.assertEqual(UserSubscription.objects.count(), 1)

    def test_early_grace_and_late_renewal_keep_recorded_due_date(self):
        for days_after_due in (-2, 2, 10, 70):
            with self.subTest(days_after_due=days_after_due):
                UserSubscription.objects.filter(usuario=self.owner).delete()
                due = self.now - timedelta(days=days_after_due)
                subscription = UserSubscription.objects.create(
                    usuario=self.owner, plan=self.plan, fecha_inicio=due - timedelta(days=30), fecha_fin=due,
                )
                previous_start = subscription.fecha_inicio
                renewed = renew_monthly_period(self.owner, at=self.now)
                self.assertEqual(renewed.pk, subscription.pk)
                self.assertEqual(renewed.fecha_inicio, previous_start)
                self.assertEqual(renewed.fecha_fin, next_month(due, due.day))
                self.assertEqual(UserSubscription.objects.filter(usuario=self.owner).count(), 1)
                if days_after_due == 70:
                    self.assertFalse(subscription_access(renewed, at=self.now)["puede_operar"])

    def test_renewal_preserves_31st_anchor_and_does_not_create_secondary_subscription(self):
        jan = datetime(2027, 1, 31, 12, tzinfo=CL)
        first = renew_monthly_period(self.owner, at=jan)
        self.assertEqual(first.fecha_fin.day, 28)
        second = renew_monthly_period(self.owner, at=datetime(2027, 2, 28, 13, tzinfo=CL))
        self.assertEqual(second.fecha_fin.day, 31)
        secondary = User.objects.create_user(username="secondary_only")
        UsuarioAsociado.objects.create(titular=self.owner, usuario_asociado=secondary)
        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            renew_monthly_period(secondary, at=jan)
        self.assertFalse(UserSubscription.objects.filter(usuario=secondary).exists())


class SubscriptionBusinessAccessTests(TestCase):
    write_routes = [
        ("post", "/api/clientes/"), ("patch", "/api/clientes/999999/"), ("delete", "/api/clientes/999999/"),
        ("post", "/api/bins/types/"), ("put", "/api/bins/types/999999/"), ("delete", "/api/bins/types/999999/"),
        ("post", "/api/bins/clientes/"), ("patch", "/api/bins/clientes/999999/"), ("delete", "/api/bins/clientes/999999/"),
        ("post", "/api/bins/movements/"),
        ("post", "/api/productos/"), ("patch", "/api/productos/999999/"), ("delete", "/api/productos/999999/"),
        ("post", "/api/productos/presentations/"), ("patch", "/api/productos/presentations/999999/"),
        ("delete", "/api/productos/presentations/999999/"),
        ("post", "/api/inventario/stock/"), ("patch", "/api/inventario/stock/999999/"), ("delete", "/api/inventario/stock/999999/"),
        ("post", "/api/ventas/sales/"), ("put", "/api/ventas/sales/999999/"), ("delete", "/api/ventas/sales/999999/"),
        ("post", "/api/ventas/items/"), ("patch", "/api/ventas/items/999999/"), ("delete", "/api/ventas/items/999999/"),
        ("post", "/api/ventas/sales/999999/confirm/"), ("post", "/api/ventas/sales/999999/pay/"),
        ("post", "/api/ventas/sales/999999/cancel/"), ("post", "/api/pagos/"),
        ("post", "/api/facturas/999999/generar/"), ("post", "/api/facturas/999999/editar/"),
    ]
    read_routes = [
        "/api/clientes/", "/api/bins/types/", "/api/bins/clientes/", "/api/bins/movements/", "/api/bins/balance/",
        "/api/productos/", "/api/productos/presentations/", "/api/inventario/", "/api/inventario/stock/",
        "/api/ventas/sales/", "/api/ventas/items/", "/api/ventas/sales/dashboard/", "/api/ventas/sales/reporte/",
        "/api/pagos/", "/api/facturas/",
    ]

    def setUp(self):
        self.owner = User.objects.create_user(username="access_owner", suscripcion_activa=True)
        self.secondary = User.objects.create_user(username="access_secondary", suscripcion_activa=True)
        self.relation = UsuarioAsociado.objects.create(titular=self.owner, usuario_asociado=self.secondary)
        self.now = timezone.now()
        self.plan = SubscriptionPlan.objects.get(codigo="bintrack_mensual_0")
        self.subscription = UserSubscription.objects.create(
            usuario=self.owner, plan=self.plan, fecha_inicio=self.now - timedelta(days=35),
            fecha_fin=self.now - timedelta(days=4),
        )
        # A legacy secondary's own paid subscription must never bypass its owner's expiry.
        UserSubscription.objects.create(usuario=self.secondary, plan=self.plan, fecha_fin=self.now + timedelta(days=10))
        self.client = APIClient()

    def business_counts(self):
        return {model._meta.label: model.objects.count() for label in
                ("clientes", "bins", "productos", "inventario", "ventas", "pagos", "facturas")
                for model in apps.get_app_config(label).get_models()}

    def test_all_business_writes_are_blocked_for_owner_and_secondary_without_mutation(self):
        before = self.business_counts()
        for user in (self.owner, self.secondary):
            self.client.force_authenticate(user)
            for method, path in self.write_routes:
                with self.subTest(user=user.username, method=method, path=path):
                    response = getattr(self.client, method)(path, {}, format="json")
                    self.assertEqual(response.status_code, 403, (path, response.data))
                    self.assertEqual(response.data["code"], "subscription_read_only")
        self.assertEqual(self.business_counts(), before)

    def test_expired_account_can_read_all_business_lists_and_reports(self):
        before = self.business_counts()
        for user in (self.owner, self.secondary):
            self.client.force_authenticate(user)
            for path in self.read_routes:
                with self.subTest(user=user.username, path=path):
                    self.assertEqual(self.client.get(path).status_code, 200, path)
        self.assertEqual(self.business_counts(), before)

    def test_active_and_grace_allow_writes_then_exact_boundary_blocks_same_session(self):
        ruts = iter(["11111111-1", "22222222-2", "33333333-3", "44444444-4"])
        for remaining in (timedelta(days=1), -timedelta(days=2)):
            self.subscription.fecha_fin = self.now + remaining
            self.subscription.save()
            for user in (self.owner, self.secondary):
                self.client.force_authenticate(user)
                with patch("apps.accounts.services.subscription_access.timezone.now", return_value=self.now):
                    response = self.client.post("/api/clientes/", {"nombre": "Prueba", "rut": next(ruts)}, format="json")
                    self.assertEqual(response.status_code, 201, response.data)
        grace_end = self.subscription.fecha_fin + timedelta(days=3)
        with patch("apps.accounts.services.subscription_access.timezone.now", return_value=grace_end):
            response = self.client.post("/api/clientes/", {"nombre": "Bloquear"}, format="json")
            self.assertEqual(response.status_code, 403)

    def test_profile_and_status_use_owner_and_do_not_renew_or_mutate_dates(self):
        self.client.force_authenticate(self.secondary)
        before = self.subscription.fecha_fin
        profile = self.client.get("/api/accounts/user/profile/").data
        status = self.client.get("/api/accounts/suscripcion/estado/").data
        self.assertFalse(profile["suscripcion_activa"])
        self.assertFalse(status["suscrito"])
        self.assertEqual(profile["suscripcion_acceso"], status["suscripcion_acceso"])
        self.assertEqual(profile["suscripcion_acceso"]["estado"], "vencida")
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.fecha_fin, before)
        self.client.force_authenticate(self.owner)
        account = self.client.get("/api/accounts/cuenta/")
        self.assertEqual(account.status_code, 200)
        self.assertEqual(account.data["suscripcion_acceso"]["estado"], "vencida")
        # Owner retains account administration, including disabling a compromised secondary.
        result = self.client.put(f"/api/accounts/cuenta/usuarios/{self.relation.pk}/", {"activo": False}, format="json")
        self.assertEqual(result.status_code, 200)

    def test_missing_or_inactive_subscription_does_not_grant_writes(self):
        self.client.force_authenticate(self.owner)
        self.subscription.fecha_fin = self.now + timedelta(days=5)
        self.subscription.activa = False
        self.subscription.save()
        self.assertEqual(self.client.post("/api/clientes/", {}).status_code, 403)
        self.subscription.delete()
        self.assertEqual(self.client.post("/api/clientes/", {}).status_code, 403)
        self.assertEqual(self.client.get("/api/clientes/").status_code, 200)

    def test_read_only_is_not_a_bypass_for_disabled_users_or_cross_tenant_reads(self):
        from apps.clientes.models import Client
        other = User.objects.create_user(username="other_tenant")
        client = Client.objects.create(usuario=other, nombre="Privado", rut="private")
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(f"/api/clientes/{client.pk}/").status_code, 404)
        self.relation.activo = False
        self.relation.save()
        self.client.force_authenticate(self.secondary)
        self.assertEqual(self.client.get("/api/clientes/").status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/clientes/").status_code, 401)

    def test_every_registered_business_view_has_subscription_permission(self):
        modules = ("apps.bins.", "apps.clientes.", "apps.productos.", "apps.inventario.",
                   "apps.ventas.", "apps.pagos.", "apps.facturas.")
        checked = set()

        def inspect(patterns):
            for pattern in patterns:
                if isinstance(pattern, URLResolver):
                    inspect(pattern.url_patterns)
                    continue
                view = getattr(pattern.callback, "cls", None)
                if view and view.__module__.startswith(modules):
                    checked.add(view)
                    self.assertIn(HasActiveSubscription, view.permission_classes, view.__name__)
                    overrides = getattr(pattern.callback, "initkwargs", {}).get("permission_classes")
                    if overrides is not None:
                        self.assertIn(HasActiveSubscription, overrides)
        inspect(get_resolver().url_patterns)
        self.assertEqual(len(checked), 18)
