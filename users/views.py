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
<<<<<<< HEAD
<<<<<<< HEAD
                return redirect("adminview-home")  # Redirect to staff dashboard
=======
                return redirect("adminview/home.html")  # Redirect to staff dashboard
>>>>>>> a4e75d4 (added path to adminview)
=======
                return redirect("adminview-home")  # Redirect to staff dashboard
>>>>>>> ba3d368 (admin-login added)
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
    
<<<<<<< HEAD
    return render(request, 'users/signup.html', {'form': form})
=======
    return render(request, 'users/signup.html', {'form': form})
def login_success(request):
    if request.user.is_authenticated:
        if request.user.is_app_admin:
            return redirect ('adminview')
        else:
            return redirect('')
        return redirect('login')
>>>>>>> 57f056b (adminview_first)
