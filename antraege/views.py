from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .forms import AntragForm, UnterrichtFormSet

# Create your views here.
@login_required(login_url="login")
def home(request):
    return render(request, "antraege/home.html")

@login_required(login_url="login")
def neuer_antrag(request):
    if request.method == "POST":
        gm = request.POST.get("gm")
        im = request.POST.get("im")
        pass
    else:
        antrag = AntragForm()
        unterricht_formset = UnterrichtFormSet()
    return render(request, "antraege/neuer_antrag.html", {"antrag": antrag, "unterricht_formset": unterricht_formset})

@login_required(login_url="login")
def user_antraege(request):
    return render(request, "antraege/user_antraege.html")