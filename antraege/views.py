import uuid
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import AntragForm, UnterrichtFormSet
from .models import Anfrage, Antrag, Zaehler, Lehrer, Fach
from .functions import send_email, send_email_schulleiter, send_email_gm, send_email_im, send_email_sekretariat
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum

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
        while False:
            try:
                    validate_afra_email(gm)
                    validate_afra_email(im)
            except ValidationError:
                    messages.error(request, "Nur E-Mail-Adressen mit '@afra.lernsax.de' sind erlaubt.")
                    return render(request, "antraege/neuer_antrag.html", {
                        "antrag": antrag,
                        "unterricht_formset": formset
                })
        if antrag.is_valid() and formset.is_valid():
            antrag_instance = antrag.save(commit=False)
            antrag_instance.user = request.user
            antrag_instance.save()
            gm = antrag.cleaned_data.get("gm").email
            im = antrag.cleaned_data.get("im").email
            
            lehrer_dict = {}
            for form in formset:
                if form.cleaned_data:  # Check if form has data
                    lehrer_id = form.cleaned_data.get("lehrer")
                    fach_id = form.cleaned_data.get("fach")
                    datum = form.cleaned_data.get("datum")
                    email = lehrer_id.email
                    if lehrer_id.email not in lehrer_dict:
                        lehrer_dict[email] = []

                    zaehler, _ = Zaehler.objects.get_or_create(
                        schueler=request.user,
                        lehrer=lehrer_id,
                        fach=fach_id
                    )    
                    zaehler.temp += 1
                    zaehler.save()

                    
                    lehrer_dict[email].append({
                        "fach": fach_id.kuerzel,
                        "datum": datum
                    })
            
            # Process each teacher's entries
            for email, unterricht_list in lehrer_dict.items():
                # Create formatted string for email
                unterricht_text = ""
                for entry in unterricht_list:
                    unterricht_text += f"{entry['fach']},{entry['datum']};\n"
                
                token = str(uuid.uuid4())
                relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
                absolute_url = request.build_absolute_uri(relative_url)
               # absolute_url = absolute_url[:4] + "s" + absolute_url[4:]
                
                Anfrage.objects.create(
                    antrag=antrag_instance,
                    email=email,
                    token=token,
                    unterricht=unterricht_text
                )
                
                send_email(
                    email, 
                    email.split("@")[0].split(".")[0], 
                    email.split("@")[0].split(".")[1], 
                    request.user.first_name+" "+request.user.last_name, 
                    unterricht_text, 
                    absolute_url
                )
            try:
                token = str(uuid.uuid4())
                relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
                absolute_url = request.build_absolute_uri(relative_url)
                #absolute_url = absolute_url[:4] + "s" + absolute_url[4:]

                Anfrage.objects.create(antrag=antrag_instance, email=gm, token=token, gm=gm)
                send_email_gm(gm, gm.split("@")[0].split(".")[0], gm.split("@")[0].split(".")[1], request.user.first_name+" "+request.user.last_name, absolute_url)
            except Exception as e:
                print(f"Failed to send email to IM {im}: {str(e)}")
                messages.warning(request, f"Fehler beim Senden der E-Mail an GM ({gm}).")
            
            token = str(uuid.uuid4())
            relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
            absolute_url = request.build_absolute_uri(relative_url)
            #absolute_url = absolute_url[:4] + "s" + absolute_url[4:]

            Anfrage.objects.create(antrag=antrag_instance, email=im, token=token, im=im)
            send_email_im(im, im.split("@")[0].split(".")[0], im.split("@")[0].split(".")[1], request.user.first_name+" "+request.user.last_name, absolute_url)
            
            messages.success(request, "Antrag erfolgreich erstellt.")
            return redirect("home")
        else:
            # Detaillierte Fehlermeldungen
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
            
            # Füge eine allgemeine Fehlermeldung hinzu, falls keine spezifische gefunden wurde
            if not any(m.level == messages.ERROR for m in messages.get_messages(request)):
                messages.error(request, "Es ist ein Fehler aufgetreten. Bitte überprüfen Sie Ihre Eingaben.")
                
            return render(request, "antraege/neuer_antrag.html", {"antrag": antrag, "unterricht_formset": formset})
    else:
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
        messages.error(request, "Anfrage bereits bearbeitet")
        return redirect("home")
    
    # Add teacher confirmations to context if principal view
    if anfrage.is_principle:
        bestaetigungen = Anfrage.objects.filter(antrag=antrag, is_principle=False)
        context["bestaetigungen"] = bestaetigungen
        context["fehlzeiten"] = Zaehler.objects.filter(schueler=antrag.user).aggregate(Sum("zaehler"))["zaehler__sum"] or 0
    
    # Handle form submission
    if request.method == "POST":
        answer = request.POST.get("answer")
        
        # Principal handling
        if anfrage.is_principle:
            if answer == "annehmen":
                anfrage.response = Anfrage.ACCEPTED
                anfrage.responded_at = timezone.now()
                anfrage.save()
                antrag.status = 'accepted'
                antrag.save()
                bestaetigungen = Anfrage.objects.filter(antrag=antrag, is_principle=False)
                for bestaetigung in bestaetigungen:
                    stunden = bestaetigung.unterricht.strip("\n").split(";")[:-1]
                    for stunde in stunden:
                        print(Fach.objects.get(kuerzel=stunde.split(",")[0].upper()))
                        obj = Zaehler.objects.get(
                            schueler=antrag.user,
                            lehrer=Lehrer.objects.get(email=bestaetigung.email),
                            fach=Fach.objects.get(kuerzel=stunde.split(",")[0].upper())
                        )
                        obj.zaehler += obj.temp
                        obj.temp = 0
                        obj.save()
                send_email_sekretariat(
            antrag.user.first_name + " " + antrag.user.last_name, 
            antrag.klasse,
            antrag.titel,
            antrag.grund,
            antrag
        )
                return redirect("home")
            elif answer == "ablehnen":
                grund = request.POST.get("grund", '')
                bestaetigungen = Anfrage.objects.filter(antrag=antrag, is_principle=False)
                for bestaetigung in bestaetigungen:
                    stunden = bestaetigung.unterricht.strip("\n").split(";")[:-1]
                    print(stunden)
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
                return redirect("home")
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
                    Anfrage.objects.create(antrag=antrag, email=Lehrer.objects.filter(principal=True).values_list('email', flat=True).first(), token=token, is_principle=True)
                    absolute_url = request.build_absolute_uri(relative_url)
                   # absolute_url = absolute_url[:4] + "s" + absolute_url[4:]

                    send_email_schulleiter(antrag.user.first_name + " " + antrag.user.last_name, absolute_url)
                return redirect("home")
                
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
                
                if mail_bool:
                    token = str(uuid.uuid4())
                    relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
                    Anfrage.objects.create(antrag=antrag, email=Lehrer.objects.filter(principal=True).values_list('email', flat=True).first(), token=token, is_principle=True)
                    absolute_url = request.build_absolute_uri(relative_url)
                    #absolute_url = absolute_url[:4] + "s" + absolute_url[4:]

                    send_email_schulleiter(antrag.user.first_name + " " + antrag.user.last_name, absolute_url)
                return redirect("home")
            else:
                messages.error(request, "Kein Feld ausgewählt")
        else:
            messages.error(request, "Anfrage bereits bearbeitet")
            return redirect("home")
    
    # Always render the template with complete context at the end
    return render(request, "antraege/antrag_bearbeiten.html", context)

@login_required
def antrag_detail(request, antrag_id):
    # Hole den spezifischen Antrag oder werfe 404
    antrag = get_object_or_404(Antrag, id=antrag_id, user=request.user)
    
    # Hole alle Anfragen für diesen Antrag
    anfragen = Anfrage.objects.filter(antrag=antrag)
    
    # Bestimme den Gesamtstatus der Anfragen
    anfragen_status = {
        'total': len(anfragen),
        'accepted': anfragen.filter(response=Anfrage.ACCEPTED).count(),
        'declined': anfragen.filter(response=Anfrage.DECLINED).count(),
        'not_responded': anfragen.filter(response=Anfrage.NOT_RESPONDED).count()
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
