from django.core.mail import send_mail
from django.conf import settings
from .models import Anfrage

def send_email(email, vorname, schueler, unterricht,token_url):
    subject = "Neuer Freistellungsantrag"
    body = f"""Hallo {vorname},\n ihr Schüler {schueler} hat einen Antrag gestellt. Folgende Stunden sind davon betroffen:\n\n
    {unterricht}
        \n\n Bitte bearbeiten sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten: {token_url}\n\n Vielen Dank! BITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = [email]
    send_mail(subject, body, settings.DEFAULT_FROM_MAIL, empfaenger, fail_silently=False)

def send_email_gm(email, vorname, schueler, unterricht,token_url):
    subject = "Neuer Freistellungsantrag"
    body = f"""Hallo {vorname},\n ihr Mentee {schueler} hat einen Antrag gestellt. Folgende Stunden sind davon betroffen:\n\n
    {unterricht}
        \n\n Bitte bearbeiten sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten: {token_url}\n\n Vielen Dank! BITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = [email]
    send_mail(subject, body, settings.DEFAULT_FROM_MAIL, empfaenger, fail_silently=False)

def send_email_schulleiter(antrag, schueler, token_url) -> bool:
    mail_bool = True
    anfragen = Anfrage.objects.filter(antrag=antrag)
    for anfrage in anfragen:
        if anfrage.response == anfrage.NOT_RESPONDED:
            mail_bool = False
            break
    if mail_bool:
        subject = "Neuer Freistellungsantrag"
        body = f"""Hallo Stefan,\n ihr Mentee {schueler} hat einen Antrag gestellt.
            \n\n Bitte bearbeiten sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten: {token_url}\n\n Vielen Dank! BITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
        """
        empfaenger = ["schulleiter@afra.lernsax.de"]
        send_mail(subject, body, settings.DEFAULT_FROM_MAIL, empfaenger, fail_silently=False)
        return mail_bool
    else:
        return mail_bool