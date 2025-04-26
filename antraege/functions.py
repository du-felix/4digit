from django.core.mail import send_mail
from django.conf import settings
from .models import Anfrage, Lehrer
import uuid
from django.urls import reverse

def send_email(email, vorname, nachname, schueler, unterricht, token_url):
    subject = f"Neuer Freistellungsantrag von {schueler}"
    body = f"""Guten Tag {vorname.capitalize()} {nachname.capitalize()},\n Ihr Schüler {schueler} hat einen Antrag auf Freistellung gestellt. Folgende Stunden sind davon betroffen:\n\n
    {unterricht}
        \n\n Bitte bearbeiten Sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten:\n{token_url}\n\nVielen Dank!
        \nBITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = [email]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def send_email_gm(email, vorname, nachname, schueler, token_url):
    subject = f"Neuer Freistellungsantrag von {schueler}"
    body = f"""Guten Tag {vorname.capitalize()} {nachname.capitalize()},\n Ihr Mentee {schueler} hat einen Antrag auf Freistellung gestellt.
        \n\n Bitte bearbeiten Sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten:\n\n{token_url}\n\nVielen Dank!
        \nBITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = [email]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def send_email_im(email, vorname, nachname, schueler, token_url):
    subject = f"Neuer Freistellungsantrag von {schueler}"
    body = f"""Guten Tag {vorname.capitalize()} {nachname.capitalize()},\n Ihr Mentee {schueler} hat einen Antrag auf Freistellung gestellt.
        \n\n Bitte bearbeiten Sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten:\n\n{token_url}\n\nVielen Dank!
        \nBITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = [email]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def send_email_schulleiter(schueler, token_url):
    subject = f"Neuer Freistellungsantrag von {schueler}"
    body = f"""Guten Tag {Lehrer.objects.filter(principal=True).values_list('name', flat=True).first()},\n der Schüler / die Schülerin {schueler} hat einen Antrag auf Freistellung gestellt.
        \n\n Bitte bearbeiten Sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten:\n\n{token_url}\n\nVielen Dank!
        \nBITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = [Lehrer.objects.filter(principal=True).values_list('email', flat=True).first()]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def send_email_sekretariat(schueler, klasse, titel, grund, antrag=None):
    from django.core.mail import send_mail
    from django.conf import settings
    from .models import Anfrage, Fach, Lehrer
    
    unterrichte_text = ""
    
    # Wenn ein Antrag übergeben wurde, Information über die Unterrichte sammeln
    if antrag:
        from .views import transform_date
        anfragen = Anfrage.objects.filter(antrag=antrag, is_principle=False, gm__isnull=True, im__isnull=True)
        unterrichte_info = []
        
        for anfrage in anfragen:
            stunden = anfrage.unterricht.strip("\n").split(";")[:-1]
            for stunde in stunden:
                if stunde:
                    elements = stunde.strip("\n").split(",")
                    fach = Fach.objects.get(kuerzel=elements[0].upper()).name
                    datum = transform_date(elements[1])
                    lehrer = Lehrer.objects.get(email=anfrage.email).name
                    unterrichte_info.append(f"{fach} ({datum}) bei {lehrer}")
        
        if unterrichte_info:
            unterrichte_text = "\n\nBetroffene Unterrichtsstunden:\n" + "\n".join(unterrichte_info)
    subject = f"Neuer Freistellungsantrag {titel} von {schueler}"
    body = f"""Guten Tag, der Schüler / die Schülerin {schueler} aus der Klasse {klasse} hat sich für folgende Schulstunden von der Schulleitung freistellen lassen:
    {unterrichte_text}
    \nGrund dafür ist: {grund}
    Vielen Dank!
    \nBITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!"""
    empfaenger = [Lehrer.objects.filter(secretariat=True).values_list('email', flat=True).first()]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)
