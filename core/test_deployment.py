"""Regression tests for the new deployment boundary and password policy."""
import io
from unittest import TestCase

from django.test import TestCase as DjangoTestCase
from django.urls import reverse

from config.proxy import ProxyGuard
from core.models import User


class ProxyBoundaryTests(TestCase):
    def test_backend_rejects_direct_requests_including_forged_https_headers(self):
        invoked = []
        guard = ProxyGuard(lambda environ, start: invoked.append(True), "a" * 64)
        for token in [None, "wrong", "é" * 64]:
            with self.subTest(token_kind=type(token).__name__):
                environ = {"wsgi.input": io.BytesIO(), "HTTP_X_FORWARDED_PROTO": "https"}
                if token is not None:
                    environ["HTTP_X_CLAIMSAFE_PROXY"] = token
                statuses = []
                result = guard(environ, lambda status, headers: statuses.append(status))
                self.assertEqual(statuses, ["404 Not Found"])
                self.assertEqual(result, [b"This endpoint is unavailable."])
                self.assertNotIn("HTTP_X_CLAIMSAFE_PROXY", environ)
        self.assertFalse(invoked)

    def test_proxy_credential_is_removed_before_application_or_error_logging(self):
        def application(environ, start):
            self.assertNotIn("HTTP_X_CLAIMSAFE_PROXY", environ)
            start("200 OK", [])
            return [b"authorised"]
        guard = ProxyGuard(application, "b" * 64)
        statuses = []
        result = guard({"HTTP_X_CLAIMSAFE_PROXY": "b" * 64}, lambda status, headers: statuses.append(status))
        self.assertEqual(statuses, ["200 OK"])
        self.assertEqual(result, [b"authorised"])

    def test_backend_refuses_to_start_without_a_sufficient_proxy_credential(self):
        for token in [None, "short"]:
            with self.assertRaises(ValueError):
                ProxyGuard(lambda environ, start: [], token)


class PasswordPolicyTests(DjangoTestCase):
    def test_unknown_host_is_rejected_even_on_the_public_homepage(self):
        response = self.client.get(reverse("home"), HTTP_HOST="outside.example.test")
        self.assertEqual(response.status_code, 400)

    def test_registration_requires_fifteen_characters_even_for_a_complex_password(self):
        password = "BroadCloud!842"
        self.assertEqual(len(password), 14)
        response = self.client.post(reverse("register"), {
            "username": "strongstudent", "email": "strong@example.test",
            "password1": password, "password2": password, "privacy_acknowledged": "on",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="strongstudent").exists())

    def test_registration_accepts_a_suitable_fifteen_character_password(self):
        password = "BroadCloud!8427"
        self.assertEqual(len(password), 15)
        response = self.client.post(reverse("register"), {
            "username": "strongstudent", "email": "strong@example.test",
            "password1": password, "password2": password, "privacy_acknowledged": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.get(username="strongstudent").check_password(password))
