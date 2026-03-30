from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class StudentCsvImportTests(TestCase):
    def setUp(self):
        self.password = "Testpass123!"
        self.staff = User.objects.create_user(
            username="staff@afra.lernsax.de",
            email="staff@afra.lernsax.de",
            password=self.password,
            is_staff=True,
        )
        self.client.login(username=self.staff.username, password=self.password)

    @patch("adminview.views._send_activation_email")
    def test_imports_exact_three_column_student_csv(self, mock_send_activation_email):
        content = (
            "ignored-login;amelie.sachse@afra.lernsax.de;Amelie Sachse\n"
            ";frieda.zielke@afra.lernsax.de;Frieda Zielke\n"
            "anything;gian-luca.popov@afra.lernsax.de;Gian Luca Popov\n"
        ).encode("utf-8")
        upload = SimpleUploadedFile("schueler.csv", content, content_type="text/csv")

        response = self.client.post(reverse("adminview-csv"), {"csv_file": upload}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="amelie.sachse@afra.lernsax.de").exists())
        self.assertTrue(User.objects.filter(username="frieda.zielke@afra.lernsax.de").exists())
        user = User.objects.get(email="gian-luca.popov@afra.lernsax.de")
        self.assertEqual(user.username, "gian-luca.popov@afra.lernsax.de")
        self.assertEqual(user.email, "gian-luca.popov@afra.lernsax.de")
        self.assertEqual(user.first_name, "Gian")
        self.assertEqual(user.last_name, "Luca Popov")
        self.assertFalse(user.is_active)
        self.assertEqual(mock_send_activation_email.call_count, 3)

    @patch("adminview.views._send_activation_email")
    def test_rejects_rows_with_wrong_column_count(self, mock_send_activation_email):
        content = (
            "amelie.sachse;amelie.sachse@afra.lernsax.de\n"
            "frieda.zielke;frieda.zielke@afra.lernsax.de;Frieda Zielke\n"
        ).encode("utf-8")
        upload = SimpleUploadedFile("invalid.csv", content, content_type="text/csv")

        response = self.client.post(reverse("adminview-csv"), {"csv_file": upload}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="frieda.zielke@afra.lernsax.de").exists())
        self.assertEqual(mock_send_activation_email.call_count, 0)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("Die CSV ist ungültig" in message for message in messages))
        self.assertTrue(any("Zeile 1" in message for message in messages))

    @patch("adminview.views._send_activation_email")
    def test_imports_cp1252_umlauts(self, mock_send_activation_email):
        content = "h.schmoeller;h.schmoeller@afra.lernsax.de;Hanna Schmöller\n".encode("cp1252")
        upload = SimpleUploadedFile("umlaut.csv", content, content_type="text/csv")

        response = self.client.post(reverse("adminview-csv"), {"csv_file": upload}, follow=True)

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email="h.schmoeller@afra.lernsax.de")
        self.assertEqual(user.username, "h.schmoeller@afra.lernsax.de")
        self.assertEqual(user.last_name, "Schmöller")
        self.assertEqual(mock_send_activation_email.call_count, 1)
