from django.core.mail import send_mail
from django.conf import settings
from .models import Anfrage, Lehrer, Fach

def send_email(email, lehrer_name, schueler_name, unterricht, token_url):
    subject = f"Neuer Freistellungsantrag von {schueler_name}"
    body = f"""Guten Tag {lehrer_name},\n Ihr Schüler {schueler_name} hat einen Antrag auf Freistellung gestellt. Folgende Stunden sind davon betroffen:\n\n
    {unterricht}
        \n\n Bitte bearbeiten Sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten:\n{token_url}\n\nVielen Dank!
        \nBITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = [email]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def send_email_gm(email, gm_name, schueler_name, token_url):
    subject = f"Neuer Freistellungsantrag von {schueler_name}"
    body = f"""Guten Tag {gm_name},\n Ihr Mentee {schueler_name} hat einen Antrag auf Freistellung gestellt.
        \n\n Bitte bearbeiten Sie den Antrag in nächster Zeit. Über folgenden Link können Sie den Antrag bearbeiten:\n\n{token_url}\n\nVielen Dank!
        \nBITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!
    """
    empfaenger = [email]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def send_email_im(email, im_name, schueler_name, token_url):
    subject = f"Neuer Freistellungsantrag von {schueler_name}"
    body = f"""Guten Tag {im_name},\n Ihr Mentee {schueler_name} hat einen Antrag auf Freistellung gestellt.
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
    # Wenn ein Antrag übergeben wurde, Information über die Unterrichte sammeln
    if antrag:
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
    subject = f"Neuer Freistellungsantrag von {schueler}: {titel}"
    body = f"""Guten Tag, der Schüler / die Schülerin {schueler} aus der Klasse {klasse} hat sich für folgende Schulstunden von der Schulleitung freistellen lassen:
    {unterrichte_text}
    \nDer Grund dafür ist: {grund}
    Vielen Dank!
    \nBITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!"""
    empfaenger = [Lehrer.objects.filter(secretariat=True).values_list('email', flat=True).first()]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def send_eltern_bestaetigung(schueler, token_url, klasse, titel, grund):
    subject = f"Elternbestätigung prüfen von {schueler}: {titel}"
    body = f"""Hallo liebes Seki,\nder Schüler / die Schülerin {schueler} aus der Klasse {klasse} hat einen Freistellungsantrag gestellt.
   \n\nBitte prüft, ob eine Elternbestätigung vorliegen muss, und wenn, ob eine vorliegt.
    \n\n Hier der Link: {token_url}
    \n\nVielen Dank!\n\nBITTE ANTWORTEN SIE NICHT AUF DIESE MAIL!"""
    empfaenger = [Lehrer.objects.filter(principal=True).values_list('email', flat=True).first()]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def schueler_benachrichtigung_eltern(antrag):
    subject = f"Update für Freistellungsantrag: {antrag.titel}"
    body = f"""Hallo,\nfür dein Antrag ist eine Elternbestätigung notwendig. Bitte fordere deine Eltern auf, 
    eine Mail an das Sekretariat zu schreiben, um den Antrag zu bestätigen.\n\n Danke! LG FGH"""
    empfaenger = antrag.user.email
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def schueler_benachrichtigung_antrag(antrag, bool):
    if bool:
        subject = f"Dein Antrag: '{antrag.titel}' wurde genehmigt"
        body = f"""Hallo,\ndein Antrag wurde genehmigt. Viel Spaß bei was auch immer.\n\nLG FGH"""
        empfaenger = antrag.user.email
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)
    else:
        subject = f"Dein Antrag: '{antrag.titel}' wurde abgelehnt"
        body = f"""Hallo,\ndein Antrag wurde abgelehnt. Vielleicht klappt's das nächste Mal.\n\nLG FGH"""
        empfaenger = antrag.user.email
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def schueler_benachrichtigung_seki(antrag):
    subject = f"Dein Antrag: '{antrag.titel}' wurde an den Schulleiter übermittelt"
    body = f"""Hallo,\ndein Antrag wurde an den Schulleiter übermittelt. Hoffentlich wird's was!\n\nLG FGH"""
    empfaenger = antrag.user.email
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, empfaenger, fail_silently=False)

def transform_date(date):
    elements = date.strip("\n").split("-")
    return elements[2] + "." + elements[1] + "." + elements[0]
def transform_datetime(datetime):
    elements = str(datetime).split(" ")
    date = elements[0]
    time = elements[1]
    date_elements = date.strip("\n").split("-")
    return date_elements[2] + "." + date_elements[1] + "." + date_elements[0]