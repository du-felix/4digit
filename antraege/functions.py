from django.core.mail import send_mail
from django.conf import settings
from .models import Anfrage
import uuid
from django.urls import reverse

def send_email(email, vorname, nachname, schueler, unterricht, token_url):
    subject = "Neuer Freistellungsantrag"
    body = f"""Hallo {vorname.capitalize()} {nachname.capitalize()},\nIhr Schüler {schueler} hat einen Antrag gestellt. Folgende Stunden sind davon betroffen:\n
    {unterricht}
        \nBitte bearbeiten Sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten:\n{token_url}\nVielen Dank! BITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = [email]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def send_email_gm(email, vorname, nachname, schueler, token_url):
    subject = "Neuer Freistellungsantrag"
    body = f"""Hallo {vorname.capitalize()} {nachname.capitalize()},\nIhr Mentee {schueler} hat einen Antrag gestellt.
        \nBitte bearbeiten Sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten:\n{token_url}\nVielen Dank! BITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = [email]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def send_email_im(email, vorname, nachname, schueler, token_url):
    subject = "Neuer Freistellungsantrag"
    body = f"""Hallo {vorname.capitalize()} {nachname.capitalize()},\nIhr Mentee {schueler} hat einen Antrag gestellt.
        \nBitte bearbeiten Sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten:\n{token_url}\n\nVielen Dank! BITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = [email]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def send_email_schulleiter(schueler, token_url):
    subject = "Neuer Freistellungsantrag"
    body = f"""Hallo Stefan Weih,\nder Schüler {schueler} hat einen Antrag gestellt.
        \nBitte bearbeiten Sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten:\n{token_url}\n\nVielen Dank! BITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = ["stefan.weih@afra.lernsax.de"]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)
