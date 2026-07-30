"""Tests for the contact endpoint: validation, honeypot, notification, throttling."""

from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.throttling import ScopedRateThrottle

from .models import Submission
from .views import ContactCreateView

VALID = {
    "name": "Aziz",
    "email": "aziz@example.com",
    "message": "I would like to discuss a partnership with the Assembly.",
    "locale": "uz",
}


class UnthrottledTestCase(TestCase):
    """
    Base for tests that are not about rate limiting.

    DRF binds `throttle_classes` on the view at import time, so
    `override_settings(REST_FRAMEWORK=...)` cannot disable it — patch the view.
    The throttle cache is process-wide, so it is also cleared between tests.
    """

    def setUp(self):
        patcher = patch.object(ContactCreateView, "throttle_classes", [])
        patcher.start()
        self.addCleanup(patcher.stop)
        cache.clear()
        self.url = reverse("v1:contact-create")

    def post(self, **overrides):
        return self.client.post(
            self.url, {**VALID, **overrides}, content_type="application/json"
        )


class SubmissionValidationTests(UnthrottledTestCase):
    def test_valid_submission_is_stored(self):
        response = self.post()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Submission.objects.count(), 1)

    def test_records_client_ip(self):
        self.post()
        self.assertIsNotNone(Submission.objects.get().ip_address)

    def test_rejects_short_message(self):
        self.assertEqual(self.post(message="hi").status_code, 400)
        self.assertEqual(Submission.objects.count(), 0)

    def test_rejects_oversized_message(self):
        self.assertEqual(self.post(message="x" * 5001).status_code, 400)

    def test_rejects_invalid_email(self):
        self.assertEqual(self.post(email="nope").status_code, 400)

    def test_rejects_short_name(self):
        self.assertEqual(self.post(name="A").status_code, 400)

    def test_rejects_unknown_locale(self):
        response = self.post(locale="zz")
        self.assertEqual(response.status_code, 400)
        self.assertIn("locale", response.json())

    def test_accepts_blank_locale(self):
        self.assertEqual(self.post(locale="").status_code, 201)

    def test_strips_surrounding_whitespace_from_name(self):
        self.post(name="  Aziz  ")
        self.assertEqual(Submission.objects.get().name, "Aziz")


class ContactDetailsTests(UnthrottledTestCase):
    """
    One way to reply is required, and either will do.

    The form presents email and phone as optional individually, so the rule
    only exists here — which makes it worth pinning down from both sides.
    """

    def test_phone_alone_is_enough(self):
        response = self.post(email="", phone="+998 90 123 45 67")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Submission.objects.get().phone, "+998 90 123 45 67")

    def test_email_alone_is_enough(self):
        self.assertEqual(self.post(phone="").status_code, 201)

    def test_rejects_neither_email_nor_phone(self):
        response = self.post(email="", phone="")
        self.assertEqual(response.status_code, 400)
        # Reported against both, so whichever the form focuses can show it.
        self.assertIn("email", response.json())
        self.assertIn("phone", response.json())
        self.assertEqual(Submission.objects.count(), 0)

    def test_accepts_both(self):
        self.assertEqual(self.post(phone="901234567").status_code, 201)

    def test_rejects_letters_in_phone(self):
        self.assertEqual(self.post(email="", phone="call me").status_code, 400)

    def test_rejects_too_few_digits(self):
        self.assertEqual(self.post(email="", phone="12345").status_code, 400)

    def test_rejects_too_many_digits(self):
        self.assertEqual(self.post(email="", phone="1" * 16).status_code, 400)

    def test_accepts_the_punctuation_people_write_numbers_with(self):
        for written in ("+998 90 123 45 67", "(90) 123-45-67", "90.123.45.67"):
            with self.subTest(written=written):
                Submission.objects.all().delete()
                self.assertEqual(self.post(email="", phone=written).status_code, 201)


class HoneypotTests(UnthrottledTestCase):
    def test_filled_honeypot_is_not_persisted(self):
        response = self.post(website="http://spam.example")
        # 201 so a bot cannot distinguish rejection from acceptance and retry.
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Submission.objects.count(), 0)

    def test_blank_honeypot_is_accepted(self):
        self.assertEqual(self.post(website="").status_code, 201)
        self.assertEqual(Submission.objects.count(), 1)

    def test_honeypot_never_appears_in_response(self):
        self.assertNotIn("website", self.post().json())


@override_settings(
    CONTACT_NOTIFY_EMAILS=["team@assembly.uz"],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class NotificationTests(UnthrottledTestCase):
    def test_sends_notification_email(self):
        self.post()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Aziz", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["team@assembly.uz"])

    def test_notification_carries_both_ways_to_reply(self):
        self.post(phone="+998 90 123 45 67")
        body = mail.outbox[0].body
        self.assertIn("aziz@example.com", body)
        self.assertIn("+998 90 123 45 67", body)

    def test_notification_marks_the_channel_the_visitor_left_out(self):
        self.post(email="", phone="+998 90 123 45 67")
        self.assertIn("Email: —", mail.outbox[0].body)

    def test_submission_survives_a_mail_outage(self):
        # A delivery failure must never lose the visitor's message.
        with patch("contact.views.send_mail", side_effect=OSError("smtp down")):
            response = self.post()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Submission.objects.count(), 1)


@override_settings(CONTACT_NOTIFY_EMAILS=[])
class NoRecipientsTests(UnthrottledTestCase):
    def test_submission_stored_when_no_recipients_configured(self):
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(Submission.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)


class TwoPerHourThrottle(ScopedRateThrottle):
    """A tight limit so the throttle test does not need six requests."""

    THROTTLE_RATES = {"contact": "2/hour"}


class ThrottleTests(TestCase):
    def setUp(self):
        patcher = patch.object(
            ContactCreateView, "throttle_classes", [TwoPerHourThrottle]
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        cache.clear()
        self.addCleanup(cache.clear)
        self.url = reverse("v1:contact-create")

    def post(self):
        return self.client.post(self.url, VALID, content_type="application/json")

    def test_third_request_within_the_hour_is_throttled(self):
        for _ in range(2):
            self.assertEqual(self.post().status_code, 201)

        response = self.post()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(Submission.objects.count(), 2)

    def test_reads_are_never_throttled(self):
        for _ in range(5):
            response = self.client.get(reverse("v1:article-list"))
            self.assertEqual(response.status_code, 200)
