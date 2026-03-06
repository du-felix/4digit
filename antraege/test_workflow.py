from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.test.utils import override_settings

from antraege.forms import TwoStepForm
from antraege.models import Antrag, Anfrage, Lehrer
from antraege.tokens import sign_existing_raw_token


User = get_user_model()


class WorkflowRegressionTests(TestCase):
    def setUp(self):
        self.password = "Testpass123!"
        self.user = User.objects.create_user(
            username="schueler@afra.lernsax.de",
            email="schueler@afra.lernsax.de",
            password=self.password,
            first_name="Max",
            last_name="Mustermann",
        )

    def _create_antrag(self, user=None):
        return Antrag.objects.create(
            user=user or self.user,
            titel="Freistellung",
            grund="Krankheit",
            klasse="11",
            anfangsdatum=date(2026, 3, 20),
            anfangszeit=time(8, 0),
            enddatum=date(2026, 3, 20),
            endzeit=time(12, 0),
        )

    def test_two_step_form_requires_second_answer_when_first_is_ja(self):
        form = TwoStepForm(data={"first_question": "ja"})
        self.assertFalse(form.is_valid())
        self.assertIn("second_question", form.errors)

    def test_seki_anfordern_creates_unique_tokens_for_multiple_secretariats(self):
        self.client.login(username=self.user.email, password=self.password)
        antrag = self._create_antrag()
        Lehrer.objects.create(email="seki1@afra.lernsax.de", name="Seki 1", secretariat=True)
        Lehrer.objects.create(email="seki2@afra.lernsax.de", name="Seki 2", secretariat=True)

        response = self.client.post(reverse("seki_anfordern"), {"antrag_id": antrag.id})
        self.assertEqual(response.status_code, 302)

        seki_requests = Anfrage.objects.filter(antrag=antrag, trigger=True)
        self.assertEqual(seki_requests.count(), 2)
        self.assertEqual(seki_requests.values_list("token", flat=True).distinct().count(), 2)

    def test_teacher_approval_creates_unique_secretariat_requests(self):
        antrag = self._create_antrag()
        token = "teacher-token"
        Anfrage.objects.create(
            antrag=antrag,
            email="lehrer@afra.lernsax.de",
            token=token,
            unterricht="MA,2026-03-20, 1. DS;\n",
        )
        Lehrer.objects.create(email="seki1@afra.lernsax.de", name="Seki 1", secretariat=True)
        Lehrer.objects.create(email="seki2@afra.lernsax.de", name="Seki 2", secretariat=True)

        response = self.client.post(
            reverse("antrag_bestaetigen", kwargs={"token": sign_existing_raw_token(token)}),
            {"btn": "bestaetigung", "answer": "annehmen"},
        )
        self.assertEqual(response.status_code, 200)

        seki_requests = Anfrage.objects.filter(antrag=antrag, email__startswith="seki")
        self.assertEqual(seki_requests.count(), 2)
        self.assertEqual(seki_requests.values_list("token", flat=True).distinct().count(), 2)

    def test_trigger_path_marks_request_as_accepted_and_creates_principal_request(self):
        antrag = self._create_antrag()
        secretariat = Lehrer.objects.create(
            email="seki@afra.lernsax.de",
            name="Sekretariat",
            secretariat=True,
        )
        Lehrer.objects.create(
            email="schulleitung@afra.lernsax.de",
            name="Schulleitung",
            principal=True,
        )
        anfrage = Anfrage.objects.create(
            antrag=antrag,
            email=secretariat.email,
            token="trigger-token",
            trigger=True,
        )

        response = self.client.post(
            reverse("antrag_bestaetigen", kwargs={"token": sign_existing_raw_token(anfrage.token)}),
            {"btn": "eltern2", "agree": "on"},
        )
        self.assertEqual(response.status_code, 200)

        anfrage.refresh_from_db()
        antrag.refresh_from_db()
        self.assertEqual(anfrage.response, Anfrage.ACCEPTED)
        self.assertTrue(antrag.eltern_notwendig)
        self.assertTrue(antrag.eltern_bestaetigung)
        self.assertTrue(Anfrage.objects.filter(antrag=antrag, is_principle=True).exists())

    def test_secondary_secretariat_account_can_open_secretariat_page(self):
        antrag = self._create_antrag()
        Lehrer.objects.create(email="seki1@afra.lernsax.de", name="Seki 1", secretariat=True)
        second = Lehrer.objects.create(email="seki2@afra.lernsax.de", name="Seki 2", secretariat=True)
        anfrage = Anfrage.objects.create(
            antrag=antrag,
            email=second.email,
            token="seki-second-token",
            unterricht="MA,2026-03-20, 1. DS;\n",
        )

        response = self.client.get(
            reverse("antrag_bestaetigen", kwargs={"token": sign_existing_raw_token(anfrage.token)})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ist eine Elternbestätigung notwendig?")

    @override_settings(ANFRAGE_TOKEN_MAX_AGE_SECONDS=0)
    def test_expired_signed_token_is_rejected(self):
        antrag = self._create_antrag()
        anfrage = Anfrage.objects.create(
            antrag=antrag,
            email="lehrer@afra.lernsax.de",
            token="expiring-token",
        )

        response = self.client.get(
            reverse("antrag_bestaetigen", kwargs={"token": sign_existing_raw_token(anfrage.token)})
        )
        self.assertEqual(response.status_code, 404)

    def test_antrag_detail_handles_missing_gm_im_and_teacher_records(self):
        self.client.login(username=self.user.email, password=self.password)
        antrag = self._create_antrag()
        Anfrage.objects.create(
            antrag=antrag,
            email="unbekannt@afra.lernsax.de",
            token="unknown-teacher-token",
            unterricht="UNBEKANNT,2026-03-20, 1. DS;\n",
        )

        response = self.client.get(reverse("antrag_detail", kwargs={"antrag_id": antrag.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Freistellung")

    def test_seki_anfordern_rejects_get(self):
        self.client.login(username=self.user.email, password=self.password)
        response = self.client.get(reverse("seki_anfordern"))
        self.assertEqual(response.status_code, 405)

    def test_seki_anfordern_forbidden_for_non_owner(self):
        owner = self.user
        other = User.objects.create_user(
            username="other@afra.lernsax.de",
            email="other@afra.lernsax.de",
            password=self.password,
        )
        antrag = self._create_antrag(user=owner)
        self.client.login(username=other.email, password=self.password)

        response = self.client.post(reverse("seki_anfordern"), {"antrag_id": antrag.id})
        self.assertEqual(response.status_code, 403)
