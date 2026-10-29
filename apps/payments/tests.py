import hashlib
import hmac
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import Mock, patch
from uuid import uuid4

from django.db import close_old_connections, connection, connections
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User, SubscriptionPlan, UserSubscription, UsuarioAsociado
from apps.accounts.services.monthly_periods import next_month
from .models import Payment, PaymentAttempt
from .services.configuration import PaymentsUnavailable, test_config as payment_config
from .services.mercadopago import MercadoPagoService
from .services.reconciliation import reconcile

TEST_SETTINGS = {
    "MERCADOPAGO_ENV": "sandbox",
    "MERCADOPAGO_TEST_ENABLED": True,
    "MERCADOPAGO_TEST_ACCESS_TOKEN": "fake-local-test-token",
    "MERCADOPAGO_TEST_COLLECTOR_ID": "123",
    "MERCADOPAGO_TEST_WEBHOOK_SECRET": "fake-local-signature-key",
    "MERCADOPAGO_TEST_NOTIFICATION_URL": "https://test.example/api/payments/webhook/",
    "MERCADOPAGO_TEST_SUCCESS_URL": "https://test.example/return/success",
    "MERCADOPAGO_TEST_FAILURE_URL": "https://test.example/return/failure",
    "MERCADOPAGO_TEST_PENDING_URL": "https://test.example/return/pending",
}
CHECKOUT_URL = "https://www.mercadopago.cl/checkout/v1/redirect?pref_id=test"
MERCHANT = {"id": 123, "country_id": "CL", "tags": ["test_user"]}


def provider_data(order, provider_id="1001", **changes):
    approved = order.created_at + timedelta(seconds=1)
    data = {
        "id": int(provider_id), "external_reference": str(order.reference),
        "status": "approved", "live_mode": False, "collector_id": 123,
        "transaction_amount": order.amount, "currency_id": "CLP",
        "date_approved": approved.isoformat(),
        "date_last_updated": (approved + timedelta(seconds=1)).isoformat(),
    }
    data.update(changes)
    return data


def signed_request(client, provider_id="1001", **changes):
    ts = "1792857600"
    request_id = "local-request-001"
    manifest = f"id:{provider_id};request-id:{request_id};ts:{ts};"
    signature = hmac.new(TEST_SETTINGS["MERCADOPAGO_TEST_WEBHOOK_SECRET"].encode(),
                         manifest.encode(), hashlib.sha256).hexdigest()
    headers = {"HTTP_X_REQUEST_ID": request_id, "HTTP_X_SIGNATURE": f"ts={ts},v1={signature}"}
    headers.update(changes)
    return client.post(
        f"/api/payments/webhook/?data.id={provider_id}&type=payment",
        {"type": "payment", "action": "payment.updated", "data": {"id": provider_id}},
        format="json", **headers,
    )


@override_settings(**TEST_SETTINGS)
class ProviderSafetyTests(SimpleTestCase):
    def setUp(self):
        self.network = patch("requests.sessions.Session.request", side_effect=AssertionError("No network in tests"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.sdk_patch = patch("apps.payments.services.mercadopago.mercadopago.SDK")
        self.sdk_class = self.sdk_patch.start()
        self.addCleanup(self.sdk_patch.stop)
        self.sdk = self.sdk_class.return_value
        self.sdk.user.return_value.get.return_value = {"status": 200, "response": MERCHANT}
        self.sdk.preference.return_value.create.return_value = {
            "status": 201, "response": {"id": "pref-001", "init_point": CHECKOUT_URL},
        }
        now = timezone.now()
        self.order = Mock(reference=uuid4(), plan_code="bintrack_mensual_0", amount=50000,
                          created_at=now, expires_at=now + timedelta(hours=24))

    def test_disabled_missing_credentials_and_production_fail_closed(self):
        for setting in [
            {"MERCADOPAGO_TEST_ENABLED": False, "DEBUG": True},
            {"MERCADOPAGO_ENV": "production"},
            {"MERCADOPAGO_TEST_ACCESS_TOKEN": "", "MERCADOPAGO_ACCESS_TOKEN": "legacy-secret"},
            {"MERCADOPAGO_TEST_COLLECTOR_ID": ""},
            {"MERCADOPAGO_TEST_WEBHOOK_SECRET": ""},
        ]:
            with self.subTest(setting=list(setting)), override_settings(**setting):
                with self.assertRaises(PaymentsUnavailable):
                    MercadoPagoService()
        self.sdk_class.assert_not_called()

    def test_configuration_repr_does_not_expose_secrets(self):
        value = repr(payment_config())
        self.assertNotIn(TEST_SETTINGS["MERCADOPAGO_TEST_ACCESS_TOKEN"], value)
        self.assertNotIn(TEST_SETTINGS["MERCADOPAGO_TEST_WEBHOOK_SECRET"], value)

    def test_real_foreign_or_wrong_country_seller_cannot_create_preference(self):
        for seller in [dict(MERCHANT, tags=[]), dict(MERCHANT, id=456), dict(MERCHANT, country_id="AR")]:
            with self.subTest(seller=seller):
                self.sdk.user.return_value.get.return_value = {"status": 200, "response": seller}
                with self.assertRaises(PaymentsUnavailable):
                    MercadoPagoService().crear_preferencia(self.order)
        self.sdk.preference.return_value.create.assert_not_called()

    def test_preference_contains_quote_expiry_return_urls_and_stable_reference(self):
        with override_settings(DEBUG=False):
            result = MercadoPagoService().crear_preferencia(self.order)
        self.assertEqual(result["init_point"], CHECKOUT_URL)
        payload, options = self.sdk.preference.return_value.create.call_args.args
        self.assertEqual(payload["items"][0]["unit_price"], 50000)
        self.assertEqual(payload["items"][0]["currency_id"], "CLP")
        self.assertEqual(payload["external_reference"], str(self.order.reference))
        self.assertTrue(payload["expires"])
        self.assertEqual(payload["back_urls"]["success"], TEST_SETTINGS["MERCADOPAGO_TEST_SUCCESS_URL"])
        self.assertEqual(options.custom_headers["x-idempotency-key"], str(self.order.reference))

    def test_bad_urls_and_unexpected_checkout_host_are_rejected(self):
        with override_settings(MERCADOPAGO_TEST_NOTIFICATION_URL="http://localhost:8000/"):
            with self.assertRaises(PaymentsUnavailable):
                MercadoPagoService().crear_preferencia(self.order)
        self.sdk.user.return_value.get.assert_not_called()
        self.sdk.preference.return_value.create.return_value = {
            "status": 201, "response": {"id": "pref", "init_point": "https://example.test/pay"},
        }
        with self.assertRaises(PaymentsUnavailable):
            MercadoPagoService().crear_preferencia(self.order)

    def test_provider_errors_are_sanitized_and_not_retried(self):
        self.sdk.payment.return_value.get.side_effect = RuntimeError("SECRET-personal-data")
        with self.assertRaises(PaymentsUnavailable) as context:
            MercadoPagoService().consultar_pago("123")
        self.assertNotIn("SECRET", str(context.exception))
        self.sdk.payment.return_value.get.assert_called_once()
        options = self.sdk_class.call_args.kwargs["request_options"]
        self.assertEqual(options.max_retries, 0)


@override_settings(**TEST_SETTINGS)
class PaymentFlowTests(TestCase):
    def live_test_settings(self):
        return override_settings(MERCADOPAGO_TEST_ALLOW_TEST_USERS_LIVE_MODE=True,
                                 MERCADOPAGO_TEST_BUYER_ID="456",
                                 MERCADOPAGO_TEST_LOCAL_OWNER_ID=str(self.owner.pk))

    def test_verified_test_users_live_mode_webhook_applies_once(self):
        order = self.create_order()
        data = provider_data(order, live_mode=True, payer={"id": 456})
        self.sdk.payment.return_value.get.return_value = {"status": 200, "response": data}
        with self.live_test_settings():
            self.assertEqual(signed_request(APIClient()).status_code, 200)
            first = UserSubscription.objects.get(usuario=self.owner).fecha_fin
            self.assertEqual(signed_request(APIClient()).status_code, 200)
            self.assertEqual(UserSubscription.objects.get(usuario=self.owner).fecha_fin, first)
        self.assertEqual(PaymentAttempt.objects.count(), 1)
        self.assertEqual(UserSubscription.objects.count(), 1)

    def test_live_mode_exception_rejects_real_or_unverified_seller(self):
        order = self.create_order()
        data = provider_data(order, live_mode=True, payer={"id": 456})
        for response in ({"status": 200, "response": dict(MERCHANT, tags=[])},
                         {"status": 200, "response": dict(MERCHANT, id=999)},
                         {"status": 200, "response": dict(MERCHANT, country_id="AR")},
                         {"status": 503, "response": {}}):
            with self.subTest(response=response), self.live_test_settings():
                self.sdk.user.return_value.get.return_value = response
                with self.assertRaises(PaymentsUnavailable):
                    reconcile("1001", data)
        self.assertFalse(PaymentAttempt.objects.exists())
        self.assertFalse(UserSubscription.objects.exists())

    def test_live_mode_exception_requires_exact_buyer_owner_and_opt_in(self):
        order = self.create_order()
        data = provider_data(order, live_mode=True, payer={"id": 456})
        cases = [dict(MERCADOPAGO_TEST_ALLOW_TEST_USERS_LIVE_MODE=False),
                 dict(MERCADOPAGO_TEST_BUYER_ID=""), dict(MERCADOPAGO_TEST_BUYER_ID="789"),
                 dict(MERCADOPAGO_TEST_BUYER_ID="123"),
                 dict(MERCADOPAGO_TEST_LOCAL_OWNER_ID=str(self.other.pk)),
                 dict(MERCADOPAGO_TEST_LOCAL_OWNER_ID="")]
        with self.live_test_settings():
            for values in cases:
                with self.subTest(values=values), override_settings(**values):
                    with self.assertRaises(ValidationError):
                        reconcile("1001", data)
            for payer in (None, {}, {"id": 999}):
                with self.assertRaises(ValidationError):
                    reconcile("1001", dict(data, payer=payer))
        self.assertFalse(PaymentAttempt.objects.exists())
        self.assertFalse(UserSubscription.objects.exists())

    def setUp(self):
        self.block_network = patch("requests.sessions.Session.request", side_effect=AssertionError("No network in tests"))
        self.block_network.start()
        self.addCleanup(self.block_network.stop)
        self.sdk_patch = patch("apps.payments.services.mercadopago.mercadopago.SDK")
        self.sdk_class = self.sdk_patch.start()
        self.addCleanup(self.sdk_patch.stop)
        self.sdk = self.sdk_class.return_value
        self.sdk.user.return_value.get.return_value = {"status": 200, "response": MERCHANT}
        self.sdk.preference.return_value.create.return_value = {
            "status": 201, "response": {"id": "pref-001", "init_point": CHECKOUT_URL},
        }
        self.owner = User.objects.create_user(username="payment_owner")
        self.other = User.objects.create_user(username="payment_other")
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.plan = SubscriptionPlan.objects.get(codigo="bintrack_mensual_0")

    def create_order(self):
        response = self.client.post("/api/payments/crear/", {}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return Payment.objects.get(pk=response.data["payment_id"])

    def secondary(self, index=1):
        user = User.objects.create_user(username=f"pay_secondary{index}")
        UsuarioAsociado.objects.create(titular=self.owner, usuario_asociado=user)
        return user

    def test_prices_for_zero_one_and_two_secondaries_and_no_renewal_on_creation(self):
        for count, price in enumerate([50000, 60000, 70000]):
            with self.subTest(count=count):
                if count:
                    self.secondary(count)
                order = self.create_order()
                self.assertEqual(order.amount, price)
                self.assertEqual(len(order.secondary_ids), count)
                self.assertEqual(order.environment, "sandbox")
                self.assertIsNotNone(order.reference)
                self.assertIsNone(order.applied_at)
                self.assertFalse(UserSubscription.objects.exists())
                order.expires_at = timezone.now() - timedelta(seconds=1)
                order.save(update_fields=["expires_at"])

    def test_client_cannot_set_price_or_plan_or_activate_by_return(self):
        for fields in [{"amount": 1}, {"plan": 1}, {"status": "approved"}]:
            response = self.client.post("/api/payments/crear/", fields, format="json")
            self.assertEqual(response.status_code, 400)
        self.assertFalse(Payment.objects.exists())
        order = self.create_order()
        response = self.client.get(f"/api/payments/confirmar/?payment_id={order.pk}&status=approved")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["applied"])
        self.assertFalse(UserSubscription.objects.exists())
        self.sdk.payment.return_value.get.assert_not_called()

    def test_checkout_retries_reuse_order_and_provider_preference(self):
        first = self.create_order()
        response = self.client.post("/api/payments/crear/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["payment_id"], first.pk)
        self.assertEqual(Payment.objects.count(), 1)
        self.sdk.preference.return_value.create.assert_called_once()

    def test_ambiguous_preference_failure_keeps_correlation_and_blocks_duplicate(self):
        self.sdk.preference.return_value.create.side_effect = RuntimeError("PRIVATE")
        response = self.client.post("/api/payments/crear/", {}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("PRIVATE", str(response.data))
        order = Payment.objects.get()
        self.assertTrue(order.needs_review)
        self.assertEqual(self.client.post("/api/payments/crear/", {}, format="json").status_code, 409)
        self.assertEqual(Payment.objects.count(), 1)
        self.sdk.preference.return_value.create.assert_called_once()

    def test_changed_roster_blocks_reusing_link_and_requires_review_on_payment(self):
        order = self.create_order()
        self.secondary()
        self.assertEqual(self.client.post("/api/payments/crear/", {}, format="json").status_code, 409)
        result = reconcile("1001", provider_data(order))
        self.assertTrue(result.needs_review)
        self.assertIsNone(result.applied_at)
        self.assertFalse(UserSubscription.objects.exists())

    def test_approved_payment_renews_once_across_webhook_and_authenticated_check(self):
        order = self.create_order()
        data = provider_data(order)
        self.sdk.payment.return_value.get.return_value = {"status": 200, "response": data}
        self.assertEqual(signed_request(APIClient()).status_code, 200)
        first_end = UserSubscription.objects.get(usuario=self.owner).fecha_fin
        for _ in range(2):
            self.assertEqual(signed_request(APIClient()).status_code, 200)
        response = self.client.post(f"/api/payments/verificar/{order.pk}/", {"provider_payment_id": "1001"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["applied"])
        self.assertEqual(UserSubscription.objects.get(usuario=self.owner).fecha_fin, first_end)
        self.assertEqual(PaymentAttempt.objects.count(), 1)

    def test_expired_subscription_renews_existing_row_from_previous_due_date(self):
        due = timezone.now() - timedelta(days=10)
        subscription = UserSubscription.objects.create(
            usuario=self.owner, plan=self.plan, fecha_inicio=due - timedelta(days=30), fecha_fin=due,
        )
        order = self.create_order()
        result = reconcile("1001", provider_data(order))
        subscription.refresh_from_db()
        local_due = timezone.localtime(due)
        self.assertEqual(subscription.fecha_fin, next_month(due, local_due.day))
        self.assertEqual(result.applied_until, subscription.fecha_fin)
        self.assertEqual(UserSubscription.objects.count(), 1)

    def test_active_and_grace_renewal_use_due_date_not_payment_date(self):
        for days in [-10, 2]:
            with self.subTest(days=days):
                # Separate owners avoid reusing an earlier paid quote.
                self.owner = User.objects.create_user(username=f"due_owner{days}")
                self.client.force_authenticate(self.owner)
                due = timezone.now() - timedelta(days=days)
                subscription = UserSubscription.objects.create(
                    usuario=self.owner, plan=self.plan, fecha_inicio=due - timedelta(days=30), fecha_fin=due,
                )
                order = self.create_order()
                reconcile(str(2000 + days), provider_data(order, str(2000 + days)))
                subscription.refresh_from_db()
                self.assertEqual(subscription.fecha_fin, next_month(due, timezone.localtime(due).day))

    def test_validation_rejects_wrong_amount_currency_seller_environment_reference_and_id(self):
        order = self.create_order()
        for fields in [
            {"transaction_amount": 1}, {"transaction_amount": "NaN"}, {"transaction_amount": "50000.01"},
            {"currency_id": "USD"}, {"collector_id": 999}, {"live_mode": True},
            {"live_mode": "false"}, {"external_reference": str(order.pk)}, {"id": 9001},
            {"date_last_updated": "bad"}, {"date_approved": None}, {"status": "mystery"},
        ]:
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                reconcile("1001", provider_data(order, **fields))
        self.assertFalse(UserSubscription.objects.exists())
        self.assertFalse(PaymentAttempt.objects.exists())
        order.refresh_from_db()
        self.assertIsNone(order.applied_at)

    def test_missing_or_bad_signature_and_legacy_ipn_cannot_query_provider(self):
        self.sdk_class.reset_mock()
        client = APIClient()
        self.assertEqual(client.post("/api/payments/webhook/?topic=payment&id=1001", {}, format="json").status_code, 401)
        self.assertEqual(signed_request(client, HTTP_X_SIGNATURE="ts=1792857600,v1=" + "0" * 64).status_code, 401)
        self.assertEqual(signed_request(client, HTTP_X_REQUEST_ID="wrong-request").status_code, 401)
        self.sdk_class.assert_not_called()

    def test_provider_failure_is_retryable_without_activation(self):
        order = self.create_order()
        self.sdk.payment.return_value.get.return_value = {"status": 500, "response": {"token": "PRIVATE"}}
        response = signed_request(APIClient())
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("PRIVATE", str(response.data))
        self.assertFalse(UserSubscription.objects.exists())
        self.assertFalse(PaymentAttempt.objects.exists())
        self.sdk.payment.return_value.get.return_value = {"status": 200, "response": provider_data(order)}
        self.assertEqual(signed_request(APIClient()).status_code, 200)

    def test_rejected_attempt_does_not_prevent_a_different_successful_attempt(self):
        order = self.create_order()
        reconcile("1001", provider_data(order, status="rejected"))
        self.assertFalse(UserSubscription.objects.exists())
        result = reconcile("1002", provider_data(order, "1002"))
        self.assertIsNotNone(result.applied_at)
        self.assertEqual(PaymentAttempt.objects.count(), 2)

    def test_two_approved_provider_payments_for_one_order_never_extend_twice(self):
        order = self.create_order()
        first = reconcile("1001", provider_data(order))
        result = reconcile("1002", provider_data(order, "1002"))
        self.assertTrue(result.needs_review)
        self.assertEqual(result.review_reason, "multiple_approved_payments")
        self.assertEqual(result.applied_until, first.applied_until)
        self.assertEqual(UserSubscription.objects.get(usuario=self.owner).fecha_fin, first.applied_until)

    def test_refunds_and_chargebacks_are_not_pending_or_automatic_date_changes(self):
        order = self.create_order()
        first = reconcile("1001", provider_data(order))
        later = (order.created_at + timedelta(minutes=5)).isoformat()
        result = reconcile("1001", provider_data(order, status="refunded", date_last_updated=later))
        self.assertEqual(result.status, "refunded")
        self.assertTrue(result.needs_review)
        self.assertEqual(UserSubscription.objects.get(usuario=self.owner).fecha_fin, first.applied_until)
        result = reconcile("1001", provider_data(order))
        self.assertEqual(result.status, "refunded")
        result = reconcile("1001", provider_data(order, status="charged_back", date_last_updated=later))
        self.assertEqual(result.status, "charged_back")

    def test_partial_refund_or_dispute_before_approval_requires_review(self):
        order = self.create_order()
        result = reconcile("1001", provider_data(order, transaction_amount_refunded=100))
        self.assertTrue(result.needs_review)
        self.assertIsNone(result.applied_at)
        reconcile("1001", provider_data(order))
        self.assertFalse(UserSubscription.objects.exists())

    def test_stale_status_does_not_downgrade_approved_order(self):
        order = self.create_order()
        first = reconcile("1001", provider_data(order))
        result = reconcile("1001", provider_data(order, status="pending"))
        self.assertEqual(result.status, "approved")
        self.assertEqual(result.applied_until, first.applied_until)

    def test_late_notification_for_timely_payment_is_accepted_but_late_payment_is_reviewed(self):
        order = self.create_order()
        with patch("apps.payments.services.reconciliation.timezone.now", return_value=order.expires_at + timedelta(days=3)):
            result = reconcile("1001", provider_data(order))
        self.assertIsNotNone(result.applied_at)
        new_order = self.create_order()
        late = new_order.expires_at + timedelta(minutes=1)
        result = reconcile("1002", provider_data(new_order, "1002", date_approved=late.isoformat(), date_last_updated=late.isoformat()))
        self.assertTrue(result.needs_review)
        self.assertIsNone(result.applied_at)

    def test_period_changed_since_checkout_is_not_silently_extended(self):
        order = self.create_order()
        due = timezone.now() + timedelta(days=15)
        UserSubscription.objects.create(usuario=self.owner, plan=self.plan, fecha_fin=due)
        result = reconcile("1001", provider_data(order))
        self.assertTrue(result.needs_review)
        self.assertEqual(UserSubscription.objects.get(usuario=self.owner).fecha_fin, due)

    def test_secondary_other_owner_anonymous_and_deactivated_owner_cannot_manage_payments(self):
        order = self.create_order()
        secondary = self.secondary()
        self.client.force_authenticate(secondary)
        for method, url, body in [
            ("post", "/api/payments/crear/", {}),
            ("get", f"/api/payments/confirmar/?payment_id={order.pk}", {}),
            ("post", f"/api/payments/verificar/{order.pk}/", {"provider_payment_id": "1001"}),
        ]:
            self.assertEqual(getattr(self.client, method)(url, body).status_code, 403)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/payments/confirmar/?payment_id={order.pk}").status_code, 404)
        self.assertEqual(self.client.post(f"/api/payments/verificar/{order.pk}/", {"provider_payment_id": "1001"}).status_code, 404)
        self.assertEqual(APIClient().get(f"/api/payments/confirmar/?payment_id={order.pk}").status_code, 401)
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.post("/api/payments/crear/", {}).status_code, 403)
        self.sdk.payment.return_value.get.assert_not_called()

    def test_authenticated_recheck_cannot_apply_other_owners_order(self):
        first = self.create_order()
        self.client.force_authenticate(self.other)
        second = self.create_order()
        self.sdk.payment.return_value.get.return_value = {"status": 200, "response": provider_data(first)}
        response = self.client.post(f"/api/payments/verificar/{second.pk}/", {"provider_payment_id": "1001"}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(UserSubscription.objects.exists())

    def test_old_simulation_never_activates_even_in_debug(self):
        order = self.create_order()
        with override_settings(DEBUG=True):
            self.assertEqual(self.client.post(f"/api/payments/simular-aprobado/{order.pk}/", {}).status_code, 410)
        self.assertFalse(UserSubscription.objects.exists())
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")

    def test_historical_orders_cannot_be_replayed_as_new_payments(self):
        old = Payment.objects.create(user=self.owner, amount=10000, provider="mercadopago", status="approved")
        with self.assertRaises(ValidationError):
            reconcile("1001", provider_data(old, external_reference=str(old.pk), transaction_amount=10000))
        self.assertFalse(UserSubscription.objects.exists())
        old.refresh_from_db()
        self.assertIsNone(old.applied_at)

    def test_renewal_failure_rolls_back_order_attempt_and_subscription(self):
        order = self.create_order()
        def fail_after_write(*args, **kwargs):
            UserSubscription.objects.create(usuario=self.owner, plan=self.plan, fecha_fin=timezone.now())
            raise RuntimeError("simulated failure")
        with patch("apps.payments.services.reconciliation.renew_monthly_period", side_effect=fail_after_write):
            with self.assertRaises(RuntimeError):
                reconcile("1001", provider_data(order))
        self.assertFalse(PaymentAttempt.objects.exists())
        self.assertFalse(UserSubscription.objects.exists())
        order.refresh_from_db()
        self.assertIsNone(order.applied_at)

    def test_configuration_disabled_prevents_new_orders_and_reconciliation(self):
        with override_settings(MERCADOPAGO_TEST_ENABLED=False):
            self.assertEqual(self.client.post("/api/payments/crear/", {}).status_code, 503)
            self.assertEqual(signed_request(APIClient()).status_code, 503)
        self.assertFalse(Payment.objects.exists())

    def test_paid_expired_or_review_order_does_not_expose_a_reusable_checkout_link(self):
        order = self.create_order()
        for updates in [{"needs_review": True}, {"expires_at": timezone.now() - timedelta(seconds=1)},
                        {"applied_at": timezone.now()}]:
            with self.subTest(updates=list(updates)):
                Payment.objects.filter(pk=order.pk).update(**updates)
                response = self.client.get(f"/api/payments/confirmar/?payment_id={order.pk}")
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(response.data["init_point"])

    def test_signature_does_not_allow_a_different_body_resource(self):
        self.create_order()
        ts, request_id, provider_id = "1792857600", "req-valid", "1001"
        manifest = f"id:{provider_id};request-id:{request_id};ts:{ts};"
        signature = hmac.new(TEST_SETTINGS["MERCADOPAGO_TEST_WEBHOOK_SECRET"].encode(),
                             manifest.encode(), hashlib.sha256).hexdigest()
        response = APIClient().post(
            "/api/payments/webhook/?data.id=1001&type=payment",
            {"type": "payment", "data": {"id": "9999"}}, format="json",
            HTTP_X_REQUEST_ID=request_id, HTTP_X_SIGNATURE=f"ts={ts},v1={signature}",
        )
        self.assertEqual(response.status_code, 401)
        self.sdk.payment.return_value.get.assert_not_called()

    def test_a_provider_id_cannot_be_rebound_to_another_local_order(self):
        first = self.create_order()
        reconcile("1001", provider_data(first, status="rejected"))
        self.client.force_authenticate(self.other)
        other = self.create_order()
        with self.assertRaises(ValidationError):
            reconcile("1001", provider_data(other))
        self.assertEqual(PaymentAttempt.objects.get().payment_id, first.pk)
        self.assertFalse(UserSubscription.objects.exists())


@override_settings(**TEST_SETTINGS)
class SettlementConcurrencyTests(TransactionTestCase):
    def test_simultaneous_notifications_apply_one_month_once(self):
        if connection.vendor != "postgresql":
            self.skipTest("Requires PostgreSQL row locks")
        owner = User.objects.create_user(username="parallel_payment_owner")
        SubscriptionPlan.objects.get_or_create(codigo="bintrack_mensual_0", defaults={
            "nombre": "Principal", "precio": 50000, "usuarios_secundarios": 0,
        })
        order = Payment.objects.create(user=owner, amount=50000, provider="mercadopago",
                                       reference=uuid4(), environment="sandbox", plan_code="bintrack_mensual_0",
                                       expires_at=timezone.now() + timedelta(hours=24))
        data = provider_data(order)
        barrier = Barrier(2, timeout=20)
        def settle(_):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '15s'")
                barrier.wait()
                return reconcile("1001", data).applied_until
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            ends = list(pool.map(settle, [1, 2]))
        self.assertEqual(ends[0], ends[1])
        self.assertEqual(PaymentAttempt.objects.count(), 1)
        self.assertEqual(UserSubscription.objects.count(), 1)
        self.assertEqual(UserSubscription.objects.get().fecha_fin, ends[0])
