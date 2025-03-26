import uuid
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import AntragForm, UnterrichtFormSet
from .models import Anfrage, Antrag
from .functions import send_email, send_email_schulleiter
from django.utils import timezone

# Create your views here.
@login_required(login_url="login")
def home(request):
    return render(request, "antraege/home.html")

@login_required(login_url="login")
def neuer_antrag(request):
    if request.method == "POST":
        gm = request.POST.get("gm")
        im = request.POST.get("im")
        formset = UnterrichtFormSet(request.POST)
        antrag = AntragForm(request.POST)
        if antrag.is_valid() and formset.is_valid():
            antrag = antrag.save(commit=False)
            antrag.user = request.user

            lehrer_dict = {}
            for form in formset:
                unterricht = form.save(commit=False)
                email = unterricht.lehrer_email.lower()
                lehrer_dict[email] += unterricht.fach + "," + str(unterricht.datum) + ";\n"

            for email, unterricht in lehrer_dict.items():
                token = str(uuid.uuid4())
                relative_url = reverse('antrag_bestaetigen', kwargs={'token': token})
                # Build the absolute URL using the request object
                absolute_url = request.build_absolute_uri(relative_url)
                Anfrage.objects.create(antrag=antrag, email=email, token=token, unterricht=unterricht)
                send_email(email, email.split("@")[0].split(".")[0], request.user.first_name, unterricht, absolute_url)

            antrag.save()
            messages.success(request, "Antrag erfolgreich erstellt.")
            return redirect("home")
        else:
            messages.error(request, "Es ist ein Fehler aufgetreten.")
            return render(request, "submit_form.html", {"antrag": antrag, "formset": formset})

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
            pass
        else:
            if answer == "annehmen":
                anfrage.response = Anfrage.ACCEPTED
                anfrage.responded_at = timezone.now()
                anfrage.save()
                send_email_schulleiter(antrag)
                messages.success(request, "Antrag erfolgreich bearbeitet.")
                redirect("home")
            elif answer == "ablehnen":
                grund = request.POST.get("grund",'')
                if not grund.strip():
                    messages.error(request, "Grund fehlt")
                    return render(request, "antraege/antrag_bestaetigen.html", context)
                
                anfrage.response = Anfrage.DECLINED
                anfrage.responded_at = timezone.now()
                anfrage.reason = grund
                anfrage.save()
                send_email_schulleiter(antrag)

                messages.success(request, "Antrag erfolgreich bearbeitet.")
                redirect("home")
            else:
                messages.error(request, "Kein Feld ausgewählt")
                return render(request, "antraege/antrag_bestaetigen.html", context)
    else:
        if anfrage.response != Anfrage.NOT_RESPONDED:
            messages.error(request, "Anfrage bereits bearbeitet")
            return redirect("home")
        return render(request, "antraege/antrag_bestaetigen.html", context)
@login_required
def antraege_liste(request):
    # Hole alle Anträge des aktuellen Benutzers
    antraege = Antrag.objects.filter(user=request.user).order_by('-erstellt_am')
    
    context = {
        'antraege': antraege
    }
    return render(request, 'antraege/antraege_liste.html', context)

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
    return render(request, 'antraege/antrag_detail.html', context)