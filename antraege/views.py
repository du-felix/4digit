from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .forms import AntragForm, UnterrichtFormSet
from .models import Antrag, Anfrage

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
                lehrer_dict[email] += unterricht.fach + "," + str(unterricht.datum) + "; "

            Anfrage.objects.bulk_create(
                [Anfrage(antrag=antrag, email=email, unterricht=unterricht) for email, unterricht in lehrer_dict.items()]
            )
            antrag.save()
            return render(request, "antraege/home.html")
    else:
        antrag = AntragForm()
        unterricht_formset = UnterrichtFormSet()
    return render(request, "antraege/neuer_antrag.html", {"antrag": antrag, "unterricht_formset": unterricht_formset})

@login_required(login_url="login")
def user_antraege(request):
    return render(request, "antraege/user_antraege.html")