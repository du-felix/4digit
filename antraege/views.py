import uuid
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import AntragForm, UnterrichtFormSet, TwoStepForm, YesNoForm
from .models import Anfrage, Antrag, Zaehler, Lehrer, Fach, AntragSubmission
from .functions import convert_date, convert_time, send_email, send_email_schulleiter, send_email_gm, send_email_im, send_email_sekretariat, send_eltern_bestaetigung, schueler_benachrichtigung_eltern, schueler_benachrichtigung_antrag, schueler_benachrichtigung_seki
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.core import signing
from django.utils.timezone import now
from django.http import HttpResponse
from datetime import timedelta
from datetime import datetime, time as dtime

# Create your views here.
def validate_afra_email(email):
    if not email.endswith('@afra.lernsax.de'):
        raise ValidationError('Nur E-Mail-Adressen, die mit "@afra.lernsax.de" enden, sind zulässig.')
    return email

@login_required(login_url="login")
def home(request):
    antraege = Antrag.objects.filter(user=request.user).order_by('-erstellt_am')

    context = {
        'antraege': antraege
    }
    return render(request, "antraege/home.html", context)

@login_required(login_url="login")
def neuer_antrag(request):
    if request.method == "POST":
        formset = UnterrichtFormSet(request.POST)
        antrag = AntragForm(request.POST)

        if antrag.is_valid() and formset.is_valid():
            # ---- Antrag-Zeitraum aus Formular holen ----
            anfangsdatum = antrag.cleaned_data.get("anfangsdatum")
            enddatum = antrag.cleaned_data.get("enddatum")
            anfangszeit = antrag.cleaned_data.get("anfangszeit")
            endzeit = antrag.cleaned_data.get("endzeit")

            def to_date(v):
                if v is None:
                    return None
                if hasattr(v, "date"):
                    return v.date()
                return v

            def to_time(v):
                if v is None:
                    return None
                if hasattr(v, "time"):
                    return v.time()
                return v

            anfangsdatum_date = to_date(anfangsdatum)
            enddatum_date = to_date(enddatum)
            anfangszeit_val = to_time(anfangszeit)
            endzeit_val = to_time(endzeit)

            # Falls Zeiten nicht angegeben wurden → Default setzen
            if anfangszeit_val is None:
                anfangszeit_val = dtime(0, 0)
            if endzeit_val is None:
                endzeit_val = dtime(23, 59)

            start_dt = end_dt = None
            if anfangsdatum_date and enddatum_date:
                start_dt = datetime.combine(anfangsdatum_date, anfangszeit_val)
                end_dt = datetime.combine(enddatum_date, endzeit_val)

            # ---- Prüfung jeder Unterrichtsstunde (Datum+Zeit im Zeitraum?) ----
            for form in formset:
                if not form.cleaned_data:
                    continue

                u_datum = to_date(form.cleaned_data.get("datum"))

                # Beginn prüfen
                if u_datum and start_dt and end_dt:

                    if not (anfangsdatum_date <= u_datum <= enddatum_date):
                        messages.error(
                            request,
                            "Beginn des Unterrichts liegt außerhalb des Antragszeitraums."
                        )
                        return render(request, "antraege/neuer_antrag.html", {
                            "antrag": antrag,
                            "unterricht_formset": formset
                        })

            # ---- 5-Tage-Frist prüfen ----
            today = timezone.now().date()
            # anfangsdatum_date ist ein date-Objekt
            min_submission_date = anfangsdatum_date - timezone.timedelta(days=5)

            if today > min_submission_date:
                messages.error(
                    request,
                    "Anträge müssen mindestens 5 Tage vor dem Anfangsdatum erstellt werden."
                )
                return render(request, "antraege/neuer_antrag.html", {
                    "antrag": antrag,
                    "unterricht_formset": formset
                })

            # ---- Antrag speichern ----
            antrag_instance = antrag.save(commit=False)
            antrag_instance.user = request.user
            antrag_instance.save()
            gm = antrag.cleaned_data.get("gm")
            im = antrag.cleaned_data.get("im")

            # ---- Unterricht/E-Mails vorbereiten ----
            lehrer_dict = {}
            for form in formset:
                if form.cleaned_data:  # Check if form has data
                    lehrer_id = form.cleaned_data.get("lehrer")
                    fach_id = form.cleaned_data.get("fach")
                    datum = form.cleaned_data.get("datum")
                    ds_zeit = form.cleaned_data.get("ds_zeit")
                    if lehrer_id not in lehrer_dict:
                        lehrer_dict[lehrer_id] = []

                    zaehler, _ = Zaehler.objects.get_or_create(
                        schueler=request.user,
                        lehrer=lehrer_id,
                        fach=fach_id
                    )
                    zaehler.temp += 1
                    zaehler.save()

                    lehrer_dict[lehrer_id].append({
                        "fach": fach_id.kuerzel,
                        "datum": datum,
                        "ds_zeitraum": ds_zeit
                    })


            # Process each teacher's entries
            for lehrer, unterricht_list in lehrer_dict.items():
                # Create formatted string for email
                unterricht_text = ""
                for entry in unterricht_list:
                    unterricht_text += f"{entry['fach']},{entry['datum']}, {entry["ds_zeitraum"]};\n"

                token = str(uuid.uuid4())
                relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
                absolute_url = request.build_absolute_uri(relative_url)
                absolute_url = absolute_url[:4] + "s" + absolute_url[4:]

                Anfrage.objects.create(
                    antrag=antrag_instance,
                    email=lehrer.email,
                    token=token,
                    unterricht=unterricht_text,
                    ds_zeitraum=entry['ds_zeitraum'],
                )

                send_email(
                    lehrer.email,
                    lehrer.name,
                    request.user.first_name + " " + request.user.last_name,
                    unterricht_text,
                    absolute_url
                )

            # GM
            try:
                token = str(uuid.uuid4())
                relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
                absolute_url = request.build_absolute_uri(relative_url)
                absolute_url = absolute_url[:4] + "s" + absolute_url[4:]

                Anfrage.objects.create(
                    antrag=antrag_instance,
                    email=gm.email,
                    token=token,
                    gm=gm.email,
                    gm_boolean=True,
                    unterricht=unterricht_text
                )
                send_email_gm(
                    gm.email,
                    gm.name,
                    request.user.first_name + " " + request.user.last_name,
                    absolute_url
                )
            except Exception as e:
                print(f"Failed to send email to IM {im.email}: {str(e)}")
                messages.warning(
                    request,
                    f"Fehler beim Senden der E-Mail an GM ({gm.email})."
                )

            # IM
            token = str(uuid.uuid4())
            relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
            absolute_url = request.build_absolute_uri(relative_url)
            absolute_url = absolute_url[:4] + "s" + absolute_url[4:]

            Anfrage.objects.create(
                antrag=antrag_instance,
                email=im.email,
                token=token,
                im=im.email,
                im_boolean=True,
                unterricht=unterricht_text
            )
            send_email_im(
                im.email,
                im.name,
                request.user.first_name + " " + request.user.last_name,
                absolute_url
            )

            return redirect("home")

        else:
            # ------- Detaillierte Fehlermeldungen bei ungültigen Formularen -------
            if not antrag.is_valid():
                for field, errors in antrag.errors.items():
                    field_name = antrag.fields[field].label or field
                    for error in errors:
                        messages.error(request, f"Fehler im Feld '{field_name}': {error}")

            if not formset.is_valid():
                # Prüfe auf Formset-Fehler
                for i, form in enumerate(formset):
                    if form.errors:
                        messages.error(request, f"Fehler im Unterrichtsformular #{i+1}")
                        for field, errors in form.errors.items():
                            field_name = form.fields[field].label or field
                            for error in errors:
                                messages.error(request, f"- Feld '{field_name}': {error}")

                # Prüfe auf Fehler im gesamten Formset
                if formset.non_form_errors():
                    for error in formset.non_form_errors():
                        messages.error(request, f"Formularfehler: {error}")

            # Allgemeine Fehlermeldung, falls keine spezifische gefunden wurde
            if not any(m.level == messages.ERROR for m in messages.get_messages(request)):
                messages.error(request, "Es ist ein Fehler aufgetreten. Bitte überprüfen Sie Ihre Eingaben.")

            return render(request, "antraege/neuer_antrag.html", {
                "antrag": antrag,
                "unterricht_formset": formset
            })

    else:
        # GET: leere Formulare anzeigen
        antrag = AntragForm()
        unterricht_formset = UnterrichtFormSet()
        return render(request, "antraege/neuer_antrag.html", {
            "antrag": antrag,
            "unterricht_formset": unterricht_formset,
        })

@login_required(login_url="login")
def user_antraege(request):
    return render(request, "antraege/user_antraege.html")

def antrag_bestaetigen(request, token):
    anfrage = Anfrage.objects.get(token=token)
    antrag = anfrage.antrag

    def _create_schulleiter(antrag):
        context["sekretariat"] = False
        token = str(uuid.uuid4())
        relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
        Anfrage.objects.create(antrag=antrag, email=Lehrer.objects.filter(principal=True).values_list('email', flat=True).first(), token=token, is_principle=True)
        absolute_url = request.build_absolute_uri(relative_url)
        absolute_url = absolute_url[:4] + "s" + absolute_url[4:]
        send_email_schulleiter(antrag.user.first_name + " " + antrag.user.last_name, absolute_url)

    # Create the initial context
    context = {
        "token": token,
        "antragsteller": antrag.user.first_name + " " + antrag.user.last_name,
        "titel": antrag.titel,
        "schueler_grund": antrag.grund, 
        "unterricht": anfrage.unterricht,
        "schulleiter": anfrage.is_principle,
        "antrag": antrag,
        "fehlzeiten": Zaehler.objects.filter(schueler=antrag.user).aggregate(Sum("zaehler"))["zaehler__sum"] or 0,

    }
    
    # If already responded, redirect with message
    if anfrage.response != Anfrage.NOT_RESPONDED and request.method == "GET":
        return HttpResponse("Anfrage bereits bearbeitet.", status=403)
    
    # Add teacher confirmations to context if principal view
    if anfrage.is_principle:
        bestaetigungen = Anfrage.objects.filter(antrag=antrag, is_principle=False)
        filtered_bestaetigungen = [a for a in bestaetigungen if not a.email in Lehrer.objects.filter(secretariat=True).values_list('email', flat=True)]

        bestaetigungen_with_function = []
        for bestaetigung in filtered_bestaetigungen:
            # Determine the name with function
            if bestaetigung.gm:
                try:
                    lehrer = Lehrer.objects.get(email=bestaetigung.email)
                    name_with_function = f"{lehrer.name} (GM)"
                except Lehrer.DoesNotExist:
                    name_with_function = f"{bestaetigung.name} (GM)"
            elif bestaetigung.im:
                try:
                    lehrer = Lehrer.objects.get(email=bestaetigung.email)
                    name_with_function = f"{lehrer.name} (IM)"
                except Lehrer.DoesNotExist:
                    name_with_function = f"{bestaetigung.name} (IM)"
            else:
                # Regular teacher
                try:
                    lehrer = Lehrer.objects.get(email=bestaetigung.email)
                    name_with_function = lehrer.name
                except Lehrer.DoesNotExist:
                    name_with_function = bestaetigung.name
            
            # Create a structured object for the template
            bestaetigungen_with_function.append({
                'name': name_with_function,
                'response': bestaetigung.response,
                'reason': bestaetigung.reason
            })
        
        context["bestaetigungen"] = bestaetigungen_with_function
        context["fehlzeiten"] = Zaehler.objects.filter(schueler=antrag.user).aggregate(Sum("zaehler"))["zaehler__sum"] or 0
    
    # Handle form submission
    if request.method == "POST" and request.POST.get("btn") == "bestaetigung":

        answer = request.POST.get("answer")
        
        # Principal handling
        if anfrage.is_principle:
            if answer == "annehmen":
                anfrage.response = Anfrage.ACCEPTED
                anfrage.responded_at = timezone.now()
                anfrage.save()
                antrag.status = 'accepted'
                antrag.save()
                bestaetigungen = Anfrage.objects.filter(
                    antrag=antrag,
                    is_principle=False,
                    gm__isnull=True,
                    im__isnull=True,
                )

                sekretariat_emails = set(
                    Lehrer.objects.filter(secretariat=True).values_list('email', flat=True)
                )

                for bestaetigung in bestaetigungen:
                    # Sekretariat explizit überspringen
                    if bestaetigung.email in sekretariat_emails:
                        continue

                    stunden = bestaetigung.unterricht.strip("\n").split(";")[:-1]
                    lehrer = Lehrer.objects.get(email=bestaetigung.email)
                    for stunde in stunden:
                        kuerzel = stunde.split(",")[0].strip().upper()
                        fach = Fach.objects.get(kuerzel=kuerzel)

                        obj = Zaehler.objects.get(
                            schueler=antrag.user,
                            lehrer=lehrer,
                            fach=fach,
                        )
                        obj.zaehler += obj.temp
                        obj.temp = 0
                        obj.save()
                seki_mails = Lehrer.objects.filter(secretariat=True).values_list('email', flat=True)
                for email in seki_mails:
                    send_email_sekretariat(
                        antrag.user.first_name + " " + antrag.user.last_name, 
                        antrag.klasse,
                        antrag.titel,
                        antrag.grund,
                        email,
                        antrag
                        )
                schueler_benachrichtigung_antrag(antrag, True)
                return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
            elif answer == "ablehnen":
                grund = request.POST.get("grund", '')
                bestaetigungen = Anfrage.objects.filter(antrag=antrag, is_principle=False)
                for bestaetigung in bestaetigungen:
                    stunden = bestaetigung.unterricht.strip("\n").split(";")[:-1]
                    for stunde in stunden:
                        obj = Zaehler.objects.get(
                            schueler=antrag.user,
                            lehrer=Lehrer.objects.get(email=bestaetigung.email),
                            fach=Fach.objects.get(kuerzel=stunde.split(",")[0].upper())
                        )
                        obj.temp = 0
                        obj.save()
                anfrage.response = Anfrage.DECLINED
                anfrage.responded_at = timezone.now()
                anfrage.reason = grund
                anfrage.save()
                antrag.status = 'declined'
                antrag.save()
                schueler_benachrichtigung_antrag(antrag, False)
                return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
            else:
                messages.error(request, "Kein Feld ausgewählt")
        
        # Teacher handling        
        elif anfrage.response == Anfrage.NOT_RESPONDED:
            if answer == "annehmen":
                anfrage.response = Anfrage.ACCEPTED
                anfrage.responded_at = timezone.now()
                anfrage.save()
                
                # Check if all responses received to notify principal
                mail_bool = True
                anfragen = Anfrage.objects.filter(antrag=antrag)
                for af in anfragen:
                    if af.response == Anfrage.NOT_RESPONDED:
                        mail_bool = False
                        break
                
                if mail_bool:
                    token = str(uuid.uuid4())
                    relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
                    absolute_url = request.build_absolute_uri(relative_url)
                    absolute_url = absolute_url[:4] + "s" + absolute_url[4:]
                    seki_mails = Lehrer.objects.filter(secretariat=True).values_list('email', flat=True)
                    for email in seki_mails:
                        Anfrage.objects.create(
                            antrag=antrag,
                            email=email,
                            token=token
                        )
                        send_eltern_bestaetigung(
                            antrag.user.first_name + " " + antrag.user.last_name,
                            absolute_url,
                            antrag.klasse,
                            antrag.titel,
                            email
                        )  

                return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
                
            elif answer == "ablehnen":
                grund = request.POST.get("grund", '')
                anfrage.response = Anfrage.DECLINED
                anfrage.responded_at = timezone.now()
                anfrage.reason = grund
                anfrage.save()
                
                # Check if all responses received to notify principal
                mail_bool = True
                anfragen = Anfrage.objects.filter(antrag=antrag)
                for af in anfragen:
                    if af.response == Anfrage.NOT_RESPONDED:
                        mail_bool = False
                        break
                
                if mail_bool and antrag.eltern_bestaetigung:
                    _create_schulleiter(antrag)
                elif mail_bool:
                    token = str(uuid.uuid4())
                    relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
                    absolute_url = request.build_absolute_uri(relative_url)
                    absolute_url = absolute_url[:4] + "s" + absolute_url[4:]
                    seki_mails = Lehrer.objects.filter(secretariat=True).values_list('email', flat=True)
                    for email in seki_mails:
                        Anfrage.objects.create(
                            antrag=antrag,
                            email=email,
                            token=token
                        )
                        send_eltern_bestaetigung(
                            antrag.user.first_name + " " + antrag.user.last_name,
                            absolute_url,
                            antrag.klasse,
                            antrag.titel,
                            email
                        )  


                return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
            else:
                messages.error(request, "Kein Feld ausgewählt")
        else:
            messages.error(request, "Anfrage bereits bearbeitet")
            return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
    elif request.method == "POST" and request.POST.get("btn") == "eltern":
        anfragen = Anfrage.objects.filter(token=token)
        form = TwoStepForm(request.POST)
        print(Anfrage.objects.filter(token=token).first().response)
        if Anfrage.objects.filter(token=token).first().response != Anfrage.NOT_RESPONDED:
            return HttpResponse("Anfrage bereits bearbeitet", status=403)
        if form.is_valid():
            first = form.cleaned_data.get("first_question")
            second = form.cleaned_data.get("second_question")
            if first == "ja":
                antrag.eltern_notwendig = True
                if second == "ja":
                    antrag.eltern_bestaetigung = True
                    _create_schulleiter(antrag)
                    schueler_benachrichtigung_seki(antrag)
                else:
                    antrag.eltern_bestaetigung = False
                    schueler_benachrichtigung_eltern(antrag)
            else:
                antrag.eltern_notwendig = False
                _create_schulleiter(antrag)
                schueler_benachrichtigung_seki(antrag)
            antrag.save()
            for anfrage in anfragen:
                anfrage.response = Anfrage.ACCEPTED
                anfrage.save()
            return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
        else:
            return HttpResponse("Felder wurden nicht ausgefüllt", status=400)

    elif request.method == "POST" and request.POST.get("btn") == "eltern2":
        form = YesNoForm(request.POST)
        anfragen = Anfrage.objects.filter(token=token)
        form = TwoStepForm(request.POST)
        if Anfrage.objects.filter(token=token).first().response != Anfrage.NOT_RESPONDED:
            return HttpResponse("Anfrage bereits bearbeitet", status=403)
        if form.is_valid():
            answer = form.cleaned_data.get("agree")
            if answer:
                antrag.eltern_bestaetigung = True
                _create_schulleiter(antrag)
                schueler_benachrichtigung_seki(antrag)
                antrag.save()
                for anfrage in anfragen:
                    anfrage.response = Anfrage.ACCEPTED
                return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
            else:
                antrag.eltern_bestaetigung = False
                schueler_benachrichtigung_eltern(antrag)
                antrag.save()
                for anfrage in anfragen:
                    anfrage.response = Anfrage.ACCEPTED
                return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
        else:
            return HttpResponse("Felder wurden nicht ausgefüllt", status=400)
        # Always render the template with complete context at the end
    if anfrage.email == Lehrer.objects.filter(secretariat=True).values_list('email', flat=True).first():
        context["sekretariat"] = True
        context["form"] = TwoStepForm()
        context["anfangsdatum"] = convert_date(str(antrag.anfangsdatum))
        context["anfangszeit"]  = convert_time(str(antrag.anfangszeit))
        context["enddatum"]     = convert_date(str(antrag.enddatum))
        context["endzeit"]      = convert_time(str(antrag.endzeit))
    return render(request, "antraege/antrag_bearbeiten.html", context)

@login_required
def antrag_detail(request, antrag_id):
    # Hole den spezifischen Antrag oder werfe 404
    antrag = get_object_or_404(Antrag, id=antrag_id, user=request.user)
    
    # Hole alle Anfragen für diesen Antrag
    anfragen = Anfrage.objects.filter(antrag=antrag)

    secretariat_emails = Lehrer.objects.filter(secretariat=True).values_list('email', flat=True)
    anfragen_non_secretariat = anfragen.exclude(email__in=secretariat_emails)
    
    # Bestimme den Gesamtstatus der Anfragen
    anfragen_status = {
        'total': anfragen_non_secretariat.count(),
        'accepted': anfragen_non_secretariat.filter(response=Anfrage.ACCEPTED).count(),
        'declined': anfragen_non_secretariat.filter(response=Anfrage.DECLINED).count(),
        'not_responded': anfragen_non_secretariat.filter(response=Anfrage.NOT_RESPONDED).count()
    }
    
    unterricht = []
    daten = []
    lehrer = []
    responses = []
    gruende = []

    for anfrage in anfragen:
        print(anfrage.response)
        if anfrage.gm:  # Wenn es ein GM ist
            gm = anfrage.email
            gm = Lehrer.objects.get(email=gm).name
            gm_response = anfrage.response
            gm_grund = anfrage.reason
        elif anfrage.im:  # Wenn es ein IM ist
            im = anfrage.email
            im = Lehrer.objects.get(email=im).name
            im_response = anfrage.response
            im_grund = anfrage.reason
        elif anfrage.is_principle: 
     # Wenn es ein Schulleiter ist
            schulleiter = Lehrer.objects.filter(principal=True).values_list('name', flat=True).first()
            schulleiter_datum = anfrage.created
            schulleiter_response = anfrage.response
            schulleiter_grund = anfrage.reason
        else:
            stunden = anfrage.unterricht.strip("\n").split(";")[:-1]
            for stunde in stunden:
                elements = stunde.strip("\n").split(",")
                daten.append(transform_date(elements[1]))
                print(elements)
                unterricht.append(Fach.objects.get(kuerzel=elements[0]).name)
                lehrer.append(Lehrer.objects.get(email=anfrage.email).name)
                gruende.append(anfrage.reason)
                responses.append(anfrage.response)
    lehrer.append(im)
    lehrer.append(gm)
    daten.append(" ")
    daten.append(" ")
    unterricht.append("IM")
    unterricht.append("GM")
    responses.append(im_response)
    responses.append(gm_response)
    gruende.append(im_grund)
    gruende.append(gm_grund)
    try:
        lehrer.append(schulleiter)
        responses.append(schulleiter_response)
        gruende.append(schulleiter_grund)
        daten.append(transform_datetime(schulleiter_datum))
        unterricht.append("Schulleiter")
    except Exception as e:
        pass

    rows = zip(lehrer, unterricht, daten, responses, gruende)

    context = {
        'antrag': antrag,
        'anfragen': anfragen,
        'anfragen_status': anfragen_status,
        "rows": rows
    }
    if not antrag.eltern_bestaetigung and antrag.eltern_notwendig:
        context["eltern"] = True
    return render(request, 'antraege/antrag.html', context)

def transform_date(date):
    elements = date.strip("\n").split("-")
    return elements[2] + "." + elements[1] + "." + elements[0]
def transform_datetime(datetime):
    elements = str(datetime).split(" ")
    date = elements[0]
    time = elements[1]
    date_elements = date.strip("\n").split("-")
    return date_elements[2] + "." + date_elements[1] + "." + date_elements[0]

def seki_anfordern(request):

    antrag_id = request.POST.get('antrag_id')
    antrag = Antrag.objects.get(id=antrag_id)

    one_hour_ago = now() - timedelta(hours=1)

    # Check if this user submitted this Antrag in the last hour
    recent_submission = AntragSubmission.objects.filter(
        user=request.user,
        antrag=antrag,
        submitted_at__gte=one_hour_ago
    ).exists()

    if recent_submission:
        messages.error(request, "Du kannst dieses Formular nur einmal pro Stunde absenden.")
        return HttpResponse("Du kannst nur einmal pro Stunde eine neue Prüfung anfordern", status=403)
    
    AntragSubmission.objects.create(user=request.user, antrag=antrag)
    # Create a token with embedded antrag ID
    token_data = {"anfordern": True}
    token = signing.dumps(token_data)

    relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
    absolute_url = request.build_absolute_uri(relative_url)
    absolute_url = absolute_url[:4] + "s" + absolute_url[4:]
 
    seki_mails = Lehrer.objects.filter(secretariat=True).values_list('email', flat=True)
    for email in seki_mails:
        Anfrage.objects.create(
            antrag=antrag,
            email=email,
            token=token,
            trigger=True
        )
        send_eltern_bestaetigung(
            antrag.user.first_name + " " + antrag.user.last_name,
            absolute_url,
            antrag.klasse,
            antrag.titel,
            email
        )  
    return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
