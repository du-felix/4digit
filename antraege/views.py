import uuid
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import AntragForm, UnterrichtFormSet
from .models import Anfrage, Antrag
from .functions import send_email, send_email_schulleiter, send_email_gm, send_email_im
from django.utils import timezone

# Create your views here.
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
            
            # Rest of your code for gm and im remains the same
            token = str(uuid.uuid4())
            relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
            absolute_url = request.build_absolute_uri(relative_url)
            Anfrage.objects.create(antrag=antrag_instance, email=gm, token=token)
            send_email_gm(gm, gm.split("@")[0].split(".")[0], gm.split("@")[0].split(".")[1], request.user.first_name, absolute_url)
            
            token = str(uuid.uuid4())
            relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
            absolute_url = request.build_absolute_uri(relative_url)
            Anfrage.objects.create(antrag=antrag_instance, email=im, token=token)
            send_email_im(im, im.split("@")[0].split(".")[0], im.split("@")[0].split(".")[1], request.user.first_name, absolute_url)
            
            messages.success(request, "Antrag erfolgreich erstellt.")
            return redirect("home")
        else:
            messages.error(request, "Es ist ein Fehler aufgetreten.")
            return render(request, "antraege/neuer_antrag.html", {"antrag": antrag, "formset": formset})
    else:
        antrag = AntragForm()
        unterricht_formset = UnterrichtFormSet()
        return render(request, "antraege/neuer_antrag.html", {"antrag": antrag, "unterricht_formset": unterricht_formset})

@login_required(login_url="login")
def user_antraege(request):
    return render(request, "antraege/user_antraege.html")

def antrag_bestaetigen(request, token):
    anfrage = Anfrage.objects.get(token=token)
    antrag = anfrage.antrag
    context = {
        "token": token,
        "antragsteller": antrag.user.first_name + " " + antrag.user.last_name,
        "titel": antrag.titel,
        "schueler_grund": antrag.grund, 
        "unterricht": anfrage.unterricht,
        "schulleiter": anfrage.is_principle,
        "antrag": antrag,
    }
    if request.method == "POST":
        answer = request.POST.get("answer")
        if anfrage.is_principle:
            bestaetigungen = Anfrage.objects.filter(antrag=antrag, is_principle=False)
            context["bestaetigungen"] = bestaetigungen
            return render(request, "antraege/antrag_bearbeiten.html", context)
        elif anfrage.NOT_RESPONDED:
            if answer == "annehmen":
                anfrage.response = Anfrage.ACCEPTED
                anfrage.responded_at = timezone.now()
                anfrage.save()
                mail_bool = True
                anfragen = Anfrage.objects.filter(antrag=antrag)
                for af in anfragen:
                    if af.response == af.NOT_RESPONDED:
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
                grund = request.POST.get("grund",'')
                if not grund.strip():
                    messages.error(request, "Grund fehlt")
                    return render(request, "antraege/antrag_bearbeiten.html", context)
                
                anfrage.response = Anfrage.DECLINED
                anfrage.responded_at = timezone.now()
                anfrage.reason = grund
                anfrage.save()
                mail_bool = True
                anfragen = Anfrage.objects.filter(antrag=antrag)
                for af in anfragen:
                    if af.response == af.NOT_RESPONDED:
                        mail_bool = False
                        break
                if mail_bool:
                    token = str(uuid.uuid4())
                    relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
                    Anfrage.objects.create(antrag=antrag, email="stefan.weih@afra.lernsax.de", token=token, is_principle=True)
                    absolute_url = request.build_absolute_url(relative_url)
                    send_email_schulleiter(antrag.user.first_name + " " + antrag.user.last_name, absolute_url)

                messages.success(request, "Antrag erfolgreich bearbeitet.")
                return redirect("home")
            else:
                messages.error(request, "Kein Feld ausgewählt")
                return render(request, "antraege/antrag_bearbeiten.html", context)
        else:
            messages.error(request, "Anfrage bereits bearbeitet")
            return redirect("home")
    else:
        if anfrage.response != Anfrage.NOT_RESPONDED:
            messages.error(request, "Anfrage bereits bearbeitet")
            return redirect("home")
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
    
    context = {
        'antrag': antrag,
        'anfragen': anfragen,
        'anfragen_status': anfragen_status
    }
    return render(request, 'antraege/antrag.html', context)