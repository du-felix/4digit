from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from antraege.models import Antrag


User = get_user_model()


class AdminviewAccessTests(TestCase):
    def setUp(self):
        self.password = "Testpass123!"
        self.student = User.objects.create_user(
            username="student@afra.lernsax.de",
            email="student@afra.lernsax.de",
            password=self.password,
        )
        self.staff = User.objects.create_user(
            username="staff@afra.lernsax.de",
            email="staff@afra.lernsax.de",
            password=self.password,
            is_staff=True,
        )

    def test_non_staff_user_is_redirected_from_adminview(self):
        self.client.login(username=self.student.email, password=self.password)
        response = self.client.get(reverse("adminview-home"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("home"))

    def test_staff_user_can_open_adminview(self):
        self.client.login(username=self.staff.email, password=self.password)
        response = self.client.get(reverse("adminview-home"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_generate_pdf_with_long_unicode_content(self):
        self.client.login(username=self.staff.email, password=self.password)
        antrag = Antrag.objects.create(
            user=self.student,
            titel="Langer Titel äöü ß " * 5,
            grund=("Sehr lange Begründung mit Unicode: Grüße, مرحبا, 你好. " * 30).strip(),
            klasse="11",
            anfangsdatum=date(2026, 3, 20),
            anfangszeit=time(8, 0),
            enddatum=date(2026, 3, 20),
            endzeit=time(12, 0),
        )

        response = self.client.get(reverse("antrag-pdf", kwargs={"antrag_id": antrag.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
