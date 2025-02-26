from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.
@login_required(login_url="login")
def home(request):
    return render(request, "antraege/home.html")

def neuer_antrag(request):
    return render(request, "antraege/neuer_antrag.html")

def user_antraege(request):
    return render(request, "antraege/user_antraege.html")