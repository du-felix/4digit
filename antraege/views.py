import uuid
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import AntragForm, UnterrichtFormSet
from .models import Anfrage
from .functions import send_email

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
    return render(request, "antraege/antrag_bestaetigen.html", {"token": token})