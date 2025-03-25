import uuid
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import AntragForm, UnterrichtFormSet
from .models import Anfrage
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
<<<<<<< HEAD
        "schulleiter": False
=======
>>>>>>> 0495227 (Enhance Antrag handling: update .gitignore, add email notification for school principal, and improve Antrag confirmation view with response handling)
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
<<<<<<< HEAD
                send_email_schulleiter(antrag)

=======
<<<<<<< HEAD
=======
                send_email_schulleiter(antrag)

>>>>>>> 0495227 (Enhance Antrag handling: update .gitignore, add email notification for school principal, and improve Antrag confirmation view with response handling)
>>>>>>> 922f95b (egal)
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
<<<<<<< HEAD
                context["schulleiter"] = send_email_schulleiter(antrag)
=======
                send_email_schulleiter(antrag)
>>>>>>> 0495227 (Enhance Antrag handling: update .gitignore, add email notification for school principal, and improve Antrag confirmation view with response handling)

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