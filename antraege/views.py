import uuid
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import AntragForm, UnterrichtFormSet
from .models import Anfrage, Antrag
from .functions import send_email, send_email_schulleiter, send_email_gm, send_email_im
from django.utils import timezone
from django.core.exceptions import ValidationError

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
        gm = request.POST.get("gm")
        im = request.POST.get("im")
        formset = UnterrichtFormSet(request.POST)
        antrag = AntragForm(request.POST)

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
            
            lehrer_dict = {}
            for form in formset:
                if form.cleaned_data:  # Check if form has data
                    email = form.cleaned_data.get("lehrer_email").lower()
                    fach = form.cleaned_data.get("fach")
                    datum = form.cleaned_data.get("datum")
                    
                    if email not in lehrer_dict:
                        lehrer_dict[email] = []
                    
                    lehrer_dict[email].append({
                        "fach": fach,
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
                    request.user.first_name, 
                    unterricht_text, 
                    absolute_url
                )
            try:
                token = str(uuid.uuid4())
                relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
                absolute_url = request.build_absolute_uri(relative_url)
                Anfrage.objects.create(antrag=antrag_instance, email=gm, token=token, gm=gm)
                send_email_gm(gm, gm.split("@")[0].split(".")[0], gm.split("@")[0].split(".")[1], request.user.first_name, absolute_url)
            except Exception as e:
                print(f"Failed to send email to IM {im}: {str(e)}")
                messages.warning(request, f"Fehler beim Senden der E-Mail an GM ({gm}).")
            
            token = str(uuid.uuid4())
            relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
            absolute_url = request.build_absolute_uri(relative_url)
            Anfrage.objects.create(antrag=antrag_instance, email=im, token=token, im=im)
            send_email_im(im, im.split("@")[0].split(".")[0], im.split("@")[0].split(".")[1], request.user.first_name, absolute_url)
            
            messages.success(request, "Antrag erfolgreich erstellt.")
            return redirect("home")
        else:
            messages.error(request, "Es ist ein Fehler aufgetreten.")
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
    }
    
    # If already responded, redirect with message
    if anfrage.response != Anfrage.NOT_RESPONDED and request.method == "GET":
        messages.error(request, "Anfrage bereits bearbeitet")
        return redirect("home")
    
    # Add teacher confirmations to context if principal view
    if anfrage.is_principle:
        bestaetigungen = Anfrage.objects.filter(antrag=antrag, is_principle=False)
        context["bestaetigungen"] = bestaetigungen
    
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
                messages.success(request, "Antrag genehmigt.")
                return redirect("home")
            elif answer == "ablehnen":
                grund = request.POST.get("grund", '')
                if not grund.strip():
                    messages.error(request, "Grund fehlt")
                    return render(request, "antraege/antrag_bearbeiten.html", context)
                
                anfrage.response = Anfrage.DECLINED
                anfrage.responded_at = timezone.now()
                anfrage.reason = grund
                anfrage.save()
                antrag.status = 'declined'
                antrag.save()
                messages.success(request, "Antrag als Schulleiter abgelehnt.")
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
                    Anfrage.objects.create(antrag=antrag, email="stefan.weih@afra.lernsax.de", token=token, is_principle=True)
                    absolute_url = request.build_absolute_uri(relative_url)
                    send_email_schulleiter(antrag.user.first_name + " " + antrag.user.last_name, absolute_url)
                
                messages.success(request, "Antrag erfolgreich bearbeitet.")
                return redirect("home")
                
            elif answer == "ablehnen":
                grund = request.POST.get("grund", '')
                if not grund.strip():
                    messages.error(request, "Grund fehlt")
                    return render(request, "antraege/antrag_bearbeiten.html", context)
                
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
                    Anfrage.objects.create(antrag=antrag, email="stefan.weih@afra.lernsax.de", token=token, is_principle=True)
                    absolute_url = request.build_absolute_uri(relative_url)
                    send_email_schulleiter(antrag.user.first_name + " " + antrag.user.last_name, absolute_url)

                messages.success(request, "Antrag erfolgreich bearbeitet.")
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
    
    gm = None
    im = None
    for anfrage in anfragen:
        if anfrage.gm:  # Wenn es ein GM ist
            gm = anfrage.email
        elif anfrage.im:  # Wenn es ein IM ist
            im = anfrage.email

    context = {
        'antrag': antrag,
        'anfragen': anfragen,
        'anfragen_status': anfragen_status,
        'gm': gm,
        'im': im,

    }
    return render(request, 'antraege/antrag.html', context)