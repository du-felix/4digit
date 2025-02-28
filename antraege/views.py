from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.
@login_required(login_url="login")
def home(request):
    return render(request, "antraege/home.html")

@login_required(login_url="login")
def neuer_antrag(request):
    return render(request, "antraege/neuer_antrag.html")

@login_required(login_url="login")
def user_antraege(request):
    return render(request, "antraege/user_antraege.html")