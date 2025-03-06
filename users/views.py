from django.shortcuts import render, redirect
from .forms import Sign_Up_Form

def login(request):
    return render(request, "users/login.html")

def signup(request):
    if request.method == 'POST':
        form = Sign_Up_Form(request.POST)
        if form.is_valid():
            form.save()

            return redirect('login') 
    else:
        form = Sign_Up_Form()
    
    return render(request, 'users/signup.html', {'form': form})
