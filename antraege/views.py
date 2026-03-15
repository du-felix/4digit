from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .forms import AntragForm, UnterrichtFormSet, TwoStepForm, YesNoForm
from .models import Anfrage, Antrag, Zaehler, Lehrer, Fach, AntragSubmission
from .functions import convert_date, convert_time, send_email, send_email_schulleiter, send_email_gm, send_email_im, send_email_sekretariat, send_eltern_bestaetigung, schueler_benachrichtigung_eltern, schueler_benachrichtigung_antrag, schueler_benachrichtigung_seki, transform_date, transform_datetime
from .tokens import make_token_pair, resolve_anfrage_from_public_token, TokenValidationError
from .workflow import (
    transition_anfrage,
    transition_antrag,
    ensure_pending,
    all_requests_responded,
    WorkflowTransitionError,
)
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from django.utils.timezone import now
from django.http import HttpResponse
from datetime import timedelta
from datetime import datetime, time as dtime
from django.views.decorators.http import require_POST

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

            def _build_absolute_url(public_token):
                relative_url = reverse("antrag_bestaetigen", kwargs={"token": public_token})
                absolute_url = request.build_absolute_uri(relative_url)
                if absolute_url.startswith("http://"):
                    absolute_url = "https://" + absolute_url[7:]
                return absolute_url

            with transaction.atomic():
                # ---- Antrag speichern ----
                antrag_instance = antrag.save(commit=False)
                antrag_instance.user = request.user
                antrag_instance.save()
                gm = antrag.cleaned_data.get("gm")
                im = antrag.cleaned_data.get("im")

                # ---- Unterricht/E-Mails vorbereiten ----
                lehrer_dict = {}
                for form in formset:
                    if form.cleaned_data:
                        lehrer_id = form.cleaned_data.get("lehrer")
                        fach_id = form.cleaned_data.get("fach")
                        datum = form.cleaned_data.get("datum")
                        ds_zeit = form.cleaned_data.get("ds_zeit")
                        if lehrer_id not in lehrer_dict:
                            lehrer_dict[lehrer_id] = []

                        zaehler, _ = Zaehler.objects.get_or_create(
                            schueler=request.user,
                            lehrer=lehrer_id,
                            fach=fach_id,
                        )
                        zaehler.temp += 1
                        zaehler.save(update_fields=["temp"])

                        lehrer_dict[lehrer_id].append(
                            {
                                "fach": fach_id.kuerzel,
                                "datum": datum,
                                "ds_zeitraum": ds_zeit,
                            }
                        )

                last_unterricht_text = ""
                for lehrer, unterricht_list in lehrer_dict.items():
                    unterricht_text = ""
                    for entry in unterricht_list:
                        unterricht_text += f"{entry['fach']},{entry['datum']}, {entry['ds_zeitraum']};\n"
                    last_unterricht_text = unterricht_text

                    raw_token, public_token = make_token_pair()
                    Anfrage.objects.create(
                        antrag=antrag_instance,
                        email=lehrer.email,
                        token=raw_token,
                        unterricht=unterricht_text,
                        ds_zeitraum=unterricht_list[-1]["ds_zeitraum"],
                    )
                    transaction.on_commit(
                        lambda lehrer_email=lehrer.email, lehrer_name=lehrer.name, unterricht=unterricht_text, public=public_token: send_email(
                            lehrer_email,
                            lehrer_name,
                            request.user.first_name + " " + request.user.last_name,
                            unterricht,
                            _build_absolute_url(public),
                            antrag_instance,
                        )
                    )

                try:
                    raw_token, public_token = make_token_pair()
                    Anfrage.objects.create(
                        antrag=antrag_instance,
                        email=gm.email,
                        token=raw_token,
                        gm=gm.email,
                        gm_boolean=True,
                        unterricht=last_unterricht_text,
                    )
                    transaction.on_commit(
                        lambda gm_email=gm.email, gm_name=gm.name, public=public_token: send_email_gm(
                            gm_email,
                            gm_name,
                            request.user.first_name + " " + request.user.last_name,
                            _build_absolute_url(public),
                            antrag_instance,
                        )
                    )
                except Exception:
                    messages.warning(request, f"Fehler beim Senden der E-Mail an GM ({gm.email}).")

                raw_token, public_token = make_token_pair()
                Anfrage.objects.create(
                    antrag=antrag_instance,
                    email=im.email,
                    token=raw_token,
                    im=im.email,
                    im_boolean=True,
                    unterricht=last_unterricht_text,
                )
                transaction.on_commit(
                    lambda im_email=im.email, im_name=im.name, public=public_token: send_email_im(
                        im_email,
                        im_name,
                        request.user.first_name + " " + request.user.last_name,
                        _build_absolute_url(public),
                        antrag_instance,
                    )
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
    return redirect("home")

def antrag_bestaetigen(request, token):
    try:
        anfrage = resolve_anfrage_from_public_token(token)
    except TokenValidationError:
        return HttpResponse("Ungültiger oder abgelaufener Link.", status=404)
    antrag = anfrage.antrag
    sekretariat_emails = set(Lehrer.objects.filter(secretariat=True).values_list('email', flat=True))

    def _build_absolute_url(public_token):
        relative_url = reverse('antrag_bestaetigen', kwargs={'token': public_token})
        absolute_url = request.build_absolute_uri(relative_url)
        if absolute_url.startswith("http://"):
            absolute_url = "https://" + absolute_url[7:]
        return absolute_url

    def _create_sekretariat_requests(trigger=False):
        for email in sekretariat_emails:
            raw_token, public_token = make_token_pair()
            Anfrage.objects.create(
                antrag=antrag,
                email=email,
                token=raw_token,
                trigger=trigger,
            )
            transaction.on_commit(
                lambda recipient=email, public=public_token: send_eltern_bestaetigung(
                    antrag.user.first_name + " " + antrag.user.last_name,
                    _build_absolute_url(public),
                    antrag.klasse,
                    antrag.titel,
                    recipient,
                )
            )

    def _create_schulleiter(antrag):
        context["sekretariat"] = False
        principal_email = Lehrer.objects.filter(principal=True).values_list('email', flat=True).first()
        if not principal_email:
            return
        raw_token, public_token = make_token_pair()
        Anfrage.objects.create(antrag=antrag, email=principal_email, token=raw_token, is_principle=True)
        transaction.on_commit(
            lambda public=public_token: send_email_schulleiter(
                antrag.user.first_name + " " + antrag.user.last_name,
                _build_absolute_url(public),
            )
        )

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
        "anfangsdatum": convert_date(str(antrag.anfangsdatum)),
        "anfangszeit": convert_time(str(antrag.anfangszeit)),
        "enddatum": convert_date(str(antrag.enddatum)),
        "endzeit": convert_time(str(antrag.endzeit)),
        "trigger": anfrage.trigger,

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
                try:
                    with transaction.atomic():
                        ensure_pending(anfrage)
                        transition_anfrage(anfrage, Anfrage.ACCEPTED)
                        transition_antrag(antrag, Antrag.STATUS_ACCEPTED)
                        bestaetigungen = Anfrage.objects.filter(
                            antrag=antrag,
                            is_principle=False,
                            gm__isnull=True,
                            im__isnull=True,
                        )

                        for bestaetigung in bestaetigungen:
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
                                obj.save(update_fields=["zaehler", "temp"])

                        for email in Lehrer.objects.filter(secretariat=True).values_list('email', flat=True):
                            transaction.on_commit(
                                lambda recipient=email: send_email_sekretariat(
                                    antrag.user.first_name + " " + antrag.user.last_name,
                                    antrag.klasse,
                                    antrag.titel,
                                    antrag.grund,
                                    recipient,
                                    antrag,
                                )
                            )
                        transaction.on_commit(lambda: schueler_benachrichtigung_antrag(antrag, True))
                except WorkflowTransitionError:
                    return HttpResponse("Anfrage bereits bearbeitet.", status=403)
                return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
            elif answer == "ablehnen":
                grund = request.POST.get("grund", '')
                try:
                    with transaction.atomic():
                        ensure_pending(anfrage)
                        bestaetigungen = Anfrage.objects.filter(antrag=antrag, is_principle=False)
                        for bestaetigung in bestaetigungen:
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
                                obj.temp = 0
                                obj.save(update_fields=["temp"])
                        transition_anfrage(anfrage, Anfrage.DECLINED, reason=grund)
                        transition_antrag(antrag, Antrag.STATUS_DECLINED)
                        transaction.on_commit(lambda: schueler_benachrichtigung_antrag(antrag, False))
                except WorkflowTransitionError:
                    return HttpResponse("Anfrage bereits bearbeitet.", status=403)
                return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
            else:
                messages.error(request, "Kein Feld ausgewählt")
        
        # Teacher handling        
        elif anfrage.response == Anfrage.NOT_RESPONDED:
            if answer == "annehmen":
                try:
                    with transaction.atomic():
                        ensure_pending(anfrage)
                        transition_anfrage(anfrage, Anfrage.ACCEPTED)
                        if all_requests_responded(antrag):
                            _create_sekretariat_requests(trigger=False)
                except WorkflowTransitionError:
                    return HttpResponse("Anfrage bereits bearbeitet.", status=403)

                return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
                
            elif answer == "ablehnen":
                grund = request.POST.get("grund", '')
                try:
                    with transaction.atomic():
                        ensure_pending(anfrage)
                        transition_anfrage(anfrage, Anfrage.DECLINED, reason=grund)
                        if all_requests_responded(antrag) and antrag.eltern_bestaetigung:
                            _create_schulleiter(antrag)
                        elif all_requests_responded(antrag):
                            _create_sekretariat_requests(trigger=False)
                except WorkflowTransitionError:
                    return HttpResponse("Anfrage bereits bearbeitet.", status=403)


                return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
            else:
                messages.error(request, "Kein Feld ausgewählt")
        else:
            messages.error(request, "Anfrage bereits bearbeitet")
            return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
    elif request.method == "POST" and request.POST.get("btn") == "eltern":
        anfragen = Anfrage.objects.filter(token=anfrage.token)
        form = TwoStepForm(request.POST)
        if anfragen.first().response != Anfrage.NOT_RESPONDED:
            return HttpResponse("Anfrage bereits bearbeitet", status=403)
        if form.is_valid():
            first = form.cleaned_data.get("first_question")
            second = form.cleaned_data.get("second_question")
            with transaction.atomic():
                if first == "ja":
                    antrag.eltern_notwendig = True
                    if second == "ja":
                        antrag.eltern_bestaetigung = True
                        _create_schulleiter(antrag)
                        transaction.on_commit(lambda: schueler_benachrichtigung_seki(antrag))
                    else:
                        antrag.eltern_bestaetigung = False
                        transaction.on_commit(lambda: schueler_benachrichtigung_eltern(antrag))
                else:
                    antrag.eltern_notwendig = False
                    _create_schulleiter(antrag)
                    transaction.on_commit(lambda: schueler_benachrichtigung_seki(antrag))
                antrag.save(update_fields=["eltern_notwendig", "eltern_bestaetigung"])
                for af in anfragen:
                    transition_anfrage(af, Anfrage.ACCEPTED)
            return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
        else:
            return HttpResponse("Felder wurden nicht ausgefüllt", status=400)

    elif request.method == "POST" and request.POST.get("btn") == "eltern2":
        form = YesNoForm(request.POST)
        anfragen = Anfrage.objects.filter(token=anfrage.token)
        if anfragen.first().response != Anfrage.NOT_RESPONDED:
            return HttpResponse("Anfrage bereits bearbeitet", status=403)
        if form.is_valid():
            answer = form.cleaned_data.get("agree")
            with transaction.atomic():
                antrag.eltern_notwendig = True
                if answer == "ja":
                    antrag.eltern_bestaetigung = True
                    _create_schulleiter(antrag)
                    transaction.on_commit(lambda: schueler_benachrichtigung_seki(antrag))
                else:
                    antrag.eltern_bestaetigung = False
                    transaction.on_commit(lambda: schueler_benachrichtigung_eltern(antrag))
                antrag.save(update_fields=["eltern_notwendig", "eltern_bestaetigung"])
                for af in anfragen:
                    transition_anfrage(af, Anfrage.ACCEPTED)
            return HttpResponse("Antrag erfolgreich bearbeitet. Sie können diesen Tab jetzt schließen, es kommt nämlich nix mehr...", status=200)
        else:
            return HttpResponse("Felder wurden nicht ausgefüllt", status=400)
        # Always render the template with complete context at the end
    if anfrage.email in sekretariat_emails and not anfrage.im_boolean and not anfrage.gm_boolean and not anfrage.is_principle:
        context["sekretariat"] = True
        context["form"] = YesNoForm() if anfrage.trigger else TwoStepForm()
        context["anfangsdatum"] = convert_date(str(antrag.anfangsdatum))
        context["anfangszeit"]  = convert_time(str(antrag.anfangszeit))
        context["enddatum"]     = convert_date(str(antrag.enddatum))
        context["endzeit"]      = convert_time(str(antrag.endzeit))
    return render(request, "antraege/antrag_bearbeiten.html", context)

@login_required(login_url="login")
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

    gm = im = gm_response = im_response = gm_grund = im_grund = None
    schulleiter = schulleiter_response = schulleiter_grund = schulleiter_datum = None

    for anfrage in anfragen:
        if anfrage.gm:  # Wenn es ein GM ist
            gm = Lehrer.objects.filter(email=anfrage.email).values_list('name', flat=True).first() or anfrage.email
            gm_response = anfrage.response
            gm_grund = anfrage.reason
        elif anfrage.im:  # Wenn es ein IM ist
            im = Lehrer.objects.filter(email=anfrage.email).values_list('name', flat=True).first() or anfrage.email
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
                if len(elements) < 2:
                    continue
                daten.append(transform_date(elements[1]))
                fach = Fach.objects.filter(kuerzel=elements[0]).values_list("name", flat=True).first() or elements[0]
                unterricht.append(fach)
                lehrer_name = Lehrer.objects.filter(email=anfrage.email).values_list("name", flat=True).first() or anfrage.email
                lehrer.append(lehrer_name)
                gruende.append(anfrage.reason)
                responses.append(anfrage.response)
    if im:
        lehrer.append(im)
        daten.append(" ")
        unterricht.append("IM")
        responses.append(im_response)
        gruende.append(im_grund)
    if gm:
        lehrer.append(gm)
        daten.append(" ")
        unterricht.append("GM")
        responses.append(gm_response)
        gruende.append(gm_grund)
    if schulleiter:
        lehrer.append(schulleiter)
        responses.append(schulleiter_response)
        gruende.append(schulleiter_grund)
        daten.append(transform_datetime(schulleiter_datum))
        unterricht.append("Schulleiter")

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

@login_required(login_url="login")
@require_POST
def seki_anfordern(request):
    antrag_id = request.POST.get('antrag_id')
    antrag = get_object_or_404(Antrag, id=antrag_id)

    # Ownership check: only the antrag's owner may trigger this
    if antrag.user != request.user:
        raise PermissionDenied

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
    
    with transaction.atomic():
        AntragSubmission.objects.create(user=request.user, antrag=antrag)
        seki_mails = Lehrer.objects.filter(secretariat=True).values_list('email', flat=True)
        for email in seki_mails:
            raw_token, public_token = make_token_pair()
            relative_url = reverse('antrag_bestaetigen', kwargs={'token': public_token})
            absolute_url = request.build_absolute_uri(relative_url)
            if absolute_url.startswith("http://"):
                absolute_url = "https://" + absolute_url[7:]
            Anfrage.objects.create(
                antrag=antrag,
                email=email,
                token=raw_token,
                trigger=True
            )
            transaction.on_commit(
                lambda recipient=email, absolute=absolute_url: send_eltern_bestaetigung(
                    antrag.user.first_name + " " + antrag.user.last_name,
                    absolute,
                    antrag.klasse,
                    antrag.titel,
                    recipient
                )
            )
    return redirect("home")
