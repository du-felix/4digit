from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as lg
from django.contrib import messages
from .forms import Sign_Up_Form

def login(request):

    if request.method == "POST":
        email = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.is_staff:
                lg(request, user)
                messages.success(request, "Login successful!")

                return redirect("adminview-home")  # Redirect to staff dashboard
            else:
                return render(request, "antraege/home.html")  
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "users/login.html")  # Render the login page


def signup(request):
    if request.method == 'POST':
        form = Sign_Up_Form(request.POST)
        if form.is_valid():
            form.save()

            return redirect('login') 
    else:
        form = Sign_Up_Form()
    
    return render(request, 'users/signup.html', {'form': form})
