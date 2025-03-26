from django.core.mail import send_mail
from django.conf import settings
from .models import Anfrage
import uuid
from django.urls import reverse

def send_email(email, vorname, schueler, unterricht,token_url):
    subject = "Neuer Freistellungsantrag"
    body = f"""Hallo {vorname},\n ihr Schüler {schueler} hat einen Antrag gestellt. Folgende Stunden sind davon betroffen:\n\n
    {unterricht}
        \n\n Bitte bearbeiten sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten: {token_url}\n\n Vielen Dank! BITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = [email]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def send_email_gm(email, vorname, schueler, token_url):
    subject = "Neuer Freistellungsantrag"
    body = f"""Hallo {vorname},\n ihr Mentee {schueler} hat einen Antrag gestellt.
        \n\n Bitte bearbeiten sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten: {token_url}\n\n Vielen Dank! BITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = [email]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def send_email_schulleiter(schueler, token_url):
    subject = "Neuer Freistellungsantrag"
    body = f"""Hallo Stefan,\n der Schüler {schueler} hat einen Antrag gestellt.
        \n\n Bitte bearbeiten sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten: {token_url}\n\n Vielen Dank! BITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = ["stefan.weih@afra.lernsax.de"]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)
