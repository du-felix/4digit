from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.
@login_required(login_url="login")
def home(request):
    return render(request, "home.html")

def neuer_antrag(request):
    return render(request, "neuer_antrag.html")

def user_antraege(request):
    return render(request, "user_antraege.html")